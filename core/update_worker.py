# core/update_worker.py
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .version_manager import VersionManager
from .drive_client import DriveClient
from .file_utils import extract_rar, run_exe, delete_file_if_exists, delete_dir_if_exists
from .logger_config import logger


class UpdateWorker(QObject):
    """
    Worker runs in a QThread:
    - Deletes old installer (.exe) / old .rar file.
    - Deletes old app folder (if it's a .rar update).
    - Downloads the new version (with progress).
    - Extracts or runs the installer.
    """

    progress = Signal(int)          # 0..100
    status = Signal(str)            # text status
    finished = Signal(str, bool)    # (message, success)

    def __init__(
        self,
        app_config: dict,
        remote_info: dict,
        drive_client: DriveClient,
        version_manager: VersionManager,
        parent=None,
    ):
        super().__init__(parent)
        self.app_config = app_config
        self.remote_info = remote_info
        self.drive_client = drive_client
        self.version_manager = version_manager

    def run(self):
        try:
            app_name = self.app_config["name"]
            logger.info("Starting update for: %s", app_name)

            # Determine base 'apps' directory relative to this file's location
            base_dir = Path(__file__).resolve().parent.parent
            apps_dir = base_dir / "apps"
            apps_dir.mkdir(exist_ok=True)  # Ensure 'apps' directory exists

            file_type = self.remote_info["file_type"].lower()

            # 1) Determine remote filename and local destination path
            filename = self.version_manager.get_remote_filename(self.remote_info)
            dest_path = self.drive_client.download_dir / filename
            logger.debug("Remote filename: %s, Destination: %s", filename, dest_path)
            
            # 2) Delete old installer / .rar file if it exists
            self.status.emit(f"[{app_name}] Cleaning up old files...")
            self.progress.emit(5)
            delete_file_if_exists(dest_path)
            
            # 3) If it's a RAR update, delete the old app directory
            if file_type == "rar":
                local_path_pattern = self.app_config.get("local_path")
                if local_path_pattern:
                    # The directory pattern is the parent of the exe pattern, e.g., "AppName_v*"
                    dir_pattern = str(Path(local_path_pattern).parent)
                    if dir_pattern and dir_pattern != '.':
                        # Construct the full search pattern inside the 'apps' directory
                        full_search_pattern = str(apps_dir / dir_pattern)
                        logger.info("Deleting old app directory matching: %s", full_search_pattern)
                        self.status.emit(f"[{app_name}] Deleting old app folder...")
                        delete_dir_if_exists(full_search_pattern)
                    else:
                        logger.warning("Could not determine directory pattern from local_path: %s", local_path_pattern)
            
            # 4) Download the new file
            self.status.emit(f"[{app_name}] Downloading {filename}...")
            logger.info("Downloading new version: %s", filename)
            downloaded_path = self._download_with_progress(
                file_id=None,
                filename=filename,
                dest_path=dest_path,
                start=10,
                end=85
            )

            # 5) Extract or run the installer
            if file_type == "rar":
                self.status.emit(f"[{app_name}] Extracting files...")
                logger.info("Extracting %s to %s", downloaded_path, apps_dir)
                self.progress.emit(90)
                extract_rar(downloaded_path, apps_dir)
                delete_file_if_exists(downloaded_path)
                self.progress.emit(100)
                self.finished.emit(f"App {app_name} updated successfully.", True)
            
            elif file_type == "exe":
                self.status.emit(f"[{app_name}] Starting installer...")
                logger.info("Running installer: %s", downloaded_path)
                self.progress.emit(90)
                run_exe(downloaded_path)
                self.progress.emit(100)
                self.finished.emit(f"Installer for {app_name} has been started.", True)
            else:
                logger.error("Unknown file type for %s: %s", app_name, file_type)
                self.finished.emit(f"Unknown file type for {app_name}: {file_type}", False)

        except Exception as e:
            app_name = self.app_config.get('name', 'Unknown App')
            logger.exception("Error updating %s", app_name)
            error_message = f"Error updating {app_name}: {str(e)[:250]}"
            self.finished.emit(error_message, False)

    def _download_with_progress(
            self,
            file_id: str | None,
            filename: str,
            dest_path: Path,
            start: int = 0,
            end: int = 100,
    ) -> Path:
        if file_id is None:
            file_id = self.drive_client._find_file_id_by_name(filename)
        if not file_id:
            raise FileNotFoundError(f"File '{filename}' not found in Drive folder")

        url = self.drive_client.DRIVE_DOWNLOAD_URL.format(file_id=file_id)
        params = {"alt": "media", "key": self.drive_client.api_key}

        # Use a larger chunk size for better performance on large files
        chunk_size = 1024 * 1024  # 1 MB

        with self.drive_client.session.get(url, params=params, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", "0") or 0)
            total_mb = total / (1024 * 1024) if total else None

            downloaded = 0
            with dest_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)

                    downloaded += len(chunk)
                    downloaded_mb = downloaded / (1024 * 1024)

                    if total_mb:
                        self.status.emit(f"Downloading {filename}: {downloaded_mb:.2f} MB / {total_mb:.2f} MB")
                        frac = downloaded / total
                        value = int(start + (end - start) * frac)
                        self.progress.emit(value)
                    else:
                        self.status.emit(f"Downloading {filename}: {downloaded_mb:.2f} MB")
                        self.progress.emit(int(start + (end - start) * 0.5))

            self.progress.emit(end)
        return dest_path
