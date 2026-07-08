from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QSlider,
                              QLabel, QSpinBox, QCheckBox)
from PyQt6.QtCore import Qt


class TrackingTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        tr = config.get("tracking", {})
        ma = config.get("multi_angle", {})

        form = QFormLayout()

        self.max_hands_spin = QSpinBox()
        self.max_hands_spin.setRange(1, 4)
        self.max_hands_spin.setValue(tr.get("max_hands", 2))
        form.addRow("最大追踪手数:", self.max_hands_spin)

        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(0, 2000)
        self.debounce_spin.setSingleStep(50)
        self.debounce_spin.setValue(tr.get("debounce_ms", 150))
        form.addRow("防抖间隔 (ms):", self.debounce_spin)

        self.lock_timeout_spin = QSpinBox()
        self.lock_timeout_spin.setRange(0, 10000)
        self.lock_timeout_spin.setSingleStep(500)
        self.lock_timeout_spin.setValue(tr.get("user_lock_timeout_ms", 3000))
        form.addRow("用户锁定超时 (ms):", self.lock_timeout_spin)

        self.hand_conf_label = QLabel(f"{tr.get('min_hand_confidence', 0.5):.2f}")
        self.hand_conf_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.hand_conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.hand_conf_slider.setRange(10, 100)
        self.hand_conf_slider.setValue(int(tr.get("min_hand_confidence", 0.5) * 100))
        form.addRow("手部检测置信度:", self.hand_conf_slider)
        form.addRow(self.hand_conf_label, QWidget())

        self.tracking_conf_label = QLabel(f"{tr.get('min_tracking_confidence', 0.5):.2f}")
        self.tracking_conf_label.setStyleSheet("color: #60a5fa; font-family: monospace;")
        self.tracking_conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.tracking_conf_slider.setRange(10, 100)
        self.tracking_conf_slider.setValue(int(tr.get("min_tracking_confidence", 0.5) * 100))
        form.addRow("追踪置信度:", self.tracking_conf_slider)
        form.addRow(self.tracking_conf_label, QWidget())

        self.hot_reload_cb = QCheckBox("配置热加载")
        self.hot_reload_cb.setChecked(tr.get("config_hot_reload", True))
        form.addRow(self.hot_reload_cb)

        self.use_3d_cb = QCheckBox("使用 3D 深度")
        self.use_3d_cb.setChecked(ma.get("use_3d_depth", True))
        form.addRow(self.use_3d_cb)

        self.palm_threshold_spin = QSpinBox()
        self.palm_threshold_spin.setRange(10, 180)
        self.palm_threshold_spin.setValue(ma.get("palm_orientation_threshold_deg", 60))
        form.addRow("手掌方向阈值 (°):", self.palm_threshold_spin)

        layout.addLayout(form)
        layout.addStretch()

    def collect(self) -> dict:
        return {
            "tracking": {
                "max_hands": self.max_hands_spin.value(),
                "debounce_ms": self.debounce_spin.value(),
                "user_lock_timeout_ms": self.lock_timeout_spin.value(),
                "min_hand_confidence": self.hand_conf_slider.value() / 100,
                "min_tracking_confidence": self.tracking_conf_slider.value() / 100,
                "config_hot_reload": self.hot_reload_cb.isChecked(),
            },
            "multi_angle": {
                "use_3d_depth": self.use_3d_cb.isChecked(),
                "palm_orientation_threshold_deg": self.palm_threshold_spin.value(),
            },
        }

    def load_config(self, config: dict):
        tr = config.get("tracking", {})
        ma = config.get("multi_angle", {})
        self.max_hands_spin.setValue(tr.get("max_hands", 2))
        self.debounce_spin.setValue(tr.get("debounce_ms", 150))
        self.lock_timeout_spin.setValue(tr.get("user_lock_timeout_ms", 3000))
        self.hand_conf_slider.setValue(int(tr.get("min_hand_confidence", 0.5) * 100))
        self.tracking_conf_slider.setValue(int(tr.get("min_tracking_confidence", 0.5) * 100))
        self.hot_reload_cb.setChecked(tr.get("config_hot_reload", True))
        self.use_3d_cb.setChecked(ma.get("use_3d_depth", True))
        self.palm_threshold_spin.setValue(ma.get("palm_orientation_threshold_deg", 60))
