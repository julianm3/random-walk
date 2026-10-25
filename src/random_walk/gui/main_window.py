"""The main window, laid out after the sketches in docs/sketches (GUI_1, GUI_2, customControl):

    +--------------------------------------------+
    |                                Random Walk |
    | +----------------------------------------+ |
    | |                                        | |
    | |   drawing area (grows): density, bars  | |
    | |                                        | |
    | +----------------------------------------+ |
    |               SELECTOR_TOP_GAP             |
    |              (*)-----------( )             |
    |             Steps         Trials           |
    |              SELECTOR_BOTTOM_GAP           |
    |  Steps |<< ---|--------------------- >>|   |
    |                  SLIDER_GAP                |
    | Trials |<< ---|--------------------- >>|   |
    |                 CONTROLS_GAP               |
    |                 <<   >/||   >>             |
    +--------------------------------------------+

The drawing area takes all spare space as the window resizes. Everything below it keeps its
size, stays centred, and keeps its spacing. At startup a data set is simulated (see
gui/walk_view.py), and the selector picks one of two animation modes on it:

- Steps: the first N trials (the Trials slider) advance from step 0 to the last step, 30
  steps a second, drawn as a density image with the histogram of their positions in front.
  The Steps slider is the playhead: it follows the animation and scrubs.
- Trials: the histogram of the trials' positions at one step (the Steps slider; the last step
  to start with) grows from 0 trials to every trial, slowly at first (see pacing.py). The
  Trials slider is the playhead: it follows the animation and scrubs.

Each mode keeps its own slider settings and playback position when switching away and back.
Right-click either slider to type an exact value.
The buttons either side of Play/Pause step back and forward: one step in Steps mode, one
trial in Trials mode, repeating while held. Keys, whatever has focus: Space plays/pauses,
Left/Right step (repeating while held), Home/End jump to the start/end. All text is in Source
Code Pro (gui/ui_fonts.py).
"""

from __future__ import annotations

import sys
import time
from dataclasses import replace

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QColor, QEnterEvent, QFont, QFontMetrics, QKeyEvent, QPalette
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSlider,
    QSpinBox,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from random_walk.config import (
    DEFAULT_P_RIGHT,
    DEFAULT_RUNS,
    DEFAULT_STEPS,
    FPS,
    TRIALS_PLAY_SECONDS,
)
from random_walk.gui import symbols, ui_fonts
from random_walk.gui.position_selector import PositionSelector
from random_walk.gui.walk_view import Drawing, WalkView
from random_walk.pacing import TrialRamp
from random_walk.playback import Playback
from random_walk.simulation import simulate_paths

TITLE = "Random Walk"
SLIDER_WIDTH = 640  # px; fixed, independent of the window width
SLIDER_HEIGHT = 24  # px; room for the 23 px handle bar, which is clipped to the widget
WINDOW_SPACING = 8  # px; the window layout's spacing between the title, drawing and controls
# Vertical gaps below the drawing area, all exact (px). They share one value so the controls
# are evenly spaced; each can still be tuned on its own.
CONTROL_GAP = 12
# +6: the drawing area's frame and the circles have no internal padding (buttons and sliders
# do), so this gap needs a little more to look the same as the others. It includes the window
# layout's spacing.
SELECTOR_TOP_GAP = CONTROL_GAP + 6  # drawing area -> position selector
SELECTOR_BOTTOM_GAP = CONTROL_GAP  # position selector -> top slider row
SLIDER_GAP = CONTROL_GAP  # between the two slider rows
CONTROLS_GAP = CONTROL_GAP  # second slider row -> player controls
# The animation modes, in selector order.
STEPS_MODE, TRIALS_MODE = 0, 1
SELECTOR_LABELS = ("Steps", "Trials")
# Light grey bars in front of the density are drawn this opaque (0-1), so it shows through.
OVERLAY_BAR_OPACITY = 0.6
# Steps mode, at each step: the density of the counted walks up to it, with the histogram of
# their positions there in front and the theory curve. The probability axis follows the
# theory peak, so the bell keeps a steady height as it spreads (see Drawing).
STEPS_DRAWING = Drawing(
    density=True,
    histogram=True,
    histogram_in_front=True,
    histogram_opacity=OVERLAY_BAR_OPACITY,
    theory=True,
    probability_from_theory=True,
)
# Trials mode: the histogram of the first trials' final positions and the theory curve, on a
# probability axis fixed to the full histogram, so the bars grow into a still frame.
TRIALS_DRAWING = Drawing(histogram=True, theory=True, probability_from_full=True)
# Trials mode plays this many frames (30 s at 30 fps), adding trials slowly at first.
TRIAL_FRAMES = TRIALS_PLAY_SECONDS * FPS
# Play/Pause button: True shows the combined symbol (one fixed glyph); False swaps between
# separate Play and Pause symbols. The tooltip follows the state either way.
COMBINED_PLAY_PAUSE = True
PLAYING_COLOR = "black"  # Play/Pause symbol colour while playing
PAUSED_COLOR = "#8c8c8c"  # ... and while paused (mid grey); it turns black on hover
TITLE_POINT_SIZE = 14
SELECTOR_POINT_SIZE = 8  # position selector labels
SLIDER_LABEL_POINT_SIZE = 8  # "Steps" / "Trials" beside the sliders
SLIDER_LABEL_GAP = 6  # px between a slider label and its row's first button
# Slider rows, top to bottom: (label, minimum, maximum, starting value). Steps mode starts
# at the last step (the whole run) with every trial taking part.
SLIDER_ROWS = (
    ("Steps", 0, DEFAULT_STEPS, DEFAULT_STEPS),
    ("Trials", 0, DEFAULT_RUNS, DEFAULT_RUNS),
)
SLIDER_LABELS = tuple(row[0] for row in SLIDER_ROWS)
TICK_MS = 15  # timer interval while playing; Playback paces by the clock, not by ticks
# Keyboard control, wherever the focus is (see MainWindow.eventFilter): key -> action.
KEY_ACTIONS: dict[int, str] = {  # (QKeyEvent.key() is an int; Qt.Key is an IntEnum)
    Qt.Key.Key_Space: "play",
    Qt.Key.Key_Left: "back",
    Qt.Key.Key_Right: "forward",
    Qt.Key.Key_Home: "start",
    Qt.Key.Key_End: "end",
}
# Those keys with any of these held are left alone (e.g. for future shortcuts).
IGNORED_WITH_MODIFIERS = (
    Qt.KeyboardModifier.ControlModifier
    | Qt.KeyboardModifier.AltModifier
    | Qt.KeyboardModifier.MetaModifier
)
EDITOR_PADDING = 16  # px added to the widest number's width in a slider's number box
EDITOR_GAP = 2  # px between the number box and the top of the slider
SPI_GETKEYBOARDDELAY = 0x0016  # Windows SystemParametersInfo: the key repeat delay setting
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
        layout.setSpacing(WINDOW_SPACING)
        self.setCentralWidget(central)

        self.title = QLabel(TITLE)
        title_row = QHBoxLayout()
        title_row.addStretch(1)
        title_row.addWidget(self.title)
        layout.addLayout(title_row)

        # The plot of the walks; stretch=1 gives it all the spare space on resize.
        self.drawing_area = WalkView()
        self.drawing_area.setMinimumSize(320, 200)
        layout.addWidget(self.drawing_area, stretch=1)

        self.position_selector = PositionSelector(SELECTOR_LABELS)
        self.slider_rows = tuple(SliderRow(*row) for row in SLIDER_ROWS)
        self.steps_slider = self.slider_rows[0].slider
        self.trials_slider = self.slider_rows[1].slider

        # Everything below the drawing area goes in its own zero-spacing layout, so the gap
        # constants are the exact gaps (the window layout would add its spacing on top).
        controls = QVBoxLayout()
        controls.setSpacing(0)
        controls.addSpacing(SELECTOR_TOP_GAP - WINDOW_SPACING)  # the window adds the rest
        controls.addWidget(self.position_selector, alignment=Qt.AlignmentFlag.AlignHCenter)
        controls.addSpacing(SELECTOR_BOTTOM_GAP)
        controls.addLayout(self.slider_rows[0].layout)
        controls.addSpacing(SLIDER_GAP)
        controls.addLayout(self.slider_rows[1].layout)
        controls.addSpacing(CONTROLS_GAP)
        controls.addLayout(self._build_player_controls())
        layout.addLayout(controls)

        self.apply_fonts()
        self.generate_data()
        self._setup_animation()
        # The keys work wherever the focus is: an application-wide filter sees each key event
        # before any widget, so a focused button can't take Space nor a slider the arrows.
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    # --- keyboard -------------------------------------------------------------------------

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Handle KEY_ACTIONS keys (press and release) while this window is active, unless a
        text or number box has the focus (it needs the keys for editing)."""
        if (
            event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease)
            and isinstance(event, QKeyEvent)
            and event.key() in KEY_ACTIONS
            and not event.modifiers() & IGNORED_WITH_MODIFIERS
            and QApplication.activeWindow() is self
            and not isinstance(QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox))
        ):
            # Releases are swallowed too: a focused button clicks on the Space release.
            if event.type() == QEvent.Type.KeyPress:
                self._on_key(event.key(), event.isAutoRepeat())
            return True
        return super().eventFilter(watched, event)

    def _on_key(self, key: int, repeat: bool) -> None:
        """Held keys repeat at the system's rate; only the step keys act on the repeats."""
        action = KEY_ACTIONS[key]
        if action == "play":
            if not repeat:  # holding Space shouldn't flicker between play and pause
                self._toggle_play()
        elif action == "start":
            self.jump(to_end=False)
        elif action == "end":
            self.jump(to_end=True)
        else:
            self.step_by(-1 if action == "back" else 1)

    @property
    def playhead_slider(self) -> QSlider:
        """The current mode's playhead: the Steps slider, or the Trials slider in Trials mode."""
        return self.steps_slider if self.mode == STEPS_MODE else self.trials_slider

    def step_by(self, delta: int) -> None:
        """Pause and move `delta` steps (Steps mode) or trials (Trials mode), stopping at the
        ends. Moving the slider shows the new frame and makes Play continue from it."""
        if self.playing:
            self.pause()
        slider = self.playhead_slider
        slider.setValue(slider.value() + delta)  # clamped to the slider's range

    def jump(self, to_end: bool) -> None:
        """Pause and jump to the start or end of the current mode, like the slider's jump
        buttons."""
        if self.playing:
            self.pause()
        slider = self.playhead_slider
        slider.setValue(slider.maximum() if to_end else slider.minimum())

    # --- animation ------------------------------------------------------------------------

    def _setup_animation(self) -> None:
        """One Playback per mode, driven by a timer while playing. Steps mode's timeline is
        steps 0..DEFAULT_STEPS; Trials mode's is TRIAL_FRAMES frames, which `ramp` turns into
        trial counts. Starts in Steps mode at the last step, showing the whole run."""
        self.mode = STEPS_MODE
        self.steps_trials = DEFAULT_RUNS  # Steps mode: the Trials slider (trials taking part)
        self.trials_shown = 0  # Trials mode: trials in the histogram (the Trials slider)
        self.trials_step = DEFAULT_STEPS  # ... and the step it counts (the Steps slider)
        now = time.monotonic()
        self.step_playback = Playback()
        self.step_playback.start(DEFAULT_STEPS + 1, now, autoplay=False)
        self.step_playback.jump_to(DEFAULT_STEPS)
        self.ramp = TrialRamp(TRIAL_FRAMES, DEFAULT_RUNS)
        self.trial_playback = Playback()
        self.trial_playback.start(TRIAL_FRAMES + 1, now, autoplay=False)

        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._on_tick)
        self.steps_slider.valueChanged.connect(self._on_steps_slider)
        self.trials_slider.valueChanged.connect(self._on_trials_slider)
        # Recounting the density for a new number of trials takes up to ~0.1 s: while the
        # Trials slider is dragged, keep the last count and recount on release.
        self.trials_slider.sliderPressed.connect(self._hold_density)
        self.trials_slider.sliderReleased.connect(self._release_density)
        self.position_selector.currentIndexChanged.connect(self.set_mode)
        for row in self.slider_rows:  # right-click: type an exact value
            row.slider.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.slider.customContextMenuRequested.connect(
                lambda _pos, r=row: self._edit_slider_value(r)
            )
        self.show_step(DEFAULT_STEPS)

    def _edit_slider_value(self, row: SliderRow) -> None:
        """Pause and open the row's number box: Enter moves the slider there, as if dragged."""
        if self.playing:
            self.pause()
        row.edit_value()

    @property
    def playback(self) -> Playback:
        """The current mode's playback."""
        return self.step_playback if self.mode == STEPS_MODE else self.trial_playback

    def set_mode(self, mode: int) -> None:
        """Switch to Steps or Trials mode (pausing), restoring that mode's sliders and frame
        (Steps mode's playhead and trials, Trials mode's step and trial count)."""
        if mode == self.mode:
            return
        if self.playing:
            self.pause()
        self.mode = mode
        # When called from code, move the selector too (its signal then finds the mode set).
        self.position_selector.setCurrentIndex(mode)
        if mode == STEPS_MODE:
            set_quietly(self.trials_slider, self.steps_trials)
        else:
            set_quietly(self.steps_slider, self.trials_step)
        self._show_current_frame()  # also puts the mode's playhead back

    def show_step(self, step: int) -> None:
        """Steps mode: show the counted trials at `step` and move the Steps slider (the
        playhead) there. The position and step axes stay still; the probability axis follows
        the theory peak continuously (plus headroom, or up to the tallest bar), so the
        histogram keeps a steady height near the top as the distribution spreads out, and the
        tick labels slide rather than anything jump."""
        drawing = replace(STEPS_DRAWING, at_step=step, trials=self.steps_trials)
        self.drawing_area.set_drawing(drawing)
        set_quietly(self.steps_slider, step)

    def show_trials(self, count: int) -> None:
        """Trials mode: show the histogram of the first `count` trials' positions at the
        chosen step, and move the Trials slider (the playhead) there."""
        self.trials_shown = count
        drawing = replace(TRIALS_DRAWING, trials=count, at_step=self.trials_step)
        self.drawing_area.set_drawing(drawing)
        set_quietly(self.trials_slider, count)

    def _show_current_frame(self) -> None:
        if self.mode == STEPS_MODE:
            self.show_step(self.step_playback.current_frame)
        else:
            self.show_trials(self.ramp.count_at(self.trial_playback.frame))

    def play(self) -> None:
        """Animate the current mode from where it is (from the start again if at the end)."""
        self.playback.play(time.monotonic())  # also rewinds to the start if at the end
        # Draw the first frame before the clock starts: in Steps mode it may count the density
        # grid (~0.1 s), which would otherwise make Playback skip ahead to catch up.
        self._show_current_frame()
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
        playback = self.playback
        frame = playback.tick(time.monotonic())
        if self.mode == STEPS_MODE:
            if frame is not None:
                self.show_step(frame)
        else:
            count = self.ramp.count_at(playback.frame)  # several frames can share a count
            if count != self.trials_shown:
                self.show_trials(count)
        if not playback.playing:  # reached the end
            self.pause()

    def _on_steps_slider(self, value: int) -> None:
        """The user moved the Steps slider (or pressed its jump buttons): pause and, in Steps
        mode, show that step (Play then continues from there); in Trials mode, count the
        trials' positions at that step."""
        if self.playing:
            self.pause()
        if self.mode == STEPS_MODE:
            self.step_playback.jump_to(value)
            self.show_step(value)
        else:
            self.trials_step = value
            self.show_trials(self.trials_shown)

    def _on_trials_slider(self, value: int) -> None:
        """The user moved the Trials slider (or pressed its jump buttons): in Steps mode, how
        many trials take part; in Trials mode, how many are in the histogram so far."""
        if self.playing:
            self.pause()
        if self.mode == STEPS_MODE:
            self.steps_trials = value
            self.show_step(self.step_playback.current_frame)
        else:
            self.trial_playback.seek(self.ramp.frame_for(value))
            self.show_trials(value)

    def _hold_density(self) -> None:
        self.drawing_area.hold_density = True

    def _release_density(self) -> None:
        self.drawing_area.hold_density = False
        self.drawing_area.update()  # recounts for the slider's number of trials

    def generate_data(self) -> None:
        """Simulate the data set (the default runs and steps, no wall) and show it. The
        default generator is seeded, so this gives the same data every time the app starts."""
        self.paths = simulate_paths(DEFAULT_RUNS, DEFAULT_STEPS, wall=None, p_right=DEFAULT_P_RIGHT)
        self.drawing_area.set_paths(self.paths, p_right=DEFAULT_P_RIGHT)

    def apply_fonts(self) -> None:
        """Set the interface font (Source Code Pro): the default for every widget, plus each
        text element's own size. The symbol buttons keep their symbol font."""
        QApplication.setFont(ui_fonts.ui_font())  # every widget without its own font
        self.title.setFont(ui_fonts.ui_font(TITLE_POINT_SIZE))
        self.position_selector.setFont(ui_fonts.ui_font(SELECTOR_POINT_SIZE))
        label_font = ui_fonts.ui_font(SLIDER_LABEL_POINT_SIZE)
        widest = max(QFontMetrics(label_font).horizontalAdvance(t) for t in SLIDER_LABELS)
        for row in self.slider_rows:
            row.set_label_font(label_font, widest)
        self.drawing_area.setFont(ui_fonts.ui_font(AXIS_POINT_SIZE))

    def _build_player_controls(self) -> QHBoxLayout:
        """Step back, Play/Pause and step forward, centred. The step buttons repeat while
        held, at the keyboard's auto-repeat delay and rate, like holding Left/Right."""
        delay, interval = keyboard_repeat()
        self.step_back = symbol_button(symbols.STEP_BACK, "Step back (Left)")
        self.step_forward = symbol_button(symbols.STEP_FORWARD, "Step forward (Right)")
        for button, delta in ((self.step_back, -1), (self.step_forward, 1)):
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(delay)
            button.setAutoRepeatInterval(interval)
            button.clicked.connect(lambda _=False, d=delta: self.step_by(d))
        self.playing = False
        self.play_pause = HoverColorButton()
        style_symbol_button(self.play_pause, self._play_symbol(), "Play")
        # Fixed to the wider of its two symbols, so toggling doesn't shift its neighbours.
        self.play_pause.setFixedWidth(
            _widest(self.play_pause, (symbols.PLAY, symbols.PAUSE, symbols.PLAY_PAUSE))
        )
        self._show_play_state()
        self.play_pause.clicked.connect(self._toggle_play)

        row = QHBoxLayout()
        row.addStretch(1)
        for button in (self.step_back, self.play_pause, self.step_forward):
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
        self.play_pause.setToolTip("Pause (Space)" if self.playing else "Play (Space)")
        normal = PLAYING_COLOR if self.playing else PAUSED_COLOR
        self.play_pause.set_colors(normal, hover=PLAYING_COLOR)

    def _play_symbol(self) -> str:
        if COMBINED_PLAY_PAUSE:
            return symbols.PLAY_PAUSE
        return symbols.PAUSE if self.playing else symbols.PLAY


def keyboard_repeat() -> tuple[int, int]:
    """The system's key auto-repeat as (delay before repeating, interval between repeats) in
    ms, for buttons that should repeat like a held key. Qt reports the rate; on Windows the
    delay is read from the system setting (0-3: 250-1000 ms), elsewhere it's 500 ms."""
    rate = QApplication.styleHints().keyboardAutoRepeatRateF() or 30.0  # repeats a second
    delay = 500
    if sys.platform == "win32":
        import ctypes

        setting = ctypes.c_uint()
        if ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETKEYBOARDDELAY, 0, ctypes.byref(setting), 0
        ):
            delay = 250 * (setting.value + 1)
    return delay, max(1, round(1000 / rate))


def set_quietly(slider: QSlider, value: int) -> None:
    """Move `slider` without firing its change handlers: a display update, not a user choice."""
    slider.blockSignals(True)
    slider.setValue(value)
    slider.blockSignals(False)


class SliderRow:
    """A fixed-size slider between jump-to-start and jump-to-end buttons, centred in its row,
    with a text label to the left.

    `layout` is the row to add to a parent layout. The buttons move the slider to its ends. An
    invisible spacer on the right mirrors the label, so the label doesn't shift the centred
    slider; give every row the same label width (set_label_font) to keep the rows aligned.
    """

    def __init__(self, label: str, minimum: int, maximum: int, value: int) -> None:
        self.label = QLabel(label)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._mirror = QWidget()  # same width as the label, on the right
        self.to_start = symbol_button(symbols.SKIP_TO_START, "Jump to start")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
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

    def edit_value(self) -> None:
        """Open a number box just above the slider's handle (see ValueEditor)."""
        self._editor = ValueEditor(self.slider)  # kept so Python doesn't delete it early
        self._editor.open_over_handle()

    def set_label_font(self, font: QFont, width: int) -> None:
        """Set the label's font and fix the label (and its mirror) to `width` px."""
        self.label.setFont(font)
        self.label.setFixedWidth(width)
        self._mirror.setFixedWidth(width)


class ValueEditor(QSpinBox):
    """A small number box popped up just above a slider's handle, holding its value with the
    text selected, so typing replaces it. Enter moves the slider to the number (as if dragged
    there, so its handlers run); Esc or a click elsewhere closes it unchanged. It only accepts
    numbers in the slider's range.

    A Popup window: Qt closes it on any click outside and gives it the keyboard while open
    (MainWindow's key filter leaves the keys to it).
    """

    def __init__(self, slider: QSlider) -> None:
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._slider = slider
        self.setRange(slider.minimum(), slider.maximum())
        self.setValue(slider.value())
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        digits = len(str(slider.maximum()))
        self.setFixedWidth(self.fontMetrics().horizontalAdvance("0" * digits) + EDITOR_PADDING)

    def open_over_handle(self) -> None:
        """Show centred above the slider's handle, with the number selected."""
        slider = self._slider
        handle = slider.style().pixelMetric(QStyle.PixelMetric.PM_SliderLength, None, slider)
        x = handle / 2 + QStyle.sliderPositionFromValue(
            slider.minimum(), slider.maximum(), slider.value(), slider.width() - handle
        )
        corner = slider.mapToGlobal(QPoint(round(x - self.width() / 2), 0))
        self.move(corner.x(), corner.y() - self.sizeHint().height() - EDITOR_GAP)
        self.show()
        self.setFocus()
        self.selectAll()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.interpretText()  # take the typed text, even if not yet committed
            value = self.value()
            self.close()
            self._slider.setValue(value)
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


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
