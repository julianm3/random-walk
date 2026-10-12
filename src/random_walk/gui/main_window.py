"""The main window, laid out after the first sketch (GUI_1):

    +--------------------------------------------+
    |                                Random Walk |
    | +----------------------------------------+ |
    | |                                        | |
    | |         drawing area (grows)           | |
    | |                                        | |
    | +----------------------------------------+ |
    |                    [1000 Steps, 10000 Times]|
    |       |<< ----o-------------------- >>|    |
    +--------------------------------------------+

The drawing area takes all spare space as the window resizes. The slider row keeps a fixed
width, stays centred, and keeps its spacing from the drawing area and the window's bottom.
Nothing is connected to the simulation yet.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from random_walk.gui import symbols

TITLE = "Random Walk"
SUMMARY = "1000 Steps, 10000 Times"  # plain text for now
SLIDER_MIN, SLIDER_MAX = 0, 1000
SLIDER_WIDTH = 640  # px; fixed, independent of the window width
SLIDER_HEIGHT = 24  # px; room for the 22 px handle bar, which is clipped to the widget
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
        font = self.title.font()
        font.setPointSize(TITLE_POINT_SIZE)
        self.title.setFont(font)
        layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignRight)

        # Placeholder for the plot; stretch=1 gives it all the spare space on resize.
        self.drawing_area = QFrame()
        self.drawing_area.setFrameShape(QFrame.Shape.Box)
        self.drawing_area.setMinimumSize(320, 200)
        layout.addWidget(self.drawing_area, stretch=1)

        self.summary = QLabel(SUMMARY)
        self.summary.setFrameShape(QFrame.Shape.Box)
        self.summary.setMargin(6)  # padding inside the frame
        font = self.summary.font()
        font.setPointSize(SUMMARY_POINT_SIZE)
        self.summary.setFont(font)
        layout.addWidget(self.summary, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addSpacing(50)
        layout.addLayout(self._build_slider_row())

    def _build_slider_row(self) -> QHBoxLayout:
        self.to_start = self._symbol_button(symbols.SKIP_TO_START, "Jump to start")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(SLIDER_MIN, SLIDER_MAX)
        self.slider.setValue(SLIDER_MIN)
        self.slider.setFixedSize(SLIDER_WIDTH, SLIDER_HEIGHT)
        self.slider.setStyleSheet(SLIDER_STYLE)

        self.to_end = self._symbol_button(symbols.SKIP_TO_END, "Jump to end")

        self.to_start.clicked.connect(lambda: self.slider.setValue(self.slider.minimum()))
        self.to_end.clicked.connect(lambda: self.slider.setValue(self.slider.maximum()))

        # Stretch on both sides keeps the fixed-width row centred as the window resizes.
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.to_start)
        row.addWidget(self.slider)
        row.addWidget(self.to_end)
        row.addStretch(1)
        return row

    def _symbol_button(self, symbol: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText(symbol)
        button.setFont(symbols.symbol_font())
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        return button
