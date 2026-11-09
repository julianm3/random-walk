"""Small widgets and helpers for the main window: a slider row with jump buttons, the number
box that edits a slider's value, a button whose colour changes on hover, media-symbol
buttons, and the system's key repeat timing."""

from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QColor, QEnterEvent, QKeyEvent, QPalette
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QHBoxLayout,
    QSlider,
    QSpinBox,
    QStyle,
    QToolButton,
)

from random_walk.gui import symbols
from random_walk.gui.style import SLIDER_HEIGHT, SLIDER_STYLE

EDITOR_PADDING = 16  # px added to the widest number's width in a slider's number box
EDITOR_GAP = 2  # px between the number box and the top of the slider
SPI_GETKEYBOARDDELAY = 0x0016  # Windows SystemParametersInfo: the key repeat delay setting


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
    """A slider `width` px wide (style.SLIDER_HEIGHT tall) between jump-to-start and
    jump-to-end buttons.

    `layout` is the row to add to a parent layout (the window centres it and puts the
    selector, whose labels name the sliders, to its left). The buttons move the slider to its
    ends.
    """

    def __init__(self, minimum: int, maximum: int, value: int, width: int) -> None:
        self.to_start = symbol_button(symbols.SKIP_TO_START, "Jump to start")

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.setFixedSize(width, SLIDER_HEIGHT)
        self.slider.setStyleSheet(SLIDER_STYLE)

        self.to_end = symbol_button(symbols.SKIP_TO_END, "Jump to end")

        self.to_start.clicked.connect(lambda: self.slider.setValue(self.slider.minimum()))
        self.to_end.clicked.connect(lambda: self.slider.setValue(self.slider.maximum()))

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.to_start)
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.to_end)

    def height(self) -> int:
        """The row's height: its tallest widget. (Asked of the widgets, not the layout, which
        reports 0 until it's in a window.)"""
        return max(w.sizeHint().height() for w in (self.to_start, self.slider, self.to_end))

    def edit_value(self) -> None:
        """Open a number box just above the slider's handle (see ValueEditor)."""
        self._editor = ValueEditor(self.slider)  # kept so Python doesn't delete it early
        self._editor.open_over_handle()


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


def widest(button: QToolButton, texts: tuple[str, ...]) -> int:
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
