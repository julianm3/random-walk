"""Dialogs opened from the drawing area's right-click menu."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from random_walk.config import MAX_WALL, MIN_WALL
from random_walk.gui.style import SLIDER_HEIGHT, SLIDER_STYLE

REGENERATES_NOTE = "(Regenerates animation data)"
NOTE_COLOR = "#8c8c8c"  # mid grey, like the paused Play symbol
MAX_SEED = 2**31 - 1  # the largest a QSpinBox holds; any seed from 0 up works
P_SLIDER_WIDTH = 200  # px; the Regenerate dialog's P(right) slider


def _note() -> QLabel:
    note = QLabel(REGENERATES_NOTE)
    note.setStyleSheet(f"color: {NOTE_COLOR};")
    return note


def _ok_cancel(dialog: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


class WallDialog(QDialog):
    """The reflecting wall: on or off, and its position (MIN_WALL to MAX_WALL). Changing
    either regenerates the data on OK, as the note says.

        Wall
        [x] Wall on
            Position [ -30 ]
        (Regenerates animation data)
                        [OK] [Cancel]
    """

    def __init__(self, enabled: bool, position: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Wall")

        self.wall_on = QCheckBox("Wall on")
        self.wall_on.setChecked(enabled)
        self.position = QSpinBox()
        self.position.setRange(MIN_WALL, MAX_WALL)
        self.position.setValue(position)
        self.position.setToolTip(f"From {MIN_WALL} to {MAX_WALL}")
        self.position_label = QLabel("Position")
        self.wall_on.toggled.connect(self._enable_position)
        self._enable_position(enabled)

        position_row = QHBoxLayout()
        position_row.addSpacing(self.wall_on.iconSize().width() + 8)  # under the box's text
        position_row.addWidget(self.position_label)
        position_row.addWidget(self.position)
        position_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.wall_on)
        layout.addLayout(position_row)
        layout.addSpacing(6)
        layout.addWidget(_note())
        layout.addWidget(_ok_cancel(self))

    def _enable_position(self, enabled: bool) -> None:
        self.position.setEnabled(enabled)
        self.position_label.setEnabled(enabled)

    def values(self) -> tuple[bool, int]:
        """(wall on, position) as chosen."""
        return self.wall_on.isChecked(), self.position.value()


class RegenerateDialog(QDialog):
    """A new data set: the random seed and P(right), the chance of a +1 step (0-100% in 1%
    steps; P(left) = 1 - P(right)). Opens with the current values; OK regenerates (the wall
    setting is kept).

        Regenerate
        Seed      [   42 ]
        P(right) 50%  ----|----  P(left) 50%
        (Regenerates animation data)
                          [OK] [Cancel]

    The slider has the main window's look (gui/style.py).
    """

    def __init__(self, seed: int, p_right: float, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Regenerate")

        self.seed = QSpinBox()
        self.seed.setRange(0, MAX_SEED)
        self.seed.setValue(seed)

        self.p_slider = QSlider(Qt.Orientation.Horizontal)
        self.p_slider.setRange(0, 100)
        self.p_slider.setValue(round(p_right * 100))
        self.p_slider.setFixedSize(P_SLIDER_WIDTH, SLIDER_HEIGHT)
        self.p_slider.setStyleSheet(SLIDER_STYLE)
        self.p_right_label = QLabel()
        self.p_left_label = QLabel()
        # Fixed to the widest text, so the slider doesn't shift as the numbers change.
        for label, text in (
            (self.p_right_label, "P(right) 100%"),
            (self.p_left_label, "P(left) 100%"),
        ):
            label.setFixedWidth(label.fontMetrics().horizontalAdvance(text))
        self.p_right_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.p_slider.valueChanged.connect(self._show_percentages)
        self._show_percentages(self.p_slider.value())

        seed_row = QHBoxLayout()
        seed_row.addWidget(QLabel("Seed"))
        seed_row.addWidget(self.seed)
        seed_row.addStretch(1)
        p_row = QHBoxLayout()
        p_row.addWidget(self.p_right_label)
        p_row.addWidget(self.p_slider)
        p_row.addWidget(self.p_left_label)

        layout = QVBoxLayout(self)
        layout.addLayout(seed_row)
        layout.addLayout(p_row)
        layout.addSpacing(6)
        layout.addWidget(_note())
        layout.addWidget(_ok_cancel(self))

    def _show_percentages(self, percent: int) -> None:
        self.p_right_label.setText(f"P(right) {percent}%")
        self.p_left_label.setText(f"P(left) {100 - percent}%")

    def values(self) -> tuple[int, float]:
        """(seed, P(right)) as chosen; P(right) from 0 to 1 (whole percentages, so 50% is
        exactly 0.5)."""
        return self.seed.value(), self.p_slider.value() / 100
