"""Pinch detection and hold-to-confirm logic on hand landmarks.

Pure module: no pygame, OpenCV or MediaPipe imports. Landmarks are
normalized (x, y) tuples indexed as in MediaPipe's 21-point hand model.
"""

import math

Landmark = tuple[float, float]

WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_MCP = 9

PINCH_ON_RATIO = 0.35
PINCH_OFF_RATIO = 0.50
HOLD_TO_CONFIRM_S = 0.8


def _distance(a: Landmark, b: Landmark) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def pinch_ratio(landmarks: list[Landmark]) -> float:
    """Thumb-index distance normalized by palm size (wrist to middle MCP)."""
    palm = max(_distance(landmarks[WRIST], landmarks[MIDDLE_MCP]), 1e-6)
    return _distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / palm


class PinchDetector:
    """Hysteresis pinch detector: closes below `on`, opens above `off`."""

    def __init__(self, on: float = PINCH_ON_RATIO, off: float = PINCH_OFF_RATIO) -> None:
        self.on = on
        self.off = off
        self.pinched = False

    def update(self, ratio: float | None) -> bool:
        if ratio is None:
            self.pinched = False
        elif self.pinched:
            self.pinched = ratio < self.off
        else:
            self.pinched = ratio < self.on
        return self.pinched


class HoldConfirm:
    """Fires once when the input stays active for `hold_s` seconds."""

    def __init__(self, hold_s: float = HOLD_TO_CONFIRM_S) -> None:
        self.hold_s = hold_s
        self._start: float | None = None
        self._fired = False

    def update(self, active: bool, now: float) -> bool:
        if not active:
            self.reset()
            return False
        if self._start is None:
            self._start = now
        if self._fired:
            return False
        if now - self._start >= self.hold_s:
            self._fired = True
            return True
        return False

    def progress(self, now: float) -> float:
        if self._start is None:
            return 0.0
        return min(1.0, max(0.0, (now - self._start) / self.hold_s))

    def reset(self) -> None:
        self._start = None
        self._fired = False
