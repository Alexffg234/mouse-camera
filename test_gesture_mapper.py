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
            "move_cursor":  {"trigger": {"from": "index_finger", "to": "index_finger", "mode": "follow", "landmark": "index_tip"}},
            "left_click":   {"trigger": {"from": "pinch", "to": "pinch", "mode": "instant", "threshold": 0.15}},
            "right_click":  {"trigger": {"from": "ok_sign", "to": "ok_sign", "mode": "instant"}},
            "double_click": {"trigger": {"from": "fist", "to": "fist", "mode": "hold", "hold_ms": 800}},
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


def _tr(gesture, mode="instant", **kw):
    """Helper to build a trigger dict."""
    return {"trigger": {"from": gesture, "to": gesture, "mode": mode, **kw}}


class TestGestureMapperLoad(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_valid_config(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        actions = mapper.get_actions_for_gesture("index_finger")
        self.assertIn("move_cursor", actions)
        self.assertIn("left_click", mapper.get_actions_for_gesture("pinch"))
        self.assertIn("double_click", mapper.get_actions_for_gesture("fist"))

    def test_unknown_gesture_raises(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "move_cursor": _tr("telepathy")
        }})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_unknown_action_raises(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "fly": _tr("pinch")
        }})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_negative_threshold_raises(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "left_click": {"trigger": {"from": "pinch", "to": "pinch", "mode": "instant", "threshold": -1}}
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
        self.assertEqual(params["trigger"]["from"], "pinch")
        self.assertEqual(params["trigger"]["threshold"], 0.15)

    def test_unmapped_gesture(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        self.assertEqual(mapper.get_actions_for_gesture("open_palm"), [])

    def test_transition_requires_different_gestures(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "show_desktop": {"trigger": {"from": "fist", "to": "fist", "mode": "transition", "timeout_ms": 2000}}
        }})
        with self.assertRaises(ValueError):
            GestureMapper(path)

    def test_get_transitions(self):
        path = _make_config(self.tmpdir, {"gesture_mouse_map": {
            "show_desktop": {"trigger": {"from": "open_palm", "to": "fist", "mode": "transition", "timeout_ms": 2000}}
        }})
        mapper = GestureMapper(path)
        transitions = mapper.get_transitions()
        self.assertEqual(len(transitions), 1)
        self.assertEqual(transitions[0]["from"], "open_palm")
        self.assertEqual(transitions[0]["to"], "fist")
        self.assertEqual(transitions[0]["action"], "show_desktop")

    def test_get_follow_actions(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        self.assertIn("move_cursor", mapper.get_follow_actions())


class TestGestureMapperHotReload(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_hot_reload_detects_change(self):
        path = _make_config(self.tmpdir)
        mapper = GestureMapper(path)
        time.sleep(1.1)
        new_cfg = {
            "gesture_mouse_map": {"left_click": _tr("index_finger")},
            "sensitivity": {"cursor_speed": 1.5, "scroll_speed": 3, "smoothing_factor": 0.3},
            "calibration": {"min_x": 0, "max_x": 1920, "min_y": 0, "max_y": 1080},
            "tracking": {"max_hands": 2, "config_hot_reload": True},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_cfg, f)
        mapper.check_reload()
        self.assertIn("left_click", mapper.get_actions_for_gesture("index_finger"))

    def test_hot_reload_disabled(self):
        path = _make_config(self.tmpdir, {"tracking": {"config_hot_reload": False}})
        mapper = GestureMapper(path)
        _make_config(self.tmpdir, {"tracking": {"config_hot_reload": False}, "gesture_mouse_map": {
            "left_click": _tr("index_finger")
        }})
        changed = mapper.check_reload()
        self.assertFalse(changed)
        self.assertIn("move_cursor", mapper.get_actions_for_gesture("index_finger"))


if __name__ == "__main__":
    unittest.main()
