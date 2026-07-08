from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QProgressBar, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

TUTORIAL_STEPS = [
    {"title": "欢迎使用手势鼠标控制", "desc": "通过摄像头捕捉你的手势来操控鼠标。让我们花 1 分钟了解基本手势。", "emoji": "👋", "target": None},
    {"title": "移动光标 — 食指", "desc": "伸出食指，摄像头会追踪你的指尖位置，光标会随之移动。", "emoji": "☝️", "action": "移动光标", "target": "index_finger", "tip": "只有食指伸直，其余手指握紧"},
    {"title": "左键点击 — 捏合", "desc": "拇指和食指捏在一起，松开即完成点击。", "emoji": "🤏", "action": "左键点击", "target": "pinch", "tip": "捏合后自然松开即可"},
    {"title": "右键点击 — OK 手势", "desc": "拇指和食指指尖相触成圈，其余三指伸直。", "emoji": "👌", "action": "右键点击", "target": "ok_sign", "tip": "食指要弯曲成圈，不要伸直"},
    {"title": "双击 — 握拳长按", "desc": "握紧拳头并保持不动 800ms，进度满后触发双击。", "emoji": "✊", "action": "双击", "target": "fist", "tip": "保持握拳不要松手"},
    {"title": "滚动 — 两指滑动", "desc": "伸出食指和中指，手掌上下滑动来滚动页面。", "emoji": "✌️", "action": "向上/下滚动", "target": "two_fingers", "tip": "两指并拢伸直，用手掌整体移动"},
    {"title": "拖拽 — 捏合保持", "desc": "拇指和食指持续捏合超过 300ms 后进入拖拽模式。", "emoji": "🤏", "action": "拖拽", "target": "pinch", "tip": "捏合后不要松开，保持住再移动"},
    {"title": "显示桌面 — 摊手变握拳", "desc": "先摊开手掌，然后握紧拳头。在 2 秒内完成过渡即可触发。", "emoji": "🤚✊", "action": "显示桌面", "target": "fist", "transition_from": "open_palm", "tip": "先摊手，再握拳"},
    {"title": "准备好开始", "desc": "现在你已经了解了所有手势，可以开始使用了。", "emoji": "🎉", "target": "open_palm", "tip": "可以在设置面板查看和调整手势绑定"},
]


class OnboardingWizard(QWidget):
    finished = pyqtSignal()
    gesture_match = pyqtSignal()

    def __init__(self, camera_view: "CameraView", parent=None):
        super().__init__(parent)
        self._camera_view = camera_view
        self._step = 0
        self._gesture_count = 0
        self._transition_from_detected = False

        # Semi-transparent overlay
        self.setWindowFlags(Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self.setStyleSheet("""
            OnboardingWizard { background: rgba(10, 10, 10, 0.92); }
            QLabel { color: #eee; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, len(TUTORIAL_STEPS))
        self.progress.setValue(1)
        self.progress.setStyleSheet("color: #3b82f6; background: #333; border: none; height: 6px; border-radius: 3px;")
        layout.addWidget(self.progress)

        # Step indicator
        self.step_label = QLabel("1 / 9")
        self.step_label.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(self.step_label)

        # Title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #fff;")
        layout.addWidget(self.title_label)

        # Emoji
        self.emoji_label = QLabel()
        self.emoji_label.setStyleSheet("font-size: 72px;")
        layout.addWidget(self.emoji_label)

        # Description
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #ccc; font-size: 14px;")
        layout.addWidget(self.desc_label)

        # Action / tip
        self.action_label = QLabel()
        self.action_label.setStyleSheet("color: #60a5fa; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.action_label)

        self.tip_label = QLabel()
        self.tip_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.tip_label)

        # Detection feedback
        self.detect_label = QLabel("")
        self.detect_label.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: bold;")
        layout.addWidget(self.detect_label)

        # Navigation
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← 上一步")
        self.prev_btn.setStyleSheet("padding: 8px 16px; background: #444; color: #eee; border-radius: 6px;")
        self.prev_btn.clicked.connect(self.prev_step)

        self.next_btn = QPushButton("下一步 →")
        self.next_btn.setStyleSheet("padding: 8px 24px; background: #3b82f6; color: #fff; border-radius: 6px; font-weight: bold;")
        self.next_btn.clicked.connect(self.next_step)

        self.skip_btn = QPushButton("稍后查看")
        self.skip_btn.setStyleSheet("color: #888; padding: 8px 16px;")
        self.skip_btn.clicked.connect(self._dismiss)

        nav_layout.addWidget(self.skip_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

        self._update_ui()

    def _update_ui(self):
        step = TUTORIAL_STEPS[self._step]
        self.step_label.setText(f"{self._step + 1} / {len(TUTORIAL_STEPS)}")
        self.progress.setValue(self._step + 1)
        self.title_label.setText(step["title"])
        self.emoji_label.setText(step["emoji"])
        self.desc_label.setText(step["desc"])
        self.action_label.setText(step.get("action", "") or "")
        self.tip_label.setText(f"💡 {step.get('tip', '')}" if step.get("tip") else "")
        self.detect_label.setText("")
        self._gesture_count = 0
        self._transition_from_detected = False

        self.prev_btn.setEnabled(self._step > 0)
        if self._step >= len(TUTORIAL_STEPS) - 1:
            self.next_btn.setText("开始使用 ✓")
            self.next_btn.setStyleSheet("padding: 8px 24px; background: #22c55e; color: #fff; border-radius: 6px; font-weight: bold;")
        else:
            self.next_btn.setText("下一步 →")
            self.next_btn.setStyleSheet("padding: 8px 24px; background: #3b82f6; color: #fff; border-radius: 6px; font-weight: bold;")

    def on_gesture(self, gesture: str, confidence: float):
        step = TUTORIAL_STEPS[self._step]
        target = step.get("target")
        if not target:
            return

        # Handle transition steps
        if step.get("transition_from"):
            if self._transition_from_detected and gesture == target:
                self._auto_advance()
            elif gesture == step["transition_from"]:
                self._transition_from_detected = True
                self.detect_label.setText(f"检测到 {gesture}，等待 {target}...")
            return

        if gesture == target and confidence > 0.6:
            self._gesture_count += 1
            if self._gesture_count >= 3:
                self.detect_label.setText(f"✓ 检测到 {gesture}！自动跳转中...")
                QTimer.singleShot(800, self._auto_advance)
        else:
            if self._gesture_count > 0:
                self._gesture_count = max(0, self._gesture_count - 1)

    def _auto_advance(self):
        if self._step < len(TUTORIAL_STEPS) - 1:
            self.next_step()
        else:
            self._dismiss()

    def next_step(self):
        if self._step < len(TUTORIAL_STEPS) - 1:
            self._step += 1
            self._update_ui()

    def prev_step(self):
        if self._step > 0:
            self._step -= 1
            self._update_ui()

    def _dismiss(self):
        from desktop_app.config_manager import ConfigManager
        ConfigManager.set_tutorial_done()
        self.hide()
        self.finished.emit()

    def resizeEvent(self, event):
        # Cover the camera view area
        self._camera_view.update()
