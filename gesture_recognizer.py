import math
from collections import Counter, deque
from typing import Dict, Optional, Tuple

from hand_tracker import HandLandmarks


def _dist_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2)


def _dist_2d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def _finger_extended(lms: Dict[int, Tuple], tip: int, pip: int) -> bool:
    """3D: finger extended if wrist→tip distance > wrist→pip distance."""
    wrist = lms[0]
    return _dist_3d(wrist, lms[tip]) > _dist_3d(wrist, lms[pip]) * 1.05


def _finger_curled(lms: Dict[int, Tuple], tip: int, pip: int) -> bool:
    return not _finger_extended(lms, tip, pip)


def _palm_angle(lms: Dict[int, Tuple]) -> float:
    """Angle (deg) of wrist→middle_MCP vector vs image vertical."""
    wrist = lms[0]
    mid_mcp = lms[9]
    dx = mid_mcp[0] - wrist[0]
    dy = mid_mcp[1] - wrist[1]
    return math.degrees(math.atan2(dx, dy))


def _hand_width(lms: Dict[int, Tuple]) -> float:
    return _dist_2d(lms[0], lms[17])


class GestureRecognizer:
    SUPPORTED = [
        "open_palm", "index_finger", "middle_index", "pinch",
        "fist", "ok_sign", "thumb_up", "two_fingers",
        "palm_up", "palm_down", "palm_left", "palm_right",
        "swipe_up", "swipe_down", "swipe_left", "swipe_right",
        "pinch_hold",
    ]

    def __init__(self, stability_frames: int = 3):
        self._history: deque = deque(maxlen=stability_frames)
        self._stability = stability_frames
        self._pinch_start: Optional[float] = None
        self._palm_center_history: deque = deque(maxlen=15)
        self._prev_gesture: str = ""
        self._stable_gesture: str = ""

    def recognize(self, landmarks: HandLandmarks, timestamp: float = 0.0) -> str:
        raw = self._classify(landmarks, timestamp)
        self._history.append(raw)
        if len(self._history) >= self._stability:
            vote = Counter(self._history).most_common(1)[0][0]
        else:
            vote = raw
        self._prev_gesture = vote
        return vote

    def _classify(self, landmarks: HandLandmarks, ts: float) -> str:
        lms = landmarks.landmarks

        idx_ext = _finger_extended(lms, 8, 6)
        mid_ext = _finger_extended(lms, 12, 10)
        ring_ext = _finger_extended(lms, 16, 14)
        pinky_ext = _finger_extended(lms, 20, 18)

        pinch_dist = _dist_3d(lms[4], lms[8])
        hw = _hand_width(lms)
        pinch_threshold = 0.08 + hw * 0.15

        if pinch_dist < pinch_threshold:
            if self._pinch_start is None:
                self._pinch_start = ts
            elif ts - self._pinch_start > 0.3:
                return "pinch_hold"
            return "pinch"
        else:
            self._pinch_start = None

        extended = sum([idx_ext, mid_ext, ring_ext, pinky_ext])

        if extended == 0:
            return "fist"

        if extended == 4:
            return "open_palm"

        # ok_sign: thumb+index close, index curled, middle/ring/pinky extended
        if (not idx_ext and pinch_dist < pinch_threshold * 1.3
                and mid_ext and ring_ext and pinky_ext):
            return "ok_sign"

        if extended == 1 and idx_ext and not mid_ext:
            return "index_finger"

        if extended == 2 and idx_ext and mid_ext and not ring_ext:
            return "two_fingers"

        if extended == 2 and idx_ext and mid_ext:
            return "middle_index"

        if extended == 1 and not idx_ext and not mid_ext:
            thumb_tip = lms[4]
            thumb_mcp = lms[2]
            if thumb_tip[1] < thumb_mcp[1]:
                return "thumb_up"

        return "none"

    def get_palm_direction(self, landmarks: HandLandmarks) -> str:
        angle = _palm_angle(landmarks.landmarks)
        if -45 < angle < 45:
            return "palm_down"
        elif angle >= 45 and angle < 135:
            return "palm_right"
        elif angle <= -45 and angle > -135:
            return "palm_left"
        return "palm_up"

    def detect_swipe(self, landmarks: HandLandmarks) -> Optional[str]:
        center = ((landmarks.landmarks[5][0] + landmarks.landmarks[9][0]) / 2,
                  (landmarks.landmarks[5][1] + landmarks.landmarks[9][1]) / 2)
        self._palm_center_history.append(center)
        if len(self._palm_center_history) < 15:
            return None
        first = self._palm_center_history[0]
        last = self._palm_center_history[-1]
        dx = last[0] - first[0]
        dy = last[1] - first[1]
        threshold = 0.08
        if abs(dx) > abs(dy) and dx > threshold:
            self._palm_center_history.clear()
            return "swipe_right"
        if abs(dx) > abs(dy) and dx < -threshold:
            self._palm_center_history.clear()
            return "swipe_left"
        if dy > threshold:
            self._palm_center_history.clear()
            return "swipe_down"
        if dy < -threshold:
            self._palm_center_history.clear()
            return "swipe_up"
        return None

    def get_previous_gesture(self) -> str:
        return self._prev_gesture

    def get_stable_gesture(self) -> str:
        return self._stable_gesture

    def set_stable_gesture(self, gesture: str):
        """Called from main.py when a gesture has been stable for transition detection."""
        self._stable_gesture = gesture
