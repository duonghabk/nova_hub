# ui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QProgressBar,
    QHeaderView,
)
from PySide6.QtCore import Qt, QThread

from core.config_manager import AppConfigManager
from core.drive_client import DriveClient
from core.version_manager import VersionManager
from core.app_loader import AppLoader
from core.update_worker import UpdateWorker
from core.logger_config import logger


class MainWindow(QMainWindow):
    def __init__(self, api_key: str, folder_url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Apps Hub")
        self.resize(900, 450)

        self.config_manager = AppConfigManager()
        self.config_manager.load()

        self.drive_client = DriveClient(api_key=api_key, folder_url=folder_url)
        self.version_manager = VersionManager(drive_client=self.drive_client)
        self.app_loader = AppLoader(parent_ui=self)

        try:
            self.version_manager.fetch_versions()
            logger.info("Successfully fetched remote version information.")
        except Exception as e:
            logger.error("Failed to fetch remote versions: %s", e, exc_info=True)
            QMessageBox.warning(
                self,
                "Network Error",
                "Could not fetch remote version information. "
                "Update functionality will be disabled. "
                "Please check your internet connection.",
            )

        # Store active threads to prevent GC
        self._threads: list[QThread] = []
        self._init_ui()
        self._populate_table()
        self._adjust_ui_size()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Run", "Update"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        layout.addWidget(self.table)

        self._status_bar = self.statusBar()
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress_bar)

    def _populate_table(self) -> None:
        apps = self.config_manager.apps
        self.table.setRowCount(len(apps))

        for row, app in enumerate(apps):
            app_id = app["id"]
            local_ver = app.get("version", "")
            remote_info = self.version_manager.get_app_version_info(app_id)
            remote_ver = remote_info.get("version", "?") if remote_info else "N/A"

            name_item = QTableWidgetItem(app["name"])
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 0, name_item)

            status_text = f"Local v{local_ver}, Remote v{remote_ver}"
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, 1, status_item)

            btn_run = QPushButton("Run")
            btn_run.clicked.connect(lambda _chk=False, a=app: self.app_loader.launch_app(a))
            self.table.setCellWidget(row, 2, btn_run)

            btn_update = QPushButton("Update")
            if not remote_info:
                btn_update.setEnabled(False)
                btn_update.setToolTip("Cannot update without remote version info.")
            else:
                btn_update.clicked.connect(
                    lambda _chk=False, a=app, r=remote_info, b=btn_update: self._on_update_clicked(a, r, b)
                )
            self.table.setCellWidget(row, 3, btn_update)

        self.table.resizeRowsToContents()

    def _adjust_ui_size(self):
        """Adjusts window height to fit table content."""
        header_height = self.table.horizontalHeader().height()
        total_rows_height = sum(self.table.rowHeight(i) for i in range(self.table.rowCount()))
        # Add some padding for status bar etc.
        new_height = header_height + total_rows_height + self.statusBar().height() + 20
        self.resize(self.width(), new_height)

    def _on_update_clicked(self, app: dict, remote_info: dict | None, btn: QPushButton) -> None:
        if not remote_info:
            QMessageBox.warning(self, "Error", f"No remote info for app: {app['name']}")
            return

        local_version = app.get("version", "")
        remote_version = remote_info.get("version", "")

        if not self.version_manager.is_update_needed(local_version, remote_version):
            QMessageBox.information(
                self,
                "Up to date",
                f"{app['name']} is already up to date.\n"
                f"Local v{local_version}, Remote v{remote_version}",
            )
            return

        btn.setEnabled(False)

        thread = QThread(self)
        worker = UpdateWorker(
            app_config=app,
            remote_info=remote_info,
            drive_client=self.drive_client,
            version_manager=self.version_manager,
        )
        worker.moveToThread(thread)

        # Store button on worker to retrieve it thread-safely in the slot
        worker.button = btn
        thread.worker = worker

        # Connect signals for thread management and UI updates
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_worker_progress)
        worker.status.connect(self._on_worker_status)

        # Main finished handler: connect directly to the slot.
        # Qt will ensure it's executed on the main thread (QueuedConnection).
        worker.finished.connect(self._on_worker_finished)

        # Thread cleanup: use a lambda to discard signal arguments.
        worker.finished.connect(lambda _msg, _ok: thread.quit())
        thread.finished.connect(thread.deleteLater)

        # Keep a reference to the thread to prevent premature garbage collection
        self._threads.append(thread)
        # Clean up finished threads from the list
        thread.finished.connect(lambda: self._threads.remove(thread))

        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_bar.showMessage(f"Updating {app['name']}...")
        thread.start()

    def _on_worker_progress(self, value: int) -> None:
        self._progress_bar.setValue(value)

    def _on_worker_status(self, text: str) -> None:
        self._status_bar.showMessage(text)

    def _on_worker_finished(self, message: str, success: bool) -> None:
        """
        This slot is executed in the main thread because the receiver (MainWindow)
        lives in the main thread.
        """
        worker = self.sender()
        if not worker:
            return

        # Retrieve context that was stored on the worker instance
        app = worker.app_config
        btn = worker.button

        self._progress_bar.setVisible(False)
        self._status_bar.showMessage("Ready")
        btn.setEnabled(True)

        if success:
            remote_info = self.version_manager.get_app_version_info(app["id"])
            if remote_info:
                new_version = remote_info.get("version")
                self.config_manager.update_local_version(app["id"], new_version)

            self._populate_table()
            self._adjust_ui_size()
            QMessageBox.information(self, "Update", message)
        else:
            QMessageBox.warning(self, "Update error", message)
