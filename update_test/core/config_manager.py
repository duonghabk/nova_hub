# core/config_manager.py
import json
from pathlib import Path


class AppConfigManager:
    """
    Load and manage local app configuration from appconfig.json.
    """

    def __init__(self, config_path: str = "config/appconfig.json"):
        self.config_path = Path(config_path)
        self._config = {}

    def load(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            self._config = json.load(f)

    @property
    def apps(self) -> list[dict]:
        """Return a list of app definitions from config."""
        return self._config.get("apps", [])

    def get_app(self, app_id: str) -> dict | None:
        """Find app config by its id."""
        for app in self.apps:
            if app.get("id") == app_id:
                return app
        return None
