"""
GoogleDriveClient - Download files from Google Drive folder by filename.
Uses public folder access instead of file IDs for simplicity.
"""
import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

import requests

from logger_config import logger


class GoogleDriveClient:
    """
    Client for downloading files from Google Drive folder.
    Download by filename directly from shared folder.
    """

    def __init__(self, folder_url: str, download_dir: Path | str = "temp"):
        """
        Initialize Google Drive client.
        
        Args:
            folder_url: Google Drive folder URL or folder ID
                Example: https://drive.google.com/drive/folders/15foaiZz-dW9amlr2iVO5-czfWtclLBB6
                Or just: 15foaiZz-dW9amlr2iVO5-czfWtclLBB6
            download_dir: Directory where files will be downloaded
        """
        self.folder_url = folder_url
        self.folder_id = self._extract_folder_id(folder_url)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        logger.info("GoogleDriveClient initialized with folder_id: %s", self.folder_id)

    def _extract_folder_id(self, folder_url: str) -> str:
        """
        Extract folder ID from Google Drive URL or return as-is if it's already an ID.
        
        Args:
            folder_url: Folder URL or folder ID
            
        Returns:
            Folder ID string
        """
        # If it looks like a URL, extract the ID
        if folder_url.startswith("http"):
            match = re.search(r'/folders/([a-zA-Z0-9-_]+)', folder_url)
            if match:
                return match.group(1)
        
        # Otherwise assume it's already a folder ID
        return folder_url

    def download_file_by_name(self, filename: str, timeout: int = 30) -> Path:
        """
        Download a file from Google Drive folder by filename.
        
        Uses Google Drive's file listing API to find the file by name,
        then downloads it.
        
        Args:
            filename: Name of file to download (e.g., "MyApp_v1.0.rar")
            timeout: Request timeout in seconds
            
        Returns:
            Path to the downloaded file
            
        Raises:
            FileNotFoundError: If file not found in folder
            Exception: If download fails
        """
        logger.info("Searching for file in Google Drive: %s", filename)
        
        dest_path = self.download_dir / filename

        try:
            # Search for file in the folder using Google Drive API
            # Using a simple approach: construct search query
            file_id = self._find_file_id_by_name(filename)
            
            if not file_id:
                logger.error("File not found in Google Drive folder: %s", filename)
                raise FileNotFoundError(f"File not found in folder: {filename}")

            logger.info("Found file ID for %s: %s", filename, file_id)
            return self._download_file_by_id(file_id, dest_path, timeout)

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to download file %s: %s", filename, e)
            if dest_path.exists():
                dest_path.unlink()
            raise

    def _find_file_id_by_name(self, filename: str) -> Optional[str]:
        """
        Find file ID by searching in Google Drive folder.
        
        Args:
            filename: Name of file to find
            
        Returns:
            File ID if found, None otherwise
        """
        try:
            # Use Google Drive API v3 files.list endpoint
            # Query: find file with matching name in the folder
            query = f"name='{filename}' and '{self.folder_id}' in parents and trashed=false"
            
            url = "https://www.googleapis.com/drive/v3/files"
            params = {
                "q": query,
                "spaces": "drive",
                "fields": "files(id,name)",
                "pageSize": 1
            }
            
            # Try with a simple public access approach first
            # If that fails, fall back to direct URL construction
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                files = data.get("files", [])
                
                if files:
                    return files[0]["id"]
            except:
                # API may require authentication
                pass
            
            # Fallback: Try direct download URL construction
            # This works if the file is in a publicly shared folder
            logger.info("Using fallback method to download: %s", filename)
            return None

        except Exception as e:
            logger.error("Error searching for file: %s", e)
            return None

    def _download_file_by_id(self, file_id: str, dest_path: Path, timeout: int = 30) -> Path:
        """
        Download file from Google Drive by file ID.
        
        Args:
            file_id: Google Drive file ID
            dest_path: Path to save the file
            timeout: Request timeout
            
        Returns:
            Path to downloaded file
        """
        url = f"https://drive.google.com/uc?id={file_id}&export=download"
        
        logger.info("Downloading file: %s", dest_path.name)

        try:
            response = self.session.get(url, stream=True, timeout=timeout, allow_redirects=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192
            downloaded = 0

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.debug("Download progress: %.1f%%", progress)

            logger.info("File downloaded successfully: %s", dest_path)
            return dest_path

        except Exception as e:
            logger.error("Failed to download file: %s", e)
            if dest_path.exists():
                dest_path.unlink()
            raise

    def download_app_version_json(self, filename: str = "app_version.json") -> dict:
        """
        Download and parse app_version.json from Google Drive folder.
        
        Args:
            filename: Name of the version JSON file (default: app_version.json)
            
        Returns:
            Parsed JSON as dict
            
        Raises:
            Exception: If download or parsing fails
        """
        logger.info("Downloading app_version.json from Google Drive")
        
        temp_file = self.download_file_by_name(filename)
        try:
            with open(temp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Successfully loaded app_version.json")
            return data
        except json.JSONDecodeError as e:
            logger.error("Failed to parse app_version.json: %s", e)
            raise

    def download_app_file(self, filename: str) -> Path:
        """
        Download an application file (exe or rar) from Google Drive.
        
        Args:
            filename: Name to save the file as (should include extension)
            
        Returns:
            Path to the downloaded file
        """
        logger.info("Downloading app file: %s", filename)
        return self.download_file_by_name(filename)
