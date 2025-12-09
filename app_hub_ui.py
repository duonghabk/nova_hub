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
)

from logger_config import logger
from app_loader import resolve_executable_path, launch_executable


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