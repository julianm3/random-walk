"""Closed-form results for the biased +/-1 walk. See docs/theory.md for the derivations."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def final_mean(steps: int, p_right: float) -> float:
    """Expected final position of a walk with no wall: steps * (per-step mean 2p - 1)."""
    return steps * (2 * p_right - 1)


def final_sd(steps: int, p_right: float) -> float:
    """Final-position sd of a walk with no wall: sqrt(steps * (per-step variance 4p(1 - p))).

    Exactly 0 at p_right = 0 or 1 (every step goes the same way), so callers can test for the
    deterministic case with `== 0`.
    """
    return float(np.sqrt(steps * 4 * p_right * (1 - p_right)))


def normal_pdf(x: NDArray[np.float64], mean: float, sd: float) -> NDArray[np.float64]:
    """Normal density; the large-STEPS approximation of the final position with no wall."""
    return np.exp(-((x - mean) ** 2) / (2 * sd**2)) / (sd * np.sqrt(2 * np.pi))


def half_normal_pdf(x: NDArray[np.float64], wall: float, sd: float) -> NDArray[np.float64]:
    """Half-normal density above `wall`; the large-STEPS approximation with a reflecting wall."""
    return (2 / (sd * np.sqrt(2 * np.pi))) * np.exp(-((x - wall) ** 2) / (2 * sd**2))


def wall_curve_valid(p_right: float) -> bool:
    """The half-normal comes from the reflection principle, which needs a driftless walk.

    A biased walk reflected off a wall is a materially different, more involved problem, and
    the half-normal would just be wrong for it, so callers should hide it rather than show a
    guess.
    """
    return p_right == 0.5
