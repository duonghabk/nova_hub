import json
import sys
import subprocess
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import winreg

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QLabel,
    QHBoxLayout,
)
from PySide6.QtCore import Qt


# -----------------------------
# Logging setup
# -----------------------------

def setup_logging():
    """
    Configure application-wide logging.
    - Creates 'logs/app_hub.log' if not exists.
    - Uses RotatingFileHandler to avoid huge log file.
    """
    logs_dir = Path(__file__).parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    log_file = logs_dir / "app_hub.log"

    logger = logging.getLogger("app_hub")
    logger.setLevel(logging.DEBUG)

    # Rotating file handler: 1 MB per file, keep last 3 backups.
    handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Avoid adding multiple handlers if setup_logging() is called twice.
    if not logger.handlers:
        logger.addHandler(handler)

    # Optional: also log to console during development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging()


# -----------------------------
# Config loading
# -----------------------------

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


# -----------------------------
# PySide6 UI
# -----------------------------

class AppHubWindow(QMainWindow):
    """
    Main window that displays a list of apps loaded from JSON config.
    Each app has a button to launch it.
    """

    def __init__(self, apps_config: list[dict], base_dir: Path):
        super().__init__()
        self.apps_config = apps_config
        self.base_dir = base_dir

        self.setWindowTitle("Apps Hub")
        self.setMinimumSize(400, 300)

        self._init_ui()

    def _init_ui(self):
        """
        Initialize the central widget and layout.
        """
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        title_label = QLabel("Applications")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # Create one row per app: [Label] [Launch Button]
        for app_cfg in self.apps_config:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            app_name = app_cfg.get("name", "Unnamed App")

            label = QLabel(app_name)
            label.setMinimumWidth(200)

            button = QPushButton("Launch")
            # Store app config in button using lambda default argument
            button.clicked.connect(
                lambda _, cfg=app_cfg: self.on_launch_clicked(cfg)
            )

            row_layout.addWidget(label)
            row_layout.addStretch(1)
            row_layout.addWidget(button)

            main_layout.addWidget(row_widget)

        main_layout.addStretch(1)
        self.setCentralWidget(central_widget)

    def on_launch_clicked(self, app_cfg: dict):
        """
        Slot called when user clicks "Launch" button for an app.
        It resolves the executable path and tries to run it.
        """
        app_name = app_cfg.get("name", "Unnamed App")
        logger.info("User requested to launch app: %s", app_name)

        exe_path = resolve_executable_path(app_cfg, self.base_dir)
        if exe_path is None:
            # Show an error dialog if we cannot resolve the exe path
            msg = (
                f"Cannot find executable for app:\n\n"
                f"{app_name}\n\n"
                f"Please check appconfig.json and file paths."
            )
            logger.error("Launch failed, no exe path for app: %s", app_name)
            QMessageBox.critical(self, "Error", msg)
            return

        try:
            launch_executable(exe_path)
        except Exception as e:
            # If launch fails, show error dialog and log the exception
            msg = (
                f"Failed to launch app:\n\n"
                f"{app_name}\n\n"
                f"Error: {e}"
            )
            logger.exception("Exception while launching app: %s", app_name)
            QMessageBox.critical(self, "Launch Error", msg)


# -----------------------------
# main entry point
# -----------------------------

def main():
    """
    Entry point of the application.
    - Loads config
    - Starts Qt event loop
    """
    base_dir = Path(__file__).parent
    config_path = base_dir / "appconfig.json"

    try:
        apps_config = load_app_config(config_path)
    except Exception as e:
        logger.exception("Failed to load config")
        # Show very simple message box before exit
        app = QApplication(sys.argv)
        QMessageBox.critical(None, "Config Error", f"Failed to load config:\n{e}")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = AppHubWindow(apps_config, base_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
