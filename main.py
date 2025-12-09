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

# Import updater components
from app_updater import (
    AppConfigManager,
    GoogleDriveClient,
    VersionManager,
    AppUpdater,
)


# Configuration constants
# Google Drive folder URL containing app files and app_version.json
# Replace with your actual Google Drive folder URL or folder ID
GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/u/0/folders/1RFiRR_7cYoIl7b4cbMgOnOPkwnYXgBB3"
# Or use folder ID directly:
# GOOGLE_DRIVE_FOLDER_URL = "15foaiZz-dW9amlr2iVO5-czfWtclLBB6"


# -----------------------------
# main entry point
# -----------------------------

def main():
    """
    Entry point of the application.
    - Initializes QApplication
    - Loads config
    - Initializes updater components
    - Creates and shows the main window
    - Starts Qt event loop
    """
    # Create the application instance early.
    app = QApplication(sys.argv)

    base_dir = Path(__file__).parent
    config_path = base_dir / "config/appconfig.json"

    try:
        apps_config = load_app_config(config_path)
    except Exception as e:
        logger.exception("Failed to load config")
        QMessageBox.critical(None, "Config Error", f"Failed to load config:\n{e}")
        sys.exit(1)

    # Initialize updater components
    updater = None
    try:
        logger.info("Initializing updater components...")

        # Create updater components
        config_manager = AppConfigManager(config_path)
        drive_client = GoogleDriveClient(folder_url=GOOGLE_DRIVE_FOLDER_URL, 
                                        download_dir=base_dir / "temp")
        version_manager = VersionManager(drive_client)

        # Create the main updater
        apps_dir = base_dir / "apps"
        updater = AppUpdater(
            config_manager=config_manager,
            version_manager=version_manager,
            drive_client=drive_client,
            apps_dir=apps_dir,
            temp_dir=base_dir / "temp"
        )

        # Try to fetch remote versions on startup
        try:
            logger.info("Fetching remote versions from Google Drive...")
            version_manager.fetch_versions("app_version.json")
            logger.info("Remote versions loaded successfully")
        except Exception as e:
            logger.warning("Could not fetch remote versions: %s (Update feature will be unavailable)", e)
            # Don't exit, just continue without update functionality
            updater = None

    except Exception as e:
        logger.exception("Failed to initialize updater")
        # Continue without updater functionality
        updater = None

    # Create main window with updater (can be None)
    window = AppHubWindow(apps_config, base_dir, updater)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
