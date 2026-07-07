import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from gesture_mapper import GestureMapper


def _make_config(config_dir, overrides=None):
    cfg = {
        "gesture_mouse_map": {
            "move_cursor":  {"gesture": "index_finger", "landmark": "index_tip"},
            "left_click":   {"gesture": "pinch", "threshold": 0.15},
            "right_click":  {"gesture": "ok_sign"},
            "double_click": {"gesture": "fist", "hold_ms": 800},
        },
        "sensitivity": {
            "cursor_speed": 1.5,
            "scroll_speed": 3,
            "smoothing_factor": 0.3,
        },
        "calibration": {"min_x": 0, "max_x": 1920, "min_y": 0, "max_y": 1080},
        "tracking": {
            "max_hands": 2,
            "min_hand_confidence": 0.5,
            "min_tracking_confidence": 0.5,
            "debounce_ms": 150,
            "config_hot_reload": True,
            "user_lock_timeout_ms": 3000,
        },
    }
    if overrides:
        cfg.update(overrides)
    path = os.path.join(config_dir, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    return path


class TestGestureMapperLoad(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_valid_config(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        self.assertEqual(mapper.get_action_for_gesture("index_finger"), "move_cursor")
        self.assertEqual(mapper.get_action_for_gesture("pinch"), "left_click")
        self.assertEqual(mapper.get_action_for_gesture("fist"), "double_click")

    def test_unknown_gesture_raises(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "move_cursor": {"gesture": "telepathy"}
        }})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_unknown_action_raises(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "fly": {"gesture": "pinch"}
        }})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_negative_threshold_raises(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "left_click": {"gesture": "pinch", "threshold": -1}
        }})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_invalid_smoothing_raises(self):
        path = _make_config(self.tmpdir, {"sensitivity": {"smoothing_factor": 2.0}})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_calibration_bounds_raises(self):
        path = _make_config(self.tmpdir, {"calibration": {"min_x": 1920, "max_x": 0, "min_y": 0, "max_y": 1080}})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_get_action_params(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        params = mapper.get_action_params("left_click")
        self.assertEqual(params["gesture"], "pinch")
        self.assertEqual(params["threshold"], 0.15)

    def test_unmapped_gesture(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        self.assertIsNone(mapper.get_action_for_gesture("open_palm"))


class TestGestureMapperHotReload(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_hot_reload_detects_change(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        # Wait to ensure different mtime (Windows has 1s filesystem resolution)
        time.sleep(1.1)
        # Rewrite config with all required fields
        new_cfg = {
            "gesture_mouse_map": {"left_click": {"gesture": "index_finger"}},
            "sensitivity": {"cursor_speed": 1.5, "scroll_speed": 3, "smoothing_factor": 0.3},
            "calibration": {"min_x": 0, "max_x": 1920, "min_y": 0, "max_y": 1080},
            "tracking": {"max_hands": 2, "config_hot_reload": True},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f)
        mapper.check_reload()
        self.assertEqual(mapper.get_action_for_gesture("index_finger"), "left_click")

    def test_hot_reload_disabled(self):
        path = _make_config(self.tmpdir, {"tracking": {"config_hot_reload": False}})
        mapper = GestureMapper(path)
        _make_config(self.tmpdir, {"tracking": {"config_hot_reload": False}, "gesture_mouse_map": {
            "left_click": {"gesture": "index_finger"}
        }})
        changed = mapper.check_reload()
        self.assertFalse(changed)
        # Old config maps index_finger -> move_cursor; must still hold that.
        self.assertEqual(mapper.get_action_for_gesture("index_finger"), "move_cursor")


if __name__ == "__main__":
    unittest.main()
