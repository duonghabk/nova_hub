import sys


from ui.main_window import MainWindow
from PySide6.QtGui import QPalette, QColor,QIcon
from PySide6.QtWidgets import QApplication

from core.api_keys import load_api_key

GOOGLE_DRIVE_FOLDER_URL = "https://drive.google.com/drive/folders/1RFiRR_7cYoIl7b4cbMgOnOPkwnYXgBB3"



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
    try:
        api_key = load_api_key()
    except (FileNotFoundError, ValueError) as e:
        # In ra console rồi exit
        print(f"[FATAL] {e}")
        sys.exit(1)
    try:
        api_key = load_api_key()
    except (FileNotFoundError, ValueError) as e:
        # In ra console rồi exit
        print(f"[FATAL] {e}")
        sys.exit(1)
    # Create the application instance early.
    app = QApplication(sys.argv)
    app.setStyle("WindowsVista")
    app.setWindowIcon(QIcon("ui/icon.ico")) # Icon cửa sổ
    app.setApplicationName("Nova Hub")

    palette = app.palette()
    palette.setColor(QPalette.Highlight, QColor("#95CDFB"))
    palette.setColor(QPalette.HighlightedText, QColor("#000000"))
    app.setPalette(palette)
    window = MainWindow(api_key=api_key, folder_url=GOOGLE_DRIVE_FOLDER_URL)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
