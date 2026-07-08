import importlib
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

# Use importlib because this mediapipe build doesn't re-export submodules.
_hl = importlib.import_module("mediapipe.tasks.python.vision.hand_landmarker")
_base = importlib.import_module("mediapipe.tasks.python.core.base_options")
_vtm = importlib.import_module("mediapipe.tasks.python.vision.core.vision_task_running_mode")
_img = importlib.import_module("mediapipe.tasks.python.vision.core.image")

_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")


@dataclass
class HandLandmarks:
    landmarks: Dict[int, Tuple[float, float, float]]
    handedness: str
    depth: float = 0.0

    def get(self, idx: int) -> Optional[Tuple[float, float, float]]:
        return self.landmarks.get(idx)


def _make_options(
    delegate,
    model_path,
    max_hands,
    min_detection_confidence,
    min_tracking_confidence,
):
    return _hl.HandLandmarkerOptions(
        base_options=_base.BaseOptions(
            model_asset_path=model_path,
            delegate=delegate,
        ),
        num_hands=max_hands,
        min_hand_detection_confidence=min_detection_confidence,
        min_tracking_confidence=min_tracking_confidence,
        running_mode=_vtm.VisionTaskRunningMode.VIDEO,
    )


class HandTracker:
    _gpu_available = None  # cached after first check

    def __init__(
        self,
        max_hands: int = 2,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
        use_gpu: bool = True,
    ):
        # Try GPU first, fall back to CPU
        if use_gpu:
            try:
                gpu_opts = _make_options(
                    _base.BaseOptions.Delegate.GPU,
                    _MODEL_PATH, max_hands,
                    min_detection_confidence, min_tracking_confidence,
                )
                self.detector = _hl.HandLandmarker.create_from_options(gpu_opts)
                HandTracker._gpu_available = True
                print("[GPU] 已启用 GPU delegate")
            except Exception:
                HandTracker._gpu_available = False
                print("[GPU] 不可用，使用 CPU")
                gpu_opts = None

        if not gpu_opts:
            options = _make_options(
                _base.BaseOptions.Delegate.CPU,
                _MODEL_PATH, max_hands,
                min_detection_confidence, min_tracking_confidence,
            )
            self.detector = _hl.HandLandmarker.create_from_options(options)

        self.connections = _hl.HandLandmarksConnections
        self._frame_ts = 0

    def process(self, frame_bgr: np.ndarray, timestamp_ms: Optional[int] = None) -> List[HandLandmarks]:
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = _img.Image(image_format=_img.ImageFormat.SRGB, data=frame_rgb)

        if timestamp_ms is None:
            self._frame_ts += 16
            timestamp_ms = self._frame_ts

        result = self.detector.detect_for_video(mp_image, timestamp_ms)
        if not result.hand_landmarks:
            return []

        out: List[HandLandmarks] = []
        for i, hand_lms in enumerate(result.hand_landmarks):
            lms = {}
            for idx, pt in enumerate(hand_lms):
                lms[idx] = (pt.x, pt.y, pt.z)
            depth = lms.get(0, (0, 0, 0))[2]
            handedness = "Right"
            if result.handedness and i < len(result.handedness):
                handedness = result.handedness[i][0].category_name
            out.append(
                HandLandmarks(
                    landmarks=lms,
                    handedness=handedness,
                    depth=depth,
                )
            )
        out.sort(key=lambda h: h.depth)
        return out

    @staticmethod
    def draw(image: np.ndarray, hands: List[HandLandmarks]) -> np.ndarray:
        for hand in hands:
            pts = {idx: (int(pt[0] * image.shape[1]), int(pt[1] * image.shape[0]))
                   for idx, pt in hand.landmarks.items()}
            for c in HandTracker._connections():
                pt_a, pt_b = pts.get(c[0]), pts.get(c[1])
                if pt_a and pt_b:
                    cv2.line(image, pt_a, pt_b, (0, 200, 0), 2)
            for idx, pt in pts.items():
                color = (255, 0, 0) if idx == 8 else (0, 150, 255)
                cv2.circle(image, pt, 4, color, -1)
        return image

    @staticmethod
    def _connections():
        return [
            (0, 1), (1, 2), (2, 3), (3, 4),
            (0, 5), (5, 6), (6, 7), (7, 8),
            (5, 9), (9, 10), (10, 11), (11, 12),
            (9, 13), (13, 14), (14, 15), (15, 16),
            (13, 17), (17, 18), (18, 19), (19, 20),
            (0, 17),
        ]

    def close(self):
        pass  # let GC handle cleanup; MediaPipe singletons can't be re-created
