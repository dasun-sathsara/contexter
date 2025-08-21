from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QApplication,
    QStyle,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
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

        # Animation properties
        self._opacity = 1.0
        self._scale = 1.0

        # Setup animations
        self.opacity_animation = QPropertyAnimation(self, b"opacity")
        self.opacity_animation.setDuration(120)
        self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.scale_animation = QPropertyAnimation(self, b"scale")
        self.scale_animation.setDuration(100)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.OutBack)

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
        font.setPointSize(13)
        font.setWeight(QFont.Weight.Medium)
        self.text_label.setFont(font)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.setContentsMargins(20, 20, 20, 20)

        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(230, 240, 250))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)

    @pyqtProperty(float)
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, value):
        self._scale = value
        # Apply scale transform to the content
        transform = f"QFrame {{ transform: scale({value}); }}"
        self.setStyleSheet(self.styleSheet() + transform)

    def dragEnterEvent(self, a0: "QDragEnterEvent | None"):
        if (
            a0 is not None
            and a0.mimeData() is not None
            and hasattr(a0.mimeData(), "hasUrls")
            and callable(getattr(a0.mimeData(), "hasUrls", None))
            and getattr(a0.mimeData(), "hasUrls", lambda: False)()
        ):
            # Animate to highlight state
            self.setStyleSheet(
                "QFrame { background-color: #d0e7f7; border: 2px dashed #308cc6; }"
            )
            self.scale_animation.setStartValue(1.0)
            self.scale_animation.setEndValue(1.02)
            self.scale_animation.start()

            self.opacity_animation.setStartValue(1.0)
            self.opacity_animation.setEndValue(0.9)
            self.opacity_animation.start()

            a0.accept()
        elif a0 is not None:
            a0.ignore()

    def dragLeaveEvent(self, a0: "QDragLeaveEvent | None"):
        # Animate back to normal state
        self.setStyleSheet("")
        self.scale_animation.setStartValue(self._scale)
        self.scale_animation.setEndValue(1.0)
        self.scale_animation.start()

        self.opacity_animation.setStartValue(self._opacity)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()

        if a0 is not None:
            a0.accept()

    def dropEvent(self, a0: "QDropEvent | None"):
        # Quick success animation
        self.setStyleSheet("")
        self.scale_animation.setStartValue(self._scale)
        self.scale_animation.setEndValue(0.95)
        self.scale_animation.finished.connect(lambda: self._bounce_back())
        self.scale_animation.start()

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

    def _bounce_back(self):
        """Helper method to complete the drop animation bounce effect."""
        self.scale_animation.finished.disconnect()
        self.scale_animation.setStartValue(0.95)
        self.scale_animation.setEndValue(1.0)
        self.scale_animation.start()

        self.opacity_animation.setStartValue(self._opacity)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.start()
