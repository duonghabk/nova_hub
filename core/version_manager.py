# core/version_manager.py
import json
from pathlib import Path
from typing import Optional

from .drive_client import DriveClient


class VersionManager:
    """
    Load app_version.json từ folder Drive.
    app_version.json chứa id, version, file_type, filename/file_name.
    """

    def __init__(self, drive_client: DriveClient, version_filename: str = "app_version.json"):
        self.drive_client = drive_client
        self.version_filename = version_filename
        self._versions: dict = {}

    def fetch_versions(self) -> None:
        version_path: Path = self.drive_client.download_file_by_name(
            self.version_filename, local_filename=self.version_filename
        )
        with version_path.open("r", encoding="utf-8") as f:
            self._versions = json.load(f)

    def get_app_version_info(self, app_id: str) -> Optional[dict]:
        apps = self._versions.get("apps", [])
        for app in apps:
            if app.get("id") == app_id:
                return app
        return None

    @staticmethod
    def get_remote_filename(app_info: dict) -> str:
        """
        Ưu tiên dùng field 'filename', sau đó 'file_name'.
        Nếu không có, fallback: <id>.<file_type>
        """
        if "filename" in app_info:
            return app_info["filename"]
        app_id = app_info["id"]
        file_type = app_info["file_type"].lower()
        return f"{app_id}.{file_type}"

    @staticmethod
    def is_update_needed(local_version: str, remote_version: str) -> bool:
        # đơn giản: khác string là update, bạn có thể thêm parse version nếu muốn
        return (local_version or "").strip() != (remote_version or "").strip()
