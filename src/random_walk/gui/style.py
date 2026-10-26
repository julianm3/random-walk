"""The interface's shared look: the slider style, used by the main window and the dialogs."""

from __future__ import annotations

SLIDER_HEIGHT = 24  # px; room for the 23 px handle bar, which is clipped to the widget

# Slider track: the part left of the handle (already played) and the part right of it.
SLIDER_DONE_COLOR = "black"
SLIDER_TODO_COLOR = "#d3d3d3"  # light grey
SLIDER_HANDLE_COLOR = "black"
SLIDER_TRACK_WIDTH = 1  # px; thickness of the track line
SLIDER_HANDLE_WIDTH = 4  # px
SLIDER_HANDLE_OVERHANG = 11  # px the handle bar extends above and below the track
# A style sheet replaces the native slider drawing entirely, so the handle is styled here too:
# a thin vertical bar, like a playhead. Qt sizes it as the track plus its (negative) vertical
# margins: 1 + 2 x 11 = 23 px tall, centred on the line.
SLIDER_STYLE = f"""
QSlider::groove:horizontal {{ height: {SLIDER_TRACK_WIDTH}px; background: {SLIDER_TODO_COLOR}; }}
QSlider::sub-page:horizontal {{ background: {SLIDER_DONE_COLOR}; }}
QSlider::add-page:horizontal {{ background: {SLIDER_TODO_COLOR}; }}
QSlider::handle:horizontal {{
    width: {SLIDER_HANDLE_WIDTH}px; margin: -{SLIDER_HANDLE_OVERHANG}px 0; border-radius: 1px;
    background: {SLIDER_HANDLE_COLOR}; border: none;
}}
"""
