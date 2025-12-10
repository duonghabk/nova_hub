# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
)
from PySide6.QtCore import Qt

from core.config_manager import AppConfigManager
from core.drive_client import DriveClient
from core.version_manager import VersionManager
from core.updater import AppUpdater
from core.file_utils import run_exe


class MainWindow(QMainWindow):
    """
    Main hub window for managing and updating apps using a single Drive folder.
    """

    def __init__(self, api_key: str, folder_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apps Hub")
        self.resize(800, 400)

        # Load local config
        self.config_manager = AppConfigManager()
        self.config_manager.load()

        # Setup Drive + versions
        self.drive_client = DriveClient(api_key=api_key, folder_url=folder_url)
        self.version_manager = VersionManager(drive_client=self.drive_client)
        self.version_manager.fetch_versions()

        self.updater = AppUpdater(
            version_manager=self.version_manager,
            drive_client=self.drive_client,
        )

        self._init_ui()
        self._populate_table()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Update", "Run"])
        layout.addWidget(self.table)

    def _populate_table(self) -> None:
        apps = self.config_manager.apps
        self.table.setRowCount(len(apps))

        for row, app in enumerate(apps):
            app_id = app["id"]
            remote_info = self.version_manager.get_app_version_info(app_id)

            name_item = QTableWidgetItem(app["name"])
            name_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 0, name_item)

            status_text = "Unknown"
            if remote_info:
                status_text = f"Remote v{remote_info.get('version', '?')}"

            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 1, status_item)

            # Update button
            btn_update = QPushButton("Update")
            btn_update.clicked.connect(
                lambda _chk=False, a=app, r=remote_info: self._on_update_clicked(a, r)
            )
            self.table.setCellWidget(row, 2, btn_update)

            # Run button
            btn_run = QPushButton("Run")
            btn_run.clicked.connect(lambda _chk=False, a=app: run_exe(a["local_path"]))
            self.table.setCellWidget(row, 3, btn_run)

    def _on_update_clicked(self, app: dict, remote_info: dict | None) -> None:
        if not remote_info:
            QMessageBox.warning(self, "Error", f"No remote info for app: {app['name']}")
            return

        need_update = self.updater.is_update_needed(
            local_path=app["local_path"],
            remote_sha256=remote_info.get("sha256", ""),
        )

        if not need_update:
            QMessageBox.information(
                self, "Up to date", f"{app['name']} is already up to date."
            )
            return

        msg = self.updater.update_app(app, remote_info)
        QMessageBox.information(self, "Update", msg)
