"""Monte Carlo simulation of 1D +/-1 random walks, with an optional reflecting wall.

numpy only - no GUI imports, so this can be tested without a display.
"""

from __future__ import annotations

from typing import Any, NamedTuple

import numpy as np
from numpy.typing import NDArray

from random_walk import theory
from random_walk.config import DEFAULT_P_RIGHT, DEFAULT_SEED, DEFAULT_WALL

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]
# Histogram bin edges/centres keep the bins' dtype (int for parity_bins) at runtime, though
# numpy's stubs declare them float.
BinArray = NDArray[Any]

# Seeded, so the app produces the same data every time it starts. The sequence still advances
# from one call to the next; pass your own `rng` for an independent, reproducible stream.
_default_rng = np.random.default_rng(DEFAULT_SEED)


def _jumps(runs: int, steps: int, p_right: float, rng: np.random.Generator | None) -> IntArray:
    return (rng or _default_rng).choice([-1, 1], size=(runs, steps), p=[1 - p_right, p_right])


def simulate(
    runs: int,
    steps: int,
    wall: int | None = DEFAULT_WALL,
    p_right: float = DEFAULT_P_RIGHT,
    rng: np.random.Generator | None = None,
) -> IntArray:
    """Return final positions of `runs` walks of `steps` jumps of +1 or -1.

    Each jump is +1 with probability `p_right` (0 to 1) and -1 otherwise.

    If `wall` is a number, a step that would take the position below it is mirrored back
    above it instead: position -> 2*wall - position. If `wall` is None, the walk is
    unrestricted (the simple case).

    `rng` defaults to a module-level generator seeded with DEFAULT_SEED; pass your own
    for an independent reproducible stream.
    """
    jumps = _jumps(runs, steps, p_right, rng)
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
    p_right: float = DEFAULT_P_RIGHT,
    rng: np.random.Generator | None = None,
) -> IntArray:
    """Like simulate(), but returns the whole position history, not just the final one.

    Shape (runs, steps + 1): column 0 is the starting position (always 0), column k is the
    position after k steps - so paths[:, -1] is exactly what simulate() would have returned
    from an identically seeded `rng`.

    Built step-major - each step's positions for every run side by side in memory - and
    returned as a transposed view (Fortran order). The wall's step-by-step loop then works
    on contiguous rows: ~0.4 s instead of ~0.8 s for 10,000 x 1000, with identical values.
    Reading one step for every run (paths[:, k], as the density grid and histograms do) is
    contiguous too.
    """
    jumps = _jumps(runs, steps, p_right, rng)
    positions = np.zeros((steps + 1, runs), dtype=np.int64)
    if wall is None:
        # (Summing the transposed view is fastest here, ~0.3 s; a contiguous copy took 0.6.)
        np.cumsum(jumps.T, axis=0, out=positions[1:])
    else:
        by_step = np.ascontiguousarray(jumps.T)  # (steps, runs): each step's jumps together
        for i in range(steps):
            row = positions[i + 1]
            np.add(positions[i], by_step[i], out=row)
            np.subtract(row, wall, out=row)  # fold anything below the wall back above it
            np.abs(row, out=row)
            np.add(row, wall, out=row)
    return positions.T


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


def density_grid(paths: IntArray, lo: int, hi: int, bin_width: int = 2) -> IntArray:
    """How many walks are at each (step, position bin): shape (steps + 1, bins).

    Row k is step k. Column j counts positions in [lo + j*bin_width, lo + (j+1)*bin_width),
    so with the default width every column holds one even and one odd position - walks at
    any step land in it, whatever their parity. `lo`..`hi` must cover every position.
    """
    n_bins = (hi - lo) // bin_width + 1
    steps = paths.shape[1]
    grid = np.zeros((steps, n_bins), dtype=np.int64)
    for step in range(steps):  # one column of paths at a time: low memory, ~30 ms for 10M
        grid[step] = np.bincount((paths[:, step] - lo) // bin_width, minlength=n_bins)
    return grid


def normalize_rows(grid: IntArray) -> FloatArray:
    """Each row scaled to its own maximum (rows of zeros stay zero), so every step is shaded
    on the same 0..1 scale however spread out its walks are."""
    peaks = grid.max(axis=1, keepdims=True)
    return np.divide(grid, peaks, out=np.zeros(grid.shape), where=peaks > 0)


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
    p_right: float = DEFAULT_P_RIGHT,
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

    mean_theory = theory.final_mean(steps, p_right)
    sigma = theory.final_sd(steps, p_right)

    if curve_x_range is not None:
        x_lo, x_hi = curve_x_range
    else:
        x_lo = float(wall_value if wall_enabled else finals.min())
        x_hi = float(finals.max())
    x = np.linspace(x_lo, x_hi, 400)

    if sigma == 0:
        # p_right = 0 or 1: every step goes the same way, so every walk ends in the same place.
        # There is no spread for a curve to describe (and its formula would divide by zero).
        show_curve = False
        curve = np.zeros_like(x)
    elif wall_enabled:
        show_curve = theory.wall_curve_valid(p_right)
        curve = theory.half_normal_pdf(x, wall_value, sigma)
    else:
        show_curve = True
        curve = theory.normal_pdf(x, mean_theory, sigma)

    stats = position_stats(finals)
    if not wall_enabled:
        stats += f" (theory: {mean_theory:.2f}, {sigma:.2f})"
    stats += f", min = {finals.min()}, max = {finals.max()}"

    return HistogramSummary(centers, counts, x, curve, stats, show_curve)
