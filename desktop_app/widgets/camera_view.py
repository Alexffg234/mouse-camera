import numpy as np
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from desktop_app.overlay_renderer import pixmap_from_frame


class CameraView(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #1a1a1a;")
        self.setScaledContents(False)

    def update_frame(self, frame_bgr: np.ndarray):
        """Update with raw BGR frame (overlay already drawn)."""
        width = self.width()
        height = self.height()
        if width == 0 or height == 0:
            return
        pixmap = pixmap_from_frame(frame_bgr, width, height)
        self.setPixmap(pixmap)

    def show_message(self, text: str):
        self.clear()
        self.setText(text)
        self.setStyleSheet("background-color: #1a1a1a; color: #888; font-size: 18px;")
