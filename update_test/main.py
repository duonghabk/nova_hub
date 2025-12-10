# main.py
import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # TODO: sửa 2 biến này theo của bạn
    API_KEY = "AIzaSyDstwvSlwJ-s-pTUp1NyLk2iKz_duaEcck"
    DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1RFiRR_7cYoIl7b4cbMgOnOPkwnYXgBB3?lfhs=2"

    window = MainWindow(api_key=API_KEY, folder_url=DRIVE_FOLDER_URL)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
