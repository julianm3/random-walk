"""Window assembly and the application entry point."""

from __future__ import annotations

from typing import Any

import dearpygui.dearpygui as dpg

from random_walk.gui.animation_tab import AnimationTab
from random_walk.gui.controls import build_shared_controls
from random_walk.gui.static_tab import build_static_tab, run_on_enter, run_static
from random_walk.gui.transport import build_preset_theme


def _bind_tick_handler(animation: AnimationTab) -> None:
    """Advance playback once per rendered frame.

    Bound to the always-visible primary window rather than to the plot itself: item
    visibility handlers only fire while their item is visible, and Transport.advance()
    checks the plot's visibility on its own.
    """

    def tick(sender: Any, app_data: Any, user_data: Any) -> None:
        animation.transport.advance()

    with dpg.item_handler_registry(tag="tick_handler_registry"):
        dpg.add_item_visible_handler(callback=tick)
    dpg.bind_item_handler_registry("primary", "tick_handler_registry")


def build_ui() -> AnimationTab:
    """Create the context, viewport and every widget, and draw the Static tab's defaults.

    Stops short of the render loop, so a caller (such as a headless test) can render frames
    itself with dpg.render_dearpygui_frame() and destroy the context when done.
    """
    dpg.create_context()
    preset_theme = build_preset_theme()
    dpg.create_viewport(title="Random Walk (Dear PyGui)", width=1050, height=800)

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=run_on_enter)

    animation = AnimationTab(preset_theme)

    with dpg.window(tag="primary"):
        build_shared_controls()  # shared by every tab
        dpg.add_separator()
        with dpg.tab_bar():
            with dpg.tab(label="Static"):
                build_static_tab()
            with dpg.tab(label="Animation"):
                animation.build()

    _bind_tick_handler(animation)

    # Show these defaults up front, before Play/Add Walk has ever been pressed.
    animation.transport.highlight_preset("fast")
    animation.on_mode_changed()

    dpg.set_primary_window("primary", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    run_static()
    return animation


def main() -> None:
    build_ui()
    dpg.start_dearpygui()
    dpg.destroy_context()
