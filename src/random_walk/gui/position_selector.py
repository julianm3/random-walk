"""A row of circles joined by a line; the selected one holds a dot (sketch: customControl).

    ( * )--------(   )--------(   )
    Position 1   Position 2   Position 3
       Text         Text         Text

With exactly two positions, `labels_beside` puts the labels either side instead, centred on
the circles, so the control is only as tall as a circle (or a label):

    Steps ( * )--------(   ) Trials

Click a circle or its label to select that position; the dot slides there and
`currentIndexChanged` is emitted. Exactly one position is selected at a time.

Geometry, all in px:
  diameter    circle diameter (the control's "height"); the dot is half of it
  spacing     edge-to-edge gap between neighbouring circles - with labels below, a minimum:
              it grows so the widest label fits, keeping every gap equal
  label_gap   from the circles to their labels: below them, or beside them with
              `labels_beside`
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFontMetricsF, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

DEFAULT_LABELS = ("Position 1\nText", "Position 2\nText", "Position 3\nText")
DEFAULT_DIAMETER = 22
DEFAULT_SPACING = 60
DEFAULT_LABEL_GAP = 6

COLOR = "black"  # outlines, connecting line and dot
LINE_WIDTH = 2  # px, circle outlines and the connecting line
MIN_LABEL_GAP = 16  # px, least horizontal space between neighbouring labels
SLIDE_MS = 180  # duration of the dot's slide to a new position


def circle_pitch(diameter: float, spacing: float, widest_label: float) -> float:
    """Centre-to-centre distance between neighbouring circles: the requested edge-to-edge
    spacing, widened if needed so the widest label fits with MIN_LABEL_GAP to spare."""
    return max(diameter + spacing, widest_label + MIN_LABEL_GAP)


class PositionSelector(QWidget):
    currentIndexChanged = Signal(int)

    def __init__(
        self,
        labels: Sequence[str] = DEFAULT_LABELS,
        diameter: int = DEFAULT_DIAMETER,
        spacing: int = DEFAULT_SPACING,
        label_gap: int = DEFAULT_LABEL_GAP,
        labels_beside: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not labels:
            raise ValueError("PositionSelector needs at least one position")
        if labels_beside and len(labels) != 2:
            raise ValueError("labels_beside needs exactly two positions")
        self._labels = list(labels)
        self._diameter = diameter
        self._spacing = spacing
        self._label_gap = label_gap
        self._beside = labels_beside
        self._index = 0
        self._dot = 0.0  # dot position in index units; fractional while sliding

        self._slide = QVariantAnimation(self)
        self._slide.setDuration(SLIDE_MS)
        self._slide.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._slide.valueChanged.connect(self._on_slide)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    # --- public API ----------------------------------------------------------------------

    def count(self) -> int:
        return len(self._labels)

    def currentIndex(self) -> int:
        return self._index

    def setCurrentIndex(self, index: int, animate: bool = True) -> None:
        """Select position `index` (0-based); the dot slides there unless `animate` is False."""
        if not 0 <= index < self.count():
            raise IndexError(f"position {index} out of range 0..{self.count() - 1}")
        if index == self._index:
            return
        self._index = index
        self._slide.stop()
        if animate:
            self._slide.setStartValue(self._dot)
            self._slide.setEndValue(float(index))
            self._slide.start()
        else:
            self._dot = float(index)
            self.update()
        self.currentIndexChanged.emit(index)

    # --- geometry ------------------------------------------------------------------------

    def _metrics(self) -> QFontMetricsF:
        return QFontMetricsF(self.font())

    def _label_size(self, text: str) -> QSize:
        rect = self._metrics().boundingRect(QRectF(), Qt.AlignmentFlag.AlignHCenter, text)
        return QSize(int(rect.width() + 1), int(rect.height() + 1))

    def _pitch(self) -> float:
        if self._beside:  # no labels between the circles to make room for
            return self._diameter + self._spacing
        widest = max(self._label_size(t).width() for t in self._labels)
        return circle_pitch(self._diameter, self._spacing, widest)

    def _side_margin(self, label: str) -> float:
        """Room from the widget edge to an end circle's centre: half the circle (plus the
        outline) and, with labels beside, the label and its gap; with labels below, half the
        circle or half its label, whichever is wider."""
        circle = self._diameter / 2 + LINE_WIDTH
        if self._beside:
            return circle + self._label_gap + self._label_size(label).width()
        return max(circle, self._label_size(label).width() / 2)

    def _labels_height(self) -> float:
        return max(self._label_size(t).height() for t in self._labels)

    def _centre(self, position: float) -> QPointF:
        """Centre of the circle at `position` (fractional while the dot slides)."""
        x = self._side_margin(self._labels[0]) + position * self._pitch()
        if self._beside:  # circles and labels share one centre line
            y = max(self._diameter + 2 * LINE_WIDTH, self._labels_height()) / 2
        else:
            y = LINE_WIDTH + self._diameter / 2
        return QPointF(x, y)

    def _circle_rect(self, index: int) -> QRectF:
        c, r = self._centre(index), self._diameter / 2
        return QRectF(c.x() - r, c.y() - r, self._diameter, self._diameter)

    def _label_rect(self, index: int) -> QRectF:
        size = self._label_size(self._labels[index])
        centre = self._centre(index)
        if self._beside:  # left of the first circle, right of the second
            reach = self._diameter / 2 + LINE_WIDTH + self._label_gap
            x = centre.x() - reach - size.width() if index == 0 else centre.x() + reach
            return QRectF(x, centre.y() - size.height() / 2, size.width(), size.height())
        top = LINE_WIDTH + self._diameter + self._label_gap
        return QRectF(centre.x() - size.width() / 2, top, size.width(), size.height())

    def _label_alignment(self, index: int) -> Qt.AlignmentFlag:
        """How a label's lines line up: towards its circle when beside it, else centred."""
        if not self._beside:
            return Qt.AlignmentFlag.AlignHCenter
        return Qt.AlignmentFlag.AlignRight if index == 0 else Qt.AlignmentFlag.AlignLeft

    def sizeHint(self) -> QSize:
        width = (
            self._side_margin(self._labels[0])
            + (self.count() - 1) * self._pitch()
            + self._side_margin(self._labels[-1])
        )
        if self._beside:
            height = max(self._diameter + 2 * LINE_WIDTH, self._labels_height())
        else:
            height = LINE_WIDTH + self._diameter + self._label_gap + self._labels_height()
        return QSize(int(width + 1), int(height + 1))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # --- painting and input --------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(COLOR)
        r = self._diameter / 2

        painter.setPen(QPen(color, LINE_WIDTH))
        for i in range(self.count() - 1):  # connecting line, edge to edge
            a, b = self._centre(i), self._centre(i + 1)
            painter.drawLine(QPointF(a.x() + r, a.y()), QPointF(b.x() - r, b.y()))

        painter.setBrush(Qt.BrushStyle.NoBrush)  # transparent circles
        for i in range(self.count()):
            painter.drawEllipse(self._circle_rect(i))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(self._centre(self._dot), r / 2, r / 2)  # dot: half the diameter

        painter.setPen(color)
        for i, text in enumerate(self._labels):
            painter.drawText(self._label_rect(i), self._label_alignment(i), text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        for i in range(self.count()):
            if self._circle_rect(i).contains(pos) or self._label_rect(i).contains(pos):
                self.setCurrentIndex(i)
                return
        super().mousePressEvent(event)

    def changeEvent(self, event: QEvent) -> None:
        if event.type() == QEvent.Type.FontChange:  # label sizes, hence geometry, changed
            self.updateGeometry()
            self.update()
        super().changeEvent(event)

    def _on_slide(self, value: float) -> None:
        self._dot = value
        self.update()
