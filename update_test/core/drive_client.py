# core/drive_client.py
import re
from pathlib import Path
from typing import Optional

import requests


class DriveClient:
    """
    Simple client for Google Drive folder using API key.
    - You give it: api_key + folder_url (or folder_id)
    - It can: find file_id by name inside that folder
             and download file content by name.
    """

    DRIVE_LIST_URL = "https://www.googleapis.com/drive/v3/files"
    DRIVE_DOWNLOAD_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"

    def __init__(self, api_key: str, folder_url: str, download_dir: str = "temp"):
        self.api_key = api_key
        self.folder_id = self._extract_folder_id(folder_url)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _extract_folder_id(folder_url: str) -> str:
        """
        Extract folder_id from a Google Drive folder URL.
        Example: https://drive.google.com/drive/folders/<FOLDER_ID>?usp=sharing
        """
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", folder_url)
        if not m:
            # In case user passes folder_id directly
            return folder_url
        return m.group(1)

    def _find_file_id_by_name(self, filename: str) -> Optional[str]:
        """
        Use Drive API to find file id by name inside the given folder.
        Requires the folder to be shared as 'Anyone with the link'.
        """
        print(f"Searching for file '{filename}' in folder '{self.folder_id}'")
        params = {
            "q": f"name='{filename}' and '{self.folder_id}' in parents and trashed=false",
            "key": self.api_key,
            "fields": "files(id, name)",
            "pageSize": 10,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        resp = requests.get(self.DRIVE_LIST_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        files = data.get("files", [])
        print(files)
        if not files:
            return None
        # Assume the first match is what we want
        return files[0]["id"]

    def download_file_by_name(self, filename: str, local_filename: str | None = None) -> Path:
        """
        Find a file by name inside the folder, then download it.
        :param filename: name in Google Drive (e.g. app_version.json, app1.rar)
        :param local_filename: local name to save as (default = same as filename)
        :return: Path to downloaded file.
        """
        print(f"Downloading file '{filename}' from folder '{self.folder_id}'")
        file_id = self._find_file_id_by_name(filename)
        if not file_id:
            raise FileNotFoundError(f"File '{filename}' not found in Google Drive folder")

        if local_filename is None:
            local_filename = filename

        dest_path = self.download_dir / local_filename

        params = {
            "alt": "media",
            "key": self.api_key,
        }
        url = self.DRIVE_DOWNLOAD_URL.format(file_id=file_id)

        resp = requests.get(url, params=params, stream=True, timeout=60)
        resp.raise_for_status()

        with dest_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return dest_path
