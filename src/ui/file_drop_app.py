import os
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QPushButton,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import QApplication

from src.ui.drop_zone import DropZone
from src.models.file_list_item import FileListItem
from src.utils.file_operations import (
    get_all_files_recursive,
    merge_file_contents,
    is_text_file,
    is_folder_empty,
)


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
        self.text_only = True  # Default to showing only text files
        self.hide_empty_folders = True  # Default to hiding empty folders

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

        # Create filter options layout
        filter_layout = QHBoxLayout()
        self.text_only_checkbox = QCheckBox("Show text files only")
        self.text_only_checkbox.setChecked(self.text_only)
        self.text_only_checkbox.stateChanged.connect(self.on_text_only_changed)
        filter_layout.addWidget(self.text_only_checkbox)
        
        self.hide_empty_folders_checkbox = QCheckBox("Hide empty folders")
        self.hide_empty_folders_checkbox.setChecked(True)  # Default to hiding empty folders
        self.hide_empty_folders_checkbox.stateChanged.connect(self.on_hide_empty_folders_changed)
        filter_layout.addWidget(self.hide_empty_folders_checkbox)
        
        filter_layout.addStretch()

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
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.file_list)
        main_layout.addLayout(button_layout)
        self.setCentralWidget(central_widget)

    def on_text_only_changed(self, state):
        """Handle change in the text-only checkbox state."""
        self.text_only = state == Qt.CheckState.Checked.value
        if self.current_folder is not None:
            self.show_folder(self.current_folder)
        else:
            self.show_initial_items()

    def on_hide_empty_folders_changed(self, state):
        """Handle change in the hide-empty-folders checkbox state."""
        self.hide_empty_folders = state == Qt.CheckState.Checked.value
        if self.current_folder is not None:
            self.show_folder(self.current_folder)
        else:
            self.show_initial_items()

    def add_files(self, paths):
        """Add files and folders to the list."""
        self.deleted_paths.clear()
        self.nav_stack = []

        # Add new paths to the existing base_paths rather than replacing them
        for path in paths:
            if os.path.exists(path) and path not in self.base_paths:
                self.base_paths.append(path)

        self.show_initial_items()

    def show_initial_items(self):
        """Show the initially added files and folders, with folders first."""
        self.file_list.clear()
        self.added_paths.clear()
        folders = [path for path in self.base_paths if os.path.isdir(path)]
        files = [path for path in self.base_paths if not os.path.isdir(path)]

        # Filter out non-text files if text_only is enabled
        if self.text_only:
            files = [path for path in files if is_text_file(path)]
            
        # Filter out empty folders if hide_empty_folders is enabled
        if self.hide_empty_folders:
            folders = [
                path for path in folders 
                if not is_folder_empty(path, self.text_only, self.deleted_paths)
            ]

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
                    # Skip empty folders if hide_empty_folders is enabled
                    if self.hide_empty_folders and is_folder_empty(full_path, self.text_only, self.deleted_paths):
                        continue
                    dirs.append(full_path)
                else:
                    # Skip non-text files if text_only is enabled
                    if self.text_only and not is_text_file(full_path):
                        continue
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
        return get_all_files_recursive(
            self.base_paths, self.deleted_paths, self.text_only
        )

    def generate_paths_text(self):
        """Generate text of all included file contents and copy to clipboard."""
        files = self.get_all_included_files()
        text = merge_file_contents(files)
        QApplication.clipboard().setText(text)
        print("File contents copied to clipboard.")
