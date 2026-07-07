import math
import unittest

from hand_tracker import HandLandmarks
from gesture_recognizer import (
    GestureRecognizer, _dist_3d, _finger_extended, _finger_curled,
    _palm_angle, _hand_width,
)


def _make_hand(lms_3d):
    return HandLandmarks(landmarks=lms_3d, handedness="Right", depth=lms_3d[0][2])


def _curled_tip(x: float, y_near_mcp: float, z: float):
    return (x, y_near_mcp, z)


class TestDist3d(unittest.TestCase):
    def test_same_point(self):
        p = (0.5, 0.5, 0.0)
        self.assertAlmostEqual(_dist_3d(p, p), 0.0)

    def test_axis_aligned(self):
        self.assertAlmostEqual(_dist_3d((0, 0, 0), (1, 0, 0)), 1.0)
        self.assertAlmostEqual(_dist_3d((0, 0, 0), (0, 1, 0)), 1.0)
        self.assertAlmostEqual(_dist_3d((0, 0, 0), (0, 0, 1)), 1.0)


class TestFingerDetection(unittest.TestCase):
    def _extended_hand(self):
        lms = {
            0: (0.5, 0.9, 0.0),
            2: (0.55, 0.85, 0.0),
            5: (0.45, 0.7, 0.0),
            6: (0.44, 0.6, 0.0),
            8: (0.42, 0.45, -0.05),
            9: (0.5, 0.7, 0.0),
            10: (0.5, 0.6, 0.0),
            12: (0.5, 0.45, -0.05),
            13: (0.57, 0.7, 0.0),
            14: (0.57, 0.6, 0.0),
            16: (0.57, 0.45, -0.05),
            17: (0.63, 0.7, 0.0),
            18: (0.63, 0.6, 0.0),
            20: (0.63, 0.45, -0.05),
        }
        return lms

    def test_extended_finger(self):
        lms = self._extended_hand()
        self.assertTrue(_finger_extended(lms, 8, 6))
        self.assertTrue(_finger_extended(lms, 12, 10))

    def test_curled_finger(self):
        lms = self._extended_hand()
        lms[8] = (0.44, 0.65, 0.02)
        self.assertTrue(_finger_curled(lms, 8, 6))


class TestGestureRecognizer(unittest.TestCase):
    """
    Coordinate convention: wrist at y=0.95, fingers extend toward lower y.
    Curled fingertips sit near MCPs (y~0.73), closer to wrist than PIPs.
    Extended fingertips reach y~0.48, far from wrist.
    """

    def _make_open_palm(self):
        lms = {
            0: (0.5, 0.95, 0.0),
            2: (0.55, 0.88, 0.0),
            4: (0.6, 0.78, -0.05),
            5: (0.42, 0.75, 0.0),
            6: (0.41, 0.65, 0.0),
            8: (0.39, 0.48, -0.06),
            9: (0.5, 0.75, 0.0),
            10: (0.5, 0.65, 0.0),
            12: (0.5, 0.48, -0.06),
            13: (0.58, 0.75, 0.0),
            14: (0.58, 0.65, 0.0),
            16: (0.59, 0.48, -0.06),
            17: (0.65, 0.75, 0.0),
            18: (0.65, 0.65, 0.0),
            20: (0.67, 0.48, -0.06),
        }
        return _make_hand(lms)

    def _make_fist(self):
        """All fingertips curled near MCPs — closer to wrist than PIPs."""
        lms = {
            0: (0.5, 0.95, 0.0),
            2: (0.55, 0.88, 0.0),
            4: (0.53, 0.80, 0.05),
            5: (0.42, 0.75, 0.0),
            6: (0.41, 0.70, 0.0),
            8: (0.42, 0.73, 0.04),
            9: (0.5, 0.75, 0.0),
            10: (0.5, 0.70, 0.0),
            12: (0.51, 0.73, 0.04),
            13: (0.58, 0.75, 0.0),
            14: (0.58, 0.70, 0.0),
            16: (0.59, 0.73, 0.04),
            17: (0.65, 0.75, 0.0),
            18: (0.65, 0.70, 0.0),
            20: (0.66, 0.73, 0.04),
        }
        return _make_hand(lms)

    def _make_index_finger(self):
        """Only index extended; middle/ring/pinky curled."""
        lms = {
            0: (0.5, 0.95, 0.0),
            2: (0.55, 0.88, 0.0),
            4: (0.53, 0.82, 0.05),
            5: (0.42, 0.75, 0.0),
            6: (0.41, 0.65, 0.0),
            8: (0.39, 0.48, -0.06),
            9: (0.5, 0.75, 0.0),
            10: (0.5, 0.70, 0.0),
            12: (0.51, 0.73, 0.04),
            13: (0.58, 0.75, 0.0),
            14: (0.58, 0.70, 0.0),
            16: (0.59, 0.73, 0.04),
            17: (0.65, 0.75, 0.0),
            18: (0.65, 0.70, 0.0),
            20: (0.66, 0.73, 0.04),
        }
        return _make_hand(lms)

    def _make_pinch(self):
        hand = self._make_index_finger()
        hand.landmarks[4] = (0.4, 0.49, -0.055)
        return hand

    def _make_two_fingers(self):
        """Index + middle extended; ring + pinky curled."""
        lms = {
            0: (0.5, 0.95, 0.0),
            2: (0.55, 0.88, 0.0),
            4: (0.53, 0.82, 0.05),
            5: (0.42, 0.75, 0.0),
            6: (0.41, 0.65, 0.0),
            8: (0.39, 0.48, -0.06),
            9: (0.5, 0.75, 0.0),
            10: (0.5, 0.65, 0.0),
            12: (0.5, 0.48, -0.06),
            13: (0.58, 0.75, 0.0),
            14: (0.58, 0.70, 0.0),
            16: (0.59, 0.73, 0.04),
            17: (0.65, 0.75, 0.0),
            18: (0.65, 0.70, 0.0),
            20: (0.66, 0.73, 0.04),
        }
        return _make_hand(lms)

    def test_open_palm(self):
        gr = GestureRecognizer(stability_frames=1)
        self.assertEqual(gr.recognize(self._make_open_palm()), "open_palm")

    def test_fist(self):
        gr = GestureRecognizer(stability_frames=1)
        self.assertEqual(gr.recognize(self._make_fist()), "fist")

    def test_index_finger(self):
        gr = GestureRecognizer(stability_frames=1)
        self.assertEqual(gr.recognize(self._make_index_finger()), "index_finger")

    def test_pinch(self):
        gr = GestureRecognizer(stability_frames=1)
        self.assertEqual(gr.recognize(self._make_pinch()), "pinch")

    def test_two_fingers(self):
        gr = GestureRecognizer(stability_frames=1)
        self.assertEqual(gr.recognize(self._make_two_fingers()), "two_fingers")

    def test_stability_filter(self):
        gr = GestureRecognizer(stability_frames=3)
        gr.recognize(self._make_open_palm())
        gr.recognize(self._make_fist())
        result = gr.recognize(self._make_fist())
        self.assertEqual(result, "fist")

    def test_hand_width(self):
        lms = {0: (0.5, 0.9, 0.0), 17: (0.65, 0.75, 0.0)}
        hw = _hand_width(lms)
        self.assertGreater(hw, 0.1)
        self.assertAlmostEqual(hw, 0.2121, places=3)


class TestUserTracker(unittest.TestCase):
    def test_selects_nearest(self):
        from user_tracker import UserTracker
        hands = [
            HandLandmarks(landmarks={0: (0.5, 0.5, 0.5)}, handedness="Right", depth=0.5),
            HandLandmarks(landmarks={0: (0.3, 0.5, 0.1)}, handedness="Left", depth=0.1),
        ]
        ut = UserTracker()
        selected = ut.select_hand(hands)
        self.assertAlmostEqual(selected.depth, 0.1)

    def test_lock_preserved(self):
        from user_tracker import UserTracker
        hand1 = HandLandmarks(landmarks={0: (0.5, 0.5, 0.2)}, handedness="Right", depth=0.2)
        ut = UserTracker()
        ut.select_hand([hand1])
        hand2 = HandLandmarks(landmarks={0: (0.5, 0.5, 0.22)}, handedness="Right", depth=0.22)
        selected = ut.select_hand([hand2])
        self.assertIsNotNone(selected)


class TestMouseController(unittest.TestCase):
    def test_init(self):
        from mouse_controller import MouseController
        config = {
            "sensitivity": {"cursor_speed": 1.5, "scroll_speed": 3, "smoothing_factor": 0.3},
            "tracking": {"debounce_ms": 150},
            "calibration": {"min_x": 0, "max_x": 1920, "min_y": 0, "max_y": 1080},
        }
        mc = MouseController(config)
        self.assertIsNotNone(mc)

    def test_update_config(self):
        from mouse_controller import MouseController
        config = {
            "sensitivity": {"cursor_speed": 1.5, "scroll_speed": 3, "smoothing_factor": 0.3},
            "tracking": {"debounce_ms": 150},
            "calibration": {"min_x": 0, "max_x": 1920, "min_y": 0, "max_y": 1080},
        }
        mc = MouseController(config)
        new_cfg = dict(config)
        new_cfg["sensitivity"] = {"cursor_speed": 3.0, "scroll_speed": 5, "smoothing_factor": 0.5}
        mc.update_config(new_cfg)
        self.assertEqual(mc._sensitivity["cursor_speed"], 3.0)


if __name__ == "__main__":
    unittest.main()
