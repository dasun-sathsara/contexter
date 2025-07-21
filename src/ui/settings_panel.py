from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from PyQt6.QtCore import Qt

from src.utils.settings_manager import SettingsManager


class SettingsPanel(QWidget):
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.text_only_checkbox = QCheckBox("Show text files only")
        self.text_only_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_setting(
                'text_only', self.text_only_checkbox.isChecked()
            )
        )
        layout.addWidget(self.text_only_checkbox)

        self.hide_empty_folders_checkbox = QCheckBox("Hide empty folders")
        self.hide_empty_folders_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_setting(
                'hide_empty_folders', self.hide_empty_folders_checkbox.isChecked()
            )
        )
        layout.addWidget(self.hide_empty_folders_checkbox)

        self.show_token_count_checkbox = QCheckBox("Show token counts")
        self.show_token_count_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_setting(
                'show_token_count', self.show_token_count_checkbox.isChecked()
            )
        )
        layout.addWidget(self.show_token_count_checkbox)

        self.dark_mode_checkbox = QCheckBox("Dark mode")
        self.dark_mode_checkbox.stateChanged.connect(
            lambda: self.settings_manager.set_setting(
                'dark_mode', self.dark_mode_checkbox.isChecked()
            )
        )
        layout.addWidget(self.dark_mode_checkbox)

        layout.addStretch()

    def load_settings(self):
        self.text_only_checkbox.setChecked(
            self.settings_manager.get_setting('text_only', True)
        )
        self.hide_empty_folders_checkbox.setChecked(
            self.settings_manager.get_setting('hide_empty_folders', True)
        )
        self.show_token_count_checkbox.setChecked(
            self.settings_manager.get_setting('show_token_count', True)
        )
        self.dark_mode_checkbox.setChecked(
            self.settings_manager.get_setting('dark_mode', False)
        )
