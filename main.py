import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase

from src.ui.file_drop_app import FileDropApp


def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app_font = (
        QFont("Liga Comic Mono")
        if "Liga Comic Mono" in QFontDatabase.families()
        else QFont("Monospace")
    )
    app.setFont(app_font)
    window = FileDropApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
