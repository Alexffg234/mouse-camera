import json
import os


class GestureMapper:
    SUPPORTED_GESTURES = [
        "open_palm", "index_finger", "middle_index", "pinch",
        "fist", "ok_sign", "thumb_up", "two_fingers",
        "palm_up", "palm_down", "palm_left", "palm_right",
        "swipe_up", "swipe_down", "swipe_left", "swipe_right",
        "pinch_hold",
    ]

    VALID_ACTIONS = [
        "move_cursor", "left_click", "right_click", "double_click",
        "scroll_up", "scroll_down", "drag",
    ]

    def __init__(self, config_path="config.json"):
        self._config_path = config_path
        self._config_mtime = 0.0
        self._config = {}
        self._load_config()

    # --- loading & validation ---

    def _load_config(self):
        with open(self._config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)
        self._validate()
        self._config_mtime = os.path.getmtime(self._config_path)

    def _validate(self):
        gm = self._config.get("gesture_mouse_map", {})
        for action, mapping in gm.items():
            if action not in self.VALID_ACTIONS:
                raise ValueError(
                    f"Unknown action '{action}'. Valid: {self.VALID_ACTIONS}"
                )
            gesture = mapping.get("gesture", "")
            if gesture not in self.SUPPORTED_GESTURES:
                raise ValueError(
                    f"Unknown gesture '{gesture}' for action '{action}'. "
                    f"Valid: {self.SUPPORTED_GESTURES}"
                )
            threshold = mapping.get("threshold")
            if threshold is not None and threshold <= 0:
                raise ValueError(f"threshold must be > 0 for '{action}'")
            hold_ms = mapping.get("hold_ms")
            if hold_ms is not None and hold_ms <= 0:
                raise ValueError(f"hold_ms must be > 0 for '{action}'")

        sensitivity = self._config.get("sensitivity", {})
        sf = sensitivity.get("smoothing_factor", 0.3)
        if not (0 < sf <= 1):
            raise ValueError("smoothing_factor must be in (0, 1]")

        cal = self._config.get("calibration", {})
        if cal.get("max_x", 0) <= cal.get("min_x", 0):
            raise ValueError("calibration max_x must be > min_x")
        if cal.get("max_y", 0) <= cal.get("min_y", 0):
            raise ValueError("calibration max_y must be > min_y")

        tr = self._config.get("tracking", {})
        if tr.get("max_hands", 1) < 1:
            raise ValueError("max_hands must be >= 1")

    # --- hot-reload ---

    def check_reload(self):
        if not self._config.get("tracking", {}).get("config_hot_reload", False):
            return False
        try:
            mtime = os.path.getmtime(self._config_path)
        except OSError:
            return False
        if mtime != self._config_mtime:
            self._load_config()
            return True
        return False

    # --- lookups ---

    def get_action_for_gesture(self, gesture_name):
        for action_name, mapping in self._config.get("gesture_mouse_map", {}).items():
            if mapping["gesture"] == gesture_name:
                return action_name
        return None

    def get_action_params(self, action_name):
        return self._config.get("gesture_mouse_map", {}).get(action_name, {})

    def get_config(self):
        return self._config
