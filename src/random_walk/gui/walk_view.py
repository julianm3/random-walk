"""The drawing area: plots a simulated data set in one of several drawings (see `Drawing`).

Walks: the first N walks (trials), each from the bottom of the plot (step 0) to the top (the
last step), with a step axis on the left. Histogram: the final positions of all trials, in
width-2 bins, as light grey bars whose heights are each bin's share of the trials, with a
probability axis on the right. A drawing can show both (an overlay): the bars go behind the
walks, and each keeps its own vertical axis.

Every drawing shares the x axis along the bottom: position, spanning the data set's full
range - the lowest to the highest reached by any trial at any step - so every walk in the set
would fit and every drawing uses the same range. Room for both side axes is always reserved,
so the plot lines up exactly from one drawing to the next. Everything stretches to fill the
area, and rescales (and re-picks its ticks) when the window is resized.

    walks                                     histogram
    +-----------------------------------+     +-----------------------------------+
    | 1000 -+           :               |     |              ___            +- 0.03|
    |  500 -+          .:.              |     |          ___|   |___        +- 0.02|
    |    0 -+------+------+------+---   |     |   ___|___|  ...    |___|___  +- 0  |
    |     -100     0     100            |     |  -100      0       100            |
    +-----------------------------------+     +-----------------------------------+
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import shiboken6
from numpy.typing import NDArray
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFontMetricsF,
    QImage,
    QPainter,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QFrame, QWidget

from random_walk.simulation import density_grid, fractions_at, normalize_rows, parity_bins
from random_walk.ticks import nice_step, nice_ticks, tick_label

MARGIN = 8  # px; blank border inside the frame, so nothing touches it
# One colour per walk, in trial order (trial 1 first), cycling if more are shown. Black, then
# the Okabe-Ito palette, which stays distinguishable with common colour-vision deficiencies.
WALK_COLORS = ("black", "#E69F00", "#56B4E9", "#009E73", "#D55E00", "#0072B2", "#CC79A7")
WALK_WIDTH = 1.0  # px
BAR_COLOR = "#d3d3d3"  # light grey histogram bars
# Density shading runs from the background (no walks) to this grey (a step's busiest cell),
# stopping short of black so black histogram bars stay distinct in front of it.
DENSITY_DARKEST = "#404040"
DENSITY_BIN_WIDTH = 2  # positions per density column (one even, one odd)
BAR_GAP = 1.0  # px between neighbouring bars, so they stay distinct
AXIS_COLOR = "black"
AXIS_WIDTH = 1.0  # px; axis lines and ticks
TICK_LENGTH = 5  # px; ticks point outwards from the plot
LABEL_GAP = 2  # px between a tick's end and its label
MIN_TICK_SPACING = 65  # px; x ticks are thinned to keep at least this far apart
MIN_Y_TICK_SPACING = 40  # px; y labels are one line tall, so they can sit closer


@dataclass(frozen=True)
class Drawing:
    """What the drawing area shows: a density image of every walk, the first `walks` walks,
    and/or the final-position histogram - back to front in that order, except that the
    histogram goes in front with `histogram_in_front`. The histogram counts every trial, or
    with `histogram_from_walks` only the walks drawn (sparse for a handful of walks), and its
    bars are `histogram_color` at `histogram_opacity` (below 1 lets what's behind show through).
    Walks take one colour each from WALK_COLORS, or all `walk_color` if set, at `walk_opacity`
    (below 1, overlapping walks build up darker, like density shading)."""

    density: bool = False
    walks: int = 0
    histogram: bool = False
    histogram_from_walks: bool = False
    histogram_color: str = BAR_COLOR
    histogram_in_front: bool = False
    histogram_opacity: float = 1.0
    walk_color: str | None = None
    walk_opacity: float = 1.0
    # Show the data set as it stood at this step (None: the last). Walks and the density stop
    # there and the histogram counts positions at it; the axes don't change.
    at_step: int | None = None


def x_to_screen(
    values: NDArray[Any] | float, x_range: tuple[int, int], area: QRectF
) -> NDArray[np.float64]:
    """Map positions in `x_range` onto the area's width (an array, 0-d for a single value)."""
    lo, hi = x_range
    span = (hi - lo) or 1  # a set whose walks never move would divide by zero
    return area.left() + (np.asarray(values, dtype=float) - lo) / span * area.width()


def walk_points(
    path: NDArray[np.int64],
    x_range: tuple[int, int],
    area: QRectF,
    total_steps: int | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Screen coordinates for one walk: x is the position scaled from `x_range` across the
    area's width, y is the step scaled from the bottom (step 0) to the top (`total_steps`,
    default the path's own last step - pass it to draw a walk cut short at its true height)."""
    steps = len(path) - 1 if total_steps is None else total_steps
    xs = x_to_screen(path, x_range, area)
    ys = area.bottom() - np.arange(len(path)) / max(steps, 1) * area.height()
    return xs, ys


def polygon_from_arrays(xs: NDArray[np.float64], ys: NDArray[np.float64]) -> QPolygonF:
    """A QPolygonF filled straight from numpy arrays.

    Building one QPointF per point in Python costs about 1 us each - 0.2 s for 200 walks of
    1001 points. Instead, size the polygon and write its point storage (pairs of doubles)
    through a numpy view of that memory, as pyqtgraph does: about 100x faster. Falls back to
    the per-point way if this PySide6 build doesn't expose the storage as expected.
    """
    n = len(xs)
    polygon = QPolygonF()
    if n == 0:
        return polygon
    polygon.resize(n)
    try:
        address = shiboken6.getCppPointer(polygon.data())[0]
        # shiboken6's type stubs omit VoidPtr's (address, size, writable) form and its
        # buffer protocol; both work at runtime.
        memory = shiboken6.VoidPtr(address, 2 * n * 8, True)  # type: ignore[call-arg]
        points = np.frombuffer(memory, dtype=np.float64).reshape(n, 2)  # type: ignore[call-overload]
        points[:, 0] = xs
        points[:, 1] = ys
    except (TypeError, ValueError, AttributeError):
        polygon = QPolygonF([QPointF(x, y) for x, y in zip(xs, ys, strict=True)])
    return polygon


def probability_ticks(highest: float, max_ticks: int) -> list[float]:
    """Ticks from 0 up to the first round value at or above `highest`, so the tallest bar
    stays below the top of the axis."""
    step = nice_step(highest, max_ticks)
    top = math.ceil(highest / step - 1e-9) * step
    return [round(i * step, 10) for i in range(round(top / step) + 1)]


class WalkView(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self._paths: NDArray[np.int64] | None = None
        self._x_range = (0, 0)
        self._steps = 0
        self._drawing = Drawing(walks=1)
        # Final-position histogram of every trial: bin centres and each bin's share.
        self._bins: NDArray[Any] = np.zeros(0)
        self._fractions: NDArray[np.float64] = np.zeros(0)
        self._density_shade: NDArray[np.float64] | None = None  # built on first use
        self._density_images: dict[int, QImage] = {}  # by last step shown

    def set_paths(self, paths: NDArray[np.int64]) -> None:
        """The data set to draw: shape (trials, steps + 1), as from simulate_paths()."""
        self._paths = paths
        self._x_range = (int(paths.min()), int(paths.max()))
        self._steps = paths.shape[1] - 1
        finals = paths[:, -1]
        self._bins, self._fractions = fractions_at(finals, parity_bins(finals))
        self._density_shade = None
        self._density_images = {}
        self.update()

    def set_drawing(self, drawing: Drawing) -> None:
        self._drawing = drawing
        self.update()

    def drawing(self) -> Drawing:
        return self._drawing

    def set_walk_count(self, count: int) -> None:
        """Draw the first `count` walks of the data set."""
        self.set_drawing(Drawing(walks=max(0, count)))

    def walk_count(self) -> int:
        return self._drawing.walks

    def x_range(self) -> tuple[int, int]:
        """Lowest and highest position in the data set (any trial, any step)."""
        return self._x_range

    def shown_step(self) -> int:
        """The last step the current drawing shows (its `at_step`, or the data's last)."""
        step = self._drawing.at_step
        return self._steps if step is None else min(max(step, 0), self._steps)

    def histogram(self) -> tuple[NDArray[Any], NDArray[np.float64]]:
        """The current drawing's histogram: bin centres and each bin's share of the trials
        counted (positions at the shown step; sums to 1) - every trial, or only the drawn
        walks."""
        d = self._drawing
        if self._paths is None or (not d.histogram_from_walks and self.shown_step() == self._steps):
            return self._bins, self._fractions  # every trial's final positions, precomputed
        trials = max(1, d.walks) if d.histogram_from_walks else len(self._paths)
        positions = self._paths[:trials, self.shown_step()]
        return fractions_at(positions, parity_bins(positions))

    # --- geometry ------------------------------------------------------------------------

    def _inner(self) -> QRectF:
        """Inside the frame, less MARGIN on every side."""
        return QRectF(self.contentsRect()).adjusted(MARGIN, MARGIN, -MARGIN, -MARGIN)

    def _x_axis_height(self) -> float:
        """Room below the plot for the x ticks and their labels."""
        return TICK_LENGTH + LABEL_GAP + QFontMetricsF(self.font()).height()

    def _plot_height(self) -> float:
        return self._inner().height() - self._x_axis_height()

    def _max_y_ticks(self) -> int:
        return max(1, int(self._plot_height() // MIN_Y_TICK_SPACING))

    def _step_tick_values(self) -> list[float]:
        return nice_ticks(0, self._steps, self._max_y_ticks(), min_step=1)

    def _probability_tick_values(self, full: bool = False) -> list[float]:
        """Ticks for the current drawing's histogram, or with `full` for every trial's."""
        fractions = self._fractions if full else self.histogram()[1]
        if len(fractions) == 0:
            return []
        return probability_ticks(float(fractions.max()), self._max_y_ticks())

    def y_ticks(self) -> list[float]:
        """Steps that get a tick on the left axis (only when walks are drawn)."""
        return self._step_tick_values() if self._shows_steps() else []

    def _shows_steps(self) -> bool:
        """Walks and the density image both run up the step axis."""
        return self._drawing.walks > 0 or self._drawing.density

    def probability_ticks(self) -> list[float]:
        """Probabilities that get a tick on the right axis (only with the histogram)."""
        return self._probability_tick_values() if self._drawing.histogram else []

    def _labels_width(self, values: list[float]) -> float:
        """Room beside the plot for ticks with these labels (0 if there are none)."""
        if not values:
            return 0.0
        metrics = QFontMetricsF(self.font())
        return max(metrics.horizontalAdvance(tick_label(v)) for v in values) + (
            LABEL_GAP + TICK_LENGTH
        )

    def walk_area(self) -> QRectF:
        """The plot: its bottom edge is the x axis; the left edge carries the step axis (walks)
        and the right edge the probability axis (histogram). Room for both side axes is always
        reserved, so the plot - and every position on the x axis - stays put when the drawing
        changes."""
        left = self._labels_width(self._step_tick_values())
        # The right axis's labels depend on the histogram shown, so reserve the wider of the
        # full histogram's and the current one's (the full one's for walk-only drawings).
        right = max(
            self._labels_width(self._probability_tick_values(full=True)),
            self._labels_width(self.probability_ticks()),
        )
        return self._inner().adjusted(left, 0, -right, -self._x_axis_height())

    def ticks(self) -> list[float]:
        """Positions that get an x tick, thinned to fit the current width."""
        lo, hi = self._x_range
        max_ticks = max(1, int(self.walk_area().width() // MIN_TICK_SPACING))
        return nice_ticks(lo, hi, max_ticks, min_step=1)  # positions are whole numbers

    # --- painting ------------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)  # the frame
        if self._paths is None or len(self._paths) == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Back to front: density, histogram bars and walks (in the drawing's order), then axes.
        d = self._drawing
        if d.density:
            self._paint_density(painter)
        if d.histogram and not d.histogram_in_front:
            self._paint_histogram(painter)
        if d.walks > 0:
            self._paint_walks(painter)
        if d.histogram and d.histogram_in_front:
            self._paint_histogram(painter)
        if self._drawing.histogram:
            self._paint_probability_axis(painter)
        if self._shows_steps():
            self._paint_step_axis(painter)
        self._paint_x_axis(painter)

    def density_image(self) -> QImage:
        """Every walk's position at every step as a greyscale image: one row per step (step 0
        at the bottom), one column per DENSITY_BIN_WIDTH positions, each row shaded relative
        to its own busiest cell; rows above the shown step are left empty. Counted once per
        data set (~0.1 s for 10,000 walks); each shown step's image is cached."""
        last = self.shown_step()
        if last not in self._density_images:
            assert self._paths is not None
            if self._density_shade is None:
                lo, hi = self._x_range
                self._density_shade = normalize_rows(
                    density_grid(self._paths, lo, hi, DENSITY_BIN_WIDTH)
                )
            shade = self._density_shade.copy()
            shade[last + 1 :] = 0  # the walks haven't got there yet
            empty = self.palette().window().color().lightness()
            darkest = QColor(DENSITY_DARKEST).lightness()
            grey = np.round(empty - shade * (empty - darkest)).astype(np.uint8)
            pixels = np.ascontiguousarray(grey[::-1])  # image rows run top-down
            height, width = pixels.shape
            image = QImage(pixels.data, width, height, width, QImage.Format.Format_Grayscale8)
            self._density_images[last] = image.copy()  # own the pixels; `pixels` is temporary
        return self._density_images[last]

    def _paint_density(self, painter: QPainter) -> None:
        image = self.density_image()
        area = self.walk_area()
        lo = self._x_range[0]
        # Column j holds positions lo + 2j and lo + 2j + 1, so it's centred half a position
        # right of lo + 2j; rows are centred on their steps.
        left = float(x_to_screen(lo - 0.5, self._x_range, area))
        right = float(
            x_to_screen(lo + image.width() * DENSITY_BIN_WIDTH - 0.5, self._x_range, area)
        )
        row = area.height() / max(self._steps, 1)
        target = QRectF(left, area.top() - row / 2, right - left, area.height() + row)
        painter.save()
        painter.setClipRect(area)
        painter.drawImage(target, image)  # nearest-neighbour scaling keeps the bins crisp
        painter.restore()

    def _paint_walks(self, painter: QPainter) -> None:
        assert self._paths is not None
        area = self.walk_area()
        shown = min(self._drawing.walks, len(self._paths))
        last = self.shown_step()
        for trial in reversed(range(shown)):  # trial 1 drawn last, so it's on top
            path = self._paths[trial, : last + 1]
            xs, ys = walk_points(path, self._x_range, area, total_steps=self._steps)
            color = QColor(self._drawing.walk_color or WALK_COLORS[trial % len(WALK_COLORS)])
            color.setAlphaF(self._drawing.walk_opacity)
            painter.setPen(QPen(color, WALK_WIDTH))
            painter.drawPolyline(polygon_from_arrays(xs, ys))

    def _paint_histogram(self, painter: QPainter) -> None:
        ticks = self.probability_ticks()
        if not ticks:
            return
        area, top = self.walk_area(), ticks[-1]
        painter.setPen(Qt.PenStyle.NoPen)
        color = QColor(self._drawing.histogram_color)
        color.setAlphaF(self._drawing.histogram_opacity)
        painter.setBrush(color)
        bins, fractions = self.histogram()
        lefts = x_to_screen(bins - 1, self._x_range, area)  # bins are 2 positions wide
        rights = x_to_screen(bins + 1, self._x_range, area)
        for left, right, fraction in zip(lefts, rights, fractions, strict=True):
            if fraction <= 0:
                continue
            height = fraction / top * area.height()
            width = max(float(right - left) - BAR_GAP, 1.0)
            painter.drawRect(
                QRectF(float(left) + BAR_GAP / 2, area.bottom() - height, width, height)
            )

    def _paint_x_axis(self, painter: QPainter) -> None:
        area, inner = self.walk_area(), self._inner()
        y = area.bottom()
        painter.setPen(QPen(QColor(AXIS_COLOR), AXIS_WIDTH))
        painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))

        metrics = QFontMetricsF(self.font())
        label_top = y + TICK_LENGTH + LABEL_GAP
        for value in self.ticks():
            x = float(x_to_screen(value, self._x_range, area))
            painter.drawLine(QPointF(x, y), QPointF(x, y + TICK_LENGTH))
            text = tick_label(value)
            width = metrics.horizontalAdvance(text)
            # Centred under the tick, but kept inside the frame at the ends.
            left = min(max(x - width / 2, inner.left()), inner.right() - width)
            rect = QRectF(left, label_top, width, metrics.height())
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_step_axis(self, painter: QPainter) -> None:
        """Left axis for walk drawings: step 0 at the bottom up to the last step."""
        self._paint_y_axis(painter, self.y_ticks(), max(self._steps, 1), right_side=False)

    def _paint_probability_axis(self, painter: QPainter) -> None:
        """Right axis for the histogram: 0 at the bottom up to the top tick."""
        ticks = self.probability_ticks()
        if ticks:
            self._paint_y_axis(painter, ticks, ticks[-1], right_side=True)

    def _paint_y_axis(
        self, painter: QPainter, ticks: list[float], top_value: float, right_side: bool
    ) -> None:
        """A vertical axis on the left or right edge of the plot, 0 at the bottom and
        `top_value` at the top, with ticks pointing outwards and labels beside them."""
        area, inner = self.walk_area(), self._inner()
        x = area.right() if right_side else area.left()
        painter.setPen(QPen(QColor(AXIS_COLOR), AXIS_WIDTH))
        painter.drawLine(QPointF(x, area.bottom()), QPointF(x, area.top()))

        metrics = QFontMetricsF(self.font())
        height = metrics.height()
        outward = TICK_LENGTH if right_side else -TICK_LENGTH
        for value in ticks:
            y = area.bottom() - value / top_value * area.height()
            painter.drawLine(QPointF(x, y), QPointF(x + outward, y))
            # Beside the tick, centred on it, but kept inside the frame.
            top = min(max(y - height / 2, inner.top()), inner.bottom() - height)
            if right_side:
                left = x + TICK_LENGTH + LABEL_GAP
                rect = QRectF(left, top, inner.right() - left, height)
                align = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            else:
                right = x - TICK_LENGTH - LABEL_GAP
                rect = QRectF(inner.left(), top, right - inner.left(), height)
                align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            painter.drawText(rect, align, tick_label(value))
