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
        "scroll_up", "scroll_down", "drag", "show_desktop",
        "copy", "paste", "cut",
    ]

    VALID_MODES = ["instant", "hold", "follow", "swipe", "transition"]

    MODE_REQUIRED_PARAMS = {
        "instant": [],
        "hold": ["hold_ms"],
        "follow": ["landmark"],
        "swipe": ["swipe_direction"],
        "transition": ["timeout_ms"],
    }

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
        for action, cfg in gm.items():
            if action not in self.VALID_ACTIONS:
                raise ValueError(f"Unknown action '{action}'. Valid: {self.VALID_ACTIONS}")
            tr = cfg.get("trigger", {})
            mode = tr.get("mode", "")
            if mode not in self.VALID_MODES:
                raise ValueError(f"Invalid mode '{mode}' for '{action}'. Valid: {self.VALID_MODES}")
            from_g = tr.get("from", "")
            to_g = tr.get("to", "")
            if from_g not in self.SUPPORTED_GESTURES:
                raise ValueError(f"Invalid gesture '{from_g}' for '{action}'")
            if to_g not in self.SUPPORTED_GESTURES:
                raise ValueError(f"Invalid gesture '{to_g}' for '{action}'")
            if mode == "transition" and from_g == to_g:
                raise ValueError(f"transition mode requires from != to for '{action}'")
            threshold = tr.get("threshold")
            if threshold is not None and threshold <= 0:
                raise ValueError(f"threshold must be > 0 for '{action}'")
            hold_ms = tr.get("hold_ms")
            if hold_ms is not None and hold_ms <= 0:
                raise ValueError(f"hold_ms must be > 0 for '{action}'")
            landmark = tr.get("landmark")
            if landmark and landmark not in ("index_tip", "middle_tip", "palm_center"):
                raise ValueError(f"Invalid landmark '{landmark}' for '{action}'")

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

    def get_actions_for_gesture(self, gesture_name):
        """Return all actions whose trigger involves this gesture."""
        result = []
        for action_name, cfg in self._config.get("gesture_mouse_map", {}).items():
            tr = cfg.get("trigger", {})
            if tr.get("from") == gesture_name or tr.get("to") == gesture_name:
                result.append(action_name)
        return result

    def get_action_params(self, action_name):
        return self._config.get("gesture_mouse_map", {}).get(action_name, {})

    def get_trigger(self, action_name):
        return self._config.get("gesture_mouse_map", {}).get(action_name, {}).get("trigger", {})

    def get_transitions(self):
        """Return all transition-mode triggers as list of (from, to, action, timeout_ms)."""
        result = []
        for action_name, cfg in self._config.get("gesture_mouse_map", {}).items():
            tr = cfg.get("trigger", {})
            if tr.get("mode") == "transition":
                result.append({
                    "from": tr["from"],
                    "to": tr["to"],
                    "action": action_name,
                    "timeout_ms": tr.get("timeout_ms", 2000),
                })
        return result

    def get_follow_actions(self):
        """Return all follow-mode trigger actions."""
        result = []
        for action_name, cfg in self._config.get("gesture_mouse_map", {}).items():
            tr = cfg.get("trigger", {})
            if tr.get("mode") == "follow":
                result.append(action_name)
        return result

    def get_config(self):
        return self._config

    def set_config(self, config: dict):
        """Replace current config with a new one, with validation."""
        self._config = config
        self._validate()
