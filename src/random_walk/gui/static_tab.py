"""The Static tab: one histogram of final positions. Deliberately simple - no timeline."""

from __future__ import annotations

from typing import Any

import dearpygui.dearpygui as dpg

from random_walk.gui.controls import read_shared_params
from random_walk.params import WalkParams
from random_walk.simulation import simulate, summarize


def build_static_tab() -> None:
    with dpg.group(horizontal=True):
        dpg.add_button(label="Run", callback=run_static)
    dpg.add_text("", tag="stats_text")
    dpg.add_spacer(height=4)
    with dpg.plot(label="", tag="plot", height=-1, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="probability density", tag="x_axis")
        with dpg.plot_axis(dpg.mvYAxis, label="final position", tag="y_axis", invert=True):
            dpg.add_bar_series(
                [], [], weight=2.0, horizontal=True, label="simulation", tag="hist_series"
            )
            dpg.add_line_series([], [], label="theory", tag="curve_series")
            dpg.add_line_series([], [], label="wall", tag="wall_series", show=False)


def static_title(params: WalkParams) -> str:
    title = f"{params.runs:,} walks of {params.steps:,} steps"
    if params.wall_enabled:
        title += f", wall at {params.wall_value}"
    if params.theta != 0:
        title += f", slope = {params.theta:g} deg"
    return title


def run_static() -> None:
    params, error = read_shared_params()
    if params is None:
        dpg.set_value("stats_text", error)
        return

    finals = simulate(params.runs, params.steps, params.wall, params.theta)
    s = summarize(finals, params.steps, params.wall_enabled, params.wall_value, params.theta)

    # View rotated 90 degrees clockwise from a vertical histogram: position is on the y-axis
    # (inverted, so increasing position points down the screen - that's what makes it
    # clockwise rather than counterclockwise), density on the x-axis. Dear PyGui's horizontal
    # bar series takes (length, category) as (x, y) - i.e. density first, position second.
    dpg.set_value("hist_series", [s.counts.tolist(), s.centers.tolist()])
    dpg.set_value("curve_series", [s.curve_y.tolist(), s.curve_x.tolist()])
    dpg.configure_item("curve_series", show=s.show_curve)

    if params.wall_enabled:
        top = max(s.counts.max(), s.curve_y.max() if s.show_curve else 0) * 1.15
        dpg.set_value("wall_series", [[0, top], [params.wall_value, params.wall_value]])
        dpg.configure_item("wall_series", show=True)
    else:
        dpg.configure_item("wall_series", show=False)

    dpg.set_value("stats_text", s.stats)
    print(f"RUNS={params.runs}, STEPS={params.steps}: {s.stats}")
    dpg.configure_item("plot", label=static_title(params))

    dpg.fit_axis_data("x_axis")
    dpg.fit_axis_data("y_axis")


def run_on_enter(sender: Any, key: int) -> None:
    """Run the Static tab when Enter/Return is pressed, anywhere - including with nothing
    focused and nothing changed, to simply repeat the current run.

    Deliberately not using add_input_int's own on_enter=True: that flag also changes how the
    widget commits its value (discarding a typed-but-unconfirmed edit on any focus loss other
    than Enter). This is a global key handler instead.
    """
    if key in (dpg.mvKey_Return, dpg.mvKey_NumPadEnter):
        run_static()
