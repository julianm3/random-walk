"""Monte Carlo simulation of 1D +/-1 random walks, with an optional reflecting or absorbing
wall, and the counts the drawing needs: histogram shares, the walks' traces, legend values.

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
    Reading one step for every run (paths[:, k], as the trace grid and histograms do) is
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


LEGEND_WIDTH = 8  # characters per number column in legend_lines()


class LegendStats(NamedTuple):
    """The step and the number of trials counted, and the measured and theoretical mean and
    sd of their positions there (no wall), and the walks' P(right). The measured ones are
    None when no trials are counted. With an absorbing wall, `trials` are the walks still
    going and `ended` those the wall has absorbed (None otherwise)."""

    step: int
    trials: int
    mean: float | None
    sd: float | None
    theory_mean: float
    theory_sd: float
    p_right: float = 0.5
    ended: int | None = None


def legend_stats(
    positions: IntArray, step: int, p_right: float, ended: int | None = None
) -> LegendStats:
    """Mean and sd (population sd, numpy's default) of `positions` - every counted walk still
    going at `step` - beside the theory for that step: mean step(2p - 1), sd
    sqrt(4p(1 - p) step). `ended`: how many counted walks an absorbing wall has ended."""
    theory_mean = theory.final_mean(step, p_right)
    theory_sd = theory.final_sd(step, p_right)
    if len(positions) == 0:
        return LegendStats(step, 0, None, None, theory_mean, theory_sd, p_right, ended)
    mean, sd = float(positions.mean()), float(positions.std())
    return LegendStats(step, len(positions), mean, sd, theory_mean, theory_sd, p_right, ended)


def legend_lines(stats: LegendStats, with_theory: bool = True) -> list[str]:
    """The legend's lines, columns aligned for a monospaced font:

        steps      250  trials       40
        mean     -3.60  theory     0.00
        sd       15.20  theory    15.81
        P(right)   60%

    The last line only when P(right) isn't 50%. With an absorbing wall the first line goes on
    with "  absorbed     1234" (`ended`), and `trials` are the walks still going. Number columns
    are LEGEND_WIDTH wide: room for -1000.00, the mean of 1000 steps all one way. Without
    `with_theory` (the wall is on: the theory is for no wall) the mean and sd lines stop
    after the measured value. A measured value is '-' when nothing was counted. (-0.00 shows
    as 0.00.)"""
    width = LEGEND_WIDTH

    def number(value: float | None) -> str:
        if value is None:
            return f"{'-':>{width}}"
        return f"{value if round(value, 2) != 0 else 0.0:{width}.2f}"  # no "-0.00"

    mean = f"{'mean':<6}{number(stats.mean)}"
    sd = f"{'sd':<6}{number(stats.sd)}"
    if with_theory:
        mean += f"  {'theory':<7}{number(stats.theory_mean)}"
        sd += f"  {'theory':<7}{number(stats.theory_sd)}"
    steps = f"{'steps':<6}{stats.step:>{width}}  {'trials':<7}{stats.trials:>{width}}"
    if stats.ended is not None:
        steps += f"  {'absorbed':<9}{stats.ended:>{width}}"
    lines = [steps, mean, sd]
    if stats.p_right != 0.5:
        # Ends in the first number column's last place; whole percents (the dialog's steps).
        percent = f"{stats.p_right * 100:.0f}%"
        lines.append(f"{'P(right)':<8}{percent:>{6 + width - 8}}")
    return lines


def fractions_at(positions: IntArray, bins: IntArray) -> tuple[BinArray, FloatArray]:
    """Bin centres and each bin's share of `positions` (raw fractions summing to 1.0)."""
    counts, edges = np.histogram(positions, bins=bins)
    return bin_centers(edges), counts / len(positions)


def absorb_steps(paths: IntArray, wall: int) -> IntArray:
    """For an absorbing wall: the step at which each walk first reaches `wall` (or goes past
    it), or the number of points (one past the last step) if it never does.

    `paths` are free walks (no wall): an absorbed walk follows its free path exactly until it
    touches the wall, and ends there. So a walk is still going at step k when k < its value
    here; its trace runs up to and including that step. (Each step moves one position, so a
    walk always ends exactly on the wall.)"""
    hit = paths <= wall
    first = hit.argmax(axis=1)
    return np.where(hit.any(axis=1), first, paths.shape[1])


def trace_span(paths: IntArray, absorbing_wall: int | None = None) -> tuple[int, int]:
    """The lowest and highest position the walks' traces reach, for the x axis: every
    position - or, with an absorbing wall, not below it (where absorbed walks would have
    wandered after contact doesn't count).

    With the wall, the low end is exact: an absorbed walk's trace never goes below the wall
    and ends on it, and a surviving walk never reaches it, so the lowest point on any trace is
    the wall if any walk was absorbed, else the free walks' minimum. The high end is the free
    walks' maximum, which could only overstate the traces' if an absorbed walk had gone on to
    the top after contact - it would just widen the axis a little. (An exact high end took
    ~100 ms per data set.)"""
    lo, hi = int(paths.min()), int(paths.max())
    if absorbing_wall is not None:
        lo = max(lo, absorbing_wall)
    return lo, hi


def trace_grid(
    paths: IntArray, lo: int, hi: int, ends: IntArray | None = None
) -> tuple[IntArray, IntArray]:
    """The walks' traces as a grid, and each step's busiest position.

    `segments` has shape (steps, hi - lo): row k is the stretch from step k to step k + 1,
    column j the unit interval [lo + j, lo + j + 1], and each cell counts the walks whose line
    from step k to k + 1 crosses it. Every step moves a walk by exactly one position (the
    reflecting wall keeps that true), so each line crosses exactly one interval, the one
    starting at the lower of its two ends. A walk from (20, 100) to (21, 101) lands in the
    cell from 20 to 21, rows 100 to 101: drawn as an image, each walk is a chain of cells
    meeting corner to corner at its exact positions. And there's no combing: in any row the
    walks going up start their interval on one parity, those going down on the other.

    `peaks` has shape (steps + 1,): the most walks at any one position at each step - the
    tallest histogram bar's count, since width-2 parity bins hold one position each.

    With `ends` (from absorb_steps, for an absorbing wall) a walk's trace stops at its
    contact step - its last segment reaches the wall - and from that step on it isn't
    counted in `peaks` (it has left the histogram).

    `lo`..`hi` must cover every position on the traces. One column of paths at a time: low
    memory.
    """
    runs, points = paths.shape
    n_positions = hi - lo + 1
    segments = np.zeros((points - 1, max(hi - lo, 1)), dtype=np.int64)
    peaks = np.zeros(points, dtype=np.int64)
    if runs == 0:
        return segments, peaks
    n_intervals = segments.shape[1]
    for k in range(points):
        # With `ends`: still going at step k means in the histogram at k, and drawing its
        # segment to k + 1 (the last one, for a walk that touches the wall at k + 1). The
        # others go to an extra, discarded bin - faster than picking out the walks going.
        going = None if ends is None else ends > k
        here = paths[:, k] - lo
        if going is not None:
            here = np.where(going, here, n_positions)
        peaks[k] = np.bincount(here, minlength=n_positions + 1)[:n_positions].max()
        if k + 1 < points:
            starts = np.minimum(paths[:, k], paths[:, k + 1]) - lo
            if going is not None:
                starts = np.where(going, starts, n_intervals)
            segments[k] = np.bincount(starts, minlength=n_intervals + 1)[:n_intervals]
    return segments, peaks


def normalize_rows(grid: IntArray) -> FloatArray:
    """Each row scaled to its own maximum (rows of zeros stay zero), so every step is shaded
    on the same 0..1 scale however spread out its walks are."""
    peaks = grid.max(axis=1, keepdims=True)
    return np.divide(grid, peaks, out=np.zeros(grid.shape), where=peaks > 0)
