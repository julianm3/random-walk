"""The density image's numbers: the walks' traces, shaded per step and squeezed to the plot.

The drawing area turns rows() into a greyscale image; everything else happens here. Counting
the traces (simulation.trace_grid) takes ~75 ms for 10,000 walks, so it's done once per number
of trials, and the squeezed shading is cached per height.

numpy only - no GUI imports, so this can be tested without a display.
"""

from __future__ import annotations

import numpy as np

from random_walk.data import WalkData
from random_walk.simulation import FloatArray, IntArray, normalize_rows, trace_grid


class DensityShading:
    """The traces of a data set's first `trials` walks (count() picks how many), as shades from
    0 (no walk) to 1: one row per stretch between steps (row k runs from step k to k + 1), one
    column per unit interval between positions (column j from lo + j to lo + j + 1). Each row
    is scaled to its own busiest cell and raised to `gamma`, which lifts the sparse cells.

    `lo`..`hi` must cover every position on the traces (WalkData.span, or wider)."""

    def __init__(self, data: WalkData, lo: int, hi: int, gamma: float) -> None:
        self._data = data
        self._lo, self._hi = lo, hi
        self._gamma = gamma
        self.trials = -1  # counted for this many trials (-1: not yet)
        self._shade: FloatArray = np.zeros((data.steps, max(hi - lo, 1)))
        self._tallest_from: FloatArray = np.zeros(0)
        # The shading squeezed to a pixel height: (height, each pixel row's first step, rows).
        self._combined: tuple[int, IntArray, FloatArray] | None = None

    @property
    def counted(self) -> bool:
        return self.trials >= 0

    def count(self, trials: int) -> bool:
        """Count the first `trials` walks' traces, unless they're already counted. True if it
        counted (any earlier rows() results are then out of date)."""
        if trials == self.trials:
            return False
        data = self._data
        ends = None if data.ends is None else data.ends[:trials]
        segments, peaks = trace_grid(data.paths[:trials], self._lo, self._hi, ends)
        self._shade = normalize_rows(segments)
        self.trials = trials
        self._combined = None
        tallest = peaks / max(trials, 1)
        self._tallest_from = np.maximum.accumulate(tallest[::-1])[::-1]
        return True

    def tallest_from(self) -> FloatArray:
        """For each step, the tallest histogram bar's share (of the counted trials) from that
        step to the last: trace_grid's peaks (width-2 parity bins hold one position each), as
        a suffix maximum."""
        return self._tallest_from

    def rows(self, last: int, height: int | None = None) -> FloatArray:
        """The shading up to step `last` - rows beyond it are 0, as the walks haven't got there
        - with gamma applied, bottom row (step 0) first.

        With `height` below the number of steps, there are that many rows instead, each the
        darkest of the steps it covers (the pixel row holding `last` only up to `last`).
        Dropping rows instead would cut gaps into a lone walk's trace."""
        shade = self._shade
        steps = len(shade)
        height = steps if height is None else min(max(height, 1), steps)
        if height < steps:  # combine, don't drop: the darkest step in each pixel row
            # (The darkest of the lifted values is the lifted darkest value, so the gamma is
            # applied once, in the cache.)
            starts, combined = self._combined_rows(height)
            lifted = combined.copy()
            boundary = last * height // steps  # the pixel row holding step `last`
            if boundary < height:  # (at the last step every row is shown)
                lifted[boundary:] = 0
                if last > starts[boundary]:  # its steps before `last` are shown
                    darkest_so_far = shade[starts[boundary] : last].max(axis=0)
                    lifted[boundary] = darkest_so_far**self._gamma
            return lifted
        lifted = shade.copy()
        lifted[last:] = 0  # (row k runs to step k + 1)
        lifted **= self._gamma
        return lifted

    def _combined_rows(self, height: int) -> tuple[IntArray, FloatArray]:
        """The whole shading squeezed into `height` rows, each the darkest of the steps it
        covers, with gamma applied, and each row's first step. Cached per count and height,
        so a frame only has to blank the rows beyond its step."""
        if self._combined is None or self._combined[0] != height:
            steps = len(self._shade)
            pixel_rows = np.arange(steps) * height // steps  # every pixel row gets >= 1 step
            starts = np.flatnonzero(np.diff(pixel_rows, prepend=-1))
            combined = np.maximum.reduceat(self._shade, starts, axis=0) ** self._gamma
            self._combined = (height, starts, combined)
        return self._combined[1], self._combined[2]
