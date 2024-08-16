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
            self.setStyleSheet(
                "QFrame { background-color: #d0e7f7; border: 2px dashed #308cc6; }"
            )
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet("")
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
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f7; font-family: "Liga Comic Mono", monospace; }
            QListWidget { background-color: white; border-radius: 5px; border: 1px solid #e0e0e0; padding: 5px; }
            QListWidget::item { padding: 3px; border-bottom: 1px solid #f0f0f0; }
            QListWidget::item:selected { background-color: #e7f0fa; color: #000000; }
            QPushButton { background-color: #4a86e8; color: white; border: none; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #3a76d8; }
            QPushButton:pressed { background-color: #2a66c8; }
        """)

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
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_paths_text)
        button_layout.addWidget(self.generate_button)
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
        elif event.key() == Qt.Key.Key_Right:
            selected_item = self.file_list.currentItem()
            if selected_item and selected_item.is_dir and selected_item.text() != "..":
                self.on_item_double_clicked(selected_item)
        elif event.key() == Qt.Key.Key_Left:
            if self.nav_stack:
                prev_state = self.nav_stack.pop()
                if isinstance(prev_state, list):
                    self.show_initial_items()
                else:
                    self.show_folder(prev_state)
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

    def get_all_included_files(self):
        """Collect all included file paths recursively, excluding deleted ones."""
        all_files = set()
        for path in self.base_paths:
            if path not in self.deleted_paths:
                if os.path.isfile(path):
                    all_files.add(path)
                elif os.path.isdir(path):
                    self._collect_files(path, all_files)
        return sorted(all_files)

    def _collect_files(self, folder, all_files):
        """Helper method to collect file paths recursively."""
        try:
            entries = os.listdir(folder)
        except Exception as e:
            print(f"Error reading folder {folder}: {e}")
            return
        for entry in entries:
            full_path = os.path.join(folder, entry)
            if full_path not in self.deleted_paths:
                if os.path.isfile(full_path):
                    all_files.add(full_path)
                elif os.path.isdir(full_path):
                    self._collect_files(full_path, all_files)

    def generate_paths_text(self):
        """Generate text of all included file contents and copy to clipboard."""
        files = self.get_all_included_files()
        output = []
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                header = (
                    f"############## {file_path.replace(os.sep, '/')} ##############"
                )
                output.append(header)
                output.append(content)
                output.append("")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        text = "\n".join(output)
        QApplication.clipboard().setText(text)
        print("File contents copied to clipboard.")


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
