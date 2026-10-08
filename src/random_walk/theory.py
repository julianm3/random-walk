"""Closed-form results for the biased +/-1 walk. See docs/theory.md for the derivations."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def p_right(theta: float) -> float:
    """Probability of a +1 step for slope `theta` (degrees, -90 to 90).

    Positive theta biases left, negative biases right; theta=0 is the unbiased 50/50 case, and
    +/-90 make the walk fully one-directional.
    """
    return float(0.5 - 0.5 * np.sin(np.radians(theta)))


def final_mean(steps: int, theta: float) -> float:
    """Expected final position of a walk with no wall: steps * (per-step mean -sin(theta))."""
    return float(-steps * np.sin(np.radians(theta)))


def final_sd(steps: int, theta: float) -> float:
    """Final-position sd of a walk with no wall: sqrt(steps) * (per-step sd |cos(theta)|).

    Computed as sqrt(steps * (1 - sin^2(theta))), which equals the above but is exactly 0 at
    theta = +/-90 (sin is exactly +/-1.0 there, while cos(90 degrees) is ~6e-17 in floating
    point), so callers can test for the deterministic case with `== 0`.
    """
    sin = np.sin(np.radians(theta))
    return float(np.sqrt(steps * (1 - sin**2)))


def normal_pdf(x: NDArray[np.float64], mean: float, sd: float) -> NDArray[np.float64]:
    """Normal density; the large-STEPS approximation of the final position with no wall."""
    return np.exp(-((x - mean) ** 2) / (2 * sd**2)) / (sd * np.sqrt(2 * np.pi))


def half_normal_pdf(x: NDArray[np.float64], wall: float, sd: float) -> NDArray[np.float64]:
    """Half-normal density above `wall`; the large-STEPS approximation with a reflecting wall."""
    return (2 / (sd * np.sqrt(2 * np.pi))) * np.exp(-((x - wall) ** 2) / (2 * sd**2))


def wall_curve_valid(theta: float) -> bool:
    """The half-normal comes from the reflection principle, which needs a driftless walk.

    A biased walk reflected off a wall is a materially different, more involved problem, and
    the half-normal would just be wrong for it, so callers should hide it rather than show a
    guess.
    """
    return theta == 0
