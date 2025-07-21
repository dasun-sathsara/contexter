import json
import os
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class SettingsManager(QObject):
    settings_changed = pyqtSignal()

    def __init__(self, file_path="settings.json"):
        super().__init__()
        self.file_path = file_path
        self.settings = {}
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._debounced_save)
        self.load_settings()

    def load_settings(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r") as f:
                self.settings = json.load(f)
        else:
            self.settings = self.get_default_settings()

    def save_settings(self):
        with open(self.file_path, "w") as f:
            json.dump(self.settings, f, indent=4)
        self.settings_changed.emit()

    def _debounced_save(self):
        """Internal method for debounced saving."""
        self.save_settings()

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value, *, defer=False, debounce_ms=300):
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            defer: If True, don't save immediately
            debounce_ms: Milliseconds to wait before saving (ignored if defer=True)
        """
        self.settings[key] = value
        if not defer:
            if debounce_ms > 0:
                # Use debounced saving to prevent excessive disk writes
                self._save_timer.start(debounce_ms)
            else:
                self.save_settings()

    def get_default_settings(self):
        return {
            "text_only": True,
            "hide_empty_folders": True,
            "dark_mode": False,
            "show_token_count": True,
        }
