import os
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication, QStyle
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette


class DropZone(QFrame):
    """Custom widget that accepts drag and drop for files and folders."""

    def __init__(self, callback_function, parent=None):
        super().__init__(parent)
        self.callback_function = callback_function
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        self.icon_label = QLabel()
        self.icon_label.setPixmap(
            QApplication.style()
            .standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon)
            .scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio)
        )
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel("Drag & Drop Files and Folders Here")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        self.text_label.setFont(font)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.setContentsMargins(20, 20, 20, 20)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(230, 240, 250))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet(
                "QFrame { background-color: #d0e7f7; border: 2px dashed #308cc6; }"
            )
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        event.accept()

    def dropEvent(self, event):
        self.setStyleSheet("")
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = [url.toLocalFile() for url in urls]
            self.callback_function(paths)
            event.accept()
        else:
            event.ignore()
