import json
import os
from PyQt6.QtCore import QObject, pyqtSignal

class SettingsManager(QObject):
    settings_changed = pyqtSignal()

    def __init__(self, file_path='settings.json'):
        super().__init__()
        self.file_path = file_path
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = self.get_default_settings()

    def save_settings(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.settings, f, indent=4)
        self.settings_changed.emit()

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    def get_default_settings(self):
        return {
            'text_only': True,
            'hide_empty_folders': True,
            'dark_mode': False,
            'show_token_count': True,
        }
