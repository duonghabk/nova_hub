"""
AppUpdater - Main updater logic.
Handles version checking, downloading, extracting, and installing apps.
"""
import shutil
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from logger_config import logger
from .config_manager import AppConfigManager
from .drive_client import GoogleDriveClient
from .file_utils import (
    calculate_sha256,
    extract_rar,
    run_exe_installer,
    verify_file_integrity,
    remove_file,
    remove_directory,
)
from .version_manager import VersionManager


class UpdateStatus(Enum):
    """Status of an update operation."""
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    EXTRACTING = "extracting"
    INSTALLING = "installing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class AppUpdater:
    """
    Main updater class that orchestrates the update process.
    Checks versions, downloads, verifies integrity, extracts, and installs apps.
    """

    def __init__(
        self,
        config_manager: AppConfigManager,
        version_manager: VersionManager,
        drive_client: GoogleDriveClient,
        apps_dir: Path | str = "apps",
        temp_dir: Path | str = "temp"
    ):
        """
        Initialize AppUpdater.
        
        Args:
            config_manager: AppConfigManager instance
            version_manager: VersionManager instance
            drive_client: GoogleDriveClient instance
            apps_dir: Directory where apps are installed
            temp_dir: Temporary directory for downloads
        """
        self.config_manager = config_manager
        self.version_manager = version_manager
        self.drive_client = drive_client
        self.apps_dir = Path(apps_dir)
        self.temp_dir = Path(temp_dir)
        self.current_status = UpdateStatus.IDLE
        self.status_callback: Optional[Callable] = None
        self.progress_callback: Optional[Callable] = None

        self.apps_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        logger.info("AppUpdater initialized with apps_dir: %s, temp_dir: %s",
                   self.apps_dir, self.temp_dir)

    def set_status_callback(self, callback: Callable[[UpdateStatus, str], None]) -> None:
        """
        Set callback for status updates.
        Callback signature: callback(status: UpdateStatus, message: str)
        
        Args:
            callback: Function to call on status change
        """
        self.status_callback = callback

    def set_progress_callback(self, callback: Callable[[int], None]) -> None:
        """
        Set callback for progress updates.
        Callback signature: callback(progress_percent: int)
        
        Args:
            callback: Function to call on progress update
        """
        self.progress_callback = callback

    def _update_status(self, status: UpdateStatus, message: str = "") -> None:
        """
        Update current status and call callback if set.
        
        Args:
            status: New status
            message: Optional status message
        """
        self.current_status = status
        logger.info("Update status: %s - %s", status.value, message)
        if self.status_callback:
            self.status_callback(status, message)

    def _update_progress(self, progress_percent: int) -> None:
        """
        Update progress and call callback if set.
        
        Args:
            progress_percent: Progress percentage (0-100)
        """
        if self.progress_callback:
            self.progress_callback(progress_percent)

    def check_updates(self) -> dict[str, dict]:
        """
        Check for available updates for all apps.
        
        Returns:
            Dict mapping app_id to update info:
            {
                "app_id": {
                    "local_version": "1.0.0",
                    "remote_version": "1.1.0",
                    "has_update": True,
                    "file_type": "rar",
                    "sha256": "abc123...",
                    "file_id": "xyz789..."
                }
            }
        """
        self._update_status(UpdateStatus.CHECKING, "Checking for updates...")
        updates_available = {}

        local_apps = self.config_manager.get_all_apps()
        logger.info("Checking updates for %d local apps", len(local_apps))

        for app in local_apps:
            app_id = app.get("id")
            local_version = app.get("version", "0.0.0")

            remote_info = self.version_manager.get_app_version_info(app_id)
            if not remote_info:
                logger.debug("No remote version info found for: %s", app_id)
                continue

            remote_version = remote_info.get("version", "0.0.0")
            has_update = self.version_manager.is_update_available(app_id, local_version)

            updates_available[app_id] = {
                "local_version": local_version,
                "remote_version": remote_version,
                "has_update": has_update,
                "file_type": remote_info.get("file_type", "unknown"),
                "sha256": remote_info.get("sha256", ""),
                "filename": remote_info.get("filename", f"{app_id}.{remote_info.get('file_type')}")
            }

        self._update_status(UpdateStatus.IDLE, f"Found {len([u for u in updates_available.values() if u['has_update']])} updates")
        return updates_available

    def update_app(self, app_id: str) -> bool:
        """
        Download, verify, extract/install an app.
        
        Args:
            app_id: The app ID to update
            
        Returns:
            True if update succeeded, False otherwise
        """
        logger.info("Starting update for app: %s", app_id)
        self._update_status(UpdateStatus.CHECKING, f"Checking {app_id}...")

        try:
            # Get remote app info
            remote_info = self.version_manager.get_app_version_info(app_id)
            if not remote_info:
                self._update_status(UpdateStatus.ERROR, f"No remote info for {app_id}")
                logger.error("No remote version info for: %s", app_id)
                return False

            filename = remote_info.get("filename", f"{app_id}.{remote_info.get('file_type')}")
            expected_sha256 = remote_info.get("sha256", "")
            file_type = remote_info.get("file_type", "unknown").lower()

            # Download file
            self._update_status(UpdateStatus.DOWNLOADING, f"Downloading {filename}...")
            logger.info("Downloading file: %s", filename)

            try:
                downloaded_path = self.drive_client.download_app_file(filename)
                self._update_progress(50)
            except Exception as e:
                self._update_status(UpdateStatus.ERROR, f"Download failed: {e}")
                logger.error("Download failed for %s: %s", app_id, e)
                return False

            # Verify integrity
            self._update_status(UpdateStatus.VERIFYING, "Verifying file integrity...")
            logger.info("Verifying file integrity for: %s", filename)

            if expected_sha256:
                if not verify_file_integrity(downloaded_path, expected_sha256):
                    self._update_status(UpdateStatus.ERROR, "File integrity check failed")
                    remove_file(downloaded_path)
                    logger.error("File integrity check failed for: %s", filename)
                    return False
                logger.info("File integrity verified")
            else:
                logger.warning("No SHA256 hash available to verify")

            self._update_progress(70)

            # Process based on file type
            if file_type == "rar":
                return self._process_rar_update(app_id, downloaded_path)
            elif file_type == "exe":
                return self._process_exe_update(app_id, downloaded_path)
            else:
                self._update_status(UpdateStatus.ERROR, f"Unsupported file type: {file_type}")
                logger.error("Unsupported file type: %s", file_type)
                remove_file(downloaded_path)
                return False

        except Exception as e:
            self._update_status(UpdateStatus.ERROR, f"Update failed: {e}")
            logger.exception("Exception during update: %s", e)
            return False

    def _process_rar_update(self, app_id: str, rar_path: Path) -> bool:
        """
        Process RAR file update.
        
        Args:
            app_id: App ID
            rar_path: Path to the .rar file
            
        Returns:
            True if successful
        """
        self._update_status(UpdateStatus.EXTRACTING, f"Extracting {rar_path.name}...")
        logger.info("Processing RAR update for: %s", app_id)

        try:
            # Create app directory if it doesn't exist
            app_dir = self.apps_dir / app_id
            app_dir.mkdir(parents=True, exist_ok=True)

            # Extract to app directory
            extract_rar(rar_path, app_dir)
            logger.info("RAR extracted to: %s", app_dir)

            self._update_progress(90)

            # Clean up downloaded file
            remove_file(rar_path)

            # Update local config with new version
            self._update_local_version(app_id)

            self._update_progress(100)
            self._update_status(UpdateStatus.COMPLETED, f"{app_id} updated successfully")
            logger.info("RAR update completed for: %s", app_id)
            return True

        except Exception as e:
            self._update_status(UpdateStatus.ERROR, f"Extraction failed: {e}")
            logger.error("Failed to process RAR update: %s", e)
            remove_file(rar_path)
            return False

    def _process_exe_update(self, app_id: str, exe_path: Path) -> bool:
        """
        Process EXE installer update.
        
        Args:
            app_id: App ID
            exe_path: Path to the .exe file
            
        Returns:
            True if installer launched (note: actual installation result can't be determined)
        """
        self._update_status(UpdateStatus.INSTALLING, f"Running installer for {app_id}...")
        logger.info("Processing EXE update for: %s", app_id)

        try:
            # Run the installer
            process = run_exe_installer(exe_path)
            logger.info("Installer launched with PID: %d", process.pid)

            # Note: We can't wait for the installer to complete without blocking
            # The UI will handle this asynchronously

            self._update_progress(100)
            self._update_status(UpdateStatus.COMPLETED,
                               f"{app_id} installer launched. Please complete the installation.")
            logger.info("EXE installer launched for: %s", app_id)

            # Clean up the exe after a delay (in production, use a separate cleanup thread)
            # For now, we'll leave it for the user to clean up
            return True

        except Exception as e:
            self._update_status(UpdateStatus.ERROR, f"Failed to launch installer: {e}")
            logger.error("Failed to launch EXE installer: %s", e)
            remove_file(exe_path)
            return False

    def _update_local_version(self, app_id: str) -> None:
        """
        Update the local app's version in config.
        
        Args:
            app_id: App ID
        """
        remote_info = self.version_manager.get_app_version_info(app_id)
        if not remote_info:
            return

        remote_version = remote_info.get("version", "0.0.0")
        app = self.config_manager.get_app_by_id(app_id)
        if app:
            app["version"] = remote_version
            logger.info("Updated local version for %s to %s", app_id, remote_version)

    def cancel_update(self) -> None:
        """
        Cancel current update operation.
        """
        self._update_status(UpdateStatus.CANCELLED, "Update cancelled by user")
        logger.info("Update cancelled")
