import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

# Import the shared logger instance. It's configured in logger_config.
from logger_config import logger

# Import the application logic and UI components
from app_loader import load_app_config
from app_hub_ui import AppHubWindow


# -----------------------------
# main entry point
# -----------------------------

def main():
    """
    Entry point of the application.
    - Initializes QApplication
    - Loads config
    - Creates and shows the main window
    - Starts Qt event loop
    """
    # Create the application instance early.
    app = QApplication(sys.argv)

    base_dir = Path(__file__).parent
    config_path = base_dir / "appconfig.json"

    try:
        apps_config = load_app_config(config_path)
    except Exception as e:
        logger.exception("Failed to load config")
        QMessageBox.critical(None, "Config Error", f"Failed to load config:\n{e}")
        sys.exit(1)

    window = AppHubWindow(apps_config, base_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
