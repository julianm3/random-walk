"""The data set's settings: how many walks and steps, the wall, the bias and the seed."""

from __future__ import annotations

from dataclasses import dataclass

from random_walk.config import DEFAULT_SEED, DEFAULT_WALL_MODE


@dataclass(frozen=True)
class WalkParams:
    """One set of the data set's settings.

    Frozen and hashable; equal settings give equal walks (see MainWindow.regenerate, which
    skips re-simulating when nothing the walks depend on changed).
    """

    runs: int
    steps: int
    wall_enabled: bool
    wall_value: int
    p_right: float
    seed: int = DEFAULT_SEED  # the random generator's seed: equal params give equal walks
    wall_mode: str = DEFAULT_WALL_MODE  # "reflect" or "absorb" (config.WALL_MODES)

    @property
    def wall(self) -> int | None:
        """The wall position to simulate with, or None for an unrestricted walk."""
        return self.wall_value if self.wall_enabled else None

    @property
    def absorbing(self) -> bool:
        """The wall is on and ends the walks that reach it, rather than reflecting them."""
        return self.wall_enabled and self.wall_mode == "absorb"
