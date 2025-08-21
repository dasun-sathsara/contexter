from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QCheckBox,
    QGraphicsOpacityEffect,
    QLabel,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from src.utils.settings_manager import SettingsManager


class SettingsPanel(QWidget):
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Add a title
        title_label = QLabel("Settings")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Medium)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Add some spacing
        layout.addSpacing(10)

        # Create checkboxes with enhanced styling
        self.text_only_checkbox = self._create_animated_checkbox("Show text files only")
        self.text_only_checkbox.stateChanged.connect(
            lambda: self._animate_setting_change(
                lambda: self.settings_manager.set_setting(
                    "text_only", self.text_only_checkbox.isChecked()
                )
            )
        )
        layout.addWidget(self.text_only_checkbox)

        self.hide_empty_folders_checkbox = self._create_animated_checkbox(
            "Hide empty folders"
        )
        self.hide_empty_folders_checkbox.stateChanged.connect(
            lambda: self._animate_setting_change(
                lambda: self.settings_manager.set_setting(
                    "hide_empty_folders", self.hide_empty_folders_checkbox.isChecked()
                )
            )
        )
        layout.addWidget(self.hide_empty_folders_checkbox)

        self.show_token_count_checkbox = self._create_animated_checkbox(
            "Show token counts"
        )
        self.show_token_count_checkbox.stateChanged.connect(
            lambda: self._animate_setting_change(
                lambda: self.settings_manager.set_setting(
                    "show_token_count", self.show_token_count_checkbox.isChecked()
                )
            )
        )
        layout.addWidget(self.show_token_count_checkbox)

        self.dark_mode_checkbox = self._create_animated_checkbox("Dark mode")
        self.dark_mode_checkbox.stateChanged.connect(
            lambda: self._animate_setting_change(
                lambda: self.settings_manager.set_setting(
                    "dark_mode", self.dark_mode_checkbox.isChecked()
                )
            )
        )
        layout.addWidget(self.dark_mode_checkbox)

        layout.addStretch()

    def _create_animated_checkbox(self, text):
        """Create a checkbox with opacity animation capability."""
        checkbox = QCheckBox(text)

        # Add opacity effect for animations
        opacity_effect = QGraphicsOpacityEffect()
        checkbox.setGraphicsEffect(opacity_effect)

        # Store animation for later use
        animation = QPropertyAnimation(opacity_effect, b"opacity")
        animation.setDuration(120)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Store references
        checkbox._opacity_effect = opacity_effect
        checkbox._animation = animation

        return checkbox

    def _animate_setting_change(self, callback):
        """Animate a setting change with a brief highlight effect."""
        # Get the sender checkbox
        sender = self.sender()
        if hasattr(sender, "_animation"):
            # Brief fade effect to indicate change
            sender._animation.setStartValue(1.0)
            sender._animation.setEndValue(0.7)
            sender._animation.finished.connect(
                lambda: self._complete_animation(sender, callback)
            )
            sender._animation.start()
        else:
            callback()

    def _complete_animation(self, checkbox, callback):
        """Complete the animation and execute the callback."""
        checkbox._animation.finished.disconnect()
        callback()

        # Animate back to full opacity
        checkbox._animation.setStartValue(0.7)
        checkbox._animation.setEndValue(1.0)
        checkbox._animation.start()

    def load_settings(self):
        self.text_only_checkbox.setChecked(
            self.settings_manager.get_setting("text_only", True)
        )
        self.hide_empty_folders_checkbox.setChecked(
            self.settings_manager.get_setting("hide_empty_folders", True)
        )
        self.show_token_count_checkbox.setChecked(
            self.settings_manager.get_setting("show_token_count", True)
        )
        self.dark_mode_checkbox.setChecked(
            self.settings_manager.get_setting("dark_mode", False)
        )
