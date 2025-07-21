from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QTabWidget,
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
from src.utils.settings_manager import SettingsManager


class FileDropApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Drop Interface")
        self.resize(1000, 800)
        self.setMinimumSize(800, 600)

        self.settings_manager = SettingsManager()
        self.settings_manager.settings_changed.connect(self.on_settings_changed)

        self.statusBar().showMessage("")
        self.setup_ui()
        self.load_initial_settings()

    def setup_ui(self):
        self.tab_widget = QTabWidget()
        main_tab = self.create_main_tab()
        self.settings_panel = SettingsPanel(self.settings_manager)

        self.tab_widget.addTab(main_tab, "Main")
        self.tab_widget.addTab(self.settings_panel, "Settings")
        self.setCentralWidget(self.tab_widget)

    def create_main_tab(self):
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)

        header_label = QLabel("File & Folder Drop Zone")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.drop_zone = DropZone(self.add_files)
        self.file_list = QListWidget()
        self.file_manager = FileManager(
            self.file_list, self, self.settings_manager
        )

        main_layout.addWidget(header_label)
        main_layout.addWidget(self.drop_zone)
        main_layout.addWidget(QLabel("Files and Folders:"))
        main_layout.addWidget(self.file_list)

        shortcut_label = QLabel(
            "Vim Shortcuts: v (visual), V (select all), y (yank), C (clear), d (delete), Esc (exit mode)"
        )
        shortcut_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        shortcut_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(shortcut_label)

        self.loading_label = QLabel("Processing...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setVisible(False)
        main_layout.addWidget(self.loading_label)

        return main_tab

    def add_files(self, paths):
        """Callback function to add files from the drop zone."""
        if self.file_manager:
            self.file_manager.add_files(paths)

    def load_initial_settings(self):
        self.on_settings_changed()

    def on_settings_changed(self):
        dark_mode = self.settings_manager.get_setting('dark_mode', False)
        if dark_mode:
            ThemeManager.apply_dark_theme(self)
        else:
            ThemeManager.apply_light_theme(self)
        self.file_manager._rebuild_tree_and_refresh_view()

    def generate_paths_text(self):
        files = self.file_manager.get_all_included_files()
        if not files:
            return

        self.loading_label.setVisible(True)
        self.worker = FileSystemWorker("merge_files", files)
        self.worker.finished.connect(self._on_merge_completed)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_merge_completed(self, text):
        self.loading_label.setVisible(False)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
        self.statusBar().showMessage("File contents copied to clipboard.", 3000)

    def _on_error(self, error_message):
        self.loading_label.setVisible(False)
        self.statusBar().showMessage(f"Error: {error_message}", 5000)
