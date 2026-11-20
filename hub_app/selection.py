"""Map a hand's horizontal position to a card index, with hysteresis.

Pure module: no pygame, OpenCV or MediaPipe imports. `x` is the normalized
landmark-9 x coordinate in the mirrored camera frame.
"""

ACTIVE_MIN_X = 0.15
ACTIVE_MAX_X = 0.85
SWITCH_MARGIN = 0.04


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _continuous_position(x: float, n: int, lo: float, hi: float) -> float:
    """Position in card units: 0.0 .. n, where whole numbers are card boundaries."""
    return _clamp((x - lo) / (hi - lo), 0.0, 1.0) * n


def x_to_index(
    x: float, n: int, lo: float = ACTIVE_MIN_X, hi: float = ACTIVE_MAX_X
) -> int:
    """Stateless mapping of x to a card index in [0, n-1]."""
    if n <= 0:
        raise ValueError("n must be at least 1")
    return min(n - 1, int(_continuous_position(x, n, lo, hi)))


class SelectionTracker:
    """Keeps the selected index; switches cards only past a boundary plus margin."""

    def __init__(
        self,
        n: int,
        start: int = 0,
        lo: float = ACTIVE_MIN_X,
        hi: float = ACTIVE_MAX_X,
    ) -> None:
        if n <= 0:
            raise ValueError("n must be at least 1")
        self.n = n
        self.lo = lo
        self.hi = hi
        self.index = int(_clamp(start, 0, n - 1))

    def update_from_x(self, x: float | None) -> int:
        if x is None:
            return self.index

        position = _continuous_position(x, self.n, self.lo, self.hi)
        margin = SWITCH_MARGIN / (self.hi - self.lo) * self.n

        while self.index < self.n - 1 and position >= self.index + 1 + margin:
            self.index += 1
        while self.index > 0 and position <= self.index - margin:
            self.index -= 1
        return self.index

    def step(self, delta: int) -> int:
        self.index = int(_clamp(self.index + delta, 0, self.n - 1))
        return self.index
