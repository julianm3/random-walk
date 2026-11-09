"""The data set: the simulated walks for one WalkParams, and what's counted from them.

generate() simulates the walks for a WalkParams. With an absorbing wall, an absorbed walk
follows its free (no-wall) path until it reaches the wall and ends there, so the walks are
simulated without a wall and each walk's contact step is recorded (`ends`).

numpy only - no GUI imports, so this can be tested without a display.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from random_walk.params import WalkParams
from random_walk.simulation import (
    BinArray,
    FloatArray,
    IntArray,
    absorb_steps,
    fractions_at,
    parity_bins,
    simulate_paths,
    trace_span,
)


@dataclass(frozen=True, eq=False)
class WalkData:
    """A simulated data set: every walk's positions, and how it was simulated.

    `paths` has shape (trials, steps + 1), as from simulate_paths(). `ends` is for an
    absorbing wall (simulation.absorb_steps): each walk's contact step, None otherwise. A walk
    is still going at step k when k < its end. `wall` is the wall's position while it's on
    (either mode), `span` the lowest and highest position on any walk's trace
    (simulation.trace_span: with an absorbing wall, not below it).
    """

    paths: IntArray
    p_right: float = 0.5
    wall: int | None = None
    ends: IntArray | None = None
    span: tuple[int, int] = (0, 0)

    @classmethod
    def from_paths(
        cls,
        paths: IntArray,
        p_right: float = 0.5,
        wall: int | None = None,
        ends: IntArray | None = None,
    ) -> WalkData:
        """A data set from walks simulated elsewhere (its span worked out from them)."""
        span = trace_span(paths, wall if ends is not None else None)
        return cls(paths, p_right, wall, ends, span)

    @property
    def trials(self) -> int:
        return len(self.paths)

    @property
    def steps(self) -> int:
        return self.paths.shape[1] - 1

    @property
    def absorbing(self) -> bool:
        return self.ends is not None

    def going(self, trials: int, step: int) -> IntArray:
        """The positions at `step` of the first `trials` walks still going there (all of them,
        unless an absorbing wall has ended some)."""
        positions = self.paths[:trials, step]
        if self.ends is None:
            return positions
        return positions[self.ends[:trials] > step]

    def ended(self, trials: int, step: int) -> int | None:
        """How many of the first `trials` walks an absorbing wall has ended by `step` (None
        without one)."""
        if self.ends is None:
            return None
        return int(np.count_nonzero(self.ends[:trials] <= step))

    def shares_at(self, trials: int, step: int) -> tuple[BinArray, FloatArray]:
        """Bin centres (width-2 parity bins) and each bin's share of the first `trials` trials
        at `step`, counting only the walks still going - shares of all those trials, not of
        the survivors, so with an absorbing wall they sum to the surviving fraction. Empty
        when none are going."""
        positions = self.going(trials, step)
        if len(positions) == 0:
            return np.zeros(0), np.zeros(0)
        centres, fractions = fractions_at(positions, parity_bins(positions))
        return centres, fractions * len(positions) / trials


def generate(params: WalkParams) -> WalkData:
    """Simulate the data set for `params`, from a fresh generator seeded with params.seed: equal
    params (or ones with params.same_walks) always give the same walks."""
    rng = np.random.default_rng(params.seed)
    if params.absorbing:
        paths = simulate_paths(params.trials, params.steps, None, params.p_right, rng)
        ends = absorb_steps(paths, params.wall_value)
        return WalkData.from_paths(paths, params.p_right, params.wall, ends)
    paths = simulate_paths(params.trials, params.steps, params.wall, params.p_right, rng)
    return WalkData.from_paths(paths, params.p_right, params.wall)
