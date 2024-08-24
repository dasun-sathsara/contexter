from PyQt6.QtWidgets import QWidget, QVBoxLayout, QCheckBox
from PyQt6.QtCore import pyqtSignal


class SettingsPanel(QWidget):
    text_only_changed = pyqtSignal(bool)
    hide_empty_folders_changed = pyqtSignal(bool)
    theme_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Text files only filter
        self.text_only_checkbox = QCheckBox("Show text files only")
        self.text_only_checkbox.setChecked(True)
        self.text_only_checkbox.stateChanged.connect(self.text_only_changed.emit)
        layout.addWidget(self.text_only_checkbox)

        # Hide empty folders filter
        self.hide_empty_folders_checkbox = QCheckBox("Hide empty folders")
        self.hide_empty_folders_checkbox.setChecked(True)
        self.hide_empty_folders_checkbox.stateChanged.connect(
            self.hide_empty_folders_changed.emit
        )
        layout.addWidget(self.hide_empty_folders_checkbox)

        # Dark mode toggle
        self.dark_mode_checkbox = QCheckBox("Dark mode")
        self.dark_mode_checkbox.stateChanged.connect(self.theme_changed.emit)
        layout.addWidget(self.dark_mode_checkbox)

        layout.addStretch()
