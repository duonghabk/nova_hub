"""
AppConfigManager - Load and manage local app configuration.
Reads from config/appconfig.json to get list of installed apps with their versions.
"""
import json
from pathlib import Path
from typing import Optional

from logger_config import logger


class AppConfigManager:
    """
    Manages local application configuration.
    Loads appconfig.json which contains info about locally installed apps.
    """

    def __init__(self, config_path: Path | str = "config/appconfig.json"):
        """
        Initialize with path to appconfig.json.
        
        Args:
            config_path: Path to config/appconfig.json
        """
        self.config_path = Path(config_path)
        self.apps_config: list[dict] = []
        self.load()

    def load(self) -> None:
        """
        Load appconfig.json and parse the apps list.
        Raises FileNotFoundError if config doesn't exist.
        """
        if not self.config_path.exists():
            logger.error("Config file not found: %s", self.config_path)
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.apps_config = data.get("apps", [])
            logger.info("Loaded %d apps from config: %s", len(self.apps_config), self.config_path)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse config JSON: %s", e)
            raise

    def get_app_by_id(self, app_id: str) -> Optional[dict]:
        """
        Get app config by ID.
        
        Args:
            app_id: The app ID to search for
            
        Returns:
            App config dict, or None if not found
        """
        for app in self.apps_config:
            if app.get("id") == app_id:
                return app
        return None

    def get_all_apps(self) -> list[dict]:
        """
        Get all apps from config.
        
        Returns:
            List of app config dicts
        """
        return self.apps_config

    def get_app_version(self, app_id: str) -> Optional[str]:
        """
        Get the version of a local app from appconfig.json.
        
        Args:
            app_id: The app ID
            
        Returns:
            Version string, or None if not found in config
        """
        app = self.get_app_by_id(app_id)
        return app.get("version") if app else None

    def reload(self) -> None:
        """
        Reload the config from disk.
        """
        self.load()
