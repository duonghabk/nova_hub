"""
Update Worker Thread
=====================
Runs update operations in background thread to prevent UI blocking.
"""
from PySide6.QtCore import QThread, Signal

from logger_config import logger
from app_updater import AppUpdater, UpdateStatus


class UpdateWorker(QThread):
    """
    Worker thread for running app update operations.
    Emits signals for UI updates.
    """

    # Signals
    status_changed = Signal(str, str)  # (status, message)
    progress_changed = Signal(int)     # (percent)
    finished = Signal(bool, str)       # (success, message)

    def __init__(self, updater: AppUpdater, app_id: str):
        """
        Initialize worker.
        
        Args:
            updater: AppUpdater instance
            app_id: App ID to update
        """
        super().__init__()
        self.updater = updater
        self.app_id = app_id
        self._is_running = True

        # Connect updater callbacks
        self.updater.set_status_callback(self._on_status_changed)
        self.updater.set_progress_callback(self._on_progress_changed)

    def run(self) -> None:
        """
        Execute update in worker thread.
        """
        logger.info("Update worker started for app: %s", self.app_id)
        try:
            if not self._is_running:
                self.finished.emit(False, "Update cancelled")
                return

            success = self.updater.update_app(self.app_id)

            if success:
                self.finished.emit(True, f"{self.app_id} updated successfully")
            else:
                self.finished.emit(False, f"Failed to update {self.app_id}")

        except Exception as e:
            logger.exception("Exception in update worker: %s", e)
            self.finished.emit(False, f"Update error: {e}")

    def _on_status_changed(self, status: UpdateStatus, message: str) -> None:
        """
        Handle status changes from updater.
        """
        self.status_changed.emit(status.value, message)

    def _on_progress_changed(self, progress: int) -> None:
        """
        Handle progress updates from updater.
        """
        self.progress_changed.emit(progress)

    def cancel(self) -> None:
        """
        Cancel the update operation.
        """
        logger.info("Update cancelled by user")
        self._is_running = False
        self.updater.cancel_update()
        self.wait()


class CheckUpdatesWorker(QThread):
    """
    Worker thread for checking available updates.
    """

    # Signals
    finished = Signal(dict)  # (updates_dict)
    error = Signal(str)      # (error_message)

    def __init__(self, updater: AppUpdater):
        """
        Initialize worker.
        
        Args:
            updater: AppUpdater instance
        """
        super().__init__()
        self.updater = updater

    def run(self) -> None:
        """
        Check for updates in worker thread.
        """
        logger.info("Check updates worker started")
        try:
            updates = self.updater.check_updates()
            self.finished.emit(updates)
        except Exception as e:
            logger.exception("Exception in check updates worker: %s", e)
            self.error.emit(str(e))
