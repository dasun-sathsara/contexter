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
    QTabWidget,
    QProgressDialog,
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
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


class FileSystemWorker(QThread):
    """Worker thread for file system operations."""

    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, operation, *args):
        super().__init__()
        self.operation = operation
        self.args = args

    def run(self):
        try:
            if self.operation == "list_dir":
                folder = self.args[0]
                try:
                    result = sorted(os.listdir(folder))
                    self.finished.emit(result)
                except Exception as e:
                    self.error.emit(str(e))
            elif self.operation == "merge_files":
                files = self.args[0]
                total_files = len(files)
                result = []
                for i, file_path in enumerate(files):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        header = f"############## {file_path.replace(os.sep, '/')} ##############"
                        result.extend([header, content, ""])
                        self.progress.emit(int((i + 1) / total_files * 100))
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")
                self.finished.emit("\n".join(result))
        except Exception as e:
            self.error.emit(str(e))


class FileDropApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Drop Interface")
        self.setMinimumSize(500, 500)
        self.added_paths = {}  # Tracks currently displayed items
        self.deleted_paths = set()  # Tracks deleted items
        self.base_paths = set()  # Changed from list to set
        self.current_folder = None
        self.nav_stack = []
        self.text_only = True  # Default to showing only text files
        self.hide_empty_folders = True  # Default to hiding empty folders
        self.worker = None
        self.progress_dialog = None

        # Set up the UI with tabs
        self.tab_widget = QTabWidget()

        # Main tab
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)

        # Apply the default light theme
        self.setStyleSheet("""
            QMainWindow, QWidget { 
                background-color: #ffffff; 
                color: #000000; 
            }
            QListWidget { 
                background-color: #ffffff; 
                color: #000000; 
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item { 
                background-color: transparent;
                color: #000000;
                padding: 3px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected { 
                background-color: #e7f0fa; 
                color: #000000; 
            }
            QPushButton { 
                background-color: #4a86e8; 
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background-color: #3a76d8; 
            }
            QPushButton:pressed { 
                background-color: #2a66c8; 
            }
            QFrame { 
                background-color: #ffffff; 
                color: #000000; 
            }
            QLabel { 
                color: #000000; 
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #000000;
                padding: 8px 16px;
                border: 1px solid #e0e0e0;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom-color: #4a86e8;
            }
            QTabBar::tab:hover {
                background-color: #e7f0fa;
            }
            QCheckBox {
                color: #000000;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
            }
            QCheckBox::indicator:checked {
                background-color: #4a86e8;
            }
            QCheckBox::indicator:hover {
                border-color: #4a86e8;
            }
        """)

        header_label = QLabel("File & Folder Drop Zone")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.drop_zone = DropZone(self.add_files)

        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)

        # Create filter options layout
        filter_layout = QVBoxLayout()
        self.text_only_checkbox = QCheckBox("Show text files only")
        self.text_only_checkbox.setChecked(self.text_only)
        self.text_only_checkbox.stateChanged.connect(self.on_text_only_changed)
        filter_layout.addWidget(self.text_only_checkbox)

        self.hide_empty_folders_checkbox = QCheckBox("Hide empty folders")
        self.hide_empty_folders_checkbox.setChecked(
            True
        )  # Default to hiding empty folders
        self.hide_empty_folders_checkbox.stateChanged.connect(
            self.on_hide_empty_folders_changed
        )
        filter_layout.addWidget(self.hide_empty_folders_checkbox)

        # Dark mode toggle
        self.dark_mode_checkbox = QCheckBox("Dark mode")
        self.dark_mode_checkbox.stateChanged.connect(self.toggle_dark_mode)
        filter_layout.addWidget(self.dark_mode_checkbox)

        settings_layout.addLayout(filter_layout)
        settings_layout.addStretch()

        # Add tabs to tab widget
        self.tab_widget.addTab(main_tab, "Main")
        self.tab_widget.addTab(settings_tab, "Settings")
        self.setCentralWidget(self.tab_widget)

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
        main_layout.addLayout(filter_layout)  # Add filter_layout only once
        main_layout.addWidget(self.file_list)
        main_layout.addLayout(button_layout)

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

    def toggle_dark_mode(self, state):
        """Toggle between light and dark mode."""
        if state == Qt.CheckState.Checked.value:
            self.setStyleSheet("""
                QMainWindow, QWidget { 
                    background-color: #1e1e1e; 
                    color: #ffffff; 
                }
                QListWidget { 
                    background-color: #2d2d30; 
                    color: #ffffff; 
                    border: 1px solid #3e3e40;
                    border-radius: 5px;
                    padding: 5px;
                }
                QListWidget::item { 
                    background-color: transparent;
                    color: #ffffff;
                    padding: 3px;
                    border-bottom: 1px solid #3e3e40;
                }
                QListWidget::item:selected { 
                    background-color: #3e3e40; 
                    color: #ffffff; 
                }
                QPushButton { 
                    background-color: #007acc; 
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background-color: #1c8ad9; 
                }
                QPushButton:pressed { 
                    background-color: #005c99; 
                }
                QFrame { 
                    background-color: #252526; 
                    color: #ffffff; 
                }
                QLabel { 
                    color: #ffffff; 
                }
                QTabWidget::pane {
                    border: 1px solid #3e3e40;
                    background-color: #1e1e1e;
                }
                QTabBar::tab {
                    background-color: #2d2d30;
                    color: #ffffff;
                    padding: 8px 16px;
                    border: 1px solid #3e3e40;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    border-bottom-color: #007acc;
                }
                QTabBar::tab:hover {
                    background-color: #3e3e40;
                }
                QCheckBox {
                    color: #ffffff;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    background-color: #2d2d30;
                    border: 1px solid #3e3e40;
                }
                QCheckBox::indicator:checked {
                    background-color: #007acc;
                }
                QCheckBox::indicator:hover {
                    border-color: #007acc;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { 
                    background-color: #ffffff; 
                    color: #000000; 
                }
                QListWidget { 
                    background-color: #ffffff; 
                    color: #000000; 
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    padding: 5px;
                }
                QListWidget::item { 
                    background-color: transparent;
                    color: #000000;
                    padding: 3px;
                    border-bottom: 1px solid #f0f0f0;
                }
                QListWidget::item:selected { 
                    background-color: #e7f0fa; 
                    color: #000000; 
                }
                QPushButton { 
                    background-color: #4a86e8; 
                    color: #ffffff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover { 
                    background-color: #3a76d8; 
                }
                QPushButton:pressed { 
                    background-color: #2a66c8; 
                }
                QFrame { 
                    background-color: #ffffff; 
                    color: #000000; 
                }
                QLabel { 
                    color: #000000; 
                }
                QTabWidget::pane {
                    border: 1px solid #e0e0e0;
                    background-color: #ffffff;
                }
                QTabBar::tab {
                    background-color: #f0f0f0;
                    color: #000000;
                    padding: 8px 16px;
                    border: 1px solid #e0e0e0;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    border-bottom-color: #4a86e8;
                }
                QTabBar::tab:hover {
                    background-color: #e7f0fa;
                }
                QCheckBox {
                    color: #000000;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                }
                QCheckBox::indicator:checked {
                    background-color: #4a86e8;
                }
                QCheckBox::indicator:hover {
                    border-color: #4a86e8;
                }
            """)

    def add_files(self, paths):
        """Add files and folders to the list."""
        self.deleted_paths.clear()
        self.nav_stack = []

        # Add new paths to the existing base_paths
        for path in paths:
            if os.path.exists(path):
                self.base_paths.add(path)

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
                path
                for path in folders
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

        # Select the first item if any exist
        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)

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

        self.worker = FileSystemWorker("list_dir", folder)
        self.worker.finished.connect(self._on_folder_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_folder_loaded(self, entries):
        """Handle the completion of folder loading."""
        dirs = []
        files = []
        for entry in entries:
            full_path = os.path.join(self.current_folder, entry)
            if full_path not in self.deleted_paths:
                if os.path.isdir(full_path):
                    if not self.hide_empty_folders or not is_folder_empty(
                        full_path, self.text_only, self.deleted_paths
                    ):
                        dirs.append(full_path)
                else:
                    if not self.text_only or is_text_file(full_path):
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

        if self.file_list.count() > (1 if self.nav_stack else 0):
            self.file_list.setCurrentRow(1 if self.nav_stack else 0)

    def _on_error(self, error_message):
        """Handle file system operation errors."""
        print(f"Error: {error_message}")

    def clear_list(self):
        """Clear the file list and reset state."""
        self.file_list.clear()
        self.added_paths.clear()
        self.deleted_paths.clear()
        self.base_paths = set()
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
            try:
                if (
                    selected_item
                    and hasattr(selected_item, "is_dir")
                    and selected_item.is_dir
                    and selected_item.text() != ".."
                ):
                    self.on_item_double_clicked(selected_item)
                    # Set focus back to the list widget and select first item
                    self.file_list.setFocus()
                    if self.file_list.count() > (1 if self.nav_stack else 0):
                        self.file_list.setCurrentRow(1 if self.nav_stack else 0)
                else:
                    # Pass the event up if not a directory
                    event.ignore()
            except (RuntimeError, AttributeError):
                # Handle case where item has been deleted
                event.ignore()
        elif event.key() == Qt.Key.Key_Left:
            if self.nav_stack:
                prev_state = self.nav_stack.pop()
                if isinstance(prev_state, (list, set)):
                    self.show_initial_items()
                else:
                    self.show_folder(prev_state)
            else:
                event.ignore()
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
                if isinstance(prev_state, (list, set)):
                    self.show_initial_items()
                else:
                    self.show_folder(prev_state)
            return
        if item.is_dir:
            if self.current_folder:
                self.nav_stack.append(self.current_folder)
            else:
                # Store None instead of base_paths to indicate we should return to initial view
                self.nav_stack.append(None)
            self.show_folder(item.path)

    def get_all_included_files(self):
        """Collect all included file paths recursively, excluding deleted ones."""
        return get_all_files_recursive(
            self.base_paths, self.deleted_paths, self.text_only
        )

    def generate_paths_text(self):
        """Generate text of all included file contents and copy to clipboard."""
        files = self.get_all_included_files()
        if not files:
            return

        self.progress_dialog = QProgressDialog(
            "Merging files...", "Cancel", 0, 100, self
        )
        self.progress_dialog.setWindowTitle("Progress")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()

        self.worker = FileSystemWorker("merge_files", files)
        self.worker.finished.connect(self._on_merge_completed)
        self.worker.progress.connect(self.progress_dialog.setValue)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_merge_completed(self, text):
        """Handle completion of file merging."""
        if self.progress_dialog:
            self.progress_dialog.close()
        QApplication.clipboard().setText(text)
        print("File contents copied to clipboard.")
