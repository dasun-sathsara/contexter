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
        self.deleted_paths = set()  # Tracks deleted items
        self.base_paths = []  # Stores initially dropped paths
        self.current_folder = None
        self.nav_stack = []

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
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_list.keyPressEvent = self.list_key_press_event

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
        self.deleted_paths.clear()
        self.nav_stack = []
        self.base_paths = [path for path in paths if os.path.exists(path)]
        self.show_initial_items()

    def show_initial_items(self):
        """Show the initially added files and folders, with folders first."""
        self.file_list.clear()
        self.added_paths.clear()
        folders = [path for path in self.base_paths if os.path.isdir(path)]
        files = [path for path in self.base_paths if not os.path.isdir(path)]
        folders.sort()
        files.sort()
        for path in folders:
            if path not in self.deleted_paths:
                item = FileListItem(path)
                self.file_list.addItem(item)
                self.added_paths[path] = item
        for path in files:
            if path not in self.deleted_paths:
                item = FileListItem(path)
                self.file_list.addItem(item)
                self.added_paths[path] = item
        self.current_folder = None

    def show_folder(self, folder):
        """Load the immediate children of the given folder."""
        self.current_folder = folder
        self.file_list.clear()
        self.added_paths.clear()
        if self.nav_stack:
            back_item = QListWidgetItem("..")
            back_item.is_dir = True
            back_item.path = None
            back_item.setFlags(back_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.file_list.addItem(back_item)
        try:
            entries = sorted(os.listdir(folder))
        except Exception as e:
            print(f"Error opening folder: {e}")
            return
        dirs = []
        files = []
        for entry in entries:
            full_path = os.path.join(folder, entry)
            if full_path not in self.deleted_paths:
                if os.path.isdir(full_path):
                    dirs.append(full_path)
                else:
                    files.append(full_path)
        dirs.sort()
        files.sort()
        for full_path in dirs:
            item = FileListItem(full_path)
            self.file_list.addItem(item)
            self.added_paths[full_path] = item
        for full_path in files:
            item = FileListItem(full_path)
            self.file_list.addItem(item)
            self.added_paths[full_path] = item

    def clear_list(self):
        """Clear the file list and reset state."""
        self.file_list.clear()
        self.added_paths.clear()
        self.deleted_paths.clear()
        self.base_paths = []
        self.current_folder = None
        self.nav_stack = []

    def list_key_press_event(self, event: QKeyEvent):
        """Handle key press events in the list widget."""
        if event.key() == Qt.Key.Key_Delete:
            self.remove_selected_items()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_item = self.file_list.currentItem()
            if selected_item:
                self.on_item_double_clicked(selected_item)
        else:
            QListWidget.keyPressEvent(self.file_list, event)

    def remove_selected_items(self):
        """Remove selected items from the list."""
        selected_items = self.file_list.selectedItems()[::-1]
        for item in selected_items:
            if item.path is not None:
                self.deleted_paths.add(item.path)
                if item.path in self.added_paths:
                    del self.added_paths[item.path]
                row = self.file_list.row(item)
                self.file_list.takeItem(row)

    def on_item_double_clicked(self, item):
        """Navigate into folder or go back if '..' is clicked."""
        if item.text() == "..":
            if self.nav_stack:
                prev_state = self.nav_stack.pop()
                if isinstance(prev_state, list):
                    self.show_initial_items()
                else:
                    self.show_folder(prev_state)
            return
        if item.is_dir:
            if self.current_folder:
                self.nav_stack.append(self.current_folder)
            else:
                self.nav_stack.append(self.base_paths)
            self.show_folder(item.path)


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
