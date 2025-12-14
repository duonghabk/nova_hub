# core/config_manager.py
import json
from pathlib import Path


class AppConfigManager:
    def __init__(self, config_path: str = "config/appconfig.json"):
        self.config_path = Path(config_path)
        self._config = {}

    def load(self) -> None:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as f:
            self._config = json.load(f)

    @property
    def apps(self) -> list[dict]:
        return self._config.get("apps", [])

    def get_app(self, app_id: str) -> dict | None:
        for app in self.apps:
            if app.get("id") == app_id:
                return app
        return None

    def update_local_version(self, app_id: str, new_version: str) -> None:
        for app in self._config.get("apps", []):
            if app["id"] == app_id:
                app["version"] = new_version
                break

        with self.config_path.open("w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=4)
