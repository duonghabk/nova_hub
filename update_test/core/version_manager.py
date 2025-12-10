# core/version_manager.py
import json
from pathlib import Path
from typing import Optional

from .drive_client import DriveClient


class VersionManager:
    """
    Load remote app version information from app_version.json in a Drive folder.
    app_version.json does NOT contain URLs, only id/version/sha256/file_type.
    """

    def __init__(self, drive_client: DriveClient, version_filename: str = "app_version.json"):
        self.drive_client = drive_client
        self.version_filename = version_filename
        self._versions: dict = {}

    def fetch_versions(self) -> None:
        """
        Download app_version.json from the Drive folder and parse it.
        """
        version_path: Path = self.drive_client.download_file_by_name(
            self.version_filename, local_filename=self.version_filename
        )
        with version_path.open("r", encoding="utf-8") as f:
            self._versions = json.load(f)

    def get_app_version_info(self, app_id: str) -> Optional[dict]:
        """
        Return version info for given app_id from app_version.json.
        """
        apps = self._versions.get("apps", [])
        for app in apps:
            if app.get("id") == app_id:
                return app
        return None

    @staticmethod
    def get_remote_filename(app_info: dict) -> str:
        """
        Determine the file name in Drive used to store the app.
        By default: "<id>.<file_type>"

        You can support override:
          if app_info has "file_name" -> use it.
        """
        if "file_name" in app_info:
            return app_info["file_name"]

        app_id = app_info["id"]
        file_type = app_info["file_type"].lower()
        return f"{app_id}.{file_type}"
