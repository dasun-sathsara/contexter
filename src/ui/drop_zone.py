from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication, QStyle
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QFont,
    QColor,
    QPalette,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDropEvent,
)


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
        style = QApplication.style()
        if style is not None:
            self.icon_label.setPixmap(
                style.standardPixmap(QStyle.StandardPixmap.SP_DirOpenIcon).scaled(
                    48, 48, Qt.AspectRatioMode.KeepAspectRatio
                )
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

    def dragEnterEvent(self, a0: "QDragEnterEvent | None"):
        if (
            a0 is not None
            and a0.mimeData() is not None
            and hasattr(a0.mimeData(), "hasUrls")
            and callable(getattr(a0.mimeData(), "hasUrls", None))
            and getattr(a0.mimeData(), "hasUrls", lambda: False)()
        ):
            self.setStyleSheet(
                "QFrame { background-color: #d0e7f7; border: 2px dashed #308cc6; }"
            )
            a0.accept()
        elif a0 is not None:
            a0.ignore()

    def dragLeaveEvent(self, a0: "QDragLeaveEvent | None"):
        self.setStyleSheet("")
        if a0 is not None:
            a0.accept()

    def dropEvent(self, a0: "QDropEvent | None"):
        self.setStyleSheet("")
        if (
            a0 is not None
            and a0.mimeData() is not None
            and hasattr(a0.mimeData(), "hasUrls")
            and callable(getattr(a0.mimeData(), "hasUrls", None))
            and getattr(a0.mimeData(), "hasUrls", lambda: False)()
            and hasattr(a0.mimeData(), "urls")
            and callable(getattr(a0.mimeData(), "urls", None))
        ):
            urls = a0.mimeData().urls()
            paths = [url.toLocalFile() for url in urls]
            self.callback_function(paths)
            a0.accept()
        elif a0 is not None:
            a0.ignore()
