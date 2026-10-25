"""How many trials Trials mode shows at each animation frame: slow at first, then faster.

Trials mode grows the final-position histogram from 0 to `total` trials over `frames` frames.
A constant rate (~11 trials a frame for 10,000 in 30 s) would rush past the sparse early
histogram, so the count starts at 1 trial a frame and grows exponentially:

    count(f) = (exp(k f) - 1) / k        (k > 0, so count'(0) = 1)

with k chosen so count(frames) = total. For 10,000 trials in 900 frames, k is about 0.0041:
~580 trials after the first 10 s and ~40 trials a frame at the end. If `total` is no more than
`frames`, the count is simply linear.

No GUI imports, so this is testable without a display.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def growth_rate(frames: int, total: int) -> float:
    """The k with (exp(k frames) - 1) / k = total, or 0 when a linear count is enough
    (total <= frames). Found by bisection; the left side grows with k."""
    if frames <= 0 or total <= frames:
        return 0.0

    def log_count(k: float) -> float:
        # log((exp(k F) - 1) / k), written so large k F can't overflow exp()
        return k * frames + math.log(-math.expm1(-k * frames)) - math.log(k)

    target = math.log(total)
    lo, hi = 1e-12, 1.0
    while log_count(hi) < target:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        if log_count(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass(frozen=True)
class TrialRamp:
    """Maps animation frames 0..frames to trial counts 0..total and back."""

    frames: int
    total: int
    rate: float = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate", growth_rate(self.frames, self.total))

    def count_at(self, frame: float) -> int:
        """Trials shown at `frame` (clamped to 0..frames): 0 at the start, `total` at the end."""
        frame = min(max(frame, 0.0), float(self.frames))
        if frame >= self.frames:
            return self.total
        if self.rate == 0:
            exact = frame * self.total / self.frames if self.frames else float(self.total)
        else:
            exact = math.expm1(self.rate * frame) / self.rate
        return min(round(exact), self.total)

    def frame_for(self, count: int) -> float:
        """The (fractional) frame at which `count` trials are shown; the inverse of count_at."""
        count = min(max(count, 0), self.total)
        if self.total == 0 or self.frames == 0:
            return 0.0
        if self.rate == 0:
            return count * self.frames / self.total
        return math.log1p(self.rate * count) / self.rate
