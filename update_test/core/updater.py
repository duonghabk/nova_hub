# core/updater.py
from pathlib import Path

from .version_manager import VersionManager
from .drive_client import DriveClient
from .file_utils import calculate_sha256, extract_rar, run_exe


class AppUpdater:
    """
    Handle update process for a single app, using:
    - VersionManager to know app info
    - DriveClient to download file by name from folder
    """

    def __init__(self, version_manager: VersionManager, drive_client: DriveClient):
        self.version_manager = version_manager
        self.drive_client = drive_client

    def is_update_needed(self, local_path: str, remote_sha256: str) -> bool:
        """
        Compare local file hash with remote sha256.
        """
        local_hash = calculate_sha256(local_path)
        return local_hash.lower() != (remote_sha256 or "").lower()

    def update_app(self, app_config: dict, remote_info: dict) -> str:
        """
        Perform update for the given app.
        Steps:
        - Compute remote filename (id.file_type)
        - Download file by name from Drive folder
        - If rar -> extract to app folder
        - If exe -> run installer
        """
        local_path = Path(app_config["local_path"])

        # Determine remote file name in Drive folder
        file_name = self.version_manager.get_remote_filename(remote_info)

        # Download file from Drive folder into temp
        downloaded_path: Path = self.drive_client.download_file_by_name(
            filename=file_name,
            local_filename=file_name,
        )

        file_type = remote_info["file_type"].lower()

        if file_type == "rar":
            extract_rar(downloaded_path, local_path.parent)
            return f"App {app_config['name']} updated (RAR extracted)."

        if file_type == "exe":
            run_exe(downloaded_path)
            return f"Installer started for {app_config['name']}."

        return f"Unknown file type for {app_config['name']}: {file_type}"
