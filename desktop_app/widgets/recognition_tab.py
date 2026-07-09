from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QSlider,
                              QLabel, QSpinBox)
from PyQt6.QtCore import Qt


class RecognitionTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.margin_label = QLabel("1.05")
        self.margin_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.margin_slider = QSlider(Qt.Orientation.Horizontal)
        self.margin_slider.setRange(100, 120)
        r = config.get("recognizer", {})
        self.margin_slider.setValue(int(r.get("finger_margin", 1.05) * 100))
        self.margin_slider.valueChanged.connect(lambda v: self.margin_label.setText(f"{v / 100:.2f}"))

        self.frames_label = QLabel("3")
        self.frames_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.frames_slider = QSlider(Qt.Orientation.Horizontal)
        self.frames_slider.setRange(1, 7)
        self.frames_slider.setValue(r.get("stability_frames", 3))
        self.frames_slider.valueChanged.connect(lambda v: self.frames_label.setText(str(v)))

        form = QFormLayout()
        form.addRow("手指伸展阈值:", self.margin_slider)
        form.addRow(self.margin_label, QWidget())
        help1 = QLabel("如果 OK 和捏合容易混淆，调大此值（更严格）")
        help1.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow(help1)
        form.addRow("稳定帧数:", self.frames_slider)
        form.addRow(self.frames_label, QWidget())
        help2 = QLabel("增加帧数可以减少手势闪烁，但会略微增加延迟")
        help2.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow(help2)
        layout.addLayout(form)
        layout.addStretch()

    def collect(self) -> dict:
        return {
            "recognizer": {
                "finger_margin": self.margin_slider.value() / 100,
                "stability_frames": self.frames_slider.value(),
            }
        }

    def load_config(self, config: dict):
        r = config.get("recognizer", {})
        self.margin_slider.setValue(int(r.get("finger_margin", 1.05) * 100))
        self.margin_label.setText(f"{r.get('finger_margin', 1.05):.2f}")
        self.frames_slider.setValue(r.get("stability_frames", 3))
        self.frames_label.setText(str(r.get("stability_frames", 3)))
