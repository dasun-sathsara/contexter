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
        self.setMinimumSize(500, 500)

        # Initialize theme state before setup_ui
        self._is_dark_mode = False
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

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.generate_button = QPushButton("Generate")
        self.generate_button.clicked.connect(self.generate_paths_text)
        button_layout.addWidget(self.generate_button)
        self.clear_button = QPushButton("Clear List")
        self.clear_button.clicked.connect(self.file_manager.clear_list)
        button_layout.addWidget(self.clear_button)

        main_layout.addWidget(header_label)
        main_layout.addWidget(self.drop_zone)
        main_layout.addWidget(list_header)
        main_layout.addWidget(self.file_list)
        main_layout.addLayout(button_layout)

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

        self.worker = FileSystemWorker("merge_files", files)
        self.worker.finished.connect(self._on_merge_completed)
        self.worker.progress.connect(
            lambda value: None
        )  # Placeholder for progress updates
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_merge_completed(self, text):
        """Handle completion of file merging."""
        # Hide the loading indicator
        self.loading_label.setVisible(False)

        QApplication.clipboard().setText(text)
        print("File contents copied to clipboard.")

    def _on_error(self, error_message):
        """Handle file system operation errors."""
        # Hide the loading indicator
        self.loading_label.setVisible(False)

        print(f"Error: {error_message}")
