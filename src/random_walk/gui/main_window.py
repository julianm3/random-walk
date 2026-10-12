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

TEMPORARY: a font selector at the top left switches the interface font live, to compare the
candidates in gui/ui_fonts.py. Remove it once a font is chosen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
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
    def __init__(self, ui_font: str = ui_fonts.SYSTEM) -> None:
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
        layout.addLayout(self._build_slider_row())

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
