import json
import os
import subprocess
from pathlib import Path

from logger_config import logger  # Import the shared logger


def load_app_config(config_path: Path) -> list[dict]:
    """
    Load app configuration from a JSON file.
    Returns a list of app dicts.

    Expected JSON format:
    {
        "apps": [
            {
                "name": "App Name",
                "local_exe": "AppFolder/App.exe",
                "installed_exe": "C:/Program Files/App/App.exe"
            }
        ]
    }
    """
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    apps = data.get("apps", [])
    logger.debug("Loaded %d apps from config", len(apps))
    return apps


def resolve_executable_path(app_cfg: dict, base_dir: Path) -> Path | None:
    """
    Decide which executable to run for a given app:
    1. If 'installed_exe' is defined and exists, use it.
    2. Else, if 'local_exe' exists inside 'apps' directory, use it.
    3. Otherwise, return None.

    base_dir: directory where main.py is located.
    """
    # Try installed exe first
    installed_exe = app_cfg.get("installed_exe", "").strip()
    if installed_exe:
        # Expand environment variables like %LOCALAPPDATA% before creating a Path object.
        expanded_path_str = os.path.expandvars(installed_exe)
        installed_path = Path(expanded_path_str)
        if installed_path.exists():
            logger.debug("Using installed exe for '%s': %s", app_cfg.get("name"), installed_path)
            return installed_path
        else:
            logger.debug(
                "Installed exe for '%s' not found at: %s",
                app_cfg.get("name"),
                installed_path,
            )

    # Fallback to local exe inside 'apps' folder
    local_exe = app_cfg.get("local_exe", "").strip()
    if local_exe:
        local_path = base_dir / "apps" / local_exe
        if local_path.exists():
            logger.debug("Using local exe for '%s': %s", app_cfg.get("name"), local_path)
            return local_path
        else:
            logger.debug(
                "Local exe for '%s' not found at: %s",
                app_cfg.get("name"),
                local_path,
            )

    # If nothing found
    logger.error("No valid executable found for app: %s", app_cfg.get("name"))
    return None


def launch_executable(exe_path: Path):
    """
    Launch the given executable using subprocess.Popen.
    This will not block the UI.
    """
    try:
        # On Windows, it's usually fine to call Popen with the exe path.
        # 'cwd' is set to the directory of the exe to avoid path issues.
        logger.info("Launching: %s", exe_path)
        subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
            shell=False,
        )
    except Exception:
        # Log full traceback for debugging
        logger.exception("Failed to launch: %s", exe_path)
        raise