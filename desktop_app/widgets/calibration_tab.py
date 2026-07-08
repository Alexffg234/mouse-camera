from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QSpinBox, QPushButton, QLabel, QMessageBox)


class CalibrationTab(QWidget):
    calibration_requested = None  # no-emit, handled by main_window

    def __init__(self, config, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        cal = config.get("calibration", {})
        form = QFormLayout()
        self.min_x_spin = QSpinBox()
        self.min_x_spin.setRange(0, 10000)
        self.min_x_spin.setValue(cal.get("min_x", 0))

        self.max_x_spin = QSpinBox()
        self.max_x_spin.setRange(0, 10000)
        self.max_x_spin.setValue(cal.get("max_x", 1920))

        self.min_y_spin = QSpinBox()
        self.min_y_spin.setRange(0, 10000)
        self.min_y_spin.setValue(cal.get("min_y", 0))

        self.max_y_spin = QSpinBox()
        self.max_y_spin.setRange(0, 10000)
        self.max_y_spin.setValue(cal.get("max_y", 1080))

        form.addRow("最小 X:", self.min_x_spin)
        form.addRow("最大 X:", self.max_x_spin)
        form.addRow("最小 Y:", self.min_y_spin)
        form.addRow("最大 Y:", self.max_y_spin)
        layout.addLayout(form)

        # Resolution display
        self.res_label = QLabel()
        self._update_res()
        layout.addWidget(self.res_label)

        btn_layout = QHBoxLayout()
        self.detect_btn = QPushButton("自动检测屏幕尺寸")
        self.detect_btn.clicked.connect(self._auto_detect)
        btn_layout.addWidget(self.detect_btn)
        layout.addLayout(btn_layout)

    def _update_res(self):
        w = self.max_x_spin.value() - self.min_x_spin.value()
        h = self.max_y_spin.value() - self.min_y_spin.value()
        self.res_label.setText(f"当前分辨率: {w} x {h}")
        self.res_label.setStyleSheet("color: #aaa; font-family: monospace;")

    def _auto_detect(self):
        try:
            import pyautogui
            w, h = pyautogui.size()
            self.min_x_spin.setValue(0)
            self.max_x_spin.setValue(w)
            self.min_y_spin.setValue(0)
            self.max_y_spin.setValue(h)
            self._update_res()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法检测屏幕: {e}")

    def collect(self) -> dict:
        return {
            "calibration": {
                "min_x": self.min_x_spin.value(),
                "max_x": self.max_x_spin.value(),
                "min_y": self.min_y_spin.value(),
                "max_y": self.max_y_spin.value(),
            }
        }

    def load_config(self, config: dict):
        cal = config.get("calibration", {})
        self.min_x_spin.setValue(cal.get("min_x", 0))
        self.max_x_spin.setValue(cal.get("max_x", 1920))
        self.min_y_spin.setValue(cal.get("min_y", 0))
        self.max_y_spin.setValue(cal.get("max_y", 1080))
        self._update_res()
