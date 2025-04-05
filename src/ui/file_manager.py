import os
from PyQt6.QtWidgets import QListWidget, QApplication, QLabel, QStatusBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QColor
from PyQt6.QtWidgets import QStyle
from typing import Set, Dict, Optional, List

from src.models.file_list_item import FileListItem
from src.utils.file_system_worker import FileSystemWorker
from src.utils.file_operations import (
    get_all_files_recursive,
    is_text_file,
    is_folder_empty,
)

from src.utils.gitignore import load_gitignore_patterns, is_ignored

from typing import cast


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

        # Vim visual mode state
        self.visual_mode = False
        self.visual_anchor_row: Optional[int] = None
        self.status_bar: Optional[QStatusBar] = None
        self.status_label: Optional[QLabel] = None

        # .gitignore PathSpec cache
        self.gitignore_specs: Dict[str, Optional[object]] = {}

        # Visual mode highlight color
        self.visual_mode_highlight_color = QColor(
            173, 216, 230, 100
        )  # Light blue with transparency
        self.visual_mode_text_color = QColor(0, 0, 139)  # Dark blue

        # Enable HTML rendering in list widget
        self.file_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.file_list.setWordWrap(False)
        # Connect list widget signals
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        # Override keyPressEvent with compatible signature
        orig_key_press = self.file_list.keyPressEvent

        def new_key_press(e: Optional[QKeyEvent]):
            if e is not None:
                self.list_key_press_event(e)
            else:
                if orig_key_press:
                    orig_key_press(e)

        self.file_list.keyPressEvent = new_key_press  # type: ignore
        self.file_list.itemSelectionChanged.connect(self.on_selection_changed)

        # Create status bar for visual mode indication
        self._setup_status_bar()

    def _setup_status_bar(self):
        """Set up a status bar to display mode information"""
        if self.parent and hasattr(self.parent, "statusBar"):
            self.status_bar = self.parent.statusBar()
            self.status_label = QLabel()
            self.status_bar.addPermanentWidget(self.status_label)
            self.status_label.hide()

    def _update_status_bar(self):
        """Update status bar with current mode information"""
        if self.status_label:
            if self.visual_mode:
                self.status_label.setText("visual")
                self.status_label.show()
            else:
                self.status_label.setText("")
                self.status_label.hide()

    def add_files(self, paths):
        """Add files and folders to the list."""
        self.deleted_paths.clear()
        self.nav_stack = []

        for path in paths:
            self.base_paths.add(path)
            # Load .gitignore for each base path
            spec = load_gitignore_patterns(path)
            self.gitignore_specs[path] = spec

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

        # Filter ignored
        filtered_folders = []
        for folder in folders:
            spec = self._get_gitignore_spec_for_path(folder)
            if not is_ignored(os.path.relpath(folder, start=os.path.dirname(folder)), spec):
                filtered_folders.append(folder)
        folders = filtered_folders

        filtered_files = []
        for file in files:
            spec = self._get_gitignore_spec_for_path(file)
            if not is_ignored(os.path.relpath(file, start=os.path.dirname(file)), spec):
                filtered_files.append(file)
        files = filtered_files

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

        # Load .gitignore for this folder
        spec = load_gitignore_patterns(folder)
        self.gitignore_specs[folder] = spec

        if self.nav_stack:
            # Create back item using FileListItem for consistent styling
            back_item = FileListItem("..")
            back_item.is_dir = True
            back_item.path = ".."  # avoid None assignment
            back_item.setFlags(back_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            style = QApplication.style()
            if style is not None:
                back_item.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
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

        spec = self._get_gitignore_spec_for_path(self.current_folder or "")

        for entry in valid_entries:
            if self.current_folder is None:
                continue
            full_path = os.path.join(self.current_folder, entry)
            rel_path = os.path.relpath(full_path, start=self.current_folder)
            if is_ignored(rel_path, spec):
                continue
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
        key = event.key()
        text = event.text()

        # Track 'd' press state
        if not hasattr(self, "_d_pressed_once"):
            self._d_pressed_once = False

        if text == "v":
            # Toggle visual mode
            self.toggle_visual_mode()
            return

        if text == "V":
            # Line visual mode (select all lines, similar to Vim's shift+V)
            self.toggle_visual_mode(True)
            return

        if text == "C":
            # Clear the list (new shortcut)
            self.clear_list()
            return

        if text == "d":
            if self._d_pressed_once:
                # Second 'd' press: delete selected items
                self.remove_selected_items()
                self._d_pressed_once = False
                return
            else:
                # First 'd' press: set flag and wait for next key
                self._d_pressed_once = True
                return
        else:
            # Reset 'd' press flag on any other key
            self._d_pressed_once = False

        if key == Qt.Key.Key_Escape:
            # Exit visual mode with Escape
            if self.visual_mode:
                self.exit_visual_mode()
                return

        if key == Qt.Key.Key_Delete:
            self.remove_selected_items()
            if self.visual_mode:
                self.exit_visual_mode()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_item = self.file_list.currentItem()
            if selected_item:
                self.on_item_double_clicked(selected_item)
                if self.visual_mode:
                    self.exit_visual_mode()
        elif key == Qt.Key.Key_Right or text == "l":
            selected_item = self.file_list.currentItem()
            try:
                if (
                    selected_item
                    and hasattr(selected_item, "is_dir")
                    and getattr(selected_item, "is_dir", False)
                    and selected_item.text() != ".."
                ):
                    self.on_item_double_clicked(selected_item)
                    self.file_list.setFocus()
                    if self.file_list.count() > (1 if self.nav_stack else 0):
                        self.file_list.setCurrentRow(1 if self.nav_stack else 0)
                        if self.visual_mode:
                            self.visual_anchor_row = self.file_list.currentRow()
                            self._update_visual_selection()
                else:
                    event.ignore()
            except (RuntimeError, AttributeError):
                event.ignore()
        elif key == Qt.Key.Key_Left or text == "h":
            if self.nav_stack:
                prev_state = self.nav_stack.pop()
                if isinstance(prev_state, (list, set)):
                    self.show_initial_items()
                elif prev_state is not None:
                    self.show_folder(prev_state)
                else:
                    self.show_initial_items()

                # Update visual selection anchor if in visual mode
                if self.visual_mode:
                    self.visual_anchor_row = 0
                    self._update_visual_selection()
            else:
                event.ignore()
        elif text == "j":
            current_row = self.file_list.currentRow()
            if current_row < self.file_list.count() - 1:
                self.file_list.setCurrentRow(current_row + 1)
                if self.visual_mode:
                    self._update_visual_selection()
        elif text == "k":
            current_row = self.file_list.currentRow()
            if current_row > 0:
                self.file_list.setCurrentRow(current_row - 1)
                if self.visual_mode:
                    self._update_visual_selection()
        elif text == "g":
            # Go to top
            if self.file_list.count() > 0:
                self.file_list.setCurrentRow(0)
                if self.visual_mode:
                    self._update_visual_selection()
        elif text == "G":
            # Go to bottom
            if self.file_list.count() > 0:
                self.file_list.setCurrentRow(self.file_list.count() - 1)
                if self.visual_mode:
                    self._update_visual_selection()
        elif text == "y":
            # Yank (copy) selected files
            if hasattr(self.parent, "generate_paths_text"):
                self.parent.generate_paths_text()
                # Exit visual mode after yanking
                if self.visual_mode:
                    self.exit_visual_mode()
        else:
            QListWidget.keyPressEvent(self.file_list, event)

    def toggle_visual_mode(self, select_all=False):
        """Toggle visual selection mode"""
        self.visual_mode = not self.visual_mode

        if self.visual_mode:
            # Enter visual mode
            current_row = self.file_list.currentRow()
            self.visual_anchor_row = current_row if not select_all else 0
            self.file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

            # Select current row or all rows
            self.file_list.clearSelection()
            if select_all:
                # Select all rows from current to end
                self.file_list.setCurrentRow(self.file_list.count() - 1)
            else:
                # Select only current row
                self.file_list.setCurrentRow(current_row)

            self._update_visual_selection()
        else:
            # Exit visual mode
            self.exit_visual_mode()

        self._update_status_bar()

    def exit_visual_mode(self):
        """Exit visual selection mode"""
        self.visual_mode = False
        self.visual_anchor_row = None
        self.file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._update_status_bar()

    def remove_selected_items(self):
        """Remove selected items from the list."""
        selected_items = self.file_list.selectedItems()[::-1]
        for item in selected_items:
            path = getattr(item, "path", None)
            if path:
                self.deleted_paths.add(path)
                if path in self.added_paths:
                    del self.added_paths[path]
                row = self.file_list.row(item)
                self.file_list.takeItem(row)

    def on_item_double_clicked(self, item):
        """Navigate into folder or go back if '..' is clicked."""
        if item.text() == "..":
            if self.nav_stack:
                prev_state = self.nav_stack.pop()
                if isinstance(prev_state, (list, set)):
                    self.show_initial_items()
                elif prev_state is not None:
                    self.show_folder(prev_state)
                else:
                    self.show_initial_items()
            return

        if hasattr(item, "is_dir") and getattr(item, "is_dir", False):
            if self.current_folder:
                self.nav_stack.append(self.current_folder)
            else:
                self.nav_stack.append(None)
            path = getattr(item, "path", None)
            if path is not None:
                self.show_folder(path)

    def get_all_included_files(self):
        """Collect all included file paths currently visible in the list, respecting .gitignore."""
        included_files = []

        def collect_files_from_folder(folder_path):
            try:
                entries = os.listdir(folder_path)
            except Exception:
                return
            spec = self._get_gitignore_spec_for_path(folder_path)
            for entry in entries:
                full_path = os.path.join(folder_path, entry)
                rel_path = os.path.relpath(full_path, start=folder_path)
                if is_ignored(rel_path, spec):
                    continue
                if full_path in self.deleted_paths:
                    continue
                if os.path.isdir(full_path):
                    collect_files_from_folder(full_path)
                elif not self.text_only or is_text_file(full_path):
                    included_files.append(full_path)

        # For each base path, recurse if folder, else add file
        for path in self.base_paths:
            if path in self.deleted_paths:
                continue
            if os.path.isdir(path):
                collect_files_from_folder(path)
            elif not self.text_only or is_text_file(path):
                included_files.append(path)

        return included_files

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

    def on_selection_changed(self):
        """Handle selection changes in the list widget."""
        # Update all items to reflect their current selection state
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            # Defensive: check update_widget_style exists on item
            if (
                item is not None
                and hasattr(item, "update_widget_style")
                and callable(getattr(item, "update_widget_style", None))
            ):
                try:
                    update_style = getattr(item, "update_widget_style", None)
                    is_selected = getattr(item, "isSelected", None)
                    if callable(update_style) and callable(is_selected):
                        update_style(is_selected())
                except AttributeError:
                    pass

    def _update_visual_selection(self):
        """Update selection range in visual mode."""
        if not self.visual_mode or self.visual_anchor_row is None:
            return

        current_row = self.file_list.currentRow()
        start = min(self.visual_anchor_row, current_row)
        end = max(self.visual_anchor_row, current_row)

        self.file_list.clearSelection()
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item:
                item.setSelected(start <= i <= end)

        # Show selection count in status bar but make it less prominent
        selected_count = len(self.file_list.selectedItems())
        if self.status_label and selected_count > 0:
            self.status_label.setText(f"visual: {selected_count}")
        else:
            self.status_label.setText("visual")
    def _get_gitignore_spec_for_path(self, path: str):
        """Return the PathSpec for the closest parent directory"""
        if not path:
            return None
        path = os.path.abspath(path)
        candidates = sorted(self.gitignore_specs.keys(), key=lambda p: -len(p))
        for base in candidates:
            if path.startswith(os.path.abspath(base)):
                return self.gitignore_specs.get(base)
        return None
