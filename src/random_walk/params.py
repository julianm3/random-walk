"""The shared RUNS/STEPS/WALL/SLOPE parameters and their validation."""

from __future__ import annotations

from dataclasses import dataclass

from random_walk.config import MAX_JUMPS, MAX_SLOPE, MAX_STEPS, MIN_SLOPE


@dataclass(frozen=True)
class WalkParams:
    """One validated set of shared parameters.

    Frozen and hashable, so it doubles as the animation modes' cache key: two runs with equal
    params can reuse the same simulated data.
    """

    runs: int
    steps: int
    wall_enabled: bool
    wall_value: int
    theta: float

    @property
    def wall(self) -> int | None:
        """The wall position to simulate with, or None for an unrestricted walk."""
        return self.wall_value if self.wall_enabled else None


def validate(runs: int, steps: int, theta: float) -> str | None:
    """Return an error message to display, or None if the values are acceptable."""
    if runs < 1 or steps < 1:
        return "RUNS and STEPS must be at least 1"
    if runs * steps > MAX_JUMPS:
        return f"RUNS x STEPS is too large (max {MAX_JUMPS:,})"
    if steps > MAX_STEPS:
        return f"STEPS is too large (max {MAX_STEPS:,})"
    if not MIN_SLOPE <= theta <= MAX_SLOPE:
        return "SLOPE must be between -90 and 90 degrees"
    return None
