"""Monte Carlo simulation of 1D +/-1 random walks, with an optional reflecting wall.

numpy only - no GUI imports, so this can be tested without a display.
"""

from __future__ import annotations

from typing import Any, NamedTuple

import numpy as np
from numpy.typing import NDArray

from random_walk import theory
from random_walk.config import DEFAULT_SLOPE, DEFAULT_WALL

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]
# Histogram bin edges/centres keep the bins' dtype (int for parity_bins) at runtime, though
# numpy's stubs declare them float.
BinArray = NDArray[Any]

_default_rng = np.random.default_rng()


def _jumps(runs: int, steps: int, theta: float, rng: np.random.Generator | None) -> IntArray:
    p = theory.p_right(theta)
    return (rng or _default_rng).choice([-1, 1], size=(runs, steps), p=[1 - p, p])


def simulate(
    runs: int,
    steps: int,
    wall: int | None = DEFAULT_WALL,
    theta: float = DEFAULT_SLOPE,
    rng: np.random.Generator | None = None,
) -> IntArray:
    """Return final positions of `runs` walks of `steps` jumps of +1 or -1.

    `theta` (degrees, -90 to 90) biases the walk; see theory.p_right().

    If `wall` is a number, a step that would take the position below it is mirrored back
    above it instead: position -> 2*wall - position. If `wall` is None, the walk is
    unrestricted (the simple case).

    `rng` defaults to a module-level generator; pass a seeded one for reproducible results.
    """
    jumps = _jumps(runs, steps, theta, rng)
    if wall is None:
        return jumps.sum(axis=1)

    positions = np.zeros(runs, dtype=np.int64)
    for i in range(steps):
        positions += jumps[:, i]
        np.abs(positions - wall, out=positions)  # fold anything below the wall back above it
        positions += wall
    return positions


def simulate_paths(
    runs: int,
    steps: int,
    wall: int | None = DEFAULT_WALL,
    theta: float = DEFAULT_SLOPE,
    rng: np.random.Generator | None = None,
) -> IntArray:
    """Like simulate(), but returns the whole position history, not just the final one.

    Shape (runs, steps + 1): column 0 is the starting position (always 0), column k is the
    position after k steps - so paths[:, -1] is exactly what simulate() would have returned
    from an identically seeded `rng`.
    """
    jumps = _jumps(runs, steps, theta, rng)
    paths = np.zeros((runs, steps + 1), dtype=np.int64)
    if wall is None:
        np.cumsum(jumps, axis=1, out=paths[:, 1:])
    else:
        for i in range(steps):
            paths[:, i + 1] = paths[:, i] + jumps[:, i]
            np.abs(paths[:, i + 1] - wall, out=paths[:, i + 1])
            paths[:, i + 1] += wall
    return paths


def parity_bins(values: IntArray) -> IntArray:
    """Width-2 histogram bin edges covering `values`, centred on the values themselves.

    Final positions all share the parity of STEPS (with or without the reflecting wall), so
    width-1 bins would leave every other bin empty.
    """
    return np.arange(values.min() - 1, values.max() + 2, 2)


def bin_centers(edges: BinArray) -> BinArray:
    """Centres of width-2 bins from parity_bins()."""
    return edges[:-1] + 1


def position_stats(positions: IntArray) -> str:
    """One-line 'mean = ..., sd = ...' summary of a set of positions."""
    return f"mean = {positions.mean():.2f}, sd = {positions.std():.2f}"


def fractions_at(positions: IntArray, bins: IntArray) -> tuple[BinArray, FloatArray]:
    """Bin centres and each bin's share of `positions` (raw fractions summing to 1.0)."""
    counts, edges = np.histogram(positions, bins=bins)
    return bin_centers(edges), counts / len(positions)


class HistogramSummary(NamedTuple):
    """Everything a final-position histogram plot needs."""

    centers: BinArray
    counts: FloatArray  # probability density per bin
    curve_x: FloatArray
    curve_y: FloatArray
    stats: str
    show_curve: bool


def summarize(
    finals: IntArray,
    steps: int,
    wall_enabled: bool,
    wall_value: int = DEFAULT_WALL,
    theta: float = DEFAULT_SLOPE,
    bins: IntArray | None = None,
    curve_x_range: tuple[float, float] | None = None,
) -> HistogramSummary:
    """Given an array of final positions, return bin centres/densities, the theory curve,
    whether to show that curve, and a one-line stats string.

    `bins` and `curve_x_range` can be fixed externally (rather than derived from `finals`)
    so the axes don't jump around when `finals` is a growing prefix of a larger run, as in
    the distribution animation.
    """
    if bins is None:
        bins = parity_bins(finals)
    counts, edges = np.histogram(finals, bins=bins, density=True)
    centers = bin_centers(edges)

    mean_theory = theory.final_mean(steps, theta)
    sigma = theory.final_sd(steps, theta)

    if curve_x_range is not None:
        x_lo, x_hi = curve_x_range
    else:
        x_lo = float(wall_value if wall_enabled else finals.min())
        x_hi = float(finals.max())
    x = np.linspace(x_lo, x_hi, 400)

    if wall_enabled:
        show_curve = theory.wall_curve_valid(theta)
        curve = theory.half_normal_pdf(x, wall_value, sigma)
    else:
        show_curve = True
        curve = theory.normal_pdf(x, mean_theory, sigma)

    stats = position_stats(finals)
    if not wall_enabled:
        stats += f" (theory: {mean_theory:.2f}, {sigma:.2f})"
    stats += f", min = {finals.min()}, max = {finals.max()}"

    return HistogramSummary(centers, counts, x, curve, stats, show_curve)
