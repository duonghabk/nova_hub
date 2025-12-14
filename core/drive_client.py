# core/drive_client.py
import re
from pathlib import Path
from typing import Optional

import requests


class DriveClient:
    """
    Client for working with a Google Drive folder (API key).
    """

    DRIVE_LIST_URL = "https://www.googleapis.com/drive/v3/files"
    DRIVE_DOWNLOAD_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"

    def __init__(self, api_key: str, folder_url: str, download_dir: str = "apps"):
        self.api_key = api_key
        self.folder_id = self._extract_folder_id(folder_url)

        # Ensure download_dir is an absolute path relative to the project root
        # Assumes this file is in <project_root>/core/
        base_dir = Path(__file__).resolve().parent.parent
        self.download_dir = base_dir / download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Session to be reused for multiple requests
        self.session = requests.Session()

    @staticmethod
    def _extract_folder_id(folder_url: str) -> str:
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", folder_url)
        if not m:
            return folder_url
        return m.group(1)

    def _find_file_id_by_name(self, filename: str) -> Optional[str]:
        params = {
            "q": f"name='{filename}' and '{self.folder_id}' in parents and trashed=false",
            "key": self.api_key,
            "fields": "files(id, name)",
            "pageSize": 10,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        resp = self.session.get(self.DRIVE_LIST_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        files = data.get("files", [])
        if not files:
            return None
        return files[0]["id"]

    def download_file_by_name(self, filename: str, local_filename: str | None = None) -> Path:
        """
        Used for "quick" jobs (like downloading app_version.json).
        The app update worker uses a separate method for detailed progress.
        """
        file_id = self._find_file_id_by_name(filename)
        if not file_id:
            raise FileNotFoundError(
                f"File '{filename}' not found in Google Drive folder {self.folder_id}"
            )

        if local_filename is None:
            local_filename = filename

        dest_path = self.download_dir / local_filename

        params = {"alt": "media", "key": self.api_key}
        url = self.DRIVE_DOWNLOAD_URL.format(file_id=file_id)

        resp = self.session.get(url, params=params, stream=True, timeout=60)
        resp.raise_for_status()

        with dest_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return dest_path
