import cv2
import numpy as np
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import Qt


def frame_to_qimage(frame_bgr: np.ndarray) -> QImage:
    """Convert OpenCV BGR ndarray to QImage for QLabel display."""
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w, channels = rgb.shape
    bytes_per_line = channels * w
    return QImage(rgb.data.tobytes(), w, h, bytes_per_line,
                  QImage.Format.Format_RGB888)


def pixmap_from_frame(frame_bgr: np.ndarray, label_width: int, label_height: int) -> QPixmap:
    """Convert BGR frame to scaled QPixmap fitting the label dimensions."""
    qimage = frame_to_qimage(frame_bgr)
    pixmap = QPixmap.fromImage(qimage)
    return pixmap.scaled(label_width, label_height, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
