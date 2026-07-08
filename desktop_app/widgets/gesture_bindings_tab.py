from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                              QComboBox, QLabel, QPushButton, QScrollArea,
                              QFrame, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal

from gesture_mapper import GestureMapper

GESTURE_LABELS = {
    "open_palm": "摊手掌", "index_finger": "食指", "middle_index": "食中指",
    "pinch": "捏合", "fist": "握拳", "ok_sign": "OK", "thumb_up": "赞",
    "two_fingers": "两指", "palm_up": "掌心朝上", "palm_down": "掌心朝下",
    "palm_left": "掌心朝左", "palm_right": "掌心朝右",
    "swipe_up": "上滑", "swipe_down": "下滑", "swipe_left": "左滑", "swipe_right": "右滑",
    "pinch_hold": "捏合长按",
}

ACTION_LABELS = {
    "move_cursor": "移动光标", "left_click": "左键点击", "right_click": "右键点击",
    "double_click": "双击", "scroll_up": "向上滚动", "scroll_down": "向下滚动",
    "drag": "拖拽", "show_desktop": "显示桌面",
    "copy": "复制 (Ctrl+C)", "paste": "粘贴 (Ctrl+V)", "cut": "剪切 (Ctrl+X)",
}

MODE_LABELS = {
    "instant": "瞬时", "hold": "长按", "follow": "跟随", "swipe": "滑动", "transition": "过渡",
}


class BindingRow(QFrame):
    """One row for configuring a single action binding."""

    def __init__(self, action: str, parent=None):
        super().__init__(parent)
        self.action = action
        self.setObjectName("binding_row")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout(self)

        # Header: checkbox + action name
        header = QHBoxLayout()
        self.enabled_cb = QCheckBox(ACTION_LABELS.get(action, action))
        self.enabled_cb.setChecked(True)
        self.enabled_cb.setStyleSheet("font-weight: bold; font-size: 13px;")
        header.addWidget(self.enabled_cb)
        header.addStretch()
        layout.addLayout(header)

        # Mode select
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("模式:"))
        self.mode_cb = QComboBox()
        for m in GestureMapper.VALID_MODES:
            self.mode_cb.addItem(MODE_LABELS[m], m)
        mode_layout.addWidget(self.mode_cb)
        layout.addLayout(mode_layout)

        # Gesture from
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("手势:"))
        self.from_cb = QComboBox()
        for g in GestureMapper.SUPPORTED_GESTURES:
            self.from_cb.addItem(GESTURE_LABELS.get(g, g) + f" ({g})", g)
        from_layout.addWidget(self.from_cb)
        layout.addLayout(from_layout)

        # Gesture to (for transition)
        self.to_widget = QWidget()
        self.to_layout = QHBoxLayout(self.to_widget)
        self.to_layout.addWidget(QLabel("目标手势:"))
        self.to_cb = QComboBox()
        for g in GestureMapper.SUPPORTED_GESTURES:
            self.to_cb.addItem(GESTURE_LABELS.get(g, g) + f" ({g})", g)
        self.to_layout.addWidget(self.to_cb)
        layout.addWidget(self.to_widget)

        # Mode-specific params
        self.hold_widget = QWidget()
        self.hold_layout = QHBoxLayout(self.hold_widget)
        self.hold_layout.addWidget(QLabel("长按时长 (ms):"))
        self.hold_ms_input = QComboBox()
        for v in [300, 500, 800, 1000, 1500, 2000]:
            self.hold_ms_input.addItem(f"{v} ms", v)
        self.hold_layout.addWidget(self.hold_ms_input)
        layout.addWidget(self.hold_widget)

        self.landmark_widget = QWidget()
        self.landmark_layout = QHBoxLayout(self.landmark_widget)
        self.landmark_layout.addWidget(QLabel("关键点:"))
        self.landmark_cb = QComboBox()
        self.landmark_cb.addItem("食指指尖", "index_tip")
        self.landmark_cb.addItem("中指指尖", "middle_tip")
        self.landmark_cb.addItem("掌心", "palm_center")
        self.landmark_layout.addWidget(self.landmark_cb)
        layout.addWidget(self.landmark_widget)

        self.swipe_widget = QWidget()
        self.swipe_layout = QHBoxLayout(self.swipe_widget)
        self.swipe_layout.addWidget(QLabel("方向:"))
        self.swipe_cb = QComboBox()
        self.swipe_cb.addItem("上滑 ↑", "up")
        self.swipe_cb.addItem("下滑 ↓", "down")
        self.swipe_cb.addItem("左滑 ←", "left")
        self.swipe_cb.addItem("右滑 →", "right")
        self.swipe_layout.addWidget(self.swipe_cb)
        layout.addWidget(self.swipe_widget)

        self.timeout_widget = QWidget()
        self.timeout_layout = QHBoxLayout(self.timeout_widget)
        self.timeout_layout.addWidget(QLabel("超时 (ms):"))
        self.timeout_input = QComboBox()
        for v in [500, 1000, 2000, 3000]:
            self.timeout_input.addItem(f"{v} ms", v)
        self.timeout_layout.addWidget(self.timeout_input)
        layout.addWidget(self.timeout_widget)

        self.mode_cb.currentTextChanged.connect(self._on_mode_change)
        self._on_mode_change()

    def _on_mode_change(self):
        mode = self.mode_cb.currentData()
        self.to_widget.setVisible(mode == "transition")
        self.hold_widget.setVisible(mode == "hold")
        self.landmark_widget.setVisible(mode == "follow")
        self.swipe_widget.setVisible(mode == "swipe")
        self.timeout_widget.setVisible(mode == "transition")
        # Non-transition: from = to
        if mode != "transition":
            gesture = self.from_cb.currentData()
            if gesture:
                idx = self.to_cb.findData(gesture)
                if idx >= 0:
                    self.to_cb.setCurrentIndex(idx)

    def get_trigger(self) -> dict:
        mode = self.mode_cb.currentData()
        gesture = self.from_cb.currentData()
        trigger = {
            "from": gesture,
            "to": self.to_cb.currentData() if mode == "transition" else gesture,
            "mode": mode,
        }
        if mode == "hold":
            trigger["hold_ms"] = self.hold_ms_input.currentData()
        elif mode == "follow":
            trigger["landmark"] = self.landmark_cb.currentData()
        elif mode == "swipe":
            trigger["swipe_direction"] = self.swipe_cb.currentData()
        elif mode == "transition":
            trigger["timeout_ms"] = self.timeout_input.currentData()
        return trigger

    def set_trigger(self, trigger: dict):
        mode = trigger.get("mode", "instant")
        mode_idx = self.mode_cb.findData(mode)
        if mode_idx >= 0:
            self.mode_cb.setCurrentIndex(mode_idx)

        from_idx = self.from_cb.findData(trigger.get("from", "open_palm"))
        if from_idx >= 0:
            self.from_cb.setCurrentIndex(from_idx)

        to_idx = self.to_cb.findData(trigger.get("to", trigger.get("from", "open_palm")))
        if to_idx >= 0:
            self.to_cb.setCurrentIndex(to_idx)

        if mode == "hold":
            v = trigger.get("hold_ms", 800)
            idx = self.hold_ms_input.findData(v)
            if idx >= 0:
                self.hold_ms_input.setCurrentIndex(idx)
        elif mode == "follow":
            landmark = trigger.get("landmark", "index_tip")
            idx = self.landmark_cb.findData(landmark)
            if idx >= 0:
                self.landmark_cb.setCurrentIndex(idx)
        elif mode == "swipe":
            d = trigger.get("swipe_direction", "up")
            idx = self.swipe_cb.findData(d)
            if idx >= 0:
                self.swipe_cb.setCurrentIndex(idx)
        elif mode == "transition":
            t = trigger.get("timeout_ms", 2000)
            idx = self.timeout_input.findData(t)
            if idx >= 0:
                self.timeout_input.setCurrentIndex(idx)

    def is_enabled(self) -> bool:
        return self.enabled_cb.isChecked()


class GestureBindingsTab(QWidget):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config

        layout = QVBoxLayout(self)

        # Legend
        legend = QLabel(
            "瞬时: 检测到立即触发  |  长按: 保持 N ms 后触发  |  "
            "跟随: 持续跟随关键点  |  滑动: 手势+方向  |  过渡: A→B 手势切换"
        )
        legend.setStyleSheet("color: #aaa; font-size: 12px; padding: 4px; "
                             "background: #2a2a2a; border-radius: 6px;")
        layout.addWidget(legend)

        # Scrollable list of bindings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        self.rows_layout = QVBoxLayout(container)
        self.rows: dict[str, BindingRow] = {}
        self._build_rows()
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _build_rows(self):
        gm = self._config.get("gesture_mouse_map", {})
        for action in GestureMapper.VALID_ACTIONS:
            row = BindingRow(action)
            if action in gm:
                row.set_trigger(gm[action].get("trigger", {}))
            self.rows[action] = row
            self.rows_layout.addWidget(row)

    def collect_config(self) -> dict:
        gm = {}
        for action, row in self.rows.items():
            if row.is_enabled():
                gm[action] = {"trigger": row.get_trigger()}
        return gm

    def load_config(self, config: dict):
        self._config = config
        gm = config.get("gesture_mouse_map", {})
        for action, row in self.rows.items():
            if action in gm:
                row.set_trigger(gm[action].get("trigger", {}))
                row.enabled_cb.setChecked(True)
            else:
                row.enabled_cb.setChecked(False)
