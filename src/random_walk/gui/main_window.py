"""The main window, laid out after the sketches in docs/sketches (GUI_1, GUI_2, customControl):

    +--------------------------------------------+
    | Drawing: [....]                Random Walk |
    | +----------------------------------------+ |
    | |                                        | |
    | |    drawing area (grows): walks, axes   | |
    | |                                        | |
    | +----------------------------------------+ |
    |                  [1000 Steps, 10000 Trials]|
    |               SELECTOR_TOP_GAP             |
    |            (*)-----( )-----( )             |
    |            Walk   Trials   Both            |
    |              SELECTOR_BOTTOM_GAP           |
    |       |<< ---|--------------------- >>|    |
    |                  SLIDER_GAP                |
    |       |<< ---|--------------------- >>|    |
    |                 CONTROLS_GAP               |
    |                 <<   >/||   >>             |
    +--------------------------------------------+

The drawing area takes all spare space as the window resizes. Everything below it keeps its
size, stays centred, and keeps its spacing. At startup a data set is simulated and drawn
(see gui/walk_view.py), in whichever drawing the drawing selector picks. Play/Pause animates
it step by step (ANIMATION_DRAWING style, 30 steps/s) and the Steps slider shows and sets the
current step; the selector, Trials slider and fast reverse/forward aren't connected yet.

All text is in Source Code Pro (gui/ui_fonts.py). TEMPORARY: a drawing selector at the top
left switches what the drawing area shows (see DRAWINGS). Remove it once the choices are made.
"""

from __future__ import annotations

import time
from dataclasses import replace

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QEnterEvent, QFont, QFontMetrics, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from random_walk.config import DEFAULT_RUNS, DEFAULT_SLOPE, DEFAULT_STEPS
from random_walk.gui import symbols, ui_fonts
from random_walk.gui.position_selector import PositionSelector
from random_walk.gui.walk_view import DENSITY_DARKEST, Drawing, WalkView
from random_walk.playback import Playback
from random_walk.simulation import simulate_paths

TITLE = "Random Walk"
SUMMARY = "1000 Steps, 10000 Trials"  # plain text for now
SLIDER_WIDTH = 640  # px; fixed, independent of the window width
SLIDER_HEIGHT = 24  # px; room for the 23 px handle bar, which is clipped to the widget
# Vertical gaps below the drawing area, all exact (px). They share one value so the controls
# are evenly spaced; each can still be tuned on its own. The summary box stays tied to the
# drawing area by the window layout's 8 px spacing.
CONTROL_GAP = 12
# +6: the summary box and the circles have no internal padding (buttons and sliders do),
# so this gap needs a little more to look the same as the others.
SELECTOR_TOP_GAP = CONTROL_GAP + 6  # summary box -> position selector
SELECTOR_BOTTOM_GAP = CONTROL_GAP  # position selector -> top slider row
SLIDER_GAP = CONTROL_GAP  # between the two slider rows
CONTROLS_GAP = CONTROL_GAP  # second slider row -> player controls
SELECTOR_LABELS = ("Walk", "Trials", "Both")
# Light grey bars in front of the walks or density are drawn this opaque (0-1), so what's
# behind them shows through.
OVERLAY_BAR_OPACITY = 0.6
# Overlay 2's walks: all in Overlay 3's density grey, translucent so overlaps build up darker.
OVERLAY_WALK_OPACITY = 0.25
# TEMPORARY drawing selector: menu entry -> what the drawing area shows. The first is the
# default.
DRAWINGS = {
    "Draw 1": Drawing(walks=1),
    "Draw 5": Drawing(walks=5),
    "Full Histogram": Drawing(histogram=True, theory=True),
    "Overlay 1": Drawing(walks=1, histogram=True),
    "Overlay 2": Drawing(
        walks=200,
        histogram=True,
        histogram_from_walks=True,
        histogram_in_front=True,
        histogram_opacity=OVERLAY_BAR_OPACITY,
        walk_color=DENSITY_DARKEST,
        walk_opacity=OVERLAY_WALK_OPACITY,
    ),
    "Overlay 3": Drawing(
        density=True,
        histogram=True,
        histogram_in_front=True,
        histogram_opacity=OVERLAY_BAR_OPACITY,
        theory=True,
    ),
    # Overlay 3 early on: density up to step 50, histogram (and theory) of positions there.
    "Overlay 4": Drawing(
        density=True,
        histogram=True,
        histogram_in_front=True,
        histogram_opacity=OVERLAY_BAR_OPACITY,
        at_step=50,
        theory=True,
    ),
}
# Play/Pause button: True shows the combined symbol (one fixed glyph); False swaps between
# separate Play and Pause symbols. The tooltip follows the state either way.
COMBINED_PLAY_PAUSE = True
PLAYING_COLOR = "black"  # Play/Pause symbol colour while playing
PAUSED_COLOR = "#8c8c8c"  # ... and while paused (mid grey); it turns black on hover
TITLE_POINT_SIZE = 14
SUMMARY_POINT_SIZE = 8
SELECTOR_POINT_SIZE = 8  # position selector labels
SLIDER_LABEL_POINT_SIZE = 8  # "Steps" / "Trials" beside the sliders
SLIDER_LABEL_GAP = 6  # px between a slider label and its row's first button
# Slider rows, top to bottom: (label, maximum, starting value); each runs from 0.
SLIDER_ROWS = (("Steps", DEFAULT_STEPS, 0), ("Trials", DEFAULT_RUNS, DEFAULT_RUNS))
SLIDER_LABELS = tuple(label for label, _, _ in SLIDER_ROWS)
# Animation: Play steps every walk forward one step per frame (Playback's "real time", 30
# steps a second: 1000 steps in ~33 s), drawn like this DRAWINGS entry at the current step.
ANIMATION_DRAWING = "Overlay 4"
TICK_MS = 15  # timer interval while playing; Playback paces by the clock, not by ticks
AXIS_POINT_SIZE = 8  # drawing area's axis labels
INITIAL_SIZE = (1000, 760)

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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(TITLE)
        self.resize(*INITIAL_SIZE)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 12, 24, 24)
        layout.setSpacing(8)
        self.setCentralWidget(central)

        self.title = QLabel(TITLE)
        title_row = QHBoxLayout()
        title_row.addLayout(self._build_drawing_selector())  # TEMPORARY
        title_row.addStretch(1)
        title_row.addWidget(self.title)
        layout.addLayout(title_row)

        # The plot of the walks; stretch=1 gives it all the spare space on resize.
        self.drawing_area = WalkView()
        self.drawing_area.setMinimumSize(320, 200)
        layout.addWidget(self.drawing_area, stretch=1)

        self.summary = QLabel(SUMMARY)
        self.summary.setFrameShape(QFrame.Shape.Box)
        self.summary.setMargin(6)  # padding inside the frame
        self.position_selector = PositionSelector(SELECTOR_LABELS)
        self.slider_rows = tuple(SliderRow(*row) for row in SLIDER_ROWS)
        self.steps_slider = self.slider_rows[0].slider

        # Everything below the drawing area goes in its own zero-spacing layout, so the gap
        # constants are the exact gaps (the window layout would add its 8 px spacing on top).
        controls = QVBoxLayout()
        controls.setSpacing(0)
        controls.addWidget(self.summary, alignment=Qt.AlignmentFlag.AlignRight)
        controls.addSpacing(SELECTOR_TOP_GAP)
        controls.addWidget(self.position_selector, alignment=Qt.AlignmentFlag.AlignHCenter)
        controls.addSpacing(SELECTOR_BOTTOM_GAP)
        controls.addLayout(self.slider_rows[0].layout)
        controls.addSpacing(SLIDER_GAP)
        controls.addLayout(self.slider_rows[1].layout)
        controls.addSpacing(CONTROLS_GAP)
        controls.addLayout(self._build_player_controls())
        layout.addLayout(controls)

        self.apply_fonts()
        self.set_drawing(next(iter(DRAWINGS)))
        self.generate_data()
        self._setup_animation()

    # --- animation ------------------------------------------------------------------------

    def _setup_animation(self) -> None:
        """Playback over steps 0..DEFAULT_STEPS, driven by a timer while playing; the Steps
        slider shows the current step and moving it jumps there."""
        self.playback = Playback()
        self.playback.start(DEFAULT_STEPS + 1, time.monotonic(), autoplay=False)
        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._on_tick)
        self.steps_slider.valueChanged.connect(self._on_steps_slider)

    def show_step(self, step: int) -> None:
        """Show the data set at `step` in the animation's drawing and move the Steps slider
        there. The position and step axes stay still; the probability axis follows the theory
        peak continuously (plus headroom), so the histogram keeps a steady height near the top
        as the distribution spreads out, and the tick labels slide rather than anything jump."""
        drawing = replace(DRAWINGS[ANIMATION_DRAWING], at_step=step, probability_from_theory=True)
        self.drawing_area.set_drawing(drawing)
        # Display updates, not user choices: don't let them fire their change handlers.
        self.drawing_selector.blockSignals(True)
        self.drawing_selector.setCurrentText(ANIMATION_DRAWING)
        self.drawing_selector.blockSignals(False)
        self.steps_slider.blockSignals(True)
        self.steps_slider.setValue(step)
        self.steps_slider.blockSignals(False)

    def play(self) -> None:
        """Animate from the Steps slider's position (from the start again if it's at the end)."""
        self.playback.jump_to(self.steps_slider.value())
        self.playback.play(time.monotonic())  # also rewinds to the start if at the end
        # Draw the first frame before the clock starts: the first one counts the density grid
        # (~0.1 s), which would otherwise make Playback skip ahead to catch up.
        self.show_step(self.playback.current_frame)
        self.playback.last_time = time.monotonic()
        self.timer.start()
        self.playing = True
        self._show_play_state()

    def pause(self) -> None:
        self.playback.pause()
        self.timer.stop()
        self.playing = False
        self._show_play_state()

    def _on_tick(self) -> None:
        frame = self.playback.tick(time.monotonic())
        if frame is not None:
            self.show_step(frame)
        if not self.playback.playing:  # reached the last step
            self.pause()

    def _on_steps_slider(self, value: int) -> None:
        """The user moved the Steps slider (or pressed its jump buttons): show that step."""
        if self.playing:
            self.pause()
        self.playback.jump_to(value)
        self.show_step(value)

    def generate_data(self) -> None:
        """Simulate the data set (the default runs and steps, no wall) and show it. The
        default generator is seeded, so this gives the same data every time the app starts."""
        self.paths = simulate_paths(DEFAULT_RUNS, DEFAULT_STEPS, wall=None, theta=DEFAULT_SLOPE)
        self.drawing_area.set_paths(self.paths, theta=DEFAULT_SLOPE)

    def apply_fonts(self) -> None:
        """Set the interface font (Source Code Pro): the default for every widget, plus each
        text element's own size. The symbol buttons keep their symbol font."""
        QApplication.setFont(ui_fonts.ui_font())  # every widget without its own font
        self.title.setFont(ui_fonts.ui_font(TITLE_POINT_SIZE))
        self.summary.setFont(ui_fonts.ui_font(SUMMARY_POINT_SIZE))
        self.position_selector.setFont(ui_fonts.ui_font(SELECTOR_POINT_SIZE))
        label_font = ui_fonts.ui_font(SLIDER_LABEL_POINT_SIZE)
        widest = max(QFontMetrics(label_font).horizontalAdvance(t) for t in SLIDER_LABELS)
        for row in self.slider_rows:
            row.set_label_font(label_font, widest)
        self.drawing_area.setFont(ui_fonts.ui_font(AXIS_POINT_SIZE))

    def _build_drawing_selector(self) -> QHBoxLayout:
        """TEMPORARY: a dropdown to switch between drawings of the data set (see DRAWINGS)."""
        self.drawing_selector = QComboBox()
        self.drawing_selector.addItems(list(DRAWINGS))
        self.drawing_selector.setToolTip("Temporary: switch between drawings of the data set")
        self.drawing_selector.currentTextChanged.connect(self.set_drawing)
        row = QHBoxLayout()
        row.addWidget(QLabel("Drawing:"))
        row.addWidget(self.drawing_selector)
        return row

    def set_drawing(self, name: str) -> None:
        """Show drawing `name`, a DRAWINGS entry (pausing any animation)."""
        if getattr(self, "playing", False):
            self.pause()
        self.drawing_area.set_drawing(DRAWINGS[name])
        self.drawing_selector.blockSignals(True)
        self.drawing_selector.setCurrentText(name)
        self.drawing_selector.blockSignals(False)

    def _build_player_controls(self) -> QHBoxLayout:
        """Fast reverse, Play/Pause and fast forward, centred. Visual only for now: Play/Pause
        toggles its symbol, nothing else happens."""
        self.fast_reverse = symbol_button(symbols.FAST_REVERSE, "Fast reverse")
        self.playing = False
        self.play_pause = HoverColorButton()
        style_symbol_button(self.play_pause, self._play_symbol(), "Play")
        # Fixed to the wider of its two symbols, so toggling doesn't shift its neighbours.
        self.play_pause.setFixedWidth(
            _widest(self.play_pause, (symbols.PLAY, symbols.PAUSE, symbols.PLAY_PAUSE))
        )
        self._show_play_state()
        self.play_pause.clicked.connect(self._toggle_play)
        self.fast_forward = symbol_button(symbols.FAST_FORWARD, "Fast forward")

        row = QHBoxLayout()
        row.addStretch(1)
        for button in (self.fast_reverse, self.play_pause, self.fast_forward):
            row.addWidget(button)
        row.addStretch(1)
        return row

    def _toggle_play(self) -> None:
        """Play or pause the animation. (Not a checkable button: the native style would draw
        it highlighted while checked.)"""
        if self.playing:
            self.pause()
        else:
            self.play()

    def _show_play_state(self) -> None:
        """Symbol, colour (black playing; grey paused, black on hover) and tooltip."""
        self.play_pause.setText(self._play_symbol())
        self.play_pause.setToolTip("Pause" if self.playing else "Play")
        normal = PLAYING_COLOR if self.playing else PAUSED_COLOR
        self.play_pause.set_colors(normal, hover=PLAYING_COLOR)

    def _play_symbol(self) -> str:
        if COMBINED_PLAY_PAUSE:
            return symbols.PLAY_PAUSE
        return symbols.PAUSE if self.playing else symbols.PLAY


class SliderRow:
    """A fixed-size slider between jump-to-start and jump-to-end buttons, centred in its row,
    with a text label to the left.

    `layout` is the row to add to a parent layout. The buttons move the slider to its ends. An
    invisible spacer on the right mirrors the label, so the label doesn't shift the centred
    slider; give every row the same label width (set_label_font) to keep the rows aligned.
    """

    def __init__(self, label: str, maximum: int, value: int) -> None:
        self.label = QLabel(label)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._mirror = QWidget()  # same width as the label, on the right
        self.to_start = symbol_button(symbols.SKIP_TO_START, "Jump to start")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, maximum)
        self.slider.setValue(value)
        self.slider.setFixedSize(SLIDER_WIDTH, SLIDER_HEIGHT)
        self.slider.setStyleSheet(SLIDER_STYLE)

        self.to_end = symbol_button(symbols.SKIP_TO_END, "Jump to end")

        self.to_start.clicked.connect(lambda: self.slider.setValue(self.slider.minimum()))
        self.to_end.clicked.connect(lambda: self.slider.setValue(self.slider.maximum()))

        # Stretch on both sides keeps the fixed-width row centred as the window resizes; the
        # label and its mirror are equal, so they don't move the slider off centre.
        self.layout = QHBoxLayout()
        self.layout.addStretch(1)
        self.layout.addWidget(self.label)
        self.layout.addSpacing(SLIDER_LABEL_GAP)
        self.layout.addWidget(self.to_start)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.to_end)
        self.layout.addSpacing(SLIDER_LABEL_GAP)
        self.layout.addWidget(self._mirror)
        self.layout.addStretch(1)

    def set_label_font(self, font: QFont, width: int) -> None:
        """Set the label's font and fix the label (and its mirror) to `width` px."""
        self.label.setFont(font)
        self.label.setFixedWidth(width)
        self._mirror.setFixedWidth(width)


def _widest(button: QToolButton, texts: tuple[str, ...]) -> int:
    """The width `button` needs for the widest of `texts`; leaves its own text unchanged."""
    original = button.text()
    widths = []
    for text in texts:
        button.setText(text)
        widths.append(button.sizeHint().width())
    button.setText(original)
    return max(widths)


class HoverColorButton(QToolButton):
    """A tool button whose text colour changes while the mouse is over it.

    Native-styled buttons have no hover text colour of their own (a style sheet could add
    one, but would replace the whole native look), so this swaps the palette on enter/leave.
    """

    def __init__(self) -> None:
        super().__init__()
        self._normal = QColor("black")
        self._hover = QColor("black")

    def set_colors(self, normal: str, hover: str) -> None:
        self._normal, self._hover = QColor(normal), QColor(hover)
        self._apply(self.underMouse())

    def enterEvent(self, event: QEnterEvent) -> None:
        self._apply(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._apply(False)
        super().leaveEvent(event)

    def _apply(self, hovered: bool) -> None:
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.ButtonText, self._hover if hovered else self._normal)
        self.setPalette(palette)


def symbol_button(symbol: str, tooltip: str) -> QToolButton:
    """A flat button showing a media symbol in the bundled symbol font."""
    button = QToolButton()
    style_symbol_button(button, symbol, tooltip)
    return button


def style_symbol_button(button: QToolButton, symbol: str, tooltip: str) -> None:
    """Make `button` (a QToolButton or subclass) a flat media-symbol button."""
    button.setText(symbol)
    button.setFont(symbols.symbol_font())
    button.setToolTip(tooltip)
    button.setAutoRaise(True)
