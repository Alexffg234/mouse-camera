import copy
import time

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from calibration import CalibrationHelper
from gesture_mapper import GestureMapper
from gesture_recognizer import GestureRecognizer
from hand_tracker import HandTracker
from mouse_controller import MouseController
from user_tracker import UserTracker
from main import draw_overlay  # type: ignore


class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    gesture_update = pyqtSignal(str, str, float, float, dict, float)
    error_occurred = pyqtSignal(str)
    calibration_requested = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self, config: dict):
        super().__init__()
        self._config = config
        self._mapper = GestureMapper()
        self._mapper.set_config(config)
        self._init_components()
        self._cap = None
        self._running = False

    def _init_components(self):
        tr = self._config.get("tracking", {})
        recognizer_cfg = self._config.get("recognizer", {})
        self._tracker = HandTracker(
            max_hands=tr.get("max_hands", 2),
            min_detection_confidence=tr.get("min_hand_confidence", 0.5),
            min_tracking_confidence=tr.get("min_tracking_confidence", 0.5),
        )
        self._recognizer = GestureRecognizer(
            stability_frames=recognizer_cfg.get("stability_frames", 3),
            finger_margin=recognizer_cfg.get("finger_margin", 1.05),
        )
        self._mouse_ctrl = MouseController(self._config)
        self._user_trk = UserTracker(lock_timeout_ms=tr.get("user_lock_timeout_ms", 3000))

    def update_config(self, config: dict):
        """Called from main thread to update config in real-time."""
        self._config = copy.deepcopy(config)
        self._mapper.set_config(config)
        self._mouse_ctrl.update_config(config)
        recognizer_cfg = config.get("recognizer", {})
        self._recognizer._finger_margin = recognizer_cfg.get("finger_margin", 1.05)

    def run(self):
        self._running = True
        self._cap = cv2.VideoCapture(0)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # minimize queued frames
        self._cap.set(cv2.CAP_PROP_FPS, 30)

        if not self._cap.isOpened():
            self.error_occurred.emit("无法打开摄像头")
            return

        hold_start: dict[str, float] = {}
        hold_fired: set[str] = set()
        instant_cooldown = self._config.get("tracking", {}).get("instant_cooldown_ms", 200) / 1000.0
        transition_state: dict[str, dict] = {}
        prev_stable_gesture = ""
        prev_instant_action: str = ""
        prev_instant_time = 0.0
        prev_time = time.time()
        fps = 30.0
        TIP_MAP = {"index_tip": 8, "middle_tip": 12, "palm_center": 9}

        try:
            while self._running:
                ret, frame = self._cap.read()
                if not ret:
                    # cap.read() returns False after release() is called from stop()
                    break

                now = time.time()
                fps = fps * 0.95 + (1.0 / max((now - prev_time), 0.001)) * 0.05
                prev_time = now

                # Config hot-reload
                if self._mapper.check_reload():
                    self._config = self._mapper.get_config()
                    self._mouse_ctrl.update_config(self._config)

                # Hand tracking (VIDEO mode: pass ms timestamp)
                all_hands = self._tracker.process(frame, timestamp_ms=int(now * 1000))
                selected = self._user_trk.select_hand(all_hands)

                current_gesture = ""
                current_action = ""
                hold_progress = 0.0
                trans_info = []
                confidence = 1.0

                if selected:
                    self._tracker.draw(frame, [selected])
                    # Stable recognition for action triggers (instant/hold/transition)
                    current_gesture = self._recognizer.recognize(selected, now)
                    confidence = self._recognizer.get_confidence()
                    current_time_ms = now * 1000

                    # Transition detection
                    all_transitions = self._mapper.get_transitions()
                    for t in all_transitions:
                        key = f"{t['from']}->{t['to']}"
                        t_state = transition_state.get(key)
                        if t_state is None:
                            if prev_stable_gesture == t["from"]:
                                transition_state[key] = {"fired": False, "ts": now}
                        else:
                            elapsed = (now - t_state["ts"]) * 1000
                            if elapsed > t["timeout_ms"]:
                                del transition_state[key]
                                continue
                            if current_gesture == t["to"] and not t_state["fired"]:
                                current_action = t["action"]
                                self._mouse_ctrl.execute(t["action"], self._mapper.get_action_params(t["action"]))
                                t_state["fired"] = True
                        trans_info.append({
                            "from": t["from"], "to": t["to"],
                            "fired": transition_state.get(key, {}).get("fired", False),
                        })

                    # Process triggers by mode
                    gm = self._config.get("gesture_mouse_map", {})
                    follow_actions = self._mapper.get_follow_actions()

                    # Follow mode: use raw gesture (no stability filter) for low latency
                    raw_gesture = self._recognizer.get_raw_gesture()
                    for action_name in follow_actions:
                        trigger = self._mapper.get_trigger(action_name)
                        if trigger["from"] == raw_gesture:
                            landmark = trigger.get("landmark", "index_tip")
                            tip_id = TIP_MAP.get(landmark, 8)
                            pos = selected.get(tip_id)
                            self._mouse_ctrl.execute(action_name, self._mapper.get_action_params(action_name), pos)

                    # Swipe mode
                    swipe_dir = self._recognizer.detect_swipe(selected)
                    if swipe_dir:
                        for action_name, action_cfg in gm.items():
                            trigger = action_cfg.get("trigger", {})
                            if (trigger.get("mode") == "swipe"
                                    and trigger["from"] == current_gesture
                                    and trigger.get("swipe_direction") == swipe_dir):
                                current_action = action_name
                                self._mouse_ctrl.execute(action_name, self._mapper.get_action_params(action_name))

                    # Hold mode: clear state when gesture releases
                    for action_name, action_cfg in gm.items():
                        trigger = action_cfg.get("trigger", {})
                        if trigger.get("mode") == "hold" and trigger["from"] != current_gesture:
                            hold_start.pop(action_name, None)
                            hold_fired.discard(action_name)

                    # Instant & Hold mode
                    for action_name, action_cfg in gm.items():
                        trigger = action_cfg.get("trigger", {})
                        mode = trigger.get("mode")
                        if mode == "instant" and trigger["from"] == current_gesture:
                            # Cooldown: don't fire the same instant action more than once per 200ms
                            if action_name != prev_instant_action or (now - prev_instant_time) > instant_cooldown:
                                current_action = action_name
                                self._mouse_ctrl.execute(action_name, self._mapper.get_action_params(action_name))
                                prev_instant_action = action_name
                                prev_instant_time = now
                        elif mode == "hold" and trigger["from"] == current_gesture:
                            if action_name not in hold_start:
                                hold_start[action_name] = current_time_ms
                            elapsed = current_time_ms - hold_start[action_name]
                            hold_ms = trigger.get("hold_ms", 800)
                            progress = min(elapsed / hold_ms, 1.0)
                            if elapsed >= hold_ms and action_name not in hold_fired:
                                current_action = action_name
                                pos = selected.get(TIP_MAP.get(trigger.get("landmark", "index_tip"), 8))
                                self._mouse_ctrl.execute(action_name, self._mapper.get_action_params(action_name), pos)
                                hold_fired.add(action_name)
                            hold_progress = max(hold_progress, progress)

                    # Stop drag if no follow gesture active (use raw for consistency with follow mode)
                    active_follow_gestures = [self._mapper.get_trigger(a)["from"] for a in follow_actions]
                    if raw_gesture not in active_follow_gestures:
                        self._mouse_ctrl.stop_drag()

                    if current_gesture != "none":
                        prev_stable_gesture = current_gesture
                else:
                    self._mouse_ctrl.stop_drag()
                    hold_start.clear()
                    hold_fired.clear()
                    self._recognizer.reset()
                    prev_stable_gesture = ""

                draw_overlay(frame, current_gesture, current_action, hold_progress,
                             self._user_trk.get_status(), fps, trans_info, confidence)

                self.frame_ready.emit(frame)
                self.gesture_update.emit(current_gesture, current_action,
                                         confidence, hold_progress,
                                         self._user_trk.get_status(), fps)

        finally:
            if self._cap:
                self._cap.release()
            self._tracker.close()
            self._running = False
            self.stopped.emit()

    def stop(self):
        self._running = False
        # Release the camera to unblock cap.read() so the thread can exit
        if self._cap:
            self._cap.release()
            self._cap = None

    def start_calibration(self):
        """Emit signal to main thread to run calibration interactively."""
        self.calibration_requested.emit()
