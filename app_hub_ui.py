"""
AppHubWindow - Main UI for the apps hub.
Displays list of apps with Launch and Update buttons.
Handles update operations in background threads.
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QLabel,
    QHBoxLayout,
    QProgressBar,
    QDialog,
    QScrollArea,
)

from logger_config import logger
from app_loader import resolve_executable_path, launch_executable
from app_updater import AppUpdater, UpdateStatus
from app_update_worker import UpdateWorker, CheckUpdatesWorker


class UpdateProgressDialog(QDialog):
    """
    Dialog showing update progress.
    """

    def __init__(self, app_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Updating {app_name}")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout()

        self.label = QLabel(f"Preparing to update {app_name}...")
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.on_cancel)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)
        self.worker = None
        self.cancelled = False

    def on_cancel(self):
        """Handle cancel button click."""
        self.cancelled = True
        if self.worker:
            self.worker.cancel()
        self.close()

    def update_status(self, status: str, message: str):
        """Update status label."""
        self.label.setText(message)

    def update_progress(self, value: int):
        """Update progress bar."""
        self.progress_bar.setValue(value)

    def set_worker(self, worker: UpdateWorker):
        """Set the worker thread."""
        self.worker = worker


class AppHubWindow(QMainWindow):
    """
    Main window that displays a list of apps loaded from JSON config.
    Each app has buttons to:
    - Launch the app
    - Check/Download updates
    """

    def __init__(self, apps_config: list[dict], base_dir: Path, updater: AppUpdater = None):
        super().__init__()
        self.apps_config = apps_config
        self.base_dir = base_dir
        self.updater = updater
        self.active_update_dialog = None
        self.update_workers = {}  # Map app_id to UpdateWorker

        self.setWindowTitle("Apps Hub")
        self.setMinimumSize(600, 400)

        self._init_ui()

    def _init_ui(self):
        """
        Initialize the central widget and layout.
        """
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Title
        title_label = QLabel("Applications")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        main_layout.addWidget(title_label)

        # Check Updates button at top
        if self.updater:
            check_updates_button = QPushButton("Check for Updates")
            check_updates_button.clicked.connect(self.on_check_updates)
            main_layout.addWidget(check_updates_button)

        # Scrollable area for apps
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        # Create one row per app: [Label] [Launch Button] [Update Button]
        for app_cfg in self.apps_config:
            row_widget = self._create_app_row(app_cfg)
            scroll_layout.addWidget(row_widget)

        scroll_layout.addStretch(1)
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        self.setCentralWidget(central_widget)

    def _create_app_row(self, app_cfg: dict) -> QWidget:
        """
        Create a row widget for an app.
        
        Args:
            app_cfg: App configuration dict
            
        Returns:
            QWidget containing the app row
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(5, 5, 5, 5)
        row_layout.setSpacing(8)

        app_name = app_cfg.get("name", "Unnamed App")
        app_id = app_cfg.get("id", "unknown")
        app_version = app_cfg.get("version", "unknown")

        # App name and version
        label = QLabel(f"{app_name} (v{app_version})")
        label.setMinimumWidth(200)
        row_layout.addWidget(label)

        # Launch button
        launch_button = QPushButton("Launch")
        launch_button.setMaximumWidth(100)
        launch_button.clicked.connect(lambda: self.on_launch_clicked(app_cfg))
        row_layout.addWidget(launch_button)

        # Update button (if updater is available)
        if self.updater:
            update_button = QPushButton("Update")
            update_button.setMaximumWidth(100)
            update_button.setObjectName(f"update_btn_{app_id}")
            update_button.clicked.connect(lambda: self.on_update_clicked(app_cfg))
            row_layout.addWidget(update_button)

        row_layout.addStretch(1)
        return row_widget

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

    def on_check_updates(self):
        """
        Check for available updates in background.
        """
        if not self.updater:
            logger.warning("Updater not available")
            return

        logger.info("Starting check updates")
        worker = CheckUpdatesWorker(self.updater)
        worker.finished.connect(self.on_check_updates_finished)
        worker.error.connect(self.on_check_updates_error)
        worker.start()

    def on_check_updates_finished(self, updates_dict: dict):
        """
        Handle check updates result.
        
        Args:
            updates_dict: Dict of available updates
        """
        logger.info("Check updates completed: %s", updates_dict)

        # Find apps with updates
        apps_with_updates = {
            app_id: info for app_id, info in updates_dict.items()
            if info.get("has_update", False)
        }

        if not apps_with_updates:
            QMessageBox.information(self, "No Updates", "All apps are up to date!")
            return

        # Build message
        msg = "Updates available for:\n\n"
        for app_id, info in apps_with_updates.items():
            local_ver = info.get("local_version", "unknown")
            remote_ver = info.get("remote_version", "unknown")
            msg += f"• {app_id}: {local_ver} → {remote_ver}\n"

        msg += "\nWould you like to update?"

        reply = QMessageBox.question(self, "Updates Available", msg,
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Update all available apps
            for app_id in apps_with_updates:
                self._start_update(app_id)

    def on_check_updates_error(self, error_msg: str):
        """
        Handle check updates error.
        
        Args:
            error_msg: Error message
        """
        logger.error("Check updates error: %s", error_msg)
        QMessageBox.critical(self, "Check Updates Error", f"Failed to check updates:\n{error_msg}")

    def on_update_clicked(self, app_cfg: dict):
        """
        Handle update button click for a specific app.
        
        Args:
            app_cfg: App configuration dict
        """
        app_id = app_cfg.get("id", "unknown")
        app_name = app_cfg.get("name", "Unnamed App")

        reply = QMessageBox.question(
            self,
            "Update Confirmation",
            f"Update {app_name}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self._start_update(app_id, app_name)

    def _start_update(self, app_id: str, app_name: str = None):
        """
        Start update for an app in background thread.
        
        Args:
            app_id: App ID to update
            app_name: App name for display (if not provided, will use app_id)
        """
        if not self.updater:
            logger.warning("Updater not available")
            return

        if app_name is None:
            app = self.updater.config_manager.get_app_by_id(app_id)
            app_name = app.get("name", app_id) if app else app_id

        logger.info("Starting update for app: %s", app_id)

        # Create progress dialog
        progress_dialog = UpdateProgressDialog(app_name, self)

        # Create and setup worker
        worker = UpdateWorker(self.updater, app_id)
        worker.status_changed.connect(progress_dialog.update_status)
        worker.progress_changed.connect(progress_dialog.update_progress)
        worker.finished.connect(lambda success, msg: self._on_update_finished(
            success, msg, app_id, progress_dialog
        ))

        progress_dialog.set_worker(worker)
        self.update_workers[app_id] = worker

        # Start worker
        worker.start()
        progress_dialog.exec()

    def _on_update_finished(self, success: bool, message: str, app_id: str, dialog: UpdateProgressDialog):
        """
        Handle update completion.
        
        Args:
            success: Whether update succeeded
            message: Status message
            app_id: App ID
            dialog: Progress dialog to close
        """
        logger.info("Update finished for %s: success=%s, message=%s", app_id, success, message)

        # Close progress dialog
        dialog.close()

        if success:
            QMessageBox.information(self, "Update Complete", message)
        else:
            QMessageBox.critical(self, "Update Failed", message)

        # Clean up worker
        if app_id in self.update_workers:
            del self.update_workers[app_id]