import os
from typing import Optional, cast
from PyQt6.QtWidgets import (
    QApplication,
    QListWidgetItem,
    QStyle,
    QWidget,
    QHBoxLayout,
    QLabel,
)
from PyQt6.QtCore import Qt


class FileListItem(QListWidgetItem):
    """Custom list item to display file/folder info."""

    def __init__(self, path: str, parent: Optional[QListWidgetItem] = None):
        super().__init__(parent)
        self.path: str = path
        self.name: str = os.path.basename(path)
        self.is_dir: bool = os.path.isdir(path)
        self.token_count: Optional[int] = None

        # Create widget to hold the content
        self.content_widget = QWidget()
        layout = QHBoxLayout(self.content_widget)
        layout.setContentsMargins(4, 8, 8, 8)
        layout.setSpacing(6)

        # Create labels for the name and token count
        self.name_label = QLabel(self.name)
        self.token_label = QLabel()
        self.token_label.setObjectName("token_label")
        self.token_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        # Set minimum height for labels to prevent text cutoff
        self.name_label.setMinimumHeight(20)
        self.token_label.setMinimumHeight(20)

        # Improve font and style
        font = self.name_label.font()
        font.setPointSize(11)  # slightly larger font
        self.name_label.setFont(font)
        self.token_label.setFont(font)

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.token_label)

        # Set appropriate icon
        style = QApplication.style()
        if style is not None:
            if self.is_dir:
                self.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
                )
            else:
                self.setIcon(
                    style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
                )

        # Improve tooltip with relative path if possible
        try:
            rel_path = os.path.relpath(path)
            self.setToolTip(rel_path)
        except Exception:
            self.setToolTip(path)

        self.update_display_text()

        # Ensure minimum height for the widget
        self.content_widget.setMinimumHeight(36)
        # Set size hint for proper layout
        self.setSizeHint(self.content_widget.sizeHint())

        # Initialize selection state
        self.update_widget_style(False)

    def update_display_text(self):
        if self.token_count is not None:
            if self.token_count >= 1000:
                token_display = f"{self.token_count / 1000:.1f}k"
            else:
                token_display = str(self.token_count)
            self.token_label.setText(token_display)
        else:
            self.token_label.setText("")

    def update_widget_style(self, is_selected: bool):
        """Update the widget style based on selection state."""
        # Use dynamic property to handle selection state
        self.content_widget.setProperty("selected", is_selected)
        # Force style refresh
        style = self.content_widget.style()
        if style is not None:
            style.unpolish(self.content_widget)
            style.polish(self.content_widget)

    def set_token_count(self, count: int):
        """Set the token count and update display."""
        self.token_count = count
        self.update_display_text()
