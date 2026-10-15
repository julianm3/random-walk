"""Axis tick values: round numbers spread evenly across a range. No GUI imports."""

from __future__ import annotations

import math

NICE_MULTIPLIERS = (1, 2, 5, 10)


def nice_step(span: float, max_ticks: int, min_step: float = 0.0) -> float:
    """The smallest step of the form 1, 2 or 5 x 10^n that divides `span` into at most
    `max_ticks` intervals, and is at least `min_step` (e.g. 1 for integer data)."""
    if span <= 0 or max_ticks < 1:
        return max(min_step, 1.0)
    raw = span / max_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiplier in NICE_MULTIPLIERS:
        step = multiplier * magnitude
        if span / step <= max_ticks * (1 + 1e-9):  # tolerance: 0.07 / 0.01 = 7.000000000000001
            return max(step, min_step)
    return max(10 * magnitude, min_step)  # unreachable in practice: 10 always satisfies


def nice_ticks(lo: float, hi: float, max_ticks: int, min_step: float = 0.0) -> list[float]:
    """Tick values inside [lo, hi], every nice_step() apart, starting from a multiple of the
    step (so 0 is a tick whenever the range includes it)."""
    if hi < lo:
        lo, hi = hi, lo
    step = nice_step(hi - lo, max_ticks, min_step)
    first = math.ceil(lo / step - 1e-9) * step
    ticks = []
    value = first
    while value <= hi + 1e-9 * step:
        ticks.append(round(value, 10) + 0.0)  # tidy float noise; +0.0 turns -0.0 into 0.0
        value += step
    return ticks


def tick_label(value: float) -> str:
    """Whole numbers without a decimal point; others with as few decimals as needed."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"
