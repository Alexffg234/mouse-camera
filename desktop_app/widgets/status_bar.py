from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatusBarWidget(QWidget):
    """Custom status bar showing gesture, action, confidence, hold, and FPS."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.gesture_label = QLabel("手势: --")
        self.gesture_label.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: bold;")

        self.action_label = QLabel("操作: --")
        self.action_label.setStyleSheet("color: #facc15; font-size: 13px; font-weight: bold;")

        self.conf_label = QLabel("置信度: --")
        self.conf_label.setStyleSheet("color: #93c5fd; font-size: 13px;")

        self.hold_label = QLabel("")
        self.hold_label.setStyleSheet("color: #f97316; font-size: 13px;")

        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #aaa; font-size: 13px;")

        layout.addWidget(self.gesture_label)
        layout.addSpacing(20)
        layout.addWidget(self.action_label)
        layout.addSpacing(20)
        layout.addWidget(self.conf_label)
        layout.addSpacing(20)
        layout.addWidget(self.hold_label)
        layout.addStretch()
        layout.addWidget(self.fps_label)

    def update(self, gesture: str, action: str, confidence: float, hold_progress: float,
               user_status: dict, fps: float):
        self.gesture_label.setText(f"手势: {gesture or '--'}")

        if confidence < 1.0 and gesture:
            self.conf_label.setText(f"置信度: {confidence:.0%}")
        else:
            self.conf_label.setText("")

        self.action_label.setText(f"操作: {action or '--'}")
        self.fps_label.setText(f"FPS: {fps:.0f}")

        if hold_progress > 0:
            self.hold_label.setText(f"长按: {hold_progress:.0%}")
        else:
            self.hold_label.setText("")
