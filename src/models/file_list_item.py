import os
from typing import Optional
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
        self.name: str = ".." if path == ".." else os.path.basename(path)
        self.is_dir: bool = False
        if path != "..":
            try:
                self.is_dir = os.path.isdir(path)
            except OSError:
                self.is_dir = False  # Default assumption if path is problematic
        elif path == "..":
            self.is_dir = True  # Special case for back navigation

        self.token_count: Optional[int] = None

        self.content_widget = QWidget()
        layout = QHBoxLayout(self.content_widget)
        layout.setContentsMargins(4, 8, 8, 8)
        layout.setSpacing(6)

        self.name_label = QLabel(self.name)
        self.token_label = QLabel()
        self.token_label.setObjectName("token_label")
        self.token_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.name_label.setMinimumHeight(20)
        self.token_label.setMinimumHeight(20)

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
                self.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirIcon))
            else:
                self.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))

        # Improve tooltip with relative path if possible
        if path != "..":
            try:
                # Attempt to get relative path from a sensible base if possible
                # This part is context dependent, using absolute for now
                self.setToolTip(os.path.abspath(path))
            except Exception:
                self.setToolTip(path)
        else:
            self.setToolTip("Go back to parent folder")

        self.update_display_text()

        self.content_widget.setMinimumHeight(36)
        self.setSizeHint(self.content_widget.sizeHint())

        # Initialize selection state
        self.update_widget_style(False)

    def update_display_text(self):
        """Updates the text displayed in the token label."""
        if self.token_count is not None:
            if self.token_count >= 1000:
                token_display = f"{self.token_count / 1000:.1f}k"
            else:
                token_display = str(self.token_count)
            self.token_label.setText(token_display)
        else:
            self.token_label.setText("")  # Clear if no token count

    def update_widget_style(self, is_selected: bool):
        """Update the widget style based on selection state."""
        # Use dynamic property to handle selection state in stylesheets
        self.content_widget.setProperty("selected", is_selected)

        # Force style refresh only if the style actually exists
        style = self.content_widget.style()
        if style is not None:
            style.unpolish(self.content_widget)
            style.polish(self.content_widget)
        else:
            # Fallback if style is somehow None (shouldn't happen in normal Qt app)
            bg_color = (
                "#e7f0fa" if is_selected else "transparent"
            )  # Example light theme colors
            self.content_widget.setStyleSheet(
                f"QWidget {{ background-color: {bg_color}; }}"
            )

    def set_token_count(self, count: int):
        """Set the token count and update display."""
        self.token_count = count
        self.update_display_text()
