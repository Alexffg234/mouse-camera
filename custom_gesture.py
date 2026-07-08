"""Custom gesture learning: extract feature vectors from hand landmarks,
match against stored templates using cosine similarity."""

import math
from typing import Dict, List, Optional, Tuple


def _dist_2d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


FEATURE_DIM = 16


def extract_features(lms: Dict[int, Tuple[float, float, float]]) -> List[float]:
    """Extract a 16-element feature vector from MediaPipe hand landmarks.

    Features 0-3:  finger extension ratios (wrist-to-tip / wrist-to-PIP)
    Features 4-6:  thumb-to-finger-tip distances normalized by hand width
    Feature  7:    palm angle normalized to [-1, 1]
    Features 8-15: finger tip positions relative to MCP, normalized by hand width
    """
    wrist = lms[0]
    hand_width = _dist_2d(lms[0], lms[17])
    if hand_width < 0.001:
        hand_width = 0.1  # prevent division by zero

    # Extension ratios (4 floats)
    f0 = _dist_2d(wrist, lms[8]) / max(_dist_2d(wrist, lms[6]), 1e-8)
    f1 = _dist_2d(wrist, lms[12]) / max(_dist_2d(wrist, lms[10]), 1e-8)
    f2 = _dist_2d(wrist, lms[16]) / max(_dist_2d(wrist, lms[14]), 1e-8)
    f3 = _dist_2d(wrist, lms[20]) / max(_dist_2d(wrist, lms[18]), 1e-8)

    # Thumb-to-finger distances normalized (3 floats)
    f4 = _dist_2d(lms[4], lms[8]) / hand_width
    f5 = _dist_2d(lms[4], lms[12]) / hand_width
    f6 = _dist_2d(lms[4], lms[16]) / hand_width

    # Palm angle normalized to [-1, 1] (1 float)
    dx = lms[9][0] - lms[0][0]
    dy = lms[9][1] - lms[0][1]
    angle_deg = math.degrees(math.atan2(dx, dy))
    f7 = max(-1.0, min(1.0, angle_deg / 180.0))

    # Finger tip positions relative to MCP, normalized (8 floats)
    tips_mcp = [
        (lms[8], lms[5]),   # index tip relative to index MCP
        (lms[12], lms[9]),  # middle tip relative to middle MCP
        (lms[16], lms[13]), # ring tip relative to ring MCP
        (lms[20], lms[17]), # pinky tip relative to pinky MCP
    ]
    result = [f0, f1, f2, f3, f4, f5, f6, f7]
    for tip, mcp in tips_mcp:
        result.append((tip[0] - mcp[0]) / hand_width)
        result.append((tip[1] - mcp[1]) / hand_width)

    return result


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return dot / (norm_a * norm_b)


class CustomGestureMatcher:
    """Match live hand features against stored custom gesture templates."""

    DEFAULT_THRESHOLD = 0.85

    def __init__(self, custom_gestures: Optional[List[dict]] = None,
                 debounce_ms: int = 150):
        self._templates: List[dict] = custom_gestures or []
        self._debounce_ms = debounce_ms
        self._last_fire: Dict[str, float] = {}

    def add(self, name: str, action: str, template: List[float],
            threshold: float = DEFAULT_THRESHOLD, description: str = ""):
        self._templates.append({
            "name": name,
            "action": action,
            "template": template,
            "threshold": threshold,
            "description": description,
        })

    def remove(self, name: str):
        self._templates = [t for t in self._templates if t["name"] != name]

    def get_all(self) -> List[dict]:
        return list(self._templates)

    def set_templates(self, templates: List[dict]):
        self._templates = templates

    def match(self, features: List[float]) -> Optional[Tuple[str, str, float]]:
        """Return (action, name, similarity) for the best matching template."""
        best = None
        best_sim = -1.0
        for t in self._templates:
            sim = cosine_similarity(features, t["template"])
            if sim > best_sim:
                best_sim = sim
                best = t
        if best and best_sim >= best["threshold"]:
            return best["action"], best["name"], best_sim
        return None

    def match_with_debounce(self, features: List[float],
                            now_ms: float) -> Optional[Tuple[str, str, float]]:
        result = self.match(features)
        if result is None:
            return None
        action, name, sim = result
        last = self._last_fire.get(name, 0)
        if now_ms - last >= self._debounce_ms:
            self._last_fire[name] = now_ms
            return result
        return None
