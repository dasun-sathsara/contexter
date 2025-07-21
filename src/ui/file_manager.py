import os
from PyQt6.QtWidgets import QListWidget, QLabel, QStatusBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from typing import Set, Dict, Optional, List, Tuple
import threading
from concurrent.futures import ThreadPoolExecutor, Future, CancelledError

from src.models.file_list_item import FileListItem
from src.utils.file_operations import FileTreeBuilder
from src.utils.token_counter import count_tokens_in_file, count_tokens_in_folder
from src.utils.settings_manager import SettingsManager


class FileManager:
    def __init__(
        self,
        list_widget: QListWidget,
        parent,
        settings_manager: SettingsManager,
    ):
        self.file_list = list_widget
        self.parent = parent
        self.settings_manager = settings_manager
        self.added_paths: Dict[str, FileListItem] = {}
        self.deleted_paths: Set[str] = set()
        self.base_paths: Set[str] = set()
        self.current_folder: Optional[str] = None
        self.nav_stack: List[Optional[str]] = []

        self.visual_mode = False
        self.visual_anchor_row: Optional[int] = None
        self.status_bar: Optional[QStatusBar] = None
        self.status_label: Optional[QLabel] = None

        self.executor = ThreadPoolExecutor(
            max_workers=min(4, os.cpu_count() or 1),
            thread_name_prefix="FileManagerWorker",
        )
        self.token_futures: Dict[str, Future] = {}
        self._futures_lock = threading.Lock()  # Thread safety for token_futures

        self.setup_list_widget()
        self._setup_status_bar()

        self.tree_builder: Optional[FileTreeBuilder] = None

    def setup_list_widget(self):
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.file_list.setWordWrap(False)
        self.file_list.setUniformItemSizes(True)
        self.file_list.setBatchSize(100)
        self.file_list.setLayoutMode(QListWidget.LayoutMode.Batched)
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_list.itemSelectionChanged.connect(self.on_selection_changed)
        self._original_key_press_event = self.file_list.keyPressEvent
        self.file_list.keyPressEvent = self._list_key_press_event

    def _setup_status_bar(self):
        """Set up a status bar widget if the parent provides one."""
        if self.parent and hasattr(self.parent, "statusBar"):
            try:
                self.status_bar = self.parent.statusBar()
                self.status_label = QLabel("")
                # Add with stretch factor 0 to keep it on the right
                self.status_bar.addPermanentWidget(self.status_label, 0)
                self.status_label.hide()
            except Exception as e:
                print(f"Error setting up status bar: {e}")
                self.status_bar = None
                self.status_label = None

    def _update_status_bar_mode(self):
        """Update status bar with current Vim mode information."""
        if not self.status_label:
            return
        if self.visual_mode:
            selected_count = len(self.file_list.selectedItems())
            mode_text = (
                f"-- VISUAL -- ({selected_count} selected)"
                if selected_count > 0
                else "-- VISUAL --"
            )
            self.status_label.setText(mode_text)
            self.status_label.setStyleSheet(
                "padding: 1px 5px; background-color: #e74c3c; color: white; border-radius: 3px;"
            )
            self.status_label.show()
        else:
            self.status_label.setText("")
            self.status_label.hide()

    def _cancel_pending_futures(self):
        """Cancel all active token counting futures."""
        with self._futures_lock:
            for future in self.token_futures.values():
                if not future.done():
                    future.cancel()
            self.token_futures.clear()

    def add_files(self, paths: List[str]):
        """Adds new base paths, rebuilds the tree, and shows the root view."""
        self._cancel_pending_futures()  # Cancel any ongoing calculations
        self.deleted_paths.clear()  # Adding new paths usually implies a fresh start
        self.nav_stack = []  # Clear navigation history
        self.base_paths.update(paths)  # Add new paths to the set of roots

        self._rebuild_tree_and_refresh_view()

        self.set_status_message(f"Added {len(paths)} root item(s).", 3000)

    def _rebuild_tree_and_refresh_view(self):
        """Rebuilds the internal file tree and refreshes the list widget view."""
        self._cancel_pending_futures()

        if not self.base_paths:
            self.file_list.clear()
            self.added_paths.clear()
            self.tree_builder = None
            return

        self.tree_builder = FileTreeBuilder(
            self.base_paths,
            text_only=self.settings_manager.get_setting("text_only", True),
            hide_empty_folders=self.settings_manager.get_setting(
                "hide_empty_folders", True
            ),
            deleted_paths=self.deleted_paths,
        )
        try:
            self.tree_builder.build_tree()
        except Exception as e:
            self.set_status_message(f"Error building file tree: {e}", 5000)
            print(f"Error building file tree: {e}")
            self.tree_builder = None
            self.file_list.clear()
            return

        self._refresh_current_view()

    def _populate_list(self, items_to_display: List[str]):
        """Populates the QListWidget with the given item paths."""
        self.file_list.clear()
        self.added_paths.clear()
        self._cancel_pending_futures()  # Cancel previous calculations

        # Optimize bulk adding
        self.file_list.setUpdatesEnabled(False)  # Pause UI updates

        if self.current_folder and self.nav_stack:  # Add '..' if not at root
            back_item = FileListItem("..")
            self.file_list.addItem(back_item)
            self.file_list.setItemWidget(back_item, back_item.content_widget)

        item_widgets_to_add = []
        paths_for_token_calc = []

        for path in items_to_display:
            if path == "..":
                continue  # Already handled

            # Check if path exists before creating item - robustness
            if path not in self.deleted_paths and (
                os.path.exists(path) or os.path.islink(path)
            ):
                item = FileListItem(path)
                self.added_paths[path] = item
                item_widgets_to_add.append((item, item.content_widget))
                paths_for_token_calc.append(path)
            else:
                print(f"Skipping non-existent or deleted path during populate: {path}")

        # Add items in bulk
        for item, widget in item_widgets_to_add:
            self.file_list.addItem(item)
            self.file_list.setItemWidget(item, widget)

        self.file_list.setUpdatesEnabled(True)  # Resume UI updates

        # Select the first item (or second if '..' exists)
        if self.file_list.count() > 0:
            select_row = 1 if self.current_folder and self.nav_stack else 0
            if select_row < self.file_list.count():
                self.file_list.setCurrentRow(select_row)

        # Calculate token counts asynchronously if enabled
        if (
            self.settings_manager.get_setting("show_token_count", True)
            and paths_for_token_calc
        ):
            self.calculate_token_counts(paths_for_token_calc)

    def show_initial_items(self):
        """Shows the top-level items based on the current tree."""
        self.current_folder = None
        if not self.tree_builder:
            self._rebuild_tree_and_refresh_view()  # Ensure tree exists
            if not self.tree_builder:
                return  # Exit if rebuild failed

        tree = self.tree_builder.get_tree()
        if not tree:
            self.file_list.clear()
            self.added_paths.clear()
            return

        top_level_folders = sorted(tree.get("folders", {}).keys())
        top_level_files = sorted(tree.get("files", []))
        items_to_show = top_level_folders + top_level_files

        self._populate_list(items_to_show)

    def show_folder(self, folder_path: str):
        """Shows the contents of a specific folder based on the current tree."""
        if not folder_path or not self.tree_builder:
            self.show_initial_items()  # Fallback to root if path or tree is invalid
            return

        self.current_folder = folder_path
        subtree = self.tree_builder.find_subtree(folder_path)  # Use helper method

        if not subtree:
            self.set_status_message(
                f"Error: Could not find folder '{os.path.basename(folder_path)}' in tree.",
                3000,
            )
            self._populate_list([])
            return

        sub_folders = sorted(subtree.get("folders", {}).keys())
        sub_files = sorted(subtree.get("files", []))
        items_to_show = sub_folders + sub_files

        self._populate_list(items_to_show)

    def _refresh_current_view(self):
        """Refreshes the list widget to show the current folder or root."""
        if self.current_folder:
            self.show_folder(self.current_folder)
        else:
            self.show_initial_items()

    def clear_list(self):
        """Clears the entire list, state, and tree."""
        self._cancel_pending_futures()
        self.file_list.clear()
        self.added_paths.clear()
        self.deleted_paths.clear()
        self.base_paths.clear()
        self.current_folder = None
        self.nav_stack = []
        self.tree_builder = None  # Remove the tree
        self.exit_visual_mode()  # Ensure visual mode is off
        self.set_status_message("File list cleared.", 2000)

    def _list_key_press_event(self, event: QKeyEvent):
        """Handles key presses in the list widget for Vim-like navigation and actions."""
        key = event.key()
        text = event.text()

        # --- Mode Toggles ---
        if text == "v" and not self.visual_mode:
            self.enter_visual_mode()
        elif text == "V" and not self.visual_mode:
            self.enter_visual_mode(select_all_below=True)
        elif key == Qt.Key.Key_Escape and self.visual_mode:
            self.exit_visual_mode()

        # --- Actions ---
        elif text == "y":
            self._handle_yank()
        elif text == "C":
            self.clear_list()
        elif text == "d" or key == Qt.Key.Key_Delete:
            self._handle_delete()

        # --- Navigation ---
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._handle_navigation_into()
        elif key == Qt.Key.Key_Right or text == "l":
            self._handle_navigation_into()
        elif key == Qt.Key.Key_Left or text == "h":
            self.navigate_back()
        elif text == "j" or key == Qt.Key.Key_Down:
            self._move_selection(1)
        elif text == "k" or key == Qt.Key.Key_Up:
            self._move_selection(-1)
        elif text == "g":
            self._move_to_edge(start=True)
        elif text == "G":
            self._move_to_edge(start=False)

        # --- Fallback ---
        else:
            if self._original_key_press_event:
                self._original_key_press_event(event)
            else:
                QListWidget.keyPressEvent(self.file_list, event)
            return  # Return early to avoid calling event.accept() again

        event.accept()

    def _handle_yank(self):
        if self.parent and hasattr(self.parent, "generate_paths_text"):
            self.parent.generate_paths_text()
            if self.visual_mode:
                self.exit_visual_mode()
            self.set_status_message("Yanked selected items.", 2000)

    def _handle_delete(self):
        self.remove_selected_items()
        if self.visual_mode:
            self.exit_visual_mode()

    def _handle_navigation_into(self):
        selected_item = self.file_list.currentItem()
        if selected_item:
            self.on_item_double_clicked(selected_item)

    def _move_selection(self, delta: int):
        current_row = self.file_list.currentRow()
        new_row = current_row + delta
        if 0 <= new_row < self.file_list.count():
            self.file_list.setCurrentRow(new_row)
            if self.visual_mode:
                self._update_visual_selection()

    def _move_to_edge(self, start: bool):
        if self.file_list.count() > 0:
            new_row = 0 if start else self.file_list.count() - 1
            self.file_list.setCurrentRow(new_row)
            if self.visual_mode:
                self._update_visual_selection()

    def navigate_back(self):
        """Navigates to the previous folder in the history."""
        if self.nav_stack:
            # Pop the *current* folder from stack first if we are inside one
            # This logic might need adjustment based on how nav_stack is pushed
            # Let's assume stack holds the PARENT history
            parent_folder = self.nav_stack.pop()
            self.show_folder(
                parent_folder
            ) if parent_folder else self.show_initial_items()

            # Update visual anchor if needed
            if self.visual_mode:
                self.visual_anchor_row = self.file_list.currentRow()
                self._update_visual_selection()
        else:
            self.set_status_message("Already at root.", 1500)

    def enter_visual_mode(self, select_all_below=False):
        """Enters visual selection mode."""
        if self.visual_mode:
            return  # Already in visual mode
        self.visual_mode = True
        current_row = self.file_list.currentRow()
        self.visual_anchor_row = current_row
        # QListWidget needs MultiSelection for this to work visually, but ExtendedSelection allows more flexibility
        # self.file_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        # Clear existing selection and select the anchor row
        self.file_list.clearSelection()
        if current_row >= 0:
            item = self.file_list.item(current_row)
            if item:
                item.setSelected(True)

        if select_all_below:
            # Select from anchor to the end
            self.file_list.setCurrentRow(self.file_list.count() - 1)
            self._update_visual_selection()  # Explicit update needed after programmatic change

        self._update_status_bar_mode()
        self.on_selection_changed()  # Trigger selection count update

    def exit_visual_mode(self):
        """Exits visual selection mode."""
        if not self.visual_mode:
            return
        self.visual_mode = False
        self.visual_anchor_row = None
        # Restore selection mode if needed, ExtendedSelection is usually fine
        # self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        # Optionally clear selection on exit? Or keep it? Keep it for now.
        self._update_status_bar_mode()

    def remove_selected_items(self):
        """Removes selected items, updates state, and refreshes the view."""
        selected_indexes = self.file_list.selectedIndexes()
        if not selected_indexes:
            self.set_status_message("No items selected to remove.", 1500)
            return

        # Determine the row to select after deletion.
        # We'll select the item at the same row as the first deleted item.
        first_deleted_row = min(index.row() for index in selected_indexes)

        paths_to_delete = set()
        for index in selected_indexes:
            item = self.file_list.item(index.row())
            if (
                isinstance(item, FileListItem)
                and hasattr(item, "path")
                and item.path != ".."
            ):
                paths_to_delete.add(item.path)

        if not paths_to_delete:
            return

        count = len(paths_to_delete)
        self.deleted_paths.update(paths_to_delete)

        # Rebuild the tree and refresh the view to reflect deletions
        self._rebuild_tree_and_refresh_view()

        # After refresh, restore the selection to the correct position
        new_count = self.file_list.count()
        if new_count > 0:
            # Clamp the selection to the new list bounds
            row_to_select = min(first_deleted_row, new_count - 1)
            self.file_list.setCurrentRow(row_to_select)

        self.set_status_message(f"Removed {count} item(s).", 2000)

    def on_item_double_clicked(self, item):
        """Handles double-click: navigates into folders or back."""
        if not isinstance(item, FileListItem):
            return  # Should be FileListItem

        if item.path == "..":
            self.navigate_back()
        elif item.is_dir:
            # Push the *current* state onto the stack before navigating
            self.nav_stack.append(self.current_folder)
            # Navigate to the new folder
            self.show_folder(item.path)

    def get_all_included_files(self) -> List[str]:
        """Returns a flat list of all file paths currently included by the tree builder."""
        if self.tree_builder:
            # Ensure deleted paths are considered even if tree isn't rebuilt immediately
            all_files = self.tree_builder.get_flat_file_list()
            return [f for f in all_files if f not in self.deleted_paths]
        return []

    # --- Token Counting ---

    def calculate_token_counts(self, paths_to_process: List[str]):
        """Calculates token counts for the given paths using the thread pool."""
        if not self.settings_manager.get_setting("show_token_count", True):
            return

        for path in paths_to_process:
            if path in self.added_paths:
                item = self.added_paths[path]
                future = self.executor.submit(
                    self._token_count_worker, path, item.is_dir
                )
                with self._futures_lock:
                    self.token_futures[path] = future
                future.add_done_callback(self._on_token_future_done)

    def _token_count_worker(self, path: str, is_dir: bool) -> Tuple[str, int]:
        """Worker function executed in the thread pool to count tokens."""
        try:
            if is_dir:
                # Use the efficient count_tokens_in_folder function
                count = count_tokens_in_folder(
                    path,
                    text_only=self.settings_manager.get_setting("text_only", True),
                    deleted_paths=self.deleted_paths,
                )
            else:
                count = count_tokens_in_file(path)
            return path, count
        except Exception as e:
            print(f"Error counting tokens for {path}: {e}")
            return path, -1

    def _on_token_future_done(self, future: Future):
        """Callback executed when a token counting future completes."""
        if future.cancelled():
            return  # Do nothing if cancelled

        try:
            path, token_count = future.result()

            # Remove future from tracking dict (thread-safe)
            with self._futures_lock:
                if path in self.token_futures:
                    del self.token_futures[path]

            # Update the corresponding list item if it still exists
            if path in self.added_paths and token_count >= 0:
                item = self.added_paths[path]
                item.set_token_count(token_count)
            elif token_count < 0:
                print(f"Token counting failed for {path}")
                # Show error state on the item
                if path in self.added_paths:
                    item = self.added_paths[path]
                    item.token_label.setText("Error")

        except CancelledError:
            pass  # Ignore if cancelled
        except Exception as e:
            print(f"Error processing token count result: {e}")

    def on_selection_changed(self):
        """Handles changes in list widget selection."""
        # Update visual style for all items (needed for custom widget background)
        # This can be slightly costly if many items are visible.
        selected_count = 0
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if isinstance(item, FileListItem):
                is_selected = item.isSelected()
                item.update_widget_style(is_selected)
                if is_selected:
                    selected_count += 1

        # Update status bar with selection count if not in visual mode
        if not self.visual_mode:
            if selected_count > 0:
                self.set_status_message(
                    f"{selected_count} item(s) selected.", 0
                )  # Persistent message
            else:
                current_message = (
                    self.status_bar.currentMessage() if self.status_bar else ""
                )
                if "item(s) selected" in current_message:
                    self.status_bar.clearMessage()
        else:
            # Update visual mode status bar count
            self._update_status_bar_mode()

    def _update_visual_selection(self):
        """Updates the selection range when in visual mode and moving."""
        if not self.visual_mode or self.visual_anchor_row is None:
            return

        current_row = self.file_list.currentRow()
        start_row = min(self.visual_anchor_row, current_row)
        end_row = max(self.visual_anchor_row, current_row)

        # Optimize selection update
        self.file_list.setUpdatesEnabled(False)
        self.file_list.clearSelection()  # Clear previous visual selection first
        for i in range(start_row, end_row + 1):
            item = self.file_list.item(i)
            if item:
                item.setSelected(True)
        self.file_list.setUpdatesEnabled(True)

        # Ensure the current row (cursor position) is visible
        self.file_list.scrollToItem(
            self.file_list.item(current_row), QListWidget.ScrollHint.EnsureVisible
        )

        # Update status bar count immediately
        self._update_status_bar_mode()

    def set_status_message(self, message: str, timeout: int = 0):
        """Displays a message in the status bar."""
        if self.status_bar:
            self.status_bar.showMessage(message, timeout)

    def shutdown(self):
        """Clean up resources like the thread pool."""
        print("Shutting down FileManager executor...")
        self._cancel_pending_futures()
        self.executor.shutdown(wait=True)
        print("FileManager executor shut down complete.")
