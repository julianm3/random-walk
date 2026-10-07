"""The play/pause/step/speed/scrubber row, wiring a Playback to its Dear PyGui widgets."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import dearpygui.dearpygui as dpg

from random_walk.config import FPS, MIN_SPEED
from random_walk.playback import PRESETS, Playback


def build_preset_theme() -> int | str:
    """A distinct button theme used to highlight whichever of Real/Slow/Fast is active."""
    with dpg.theme() as theme, dpg.theme_component(dpg.mvButton):
        dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 120, 200), category=dpg.mvThemeCat_Core)
        dpg.add_theme_color(
            dpg.mvThemeCol_ButtonHovered, (60, 140, 220), category=dpg.mvThemeCat_Core
        )
        dpg.add_theme_color(
            dpg.mvThemeCol_ButtonActive, (30, 100, 180), category=dpg.mvThemeCat_Core
        )
    return theme


class Transport:
    """One timeline's transport controls.

    `prefix` namespaces the widget tags ("<prefix>_scrub", ...). `plot` is the plot whose
    visibility gates playback. `redraw(frame)` draws one frame. `play`, if given, overrides
    what the Play side of the Play/Pause button does (the Animation tab uses this to make
    Play also act as Start).
    """

    def __init__(
        self,
        prefix: str,
        plot: str,
        redraw: Callable[[int], None],
        preset_theme: int | str,
        play: Callable[[], None] | None = None,
    ) -> None:
        self.pb = Playback()
        self.prefix = prefix
        self.plot = plot
        self.redraw = redraw
        self.preset_theme = preset_theme
        self._play_fn = play or self.play

    def tag(self, name: str) -> str:
        return f"{self.prefix}_{name}"

    def build(self) -> None:
        with dpg.group(horizontal=True):
            dpg.add_button(label="Restart", callback=self.restart)
            dpg.add_button(label="Step Back", callback=self.step_back)
            dpg.add_button(label="Reverse", callback=self.reverse)
            dpg.add_button(label="Play", tag=self.tag("play_pause"), callback=self.play_pause)
            dpg.add_button(label="Fast Fwd", callback=self.fast_forward)
            dpg.add_button(label="Step Fwd", callback=self.step_forward)
            dpg.add_button(label="Jump to Finish", callback=self.finish)
            dpg.add_text("  speed")
            dpg.add_slider_float(
                tag=self.tag("speed"),
                default_value=FPS,
                min_value=MIN_SPEED,
                max_value=FPS * 4,
                width=140,
                format="%.1f/s",
                callback=self._on_speed_changed,
            )
            for name in PRESETS:
                dpg.add_button(
                    label=name.capitalize(),
                    tag=self.tag(f"preset_{name}"),
                    callback=self._on_preset,
                    user_data=name,
                )
        dpg.add_slider_float(
            tag=self.tag("scrub"),
            default_value=0.0,
            min_value=0,
            max_value=1,
            width=-1,
            clamped=True,
            callback=self._on_scrub,
        )

    # --- per-frame update ---------------------------------------------------------------

    def advance(self) -> None:
        """Called every rendered frame (bound to the always-visible primary window - see
        gui/app.py) to move playback along and redraw when the integer frame changes.

        Checks its own plot's visibility rather than relying on a handler bound to that plot:
        a handler bound directly to a plot was once observed to never fire on the first walk
        added to it (empty axis with no series yet when the handler was registered).
        """
        if self.pb.n == 0:
            return
        if not dpg.is_item_visible(self.plot):
            return  # this tab isn't the one currently open - stay paused, save CPU too
        was_playing = self.pb.playing
        frame_int = self.pb.tick(dpg.get_total_time())
        if was_playing:
            self.sync_play_pause_label()  # playing can have just auto-stopped at either end
        if frame_int is not None:
            self.redraw(frame_int)
        if dpg.does_item_exist(self.tag("scrub")):
            dpg.set_value(self.tag("scrub"), self.pb.frame)

    # --- (re)loading a timeline ---------------------------------------------------------

    def start(self, n: int, autoplay: bool = True) -> None:
        """A new timeline of `n` frames: reset the frame/scrub range and, unless told
        otherwise, begin playing immediately at whatever speed is currently set."""
        self.pb.start(n, dpg.get_total_time(), autoplay)
        self.sync_play_pause_label()
        dpg.configure_item(self.tag("scrub"), max_value=max(n - 1, 1))
        dpg.configure_item(self.tag("speed"), max_value=self.pb.speed_slider_max())
        if not self.pb.speed_touched:
            # Default to Fast until the user explicitly picks a speed; once they have, respect
            # that choice across subsequent starts rather than resetting it.
            self.apply_preset("fast", touched=False)
        else:
            # n may have changed, which changes what Slow/Fast even mean - refresh the
            # highlight in case it now does (or no longer does) line up.
            self.highlight_preset(self.pb.matching_preset())

    def restore(self, n: int, frame: float) -> None:
        """Show an existing timeline paused at `frame` (the caller redraws it)."""
        self.pb.restore(n, frame)
        dpg.configure_item(self.tag("scrub"), max_value=max(n - 1, 1))
        dpg.set_value(self.tag("scrub"), frame)
        self.sync_play_pause_label()

    def reset(self) -> None:
        self.pb.reset()
        self.sync_play_pause_label()

    # --- buttons ------------------------------------------------------------------------

    def play(self) -> None:
        self.pb.play(dpg.get_total_time())
        self.sync_play_pause_label()

    def reverse(self) -> None:
        self.pb.reverse(dpg.get_total_time())
        self.sync_play_pause_label()

    def pause(self) -> None:
        self.pb.pause()
        self.sync_play_pause_label()

    def play_pause(self) -> None:
        if self.pb.playing:
            self.pause()
        else:
            self._play_fn()
        self.sync_play_pause_label()

    def fast_forward(self) -> None:
        self.pb.fast(1, dpg.get_total_time())
        self.sync_play_pause_label()

    def restart(self) -> None:
        self._show_jump(self.pb.restart())

    def finish(self) -> None:
        self._show_jump(self.pb.finish())

    def step_forward(self) -> None:
        self._show_jump(self.pb.step(1))

    def step_back(self) -> None:
        self._show_jump(self.pb.step(-1))

    def _show_jump(self, frame_int: int | None) -> None:
        """After a Playback jump (which always pauses): update the label, redraw, move the
        scrubber."""
        self.sync_play_pause_label()
        if frame_int is None:
            return  # nothing has been started yet - nothing to draw
        self.redraw(frame_int)
        dpg.set_value(self.tag("scrub"), self.pb.frame)

    def _on_scrub(self, sender: Any, app_data: float, user_data: Any) -> None:
        self._show_jump(self.pb.jump_to(int(round(app_data))))

    # --- speed --------------------------------------------------------------------------

    def _on_speed_changed(self, sender: Any, app_data: float, user_data: Any) -> None:
        self.pb.set_speed(app_data)
        self.highlight_preset(self.pb.matching_preset())

    def _on_preset(self, sender: Any, app_data: Any, user_data: str) -> None:
        self.apply_preset(user_data)

    def apply_preset(self, name: str, touched: bool = True) -> None:
        speed = self.pb.apply_preset(name, touched)
        if dpg.does_item_exist(self.tag("speed")):
            dpg.set_value(self.tag("speed"), speed)
        self.highlight_preset(name)

    def highlight_preset(self, which: str | None) -> None:
        """Give whichever preset button matches `which` the highlighted theme, and clear it
        from the others."""
        for name in PRESETS:
            tag = self.tag(f"preset_{name}")
            if dpg.does_item_exist(tag):
                dpg.bind_item_theme(tag, self.preset_theme if name == which else 0)

    def sync_play_pause_label(self) -> None:
        """Keep the Play/Pause button's text matching actual playback state - needed because
        `playing` can flip to False on its own (reaching either end of the timeline)."""
        tag = self.tag("play_pause")
        if dpg.does_item_exist(tag):
            dpg.set_item_label(tag, "Pause" if self.pb.playing else "Play")
