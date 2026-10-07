"""The shared RUNS/STEPS/WALL/SLOPE control panel at the top of the window."""

from __future__ import annotations

import dearpygui.dearpygui as dpg

from random_walk.config import (
    DEFAULT_RUNS,
    DEFAULT_SLOPE,
    DEFAULT_STEPS,
    DEFAULT_WALL,
    MAX_RUNS_INPUT,
    MAX_SLOPE,
    MAX_STEPS,
    MIN_SLOPE,
)
from random_walk.params import WalkParams, validate


def build_shared_controls() -> None:
    with dpg.group(horizontal=True):
        # label="" (a separate add_text instead) puts the label to the LEFT of each box -
        # add_input_int's own label always renders to its right.
        dpg.add_text("RUNS")
        dpg.add_input_int(
            default_value=DEFAULT_RUNS,
            tag="runs_input",
            width=120,
            min_value=1,
            min_clamped=True,
            max_value=MAX_RUNS_INPUT,
        )
        dpg.add_text("STEPS")
        dpg.add_input_int(
            default_value=DEFAULT_STEPS,
            tag="steps_input",
            width=120,
            min_value=1,
            min_clamped=True,
            max_value=MAX_STEPS,
        )
        dpg.add_checkbox(label="enable wall", default_value=False, tag="wall_checkbox")
        dpg.add_text("WALL")
        dpg.add_input_int(default_value=DEFAULT_WALL, tag="wall_input", width=90)
        dpg.add_text("SLOPE")
        dpg.add_input_float(
            default_value=DEFAULT_SLOPE,
            tag="slope_input",
            width=100,
            min_value=MIN_SLOPE,
            max_value=MAX_SLOPE,
            min_clamped=True,
            max_clamped=True,
            format="%.1f",
        )


def read_shared_params() -> tuple[WalkParams | None, str | None]:
    """Read + validate the shared controls. The only place these widgets should be read.

    Returns (params, None) on success, or (None, error message to display) on failure.
    """
    runs = dpg.get_value("runs_input")
    steps = dpg.get_value("steps_input")
    theta = dpg.get_value("slope_input")
    error = validate(runs, steps, theta)
    if error:
        return None, error
    params = WalkParams(
        runs=runs,
        steps=steps,
        wall_enabled=dpg.get_value("wall_checkbox"),
        wall_value=dpg.get_value("wall_input"),
        theta=theta,
    )
    return params, None
