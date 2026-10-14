"""A row of circles joined by a line; the selected one holds a dot (sketch: customControl).

    ( * )--------(   )--------(   )
    Position 1   Position 2   Position 3
       Text         Text         Text

Click a circle or its label to select that position; the dot slides there and
`currentIndexChanged` is emitted. Exactly one position is selected at a time.

Geometry, all in px:
  diameter    circle diameter (the control's "height"); the dot is half of it
  spacing     edge-to-edge gap between neighbouring circles - a minimum: it grows so the widest
              label fits, keeping every gap equal
  label_gap   from the bottom of the circles to the top of the labels
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
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not labels:
            raise ValueError("PositionSelector needs at least one position")
        self._labels = list(labels)
        self._diameter = diameter
        self._spacing = spacing
        self._label_gap = label_gap
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
        widest = max(self._label_size(t).width() for t in self._labels)
        return circle_pitch(self._diameter, self._spacing, widest)

    def _side_margin(self, label: str) -> float:
        """Room from the widget edge to an end circle's centre: half the circle (plus the
        outline) or half that circle's label, whichever is wider."""
        return max(self._diameter / 2 + LINE_WIDTH, self._label_size(label).width() / 2)

    def _centre(self, position: float) -> QPointF:
        """Centre of the circle at `position` (fractional while the dot slides)."""
        x = self._side_margin(self._labels[0]) + position * self._pitch()
        return QPointF(x, LINE_WIDTH + self._diameter / 2)

    def _circle_rect(self, index: int) -> QRectF:
        c, r = self._centre(index), self._diameter / 2
        return QRectF(c.x() - r, c.y() - r, self._diameter, self._diameter)

    def _label_rect(self, index: int) -> QRectF:
        size = self._label_size(self._labels[index])
        top = LINE_WIDTH + self._diameter + self._label_gap
        x = self._centre(index).x() - size.width() / 2
        return QRectF(x, top, size.width(), size.height())

    def sizeHint(self) -> QSize:
        width = (
            self._side_margin(self._labels[0])
            + (self.count() - 1) * self._pitch()
            + self._side_margin(self._labels[-1])
        )
        labels_height = max(self._label_size(t).height() for t in self._labels)
        height = LINE_WIDTH + self._diameter + self._label_gap + labels_height
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
            painter.drawText(self._label_rect(i), Qt.AlignmentFlag.AlignHCenter, text)

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
