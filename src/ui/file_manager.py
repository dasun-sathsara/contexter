import os
from PyQt6.QtWidgets import QListWidget, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QStyle
from typing import Set, Dict, Optional, List

from src.models.file_list_item import FileListItem
from src.utils.file_system_worker import FileSystemWorker
from src.utils.file_operations import (
    get_all_files_recursive,
    is_text_file,
    is_folder_empty,
)


class FileManager:
    def __init__(self, list_widget: QListWidget, parent=None):
        self.file_list = list_widget
        self.parent = parent
        self.added_paths: Dict[str, FileListItem] = {}
        self.deleted_paths: Set[str] = set()
        self.base_paths: Set[str] = set()
        self.current_folder: Optional[str] = None
        self.nav_stack: List[Optional[str]] = []
        self.text_only = True
        self.hide_empty_folders = True
        self.show_token_count = True
        self.worker = None
        self.progress_dialog = None
        self.token_workers = []

        # Enable HTML rendering in list widget
        self.file_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.file_list.setWordWrap(False)
        # Connect list widget signals
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_list.keyPressEvent = self.list_key_press_event

    def add_files(self, paths):
        """Add files and folders to the list."""
        self.deleted_paths.clear()
        self.nav_stack = []

        for path in paths:
            self.base_paths.add(path)

        self.show_initial_items()

        # Calculate token counts if enabled
        if self.show_token_count:
            self.calculate_token_counts()

    def show_initial_items(self):
        """Show the initially added files and folders."""
        self.file_list.clear()
        self.added_paths.clear()

        folders = [path for path in self.base_paths if path and os.path.isdir(path)]
        files = [path for path in self.base_paths if path and not os.path.isdir(path)]

        if self.text_only:
            files = [path for path in files if is_text_file(path)]

        if self.hide_empty_folders:
            folders = [
                path
                for path in folders
                if not is_folder_empty(path, self.text_only, self.deleted_paths)
            ]

        folders.sort()
        files.sort()

        for path in folders + files:
            if path not in self.deleted_paths:
                item = FileListItem(path)
                self.file_list.addItem(item)
                self.file_list.setItemWidget(item, item.content_widget)
                self.added_paths[path] = item

        self.current_folder = None
        if self.file_list.count() > 0:
            self.file_list.setCurrentRow(0)

    def show_folder(self, folder: str):
        """Load the immediate children of the given folder."""
        if not folder:
            self.show_initial_items()
            return

        self.current_folder = folder
        self.file_list.clear()
        self.added_paths.clear()

        if self.nav_stack:
            # Create back item using FileListItem for consistent styling
            back_item = FileListItem("..")
            back_item.is_dir = True
            back_item.path = None
            back_item.setFlags(back_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            back_item.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft)
            )
            self.file_list.addItem(back_item)
            self.file_list.setItemWidget(back_item, back_item.content_widget)

        self.worker = FileSystemWorker("list_dir", folder)
        self.worker.finished.connect(self._on_folder_loaded)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_folder_loaded(self, entries):
        """Handle completion of folder loading."""
        dirs = []
        files = []

        valid_entries = [entry for entry in entries if entry]

        for entry in valid_entries:
            full_path = os.path.join(self.current_folder, entry)
            if full_path not in self.deleted_paths:
                if os.path.isdir(full_path):
                    if not self.hide_empty_folders or not is_folder_empty(
                        full_path, self.text_only, self.deleted_paths
                    ):
                        dirs.append(full_path)
                elif not self.text_only or is_text_file(full_path):
                    files.append(full_path)

        dirs.sort()
        files.sort()

        for full_path in dirs + files:
            item = FileListItem(full_path)
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, item.content_widget)
            self.added_paths[full_path] = item

        if self.file_list.count() > (1 if self.nav_stack else 0):
            self.file_list.setCurrentRow(1 if self.nav_stack else 0)

        # Calculate token counts if enabled
        if self.show_token_count:
            self.calculate_token_counts()

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
                    self.file_list.setFocus()
                    if self.file_list.count() > (1 if self.nav_stack else 0):
                        self.file_list.setCurrentRow(1 if self.nav_stack else 0)
                else:
                    event.ignore()
            except (RuntimeError, AttributeError):
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
                self.nav_stack.append(None)
            self.show_folder(item.path)

    def get_all_included_files(self):
        """Collect all included file paths recursively."""
        return get_all_files_recursive(
            self.base_paths, self.deleted_paths, self.text_only
        )

    def calculate_token_counts(self):
        """Calculate token counts for all visible items asynchronously."""
        if not self.show_token_count:
            return

        # Clear any existing token workers
        for worker in self.token_workers:
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        self.token_workers = []

        # Process all visible items
        for path, item in self.added_paths.items():
            worker = FileSystemWorker(
                "count_tokens", path, self.text_only, self.deleted_paths
            )
            worker.token_count_result.connect(self._on_token_count_result)
            worker.error.connect(self._on_error)
            self.token_workers.append(worker)
            worker.start()

    def _on_token_count_result(self, path, token_count):
        """Handle token count result for a file or folder."""
        if path in self.added_paths:
            item = self.added_paths[path]
            item.set_token_count(token_count)

    def on_show_token_count_changed(self, state):
        """Handle change in the show-token-count checkbox state."""
        self.show_token_count = state

        # Update all items to show/hide token counts
        for path, item in self.added_paths.items():
            if not state:
                # Reset token display if disabled
                item.token_count = None
                item.update_display_text()
            elif item.token_count is None:
                # Recalculate if enabled and not already calculated
                self.calculate_token_counts()
                break
