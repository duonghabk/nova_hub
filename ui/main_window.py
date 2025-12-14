# ui/main_window.py
import datetime
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
    QLabel,
    QFormLayout,
)
from PySide6.QtCore import Qt, QThread, QFile
from PySide6.QtUiTools import QUiLoader

from core.config_manager import AppConfigManager
from core.drive_client import DriveClient
from core.version_manager import VersionManager
from core.app_loader import AppLoader
from core.update_worker import UpdateWorker
from core.logger_config import logger
from core.auth import mock_authenticate


class MainWindow(QMainWindow):
    def __init__(self, api_key: str, folder_url: str, parent=None):
        super().__init__(parent)

        # # Tải giao diện từ file .ui
        loader = QUiLoader()
        ui_file = QFile("ui/nova_hub.ui")
        ui_file.open(QFile.OpenModeFlag.ReadOnly)
        central_widget = loader.load(ui_file, self)
        ui_file.close()

        

        self.setCentralWidget(central_widget)

        self.setWindowTitle("Nova Hub")
        self.resize(480, 400)  # Kích thước ban đầu cho màn hình đăng nhập

        # Lưu trữ api_key và folder_url để khởi tạo sau
        self.api_key = api_key
        self.folder_url = folder_url

        # Trì hoãn việc khởi tạo các thành phần này cho đến sau khi đăng nhập
        self.config_manager = None
        self.drive_client = None
        self.version_manager = None
        self.app_loader = None
        self.user_data = None

        # Lưu trữ các thread đang hoạt động để tránh bị thu gom rác
        self._threads: list[QThread] = []
        self._init_login_page()

        self._status_bar = self.statusBar()
        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimum(0)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._status_bar.addPermanentWidget(self._progress_bar)
        self._status_bar.hide()  # Ẩn cho đến khi ứng dụng chính hiển thị

    # Phương thức _init_ui không còn cần thiết vì UI được tải từ file .ui
    # và đã bị xóa.

    def _init_login_page(self):
        # Truy cập các widget từ UI đã tải thông qua self.centralWidget()
        ui = self.centralWidget()
        ui.stackedWidget.setCurrentWidget(ui.login_page)
        ui.login_button.clicked.connect(self._handle_login)
        ui.radio_username.toggled.connect(self._toggle_login_type)
        ui.password_input.returnPressed.connect(self._handle_login)
        self._toggle_login_type()  # Đặt nhãn ban đầu

    def _toggle_login_type(self):
        ui = self.centralWidget()
        if ui.radio_username.isChecked():
            ui.username_label.setText("Username:")
        else:
            ui.username_label.setText("Phone:")

    def _handle_login(self):
        ui = self.centralWidget()
        login_type = "username" if ui.radio_username.isChecked() else "phone"
        login_id = ui.username_input.text().strip()
        password = ui.password_input.text()

        if not login_id or not password:
            ui.error_label.setText("Please enter credentials.")
            return

        ui.error_label.setText("Logging in...")
        ui.login_button.setEnabled(False)

        user_data = mock_authenticate(login_id, password, login_type)

        ui.login_button.setEnabled(True)

        if not user_data:
            ui.error_label.setText("Invalid credentials.")
            return

        try:
            expiration_date = datetime.datetime.strptime(
                user_data["Date"], "%Y-%m-%d"
            ).date()
            if expiration_date < datetime.date.today():
                ui.error_label.setText(
                    f"Subscription expired on {expiration_date.strftime('%Y-%m-%d')}."
                )
                return
        except (ValueError, KeyError):
            ui.error_label.setText("Invalid user data format (date).")
            return

        self.user_data = user_data
        self._init_main_app()

    def _init_main_app(self):
        """Khởi tạo các thành phần chính của ứng dụng sau khi đăng nhập thành công."""
        self.centralWidget().error_label.setText("")

        self.config_manager = AppConfigManager()
        self.config_manager.load()

        self.drive_client = DriveClient(api_key=self.api_key, folder_url=self.folder_url)
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

        self._init_main_page_ui()
        self._populate_user_info()
        self._populate_table()

        self.centralWidget().stackedWidget.setCurrentWidget(self.centralWidget().main_page)
        self.resize(900, 450)
        self._adjust_ui_size()
        self._status_bar.show()

    def _init_main_page_ui(self):
        self.table = self.centralWidget().apps_table
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Run", "Update"])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )

    def _populate_table(self) -> None:
        user_permissions = self.user_data.get("Permissions", [])
        all_apps = self.config_manager.apps
        apps = [app for app in all_apps if app["id"] in user_permissions]

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

    def _populate_user_info(self):
        ui = self.centralWidget()
        layout = ui.user_info_widget.layout()
        # Xóa các widget hiện có khỏi layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        layout.addRow("Username:", QLabel(self.user_data.get("User_Name", "N/A")))
        layout.addRow("Phone:", QLabel(self.user_data.get("Phone", "N/A")))
        layout.addRow("Company:", QLabel(self.user_data.get("Company", "N/A")))
        layout.addRow("Expires:", QLabel(self.user_data.get("Date", "N/A")))

    def _adjust_ui_size(self):
        """Adjusts window height to fit table content."""
        header_height = self.table.horizontalHeader().height()
        total_rows_height = sum(self.table.rowHeight(i) for i in range(self.table.rowCount()))
        new_height = header_height + total_rows_height + self.statusBar().height() + self.centralWidget().user_info_widget.height() + 50
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
