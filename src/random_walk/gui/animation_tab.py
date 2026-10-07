"""The Animation tab: one shared plot and one shared timeline, with a dropdown choosing which
of four displays is currently shown:

  Distribution       - runs are added one at a time to a growing histogram.
  Single Walk        - pick one walk (max/min ending point, or the nth one) and watch its
                       position step by step. Multiple walks can be added and compared; each
                       stays on screen until Clear.
  Evolving Histogram - a histogram of every walk's CURRENT position, evolving as the steps
                       progress.
  All Paths          - every walk's own path animating together (capped, for render
                       performance).
"""

from __future__ import annotations

from typing import Any

import dearpygui.dearpygui as dpg
import numpy as np

from random_walk.config import DEFAULT_MAX_LINES, DEFAULT_STEPS, HIST_X_MAX, MAX_LINES_CAP
from random_walk.gui.controls import read_shared_params
from random_walk.gui.transport import Transport
from random_walk.simulation import (
    fractions_at,
    parity_bins,
    position_stats,
    simulate,
    simulate_paths,
    summarize,
)

ANIM_MODES = ["Distribution", "Single Walk", "Evolving Histogram", "All Paths"]
SINGLE_WALK_CHOICES = ["max ending point", "min ending point", "nth walk"]

X_LABELS = {
    "Distribution": "probability density",
    "Single Walk": "step",
    "Evolving Histogram": "fraction of walks",
    "All Paths": "step",
}

ModeData = dict[str, Any]


class AnimationTab:
    def __init__(self, preset_theme: int | str) -> None:
        # Each mode's simulated data, cached independently - None until that mode has been run
        # at least once. Keeping these separate means switching modes never loses anything,
        # and re-running a mode with unchanged params just resumes instead of re-simulating
        # (each has its own "cache_key", a WalkParams, for that check).
        self.data: dict[str, ModeData | None] = {mode: None for mode in ANIM_MODES}
        self.transport = Transport(
            "anim",
            plot="anim_plot",
            redraw=self.redraw,
            preset_theme=preset_theme,
            play=self.play_or_start,
        )
        self._starters = {
            "Distribution": self.start_distribution,
            "Evolving Histogram": self.start_histogram,
            "All Paths": self.start_paths,
        }
        self._redrawers = {
            "Distribution": self.redraw_distribution,
            "Single Walk": self.redraw_single,
            "Evolving Histogram": self.redraw_histogram,
            "All Paths": self.redraw_paths,
        }

    def build(self) -> None:
        with dpg.group(horizontal=True):
            dpg.add_text("Show")
            dpg.add_combo(
                ANIM_MODES,
                default_value="Distribution",
                tag="anim_mode",
                width=200,
                callback=self.on_mode_changed,
            )
        with dpg.group(horizontal=True, tag="sw_controls", show=False):
            dpg.add_radio_button(
                SINGLE_WALK_CHOICES,
                default_value=SINGLE_WALK_CHOICES[0],
                tag="sw_mode",
                horizontal=True,
            )
            dpg.add_text("N")
            dpg.add_input_int(default_value=1, tag="sw_n", width=90, min_value=1, min_clamped=True)
            dpg.add_button(label="Add Walk", callback=self.add_walk)
            dpg.add_button(label="Clear", callback=self.clear_single)
        with dpg.group(horizontal=True, tag="ap_controls", show=False):
            dpg.add_text("max lines")
            dpg.add_input_int(
                default_value=DEFAULT_MAX_LINES,
                tag="ap_max_lines",
                width=100,
                min_value=1,
                max_value=MAX_LINES_CAP,
                min_clamped=True,
                max_clamped=True,
            )
        dpg.add_text("", tag="anim_stats_text")
        with dpg.plot(label="", tag="anim_plot", height=-60, width=-1):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="probability density", tag="anim_x_axis")
            with dpg.plot_axis(dpg.mvYAxis, label="final position", tag="anim_y_axis", invert=True):
                dpg.add_bar_series(
                    [], [], weight=2.0, horizontal=True, label="simulation", tag="anim_hist_series"
                )
                dpg.add_line_series([], [], label="theory", tag="anim_curve_series")
                dpg.add_line_series([], [], label="wall", tag="anim_wall_series", show=False)
        self.transport.build()

    def current_mode(self) -> str:
        return dpg.get_value("anim_mode")

    def _begin(self, n: int, redraw: Any) -> None:
        """Common tail of every mode's start: start the timeline and draw its first frame."""
        self.transport.start(n)
        redraw(0)
        self.transport.pb.last_drawn = 0

    # --- Distribution: runs added one at a time to a growing histogram ------------------

    def start_distribution(self) -> None:
        params, error = read_shared_params()
        if params is None:
            dpg.set_value("anim_stats_text", error)
            return

        finals = simulate(params.runs, params.steps, params.wall, params.theta)
        bins = parity_bins(finals)
        lo = params.wall_value if params.wall_enabled else finals.min()
        curve_x_range = (float(lo), float(finals.max()))

        # Fixed, once, from the COMPLETE data set, so the axes stay put while the animation
        # plays - otherwise the view would keep rescaling as each new run comes in.
        full = summarize(
            finals,
            params.steps,
            params.wall_enabled,
            params.wall_value,
            params.theta,
            bins=bins,
            curve_x_range=curve_x_range,
        )
        x_max = max(full.counts.max(), full.curve_y.max() if full.show_curve else 0) * 1.15

        title = f"{params.runs:,} walks of {params.steps:,} steps - building up run by run"
        self.data["Distribution"] = {
            "finals": finals,
            "params": params,
            "bins": bins,
            "curve_x_range": curve_x_range,
            "cache_key": params,
            "n": params.runs + 1,
            "x_max": x_max,
            "y_lo": bins.min(),
            "y_hi": bins.max(),
            "title": title,
        }
        dpg.configure_item("anim_plot", label=title)
        self.apply_mode_visuals("Distribution")
        self._begin(params.runs + 1, self.redraw_distribution)

    def redraw_distribution(self, frame_int: int) -> None:
        data = self.data["Distribution"]
        if data is None:
            return
        finals_all = data["finals"]
        params = data["params"]
        included = finals_all[:frame_int]

        if frame_int < 2:
            dpg.set_value("anim_hist_series", [[], []])
            dpg.configure_item("anim_curve_series", show=False)
            dpg.configure_item("anim_wall_series", show=False)
            dpg.set_value("anim_stats_text", f"{frame_int} of {len(finals_all)} runs so far")
            return

        s = summarize(
            included,
            params.steps,
            params.wall_enabled,
            params.wall_value,
            params.theta,
            bins=data["bins"],
            curve_x_range=data["curve_x_range"],
        )

        dpg.set_value("anim_hist_series", [s.counts.tolist(), s.centers.tolist()])
        dpg.set_value("anim_curve_series", [s.curve_y.tolist(), s.curve_x.tolist()])
        dpg.configure_item("anim_curve_series", show=s.show_curve)

        if params.wall_enabled:
            top = max(s.counts.max(), s.curve_y.max() if s.show_curve else 0) * 1.15
            dpg.set_value("anim_wall_series", [[0, top], [params.wall_value, params.wall_value]])
            dpg.configure_item("anim_wall_series", show=True)
        else:
            dpg.configure_item("anim_wall_series", show=False)

        dpg.set_value(
            "anim_stats_text", f"{frame_int} of {len(finals_all)} runs so far - {s.stats}"
        )

    # --- Single Walk: one walk at a time, each kept on screen once drawn ----------------

    def _finish_active_single_walk(self) -> None:
        """If a walk is mid-reveal, snap it to fully drawn before starting a new one, so
        previously selected walks always end up completely shown rather than half-drawn."""
        data = self.data["Single Walk"]
        if data and data["active_tag"] is not None:
            path = data["active_path"]
            dpg.set_value(data["active_tag"], [list(range(len(path))), path.tolist()])

    def add_walk(self) -> None:
        params, error = read_shared_params()
        if params is None:
            dpg.set_value("anim_stats_text", error)
            return

        choice = dpg.get_value("sw_mode")
        n = dpg.get_value("sw_n")
        if choice == "nth walk" and not 1 <= n <= params.runs:
            dpg.set_value("anim_stats_text", f"N must be between 1 and {params.runs}")
            return

        data = self.data["Single Walk"]
        if data is None:
            data = {
                "active_tag": None,
                "active_path": None,
                "counter": 0,
                "line_tags": [],
                "y_lo": None,
                "y_hi": None,
                "cache_key": None,
                "paths": None,
                "n": 0,
                "steps": 0,
            }
            self.data["Single Walk"] = data

        # Reuse the same simulated batch across Add Walk clicks (so "max" and "min" are the
        # actual max and min of one shared population, not two unrelated ones) unless the
        # params have changed since the last click.
        if data["cache_key"] != params:
            data["paths"] = simulate_paths(params.runs, params.steps, params.wall, params.theta)
            data["cache_key"] = params
        paths = data["paths"]

        finals = paths[:, -1]
        if choice == "max ending point":
            idx = int(np.argmax(finals))
        elif choice == "min ending point":
            idx = int(np.argmin(finals))
        else:
            idx = n - 1
        path = paths[idx]

        self._finish_active_single_walk()

        data["counter"] += 1
        tag = f"sw_line_{data['counter']}"
        dpg.add_line_series(
            [0], [0], label=f"walk #{idx + 1} ({choice})", tag=tag, parent="anim_y_axis"
        )
        data["line_tags"].append(tag)
        data["active_tag"] = tag
        data["active_path"] = path
        data["steps"] = params.steps
        data["n"] = params.steps + 1
        data["title"] = f"{params.runs:,} walks of {params.steps:,} steps"

        lo, hi = int(path.min()), int(path.max())
        data["y_lo"] = lo if data["y_lo"] is None else min(data["y_lo"], lo)
        data["y_hi"] = hi if data["y_hi"] is None else max(data["y_hi"], hi)

        dpg.set_value("anim_stats_text", f"walk #{idx + 1} ({choice}): final position = {path[-1]}")
        dpg.configure_item("anim_plot", label=data["title"])
        self.apply_mode_visuals("Single Walk")
        self._begin(params.steps + 1, self.redraw_single)

    def redraw_single(self, frame_int: int) -> None:
        data = self.data["Single Walk"]
        if data is None or data["active_tag"] is None:
            return
        path = data["active_path"][: frame_int + 1]
        dpg.set_value(data["active_tag"], [list(range(len(path))), path.tolist()])

    def clear_single(self) -> None:
        data = self.data["Single Walk"]
        if data is not None:
            for tag in data["line_tags"]:
                if dpg.does_item_exist(tag):
                    dpg.delete_item(tag)
        self.data["Single Walk"] = None
        self.transport.reset()
        dpg.set_axis_limits_auto("anim_x_axis")
        dpg.set_axis_limits_auto("anim_y_axis")
        dpg.set_value("anim_stats_text", "")

    # --- Evolving Histogram: a histogram of every walk's current position, over steps ---

    def start_histogram(self) -> None:
        params, error = read_shared_params()
        if params is None:
            dpg.set_value("anim_stats_text", error)
            return

        paths = simulate_paths(params.runs, params.steps, params.wall, params.theta)
        # Fixed bins from the global min/max seen across every step of every walk, so the
        # view doesn't keep rescaling as the spread grows over time.
        bins = parity_bins(paths)

        title = f"{params.runs:,} walks of {params.steps:,} steps"
        self.data["Evolving Histogram"] = {
            "paths": paths,
            "bins": bins,
            "wall_enabled": params.wall_enabled,
            "wall_value": params.wall_value,
            "steps": params.steps,
            "cache_key": params,
            "n": params.steps + 1,
            "y_lo": bins.min(),
            "y_hi": bins.max(),
            "title": title,
        }
        dpg.configure_item("anim_plot", label=title)
        self.apply_mode_visuals("Evolving Histogram")
        self._begin(params.steps + 1, self.redraw_histogram)

    def redraw_histogram(self, frame_int: int) -> None:
        data = self.data["Evolving Histogram"]
        if data is None:
            return
        column = data["paths"][:, frame_int]
        centers, fractions = fractions_at(column, data["bins"])
        dpg.set_value("anim_hist_series", [fractions.tolist(), centers.tolist()])

        if data["wall_enabled"]:
            dpg.set_value(
                "anim_wall_series", [[0, HIST_X_MAX], [data["wall_value"], data["wall_value"]]]
            )
            dpg.configure_item("anim_wall_series", show=True)
        else:
            dpg.configure_item("anim_wall_series", show=False)

        dpg.set_value(
            "anim_stats_text", f"step {frame_int} of {data['steps']}: {position_stats(column)}"
        )

    # --- All Paths: every walk's own path animating together (capped) -------------------

    def start_paths(self) -> None:
        params, error = read_shared_params()
        if params is None:
            dpg.set_value("anim_stats_text", error)
            return

        max_lines = dpg.get_value("ap_max_lines")
        paths = simulate_paths(params.runs, params.steps, params.wall, params.theta)
        count = min(params.runs, max_lines)
        sample_idx = np.linspace(0, params.runs - 1, count).astype(int)

        old = self.data["All Paths"]
        if old is not None:
            for tag in old["line_tags"]:
                if dpg.does_item_exist(tag):
                    dpg.delete_item(tag)

        # Start each line with just its first point; redraw_paths() grows them frame by
        # frame. The x-axis is static, so each line's own data has to grow (rather than
        # revealing a full line via a moving axis limit).
        line_tags = []
        for k, idx in enumerate(sample_idx):
            tag = f"ap_line_{k}"
            dpg.add_line_series([0], [int(paths[idx, 0])], tag=tag, parent="anim_y_axis")
            line_tags.append(tag)

        title = f"{params.runs:,} walks of {params.steps:,} steps ({count} shown)"
        self.data["All Paths"] = {
            "paths": paths,
            "line_tags": line_tags,
            "sample_idx": sample_idx,
            "steps": params.steps,
            "cache_key": params,
            "n": params.steps + 1,
            "y_lo": paths.min(),
            "y_hi": paths.max(),
            "title": title,
        }
        dpg.configure_item("anim_plot", label=title)
        self.apply_mode_visuals("All Paths")
        self._begin(params.steps + 1, self.redraw_paths)

    def redraw_paths(self, frame_int: int) -> None:
        data = self.data["All Paths"]
        if data is None:
            return
        xs = list(range(frame_int + 1))
        for tag, idx in zip(data["line_tags"], data["sample_idx"], strict=True):
            dpg.set_value(tag, [xs, data["paths"][idx, : frame_int + 1].tolist()])
        column = data["paths"][:, frame_int]
        dpg.set_value(
            "anim_stats_text", f"step {frame_int} of {data['steps']}: {position_stats(column)}"
        )

    # --- Mode dispatch: one dropdown, one Play button, one redraw callback --------------

    def redraw(self, frame_int: int) -> None:
        self._redrawers[self.current_mode()](frame_int)

    def play_or_start(self) -> None:
        """The Play side of Play/Pause. Single Walk has its own Add Walk button for starting
        something new, so Play there is always a plain resume. The other three modes have no
        separate Start button - Play (re)simulates if there's no data yet or the params
        changed since last time; otherwise it's a plain resume too."""
        mode = self.current_mode()
        if mode == "Single Walk":
            self.transport.play()
            return
        params, error = read_shared_params()
        data = self.data[mode]
        if params is None or data is None or data["cache_key"] != params:
            self._starters[mode]()
        else:
            self.transport.play()

    def apply_mode_visuals(self, mode: str) -> None:
        """Show/hide this mode's controls and series, and set the axis labels/ranges. Used by
        each mode's start (right after it (re)computes data) and by on_mode_changed() (which
        may have no data yet for the newly chosen mode)."""
        data = self.data[mode]

        dpg.configure_item("sw_controls", show=(mode == "Single Walk"))
        dpg.configure_item("ap_controls", show=(mode == "All Paths"))
        dpg.configure_item("anim_x_axis", label=X_LABELS[mode])

        is_bar_mode = mode in ("Distribution", "Evolving Histogram")
        dpg.configure_item("anim_hist_series", show=is_bar_mode and data is not None)
        dpg.configure_item("anim_curve_series", show=False)  # only redraw_distribution re-shows
        dpg.configure_item("anim_wall_series", show=False)  # only the two histogram redraws do

        for line_mode in ("Single Walk", "All Paths"):
            line_data = self.data[line_mode]
            for tag in line_data["line_tags"] if line_data else []:
                dpg.configure_item(tag, show=(mode == line_mode))

        if data is not None:
            if mode == "Distribution":
                dpg.set_axis_limits("anim_x_axis", 0, data["x_max"])
            elif mode == "Evolving Histogram":
                dpg.set_axis_limits("anim_x_axis", 0, HIST_X_MAX)
            else:
                dpg.set_axis_limits("anim_x_axis", 0, data["steps"])
            dpg.set_axis_limits("anim_y_axis", data["y_lo"], data["y_hi"])
        else:
            # Nothing simulated for this mode yet - a reasonable placeholder until Play/Add Walk.
            if mode == "Evolving Histogram":
                dpg.set_axis_limits("anim_x_axis", 0, HIST_X_MAX)
            elif mode in ("Single Walk", "All Paths"):
                dpg.set_axis_limits("anim_x_axis", 0, DEFAULT_STEPS)
            else:
                dpg.set_axis_limits_auto("anim_x_axis")
            dpg.set_axis_limits_auto("anim_y_axis")

    def on_mode_changed(self) -> None:
        """Switching modes always pauses and shows that mode's last known state: Single Walk's
        walks are restored exactly as left; the other three re-show their last completed run
        (if any) rather than replaying it, since replaying is one cheap Play click away."""
        mode = self.current_mode()
        data = self.data[mode]
        n = data["n"] if data else 0
        self.transport.restore(n, float(n - 1) if data else 0.0)
        self.apply_mode_visuals(mode)
        if data is not None:
            dpg.configure_item("anim_plot", label=data["title"])
            self.redraw(self.transport.pb.current_frame)
        else:
            dpg.configure_item("anim_plot", label="")
            dpg.set_value("anim_stats_text", "")
