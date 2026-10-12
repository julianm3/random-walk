"""The main window, laid out after the sketches in docs/sketches (GUI_1, GUI_2):

    +--------------------------------------------+
    | Font: [....]                   Random Walk |
    | +----------------------------------------+ |
    | |                                        | |
    | |         drawing area (grows)           | |
    | |                                        | |
    | +----------------------------------------+ |
    |                   [1000 Steps, 10000 Times]|
    |       |<< ---|--------------------- >>|    |
    |                  SLIDER_GAP                |
    |       |<< ---|--------------------- >>|    |
    |                 CONTROLS_GAP               |
    |                 <<   >/||   >>             |
    +--------------------------------------------+

The drawing area takes all spare space as the window resizes. Everything below it keeps its
size, stays centred, and keeps its spacing. Nothing is connected to the simulation yet.

TEMPORARY: a font selector at the top left switches the interface font live, to compare the
candidates in gui/ui_fonts.py. Remove it once a font is chosen.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QEnterEvent, QPalette
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

from random_walk.gui import symbols, ui_fonts

TITLE = "Random Walk"
SUMMARY = "1000 Steps, 10000 Times"  # plain text for now
SLIDER_MIN, SLIDER_MAX = 0, 1000
SLIDER_WIDTH = 640  # px; fixed, independent of the window width
SLIDER_HEIGHT = 24  # px; room for the 22 px handle bar, which is clipped to the widget
SLIDER_GAP = 36  # px; vertical space between the two slider rows
CONTROLS_GAP = 24  # px; vertical space between the second slider row and the player controls
# Play/Pause button: True shows the combined symbol (one fixed glyph); False swaps between
# separate Play and Pause symbols. The tooltip follows the state either way.
COMBINED_PLAY_PAUSE = True
PLAYING_COLOR = "black"  # Play/Pause symbol colour while playing
PAUSED_COLOR = "#8c8c8c"  # ... and while paused (mid grey); it turns black on hover
TITLE_POINT_SIZE = 14
SUMMARY_POINT_SIZE = 11
INITIAL_SIZE = (1000, 760)

# Slider track: the part left of the handle (already played) and the part right of it.
SLIDER_DONE_COLOR = "black"
SLIDER_TODO_COLOR = "#d3d3d3"  # light grey
SLIDER_HANDLE_COLOR = "black"
# A style sheet replaces the native slider drawing entirely, so the handle is styled here too:
# a thin vertical bar, like a playhead. It's 4 px wide and 22 px tall; the negative vertical
# margin lets it extend 9 px above and below the 4 px track.
SLIDER_STYLE = f"""
QSlider::groove:horizontal {{ height: 4px; background: {SLIDER_TODO_COLOR}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {SLIDER_DONE_COLOR}; border-radius: 2px; }}
QSlider::add-page:horizontal {{ background: {SLIDER_TODO_COLOR}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 4px; height: 22px; margin: -9px 0; border-radius: 1px;
    background: {SLIDER_HANDLE_COLOR}; border: none;
}}
"""


class MainWindow(QMainWindow):
    def __init__(self, ui_font: str = ui_fonts.DEFAULT) -> None:
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
        title_row.addLayout(self._build_font_selector())  # TEMPORARY
        title_row.addStretch(1)
        title_row.addWidget(self.title)
        layout.addLayout(title_row)

        # Placeholder for the plot; stretch=1 gives it all the spare space on resize.
        self.drawing_area = QFrame()
        self.drawing_area.setFrameShape(QFrame.Shape.Box)
        self.drawing_area.setMinimumSize(320, 200)
        layout.addWidget(self.drawing_area, stretch=1)

        self.summary = QLabel(SUMMARY)
        self.summary.setFrameShape(QFrame.Shape.Box)
        self.summary.setMargin(6)  # padding inside the frame
        layout.addWidget(self.summary, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addSpacing(50)
        # The bottom controls get their own zero-spacing layout, so SLIDER_GAP and CONTROLS_GAP
        # are the exact gaps (the window layout would add its 8 px spacing on top).
        self.slider_rows = (SliderRow(), SliderRow())
        controls = QVBoxLayout()
        controls.setSpacing(0)
        controls.addLayout(self.slider_rows[0].layout)
        controls.addSpacing(SLIDER_GAP)
        controls.addLayout(self.slider_rows[1].layout)
        controls.addSpacing(CONTROLS_GAP)
        controls.addLayout(self._build_player_controls())
        layout.addLayout(controls)

        self.set_ui_font(ui_font)

    def set_ui_font(self, name: str) -> None:
        """Switch the interface text to candidate font `name` (see gui/ui_fonts.py). The
        symbol buttons keep their own font."""
        QApplication.setFont(ui_fonts.ui_font(name))  # every widget without its own font
        self.title.setFont(ui_fonts.ui_font(name, TITLE_POINT_SIZE))
        self.summary.setFont(ui_fonts.ui_font(name, SUMMARY_POINT_SIZE))
        self.font_selector.blockSignals(True)
        self.font_selector.setCurrentText(name)
        self.font_selector.blockSignals(False)

    def _build_font_selector(self) -> QHBoxLayout:
        """TEMPORARY: a dropdown to compare the candidate interface fonts live."""
        self.font_selector = QComboBox()
        self.font_selector.addItems(list(ui_fonts.CANDIDATES))
        self.font_selector.setToolTip("Temporary: compare candidate interface fonts")
        self.font_selector.currentTextChanged.connect(self.set_ui_font)
        row = QHBoxLayout()
        row.addWidget(QLabel("Font:"))
        row.addWidget(self.font_selector)
        return row

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
        """While "playing", the button offers Pause; otherwise it offers Play. (Not a checkable
        button: the native style would draw it highlighted while checked.)"""
        self.playing = not self.playing
        self._show_play_state()

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
    """A fixed-size slider between jump-to-start and jump-to-end buttons, centred in its row.

    `layout` is the row to add to a parent layout. The buttons move the slider to its ends.
    """

    def __init__(self) -> None:
        self.to_start = symbol_button(symbols.SKIP_TO_START, "Jump to start")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(SLIDER_MIN, SLIDER_MAX)
        self.slider.setValue(SLIDER_MIN)
        self.slider.setFixedSize(SLIDER_WIDTH, SLIDER_HEIGHT)
        self.slider.setStyleSheet(SLIDER_STYLE)

        self.to_end = symbol_button(symbols.SKIP_TO_END, "Jump to end")

        self.to_start.clicked.connect(lambda: self.slider.setValue(self.slider.minimum()))
        self.to_end.clicked.connect(lambda: self.slider.setValue(self.slider.maximum()))

        # Stretch on both sides keeps the fixed-width row centred as the window resizes.
        self.layout = QHBoxLayout()
        self.layout.addStretch(1)
        self.layout.addWidget(self.to_start)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.to_end)
        self.layout.addStretch(1)


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
