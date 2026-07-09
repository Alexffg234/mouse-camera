import time
from typing import List, Optional

from hand_tracker import HandLandmarks


class UserTracker:
    """Select and lock onto the nearest hand for multi-user scenarios."""

    def __init__(self, lock_timeout_ms: int = 3000, depth_drift_threshold: float = 0.2):
        self.locked_depth: Optional[float] = None
        self.last_lock_time: float = 0.0
        self.lock_timeout_ms = lock_timeout_ms
        self.depth_drift_threshold = depth_drift_threshold

    def select_hand(self, all_hands: List[HandLandmarks]) -> Optional[HandLandmarks]:
        if not all_hands:
            self.locked_depth = None
            return None

        nearest = min(all_hands, key=lambda h: h.depth)

        if self.locked_depth is None:
            self._lock(nearest)
            return nearest

        if self._lock_valid(nearest):
            return nearest
        elif self._lock_expired():
            self._lock(nearest)
            return nearest
        else:
            return nearest

    def _lock(self, hand: HandLandmarks):
        self.locked_depth = hand.depth
        self.last_lock_time = time.time()

    def _lock_valid(self, hand: HandLandmarks) -> bool:
        drift = abs(hand.depth - self.locked_depth) / max(abs(self.locked_depth), 0.01)
        return drift < self.depth_drift_threshold

    def _lock_expired(self) -> bool:
        elapsed = (time.time() - self.last_lock_time) * 1000
        return elapsed > self.lock_timeout_ms

    def get_status(self) -> dict:
        return {
            "locked": self.locked_depth is not None,
            "depth": self.locked_depth,
        }
