import textwrap
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QProgressDialog,
    QStatusBar,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.ui.drop_zone import DropZone
from src.ui.theme_manager import ThemeManager
from src.ui.settings_panel import SettingsPanel
from src.ui.file_manager import FileManager
from src.utils.file_system_worker import FileSystemWorker


class FileDropApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Drop Interface")
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)

        # Initialize theme state before setup_ui
        self._is_dark_mode = False

        # Create status bar
        self.statusBar().showMessage("")

        self.setup_ui()

        # Apply initial theme
        ThemeManager.apply_light_theme(self)

    def setup_ui(self):
        # Set up the UI with tabs
        self.tab_widget = QTabWidget()

        # Main tab
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)

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
        self.file_manager = FileManager(self.file_list, self)

        main_layout.addWidget(header_label)
        main_layout.addWidget(self.drop_zone)
        main_layout.addWidget(list_header)
        main_layout.addWidget(self.file_list)

        # Add a keyboard shortcut hint label
        shortcut_label = QLabel(
            "Vim Shortcuts: v (visual mode), V (select all lines), y (copy), C (clear list), d+d (delete), Esc (exit mode)"
        )
        shortcut_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcut_label.setStyleSheet("color: #666; font-size: 10.5px;")
        main_layout.addWidget(shortcut_label)

        # Add a loading indicator
        self.loading_label = QLabel("Processing...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setVisible(False)  # Initially hidden
        main_layout.addWidget(self.loading_label)

        # Settings tab
        self.settings_panel = SettingsPanel()
        # Initialize checkbox state
        self.settings_panel.dark_mode_checkbox.setChecked(self._is_dark_mode)
        self.settings_panel.text_only_changed.connect(self.on_text_only_changed)
        self.settings_panel.hide_empty_folders_changed.connect(
            self.on_hide_empty_folders_changed
        )
        self.settings_panel.theme_changed.connect(self.toggle_dark_mode)
        self.settings_panel.show_token_count_changed.connect(
            self.on_show_token_count_changed
        )

        # Add tabs to tab widget
        self.tab_widget.addTab(main_tab, "Main")
        self.tab_widget.addTab(self.settings_panel, "Settings")
        self.setCentralWidget(self.tab_widget)

    def add_files(self, paths):
        """Add files and folders to the list."""
        self.file_manager.add_files(paths)

    def on_text_only_changed(self, state):
        """Handle change in the text-only checkbox state."""
        self.file_manager.text_only = state == Qt.CheckState.Checked.value
        if self.file_manager.current_folder is not None:
            self.file_manager.show_folder(self.file_manager.current_folder)
        else:
            self.file_manager.show_initial_items()

    def on_hide_empty_folders_changed(self, state):
        """Handle change in the hide-empty-folders checkbox state."""
        self.file_manager.hide_empty_folders = state == Qt.CheckState.Checked.value
        if self.file_manager.current_folder is not None:
            self.file_manager.show_folder(self.file_manager.current_folder)
        else:
            self.file_manager.show_initial_items()

    def on_show_token_count_changed(self, state):
        """Handle change in the show-token-count checkbox state."""
        self.file_manager.on_show_token_count_changed(
            state == Qt.CheckState.Checked.value
        )

    def toggle_dark_mode(self, state):
        """Toggle between light and dark mode."""
        self._is_dark_mode = state  # Use the Boolean value directly
        if self._is_dark_mode:
            ThemeManager.apply_dark_theme(self)
        else:
            ThemeManager.apply_light_theme(self)

    def generate_paths_text(self):
        """Generate text of all included file contents and copy to clipboard."""
        files = self.file_manager.get_all_included_files()
        if not files:
            return

        # Show the loading indicator
        self.loading_label.setVisible(True)

        # Save file list for later use in _on_merge_completed
        self._merge_files_list = list(files)

        self.worker = FileSystemWorker("merge_files", files)
        self.worker.finished.connect(self._on_merge_completed_wrapper)
        self.worker.progress.connect(
            lambda value: None
        )  # Placeholder for progress updates
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_merge_completed(self, text):
        """Handle completion of file merging."""
        # Hide the loading indicator
        self.loading_label.setVisible(False)

        # The worker returns the merged content of all files as one string.
        # To improve organization, we need to split it back into per-file content.
        # But since the worker returns a single merged string, we can't do that here.
        # So just copy the merged text as-is.
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
        self.statusBar().showMessage("File contents copied to clipboard.", 3000)

    def _on_error(self, error_message):
        """Handle file system operation errors."""
        # Hide the loading indicator
        self.loading_label.setVisible(False)

        self.statusBar().showMessage(f"Error: {error_message}", 5000)
    def _on_merge_completed_wrapper(self, merged_text):
        """Reorganize merged text by file and copy to clipboard."""
        # Hide the loading indicator
        self.loading_label.setVisible(False)

        # Compose output with file headers
        output_lines = ["===== Combined File Contents =====\n"]
        offset = 0
        for idx, file_path in enumerate(self._merge_files_list, 1):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                content = "[Error reading file]"
            output_lines.append(f"\n--- File {idx}: {file_path} ---\n")
            output_lines.append(content.strip() + "\n")
        output_lines.append("\n===== End =====\n")
        improved_text = "\n".join(output_lines)

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(improved_text)
        self.statusBar().showMessage("File contents copied to clipboard.", 3000)
