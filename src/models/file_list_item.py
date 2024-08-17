import os
from PyQt6.QtWidgets import QApplication, QListWidgetItem, QStyle


class FileListItem(QListWidgetItem):
    """Custom list item to display file/folder info."""

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path
        self.name = os.path.basename(path)
        self.is_dir = os.path.isdir(path)
        self.setText(self.name)
        if self.is_dir:
            self.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            )
        else:
            self.setIcon(
                QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            )
        self.setToolTip(path)
