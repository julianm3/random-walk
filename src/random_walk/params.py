"""The data set's settings: how many walks and steps, the wall, the bias and the seed."""

from __future__ import annotations

from dataclasses import dataclass

from random_walk.config import DEFAULT_SEED, DEFAULT_WALL_MODE


@dataclass(frozen=True)
class WalkParams:
    """One set of the data set's settings.

    Frozen and hashable; equal settings give equal walks (data.generate). same_walks() says
    whether two settings give the same walks even when not equal (MainWindow.regenerate
    re-simulates only when they don't).
    """

    trials: int
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

    def same_walks(self, other: WalkParams) -> bool:
        """`other` gives exactly the same walks: they differ, if at all, only in settings that
        don't count while the wall is off (its position and mode)."""
        return self._walks_key() == other._walks_key()

    def _walks_key(self) -> tuple[object, ...]:
        """What the simulated walks depend on. (The wall mode only matters while it's on.)"""
        mode = self.wall_mode if self.wall_enabled else None
        return (self.trials, self.steps, self.wall, mode, self.p_right, self.seed)
