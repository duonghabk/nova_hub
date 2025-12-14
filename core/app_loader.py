# core/app_loader.py
import os
import glob
from PySide6.QtWidgets import QMessageBox

from .file_utils import run_exe
from .logger_config import logger  # Import the shared logger


class AppLoader:
    def __init__(self, parent_ui=None):
        """
        Initializes the AppLoader.
        :param parent_ui: Parent widget for displaying message boxes.
        """
        self.parent_ui = parent_ui

    def _find_executable_path(self, path_pattern: str) -> str | None:
        """
        Finds an executable file based on a path pattern with wildcards and environment variables.
        """
        if not path_pattern:
            logger.debug("Path pattern is empty or None.")
            return None

        # Expand environment variables like %LOCALAPPDATA%
        expanded_path = os.path.expandvars(path_pattern)
        logger.debug("Searching for executable with pattern: %s", expanded_path)

        # Use glob to find matching files, recursive=True allows for ** patterns
        found_files = glob.glob(expanded_path, recursive=True)
        if found_files:
            found_path = found_files[0]
            logger.info("Found executable: %s", found_path)
            return found_path
        else:
            logger.debug("No executable found for pattern: %s", expanded_path)
            return None

    def launch_app(self, app_config: dict) -> None:
        """
        Finds and launches an application based on its configuration.
        It checks 'local_path' first (relative to project_root/apps), then 'installed_exe'.
        Displays status messages using the parent UI.
        """
        exe_path = None
        app_name = app_config.get("name", "Unknown App")
        logger.info("Attempting to launch app: %s", app_name)

        # Determine base directory (project root)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        apps_dir = os.path.join(base_dir, "apps")
        # 1. If not found, fall back to installed_exe
        if  "installed_exe" in app_config:
            logger.debug("checking installed_exe...")
            exe_path = self._find_executable_path(app_config["installed_exe"])

        # 2. Try to find the executable using local_path
        local_path_pattern = app_config.get("local_path")
        if not exe_path and local_path_pattern:
            full_local_pattern = os.path.join(apps_dir, local_path_pattern)
            logger.debug("Checking local_path...")
            exe_path = self._find_executable_path(full_local_pattern)
        

        # 3. Launch the executable if found, otherwise show an error
        if exe_path:
            try:
                logger.info("Launching executable for '%s' from: %s", app_name, exe_path)
                run_exe(exe_path)
            except Exception as e:
                error_message = f"Failed to run {app_name}:\n{e}"
                logger.exception("Failed to launch executable %s.", exe_path) # Logs with stack trace
                if self.parent_ui:
                    QMessageBox.warning(self.parent_ui, "Run Error", error_message)
        else:
            error_message = f"Could not find executable for {app_name}."
            logger.error(error_message)
            if self.parent_ui:
                QMessageBox.warning(self.parent_ui, "Not Found", error_message)
