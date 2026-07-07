import time
from typing import Optional

import pyautogui


class MouseController:
    def __init__(self, config: dict):
        self._config = config
        self._sensitivity = config.get("sensitivity", {})
        self._tracking = config.get("tracking", {})

        self._smooth_x: Optional[float] = None
        self._smooth_y: Optional[float] = None

        self._last_action_time: dict[str, float] = {}

        self._dragging = False

        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

    def update_config(self, config: dict):
        self._config = config
        self._sensitivity = config.get("sensitivity", {})
        self._tracking = config.get("tracking", {})

    def execute(self, action: str, params: dict,
                landmark_pos: Optional[tuple] = None) -> bool:
        now = time.time() * 1000
        debounce = self._tracking.get("debounce_ms", 150)

        if action != "move_cursor" and action != "drag":
            last = self._last_action_time.get(action, 0)
            if (now - last) < debounce:
                return False
            self._last_action_time[action] = now

        handler = {
            "move_cursor": self._move,
            "left_click": self._left_click,
            "right_click": self._right_click,
            "double_click": self._double_click,
            "scroll_up": self._scroll_up,
            "scroll_down": self._scroll_down,
            "drag": self._drag,
        }.get(action)

        if handler:
            handler(landmark_pos, params)
            return True
        return False

    def _move(self, landmark_pos: Optional[tuple], params: dict):
        if landmark_pos is None:
            return
        cal = self._config.get("calibration", {})
        mirror = self._config.get("mirror_fix", {})
        flip_x = mirror.get("flip_x", True)
        flip_y = mirror.get("flip_y", False)
        x = 1.0 - landmark_pos[0] if flip_x else landmark_pos[0]
        y = 1.0 - landmark_pos[1] if flip_y else landmark_pos[1]
        screen_x = x * (cal["max_x"] - cal["min_x"]) + cal["min_x"]
        screen_y = y * (cal["max_y"] - cal["min_y"]) + cal["min_y"]

        alpha = self._sensitivity.get("smoothing_factor", 0.3)
        speed = self._sensitivity.get("cursor_speed", 1.5)

        if self._smooth_x is None:
            self._smooth_x = screen_x
            self._smooth_y = screen_y
        else:
            self._smooth_x = alpha * screen_x + (1 - alpha) * self._smooth_x
            self._smooth_y = alpha * screen_y + (1 - alpha) * self._smooth_y

        pyautogui.moveTo(int(self._smooth_x), int(self._smooth_y))

    def _left_click(self, *_):
        pyautogui.click(button="left")

    def _right_click(self, *_):
        pyautogui.click(button="right")

    def _double_click(self, *_):
        pyautogui.click(button="left", clicks=2, interval=0.05)

    def _scroll_up(self, *_):
        speed = self._sensitivity.get("scroll_speed", 3)
        pyautogui.scroll(speed)

    def _scroll_down(self, *_):
        speed = self._sensitivity.get("scroll_speed", 3)
        pyautogui.scroll(-speed)

    def _drag(self, landmark_pos: Optional[tuple], params: dict):
        if landmark_pos is not None:
            cal = self._config.get("calibration", {})
            mirror = self._config.get("mirror_fix", {})
            flip_x = mirror.get("flip_x", True)
            flip_y = mirror.get("flip_y", False)
            x = 1.0 - landmark_pos[0] if flip_x else landmark_pos[0]
            y = 1.0 - landmark_pos[1] if flip_y else landmark_pos[1]
            sx = x * (cal["max_x"] - cal["min_x"]) + cal["min_x"]
            sy = y * (cal["max_y"] - cal["min_y"]) + cal["min_y"]
            if not self._dragging:
                self._dragging = True
                pyautogui.mouseDown(button="left")
                pyautogui.moveTo(int(sx), int(sy))
            else:
                pyautogui.moveTo(int(sx), int(sy))
        elif self._dragging:
            pyautogui.mouseUp(button="left")
            self._dragging = False

    def stop_drag(self):
        if self._dragging:
            pyautogui.mouseUp(button="left")
            self._dragging = False
