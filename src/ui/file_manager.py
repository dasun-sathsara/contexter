import os
from PyQt6.QtWidgets import QListWidget, QApplication, QLabel, QStatusBar
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QColor
from PyQt6.QtWidgets import QStyle
from typing import Set, Dict, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, Future, CancelledError

from src.models.file_list_item import FileListItem
from src.utils.file_system_worker import FileSystemWorker
from src.utils.file_operations import FileTreeBuilder, is_text_file
from src.utils.token_counter import count_tokens_in_file, count_tokens_in_folder


class FileManager:
    def __init__(self, list_widget: QListWidget, parent=None):
        self.file_list = list_widget
        self.parent = parent  # Reference to the main window (FileDropApp)
        self.added_paths: Dict[
            str, FileListItem
        ] = {}  # Path -> ListWidgetItem mapping for quick access
        self.deleted_paths: Set[str] = (
            set()
        )  # Stores paths explicitly deleted by the user
        self.base_paths: Set[str] = set()  # Top-level paths added by the user
        self.current_folder: Optional[str] = (
            None  # Path of the currently viewed folder, None for root
        )
        self.nav_stack: List[Optional[str]] = []  # History for back navigation

        # Settings state
        self.text_only = True
        self.hide_empty_folders = True
        self.show_token_count = True

        # Vim visual mode state
        self.visual_mode = False
        self.visual_anchor_row: Optional[int] = None
        self.status_bar: Optional[QStatusBar] = None
        self.status_label: Optional[QLabel] = None

        # Use a thread pool for concurrent operations like token counting
        # Adjust max_workers based on typical core counts or desired responsiveness
        self.executor = ThreadPoolExecutor(
            max_workers=os.cpu_count() or 4, thread_name_prefix="FileManagerWorker"
        )
        self.token_futures: Dict[str, Future] = {}  # path -> Future for token counting

        # Setup list widget properties
        self.file_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )  # Allow multi-select generally
        self.file_list.setTextElideMode(
            Qt.TextElideMode.ElideMiddle
        )  # Better for long names
        self.file_list.setWordWrap(False)
        self.file_list.setUniformItemSizes(
            True
        )  # Performance optimization if items are similar height
        self.file_list.setBatchSize(100)  # Performance for large lists
        self.file_list.setLayoutMode(QListWidget.LayoutMode.Batched)  # Performance

        # Connect signals
        self.file_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.file_list.itemSelectionChanged.connect(self.on_selection_changed)

        # Override keyPressEvent for Vim bindings
        # Keep the original implementation for fallback
        self._original_key_press_event = self.file_list.keyPressEvent
        self.file_list.keyPressEvent = self._list_key_press_event  # type: ignore

        # Vim 'd' press state tracking
        self._d_pressed_once = False
        self._d_press_timer = QTimer()
        self._d_press_timer.setSingleShot(True)
        self._d_press_timer.setInterval(500)  # 0.5 second window for 'dd'
        self._d_press_timer.timeout.connect(self._reset_d_press)

        self._setup_status_bar()

        # File tree builder instance
        self.tree_builder: Optional[FileTreeBuilder] = None

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

    def _reset_d_press(self):
        """Reset the flag indicating 'd' was pressed once."""
        self._d_pressed_once = False

    def _cancel_pending_futures(self):
        """Cancel all active token counting futures."""
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

        # Show temporary loading state?
        # self.file_list.clear()
        # self.file_list.addItem("Building file tree...")

        # Rebuild the tree with current settings and deleted paths
        self.tree_builder = FileTreeBuilder(
            self.base_paths,
            text_only=self.text_only,
            hide_empty_folders=self.hide_empty_folders,
            deleted_paths=self.deleted_paths,
        )
        # Building the tree can take time, consider a worker thread if it blocks UI significantly
        # For now, assume it's fast enough for typical cases.
        try:
            self.tree_builder.build_tree()
        except Exception as e:
            self.set_status_message(f"Error building file tree: {e}", 5000)
            print(f"Error building file tree: {e}")
            self.tree_builder = None  # Invalidate tree on error
            self.file_list.clear()
            return

        # Refresh the view (root or current folder)
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
        if self.show_token_count and paths_for_token_calc:
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
        tree = self.tree_builder.get_tree()
        subtree = self.tree_builder.find_subtree(folder_path)  # Use helper method

        if not subtree:
            self.set_status_message(
                f"Error: Could not find folder '{os.path.basename(folder_path)}' in tree.",
                3000,
            )
            # Maybe navigate back automatically? Or just show empty?
            # Let's show empty for now, with the '..' item
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
        text = event.text()  # Gets the character, respects modifiers like Shift

        # --- Visual Mode Toggles ---
        if text == "v" and not self.visual_mode:
            self.enter_visual_mode()
            event.accept()
            return
        elif (
            text == "V" and not self.visual_mode
        ):  # Visual Line Mode (select all below)
            self.enter_visual_mode(select_all_below=True)
            event.accept()
            return
        elif key == Qt.Key.Key_Escape and self.visual_mode:
            self.exit_visual_mode()
            event.accept()
            return

        # --- Actions ---
        if text == "y":  # Yank (Copy)
            if self.parent and hasattr(self.parent, "generate_paths_text"):
                self.parent.generate_paths_text()  # Assuming this handles selection logic
                if self.visual_mode:
                    self.exit_visual_mode()  # Exit visual mode after yanking
                self.set_status_message("Yanked selected items.", 2000)
            event.accept()
            return
        elif text == "C":  # Clear List (Shift+c equivalent)
            self.clear_list()
            event.accept()
            return
        elif text == "d":  # Delete Action (single 'd')
            self.remove_selected_items()
            if self.visual_mode:
                self.exit_visual_mode()  # Exit visual mode after deleting
            event.accept()
            return
        elif key == Qt.Key.Key_Delete:  # Standard Delete key
            self.remove_selected_items()
            if self.visual_mode:
                self.exit_visual_mode()
            event.accept()
            return

        # --- Navigation ---
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_item = self.file_list.currentItem()
            if selected_item:
                self.on_item_double_clicked(selected_item)
                # Don't exit visual mode on enter/navigate
            event.accept()
            return
        elif key == Qt.Key.Key_Right or text == "l":  # Navigate into folder
            selected_item = self.file_list.currentItem()
            if (
                selected_item
                and getattr(selected_item, "is_dir", False)
                and selected_item.text() != ".."
            ):
                self.on_item_double_clicked(selected_item)
            event.accept()
            return
        elif key == Qt.Key.Key_Left or text == "h":  # Navigate back
            self.navigate_back()
            event.accept()
            return
        elif text == "j" or key == Qt.Key.Key_Down:  # Move Down
            current_row = self.file_list.currentRow()
            if current_row < self.file_list.count() - 1:
                self.file_list.setCurrentRow(current_row + 1)
                if self.visual_mode:
                    self._update_visual_selection()
            event.accept()
            return
        elif text == "k" or key == Qt.Key.Key_Up:  # Move Up
            current_row = self.file_list.currentRow()
            if current_row > 0:
                self.file_list.setCurrentRow(current_row - 1)
                if self.visual_mode:
                    self._update_visual_selection()
            event.accept()
            return
        elif text == "g":  # Go to Top (first item)
            if self.file_list.count() > 0:
                self.file_list.setCurrentRow(0)
                if self.visual_mode:
                    self._update_visual_selection()
            event.accept()
            return
        elif text == "G":  # Go to Bottom (last item)
            if self.file_list.count() > 0:
                self.file_list.setCurrentRow(self.file_list.count() - 1)
                if self.visual_mode:
                    self._update_visual_selection()
            event.accept()
            return

        # If no custom binding handled, fall back to default behavior
        if not event.isAccepted():
            if self._original_key_press_event:
                self._original_key_press_event(event)
            else:
                # Fallback if original somehow missing
                QListWidget.keyPressEvent(self.file_list, event)

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
            # Maybe beep or show status message "Already at root"
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
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            self.set_status_message("No items selected to remove.", 1500)
            return

        count = 0
        paths_to_delete = set()
        for item in selected_items:
            # Ensure it's a FileListItem and not the '..' item
            if (
                isinstance(item, FileListItem)
                and hasattr(item, "path")
                and item.path != ".."
            ):
                paths_to_delete.add(item.path)
                count += 1

        if not paths_to_delete:
            return

        self.deleted_paths.update(paths_to_delete)

        # Rebuild the tree and refresh the view to reflect deletions
        # This is crucial for consistency, especially with 'hide empty folders'
        self._rebuild_tree_and_refresh_view()

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
        if not self.show_token_count:
            return

        # Cancel futures for paths no longer visible or relevant?
        # For simplicity, let's just not submit if a future already exists and isn't done.
        # A more robust approach might involve tracking visible items vs futures.

        for path in paths_to_process:
            if path in self.added_paths and path not in self.token_futures:
                item = self.added_paths[path]
                # Clear existing count visually while calculating
                item.set_token_count(
                    -1
                )  # Use -1 or None to indicate loading? Let's use None.
                item.token_count = None
                item.update_display_text()

                # Submit task to executor
                future = self.executor.submit(
                    self._token_count_worker, path, item.is_dir
                )
                self.token_futures[path] = future
                # Add callback to handle result when done
                future.add_done_callback(self._on_token_future_done)

    def _token_count_worker(self, path: str, is_dir: bool) -> Tuple[str, int]:
        """Worker function executed in the thread pool to count tokens."""
        try:
            if is_dir:
                # Pass current filters/state if needed by the counter function
                count = count_tokens_in_folder(path, self.text_only, self.deleted_paths)
            else:
                # Only count if it's a text file (if filter enabled)
                if not self.text_only or is_text_file(path):
                    count = count_tokens_in_file(path)
                else:
                    count = 0  # Don't count non-text files if filter is on
            return path, count
        except Exception as e:
            print(f"Error counting tokens for {path}: {e}")
            return path, -1  # Indicate error with -1

    def _on_token_future_done(self, future: Future):
        """Callback executed when a token counting future completes."""
        if future.cancelled():
            # print(f"Token count future cancelled.")
            return  # Do nothing if cancelled

        try:
            path, token_count = future.result()

            # Remove future from tracking dict
            if path in self.token_futures:
                del self.token_futures[path]

            # Update the corresponding list item if it still exists
            if path in self.added_paths and token_count >= 0:
                item = self.added_paths[path]
                item.set_token_count(token_count)
            elif token_count < 0:
                print(f"Token counting failed for {path}")
                # Optionally show error state on the item
                if path in self.added_paths:
                    item = self.added_paths[path]
                    item.token_label.setText("Error")

        except CancelledError:
            # print(f"Token count future cancelled (caught in callback).")
            pass  # Ignore if cancelled
        except Exception as e:
            print(f"Error processing token count result: {e}")
            # Attempt to remove future if result() failed but key exists
            # This part is tricky; need to associate future back to path if result fails early
            # A safer way is to pass path within the callback closure if possible,
            # or iterate futures dict, but that's less efficient.

    def on_show_token_count_changed(self, state: bool):
        """Handles changes to the 'Show token count' setting."""
        self.show_token_count = state
        self._cancel_pending_futures()  # Stop any ongoing calculations

        # If enabling, calculate for all visible items. If disabling, clear counts.
        if state:
            # Recalculate for currently visible items
            visible_paths = list(self.added_paths.keys())
            self.calculate_token_counts(visible_paths)
        else:
            # Clear token display for all visible items
            for item in self.added_paths.values():
                item.token_count = None
                item.update_display_text()

    def on_settings_changed(self):
        """Called when text_only or hide_empty_folders setting changes."""
        self._rebuild_tree_and_refresh_view()

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
                # Clear message if nothing is selected (unless another persistent message exists)
                # This needs careful handling not to overwrite important messages.
                # Maybe only clear if the current message is a selection count message.
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
