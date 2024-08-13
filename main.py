import sys
import os
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QStyle,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QKeyEvent, QColor, QPalette, QFontDatabase


class FileListItem(QListWidgetItem):
    """Custom list item to display file/folder info."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.name = os.path.basename(path)
        self.is_dir = os.path.isdir(path)
        self.setText(self.name)
        if self.is_dir:
            self.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            )
        else:
            self.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            )
        self.setToolTip(path)


class DropZone(QFrame):
    """Custom widget that accepts drag and drop for files and folders."""

    def __init__(self, callback_function, parent=None):
        super().__init__(parent)
        self.callback_function = callback_function
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(
            QApplication.style()
            .standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon)
            .scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio)
        )
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel("Drag & Drop Files and Folders Here")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        self.text_label.setFont(font)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.setContentsMargins(20, 20, 20, 20)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(230, 240, 250))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls]
            self.callback_function(paths)
            event.accept()
        else:
            event.ignore()


class FileDropApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Drop Interface")
        self.setMinimumSize(500, 500)
        self.added_paths = {}  # Tracks currently displayed items
        self.base_paths = []  # Stores initially dropped paths

        # Set up the UI
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        header_label = QLabel("File & Folder Drop Zone")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.drop_zone = DropZone(self.add_files)

        list_header = QLabel("Files and Folders:")
        list_header_font = QFont()
        list_header_font.setPointSize(12)
        list_header_font.setBold(True)
        list_header.setFont(list_header_font)

        self.file_list = QListWidget()
        self.file_list.setIconSize(QSize(24, 24))

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.clear_button = QPushButton("Clear List")
        self.clear_button.clicked.connect(self.clear_list)
        button_layout.addWidget(self.clear_button)

        main_layout.addWidget(header_label)
        main_layout.addWidget(self.drop_zone)
        main_layout.addWidget(list_header)
        main_layout.addWidget(self.file_list)
        main_layout.addLayout(button_layout)
        self.setCentralWidget(central_widget)

    def add_files(self, paths):
        """Add files and folders to the list."""
        self.base_paths = [path for path in paths if os.path.exists(path)]
        self.show_initial_items()

    def show_initial_items(self):
        """Show the initially added files and folders."""
        self.file_list.clear()
        self.added_paths.clear()
        folders = [path for path in self.base_paths if os.path.isdir(path)]
        files = [path for path in self.base_paths if not os.path.isdir(path)]
        folders.sort()
        files.sort()
        for path in folders:
            item = FileListItem(path)
            self.file_list.addItem(item)
            self.added_paths[path] = item
        for path in files:
            item = FileListItem(path)
            self.file_list.addItem(item)
            self.added_paths[path] = item

    def clear_list(self):
        """Clear the file list and reset state."""
        self.file_list.clear()
        self.added_paths.clear()
        self.base_paths = []


if __name__ == "__main__":
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
