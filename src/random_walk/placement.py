"""Which top corner of the plot the legend box goes in. No GUI imports.

The box starts at the top right and moves to the other top corner when the histogram's bars
crowd its corner but not the other. A margin (hysteresis) stops it flickering between two
corners that are about equally crowded, e.g. a centred bell whose bars brush both.
"""

from __future__ import annotations

from typing import Literal

Side = Literal["left", "right"]
SWITCH_RATIO = 0.5  # move only if the other corner is covered at most this much as the current


def legend_side(current: Side, covered_left: float, covered_right: float) -> Side:
    """The corner for the legend, given how much of the bars the box would cover in each
    (any consistent measure, e.g. pixel area). Stays put while its corner is clear or the
    other is not clearly emptier."""
    here, there = (
        (covered_left, covered_right) if current == "left" else (covered_right, covered_left)
    )
    if here > 0 and there <= here * SWITCH_RATIO:
        return "right" if current == "left" else "left"
    return current
