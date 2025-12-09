"""
VersionManager - Manage remote app versions from Google Drive.
Loads app_version.json and provides version comparison utilities.
"""
import json
from pathlib import Path
from typing import Optional

from logger_config import logger
from .drive_client import GoogleDriveClient


class VersionManager:
    """
    Manages remote app version information.
    Loads app_version.json from Google Drive and provides version comparison.
    """

    def __init__(self, drive_client: GoogleDriveClient):
        """
        Initialize VersionManager.
        
        Args:
            drive_client: GoogleDriveClient instance for downloading files
        """
        self.drive_client = drive_client
        self.versions_data: dict = {}
        self.apps_versions: list[dict] = []
        logger.info("VersionManager initialized")

    def fetch_versions(self, filename: str = "app_version.json") -> dict:
        """
        Download and load app_version.json from Google Drive.
        
        Args:
            filename: Name of the version JSON file (default: app_version.json)
            
        Returns:
            Parsed app_version.json as dict
            
        Raises:
            Exception: If download or parsing fails
        """
        logger.info("Fetching app versions from Google Drive: %s", filename)
        try:
            self.versions_data = self.drive_client.download_app_version_json(filename)
            self.apps_versions = self.versions_data.get("apps", [])
            logger.info("Fetched version info for %d apps", len(self.apps_versions))
            return self.versions_data
        except Exception as e:
            logger.error("Failed to fetch versions: %s", e)
            raise

    def get_app_version_info(self, app_id: str) -> Optional[dict]:
        """
        Get version information for a specific app.
        
        Args:
            app_id: The app ID to search for
            
        Returns:
            App version info dict with keys: id, name, version, file_type, filename, sha256
            or None if not found
        """
        for app in self.apps_versions:
            if app.get("id") == app_id:
                return app
        logger.warning("Version info not found for app: %s", app_id)
        return None

    def get_all_apps_versions(self) -> list[dict]:
        """
        Get version information for all apps.
        
        Returns:
            List of app version info dicts
        """
        return self.apps_versions

    def compare_versions(self, local_version: str, remote_version: str) -> int:
        """
        Compare two version strings (semantic versioning).
        
        Args:
            local_version: Local version string (e.g., "1.0.0")
            remote_version: Remote version string (e.g., "1.1.0")
            
        Returns:
            -1 if local < remote (update available)
             0 if local == remote (same version)
             1 if local > remote (local is newer)
        """
        def parse_version(version_str: str) -> tuple:
            """Parse semantic version string to tuple of integers."""
            try:
                parts = version_str.split(".")
                return tuple(int(p) for p in parts[:3])  # Major.Minor.Patch
            except (ValueError, AttributeError):
                logger.warning("Could not parse version: %s", version_str)
                return (0, 0, 0)

        local = parse_version(local_version)
        remote = parse_version(remote_version)

        if local < remote:
            return -1  # Update available
        elif local > remote:
            return 1   # Local is newer
        else:
            return 0   # Same version

    def is_update_available(self, app_id: str, local_version: str) -> bool:
        """
        Check if an update is available for the given app.
        
        Args:
            app_id: The app ID
            local_version: Current local version
            
        Returns:
            True if update is available (remote > local)
        """
        remote_info = self.get_app_version_info(app_id)
        if not remote_info:
            logger.warning("No remote version info found for: %s", app_id)
            return False

        remote_version = remote_info.get("version", "0.0.0")
        result = self.compare_versions(local_version, remote_version)
        
        if result == -1:
            logger.info(
                "Update available for %s: %s -> %s",
                app_id, local_version, remote_version
            )
            return True
        else:
            logger.info("No update needed for %s (local: %s, remote: %s)", 
                       app_id, local_version, remote_version)
            return False
