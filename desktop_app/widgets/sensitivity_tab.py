from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QSlider,
                              QLabel, QDoubleSpinBox, QSpinBox)
from PyQt6.QtCore import Qt


class SensitivityTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.cursor_speed_label = QLabel("1.5")
        self.cursor_speed_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.cursor_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.cursor_speed_slider.setRange(5, 50)
        self.cursor_speed_slider.setValue(int(config.get("sensitivity", {}).get("cursor_speed", 1.5) * 10))
        self.cursor_speed_slider.valueChanged.connect(lambda v: self.cursor_speed_label.setText(f"{v / 10:.1f}"))

        self.scroll_speed_label = QLabel("3")
        self.scroll_speed_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.scroll_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.scroll_speed_slider.setRange(1, 10)
        self.scroll_speed_slider.setValue(config.get("sensitivity", {}).get("scroll_speed", 3))
        self.scroll_speed_slider.valueChanged.connect(lambda v: self.scroll_speed_label.setText(str(v)))

        self.smoothing_label = QLabel("0.30")
        self.smoothing_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.smoothing_slider.setRange(5, 100)
        self.smoothing_slider.setValue(int(config.get("sensitivity", {}).get("smoothing_factor", 0.3) * 100))
        self.smoothing_slider.valueChanged.connect(lambda v: self.smoothing_label.setText(f"{v / 100:.2f}"))

        form = QFormLayout()
        form.addRow("光标速度:", self.cursor_speed_slider)
        form.addRow(self.cursor_speed_label, QWidget())
        form.addRow("滚动速度:", self.scroll_speed_slider)
        form.addRow(self.scroll_speed_label, QWidget())
        form.addRow("平滑系数:", self.smoothing_slider)
        form.addRow(self.smoothing_label, QWidget())
        layout.addLayout(form)
        layout.addStretch()

    def collect(self) -> dict:
        return {
            "sensitivity": {
                "cursor_speed": self.cursor_speed_slider.value() / 10,
                "scroll_speed": self.scroll_speed_slider.value(),
                "smoothing_factor": self.smoothing_slider.value() / 100,
            }
        }

    def load_config(self, config: dict):
        s = config.get("sensitivity", {})
        self.cursor_speed_slider.setValue(int(s.get("cursor_speed", 1.5) * 10))
        self.cursor_speed_label.setText(f"{s.get('cursor_speed', 1.5):.1f}")
        self.scroll_speed_slider.setValue(s.get("scroll_speed", 3))
        self.scroll_speed_label.setText(str(s.get("scroll_speed", 3)))
        self.smoothing_slider.setValue(int(s.get("smoothing_factor", 0.3) * 100))
        self.smoothing_label.setText(f"{s.get('smoothing_factor', 0.3):.2f}")
