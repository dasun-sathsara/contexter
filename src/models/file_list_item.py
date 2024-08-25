import os
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

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.name = os.path.basename(path)
        self.is_dir = os.path.isdir(path)
        self.token_count = None

        # Create widget to hold the content
        self.content_widget = QWidget()
        layout = QHBoxLayout(self.content_widget)
        # Increase vertical padding significantly and adjust spacing
        layout.setContentsMargins(4, 8, 8, 8)
        layout.setSpacing(6)

        # Create labels for the name and token count
        self.name_label = QLabel(self.name)
        self.token_label = QLabel()
        self.token_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        # Set minimum height for labels to prevent text cutoff
        self.name_label.setMinimumHeight(20)
        self.token_label.setMinimumHeight(20)

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.token_label)

        # Set appropriate icon
        if self.is_dir:
            self.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            )
        else:
            self.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            )

        self.setToolTip(path)
        self.update_display_text()

        # Ensure minimum height for the widget
        self.content_widget.setMinimumHeight(36)
        # Set size hint for proper layout
        self.setSizeHint(self.content_widget.sizeHint())

    def update_display_text(self):
        if self.token_count is not None:
            if self.token_count >= 1000:
                token_display = f"{self.token_count / 1000:.1f}k"
            else:
                token_display = str(self.token_count)
            # Adjust font size and add padding to prevent text cutoff
            self.token_label.setStyleSheet("""
                font-size: 0.9rem;
                color: #888;
                padding: 2px 0;
            """)
            self.token_label.setText(token_display)
        else:
            self.token_label.setText("")

    def set_token_count(self, count):
        """Set the token count and update display."""
        self.token_count = count
        self.update_display_text()
