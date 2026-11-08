"""The dialog opened from the drawing area's right-click menu."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from random_walk.config import MAX_WALL, MIN_WALL
from random_walk.gui.style import SLIDER_HEIGHT, SLIDER_STYLE
from random_walk.params import WalkParams

REGENERATES_NOTE = "(data will be regenerated)"  # the user's wording
NOTE_COLOR = "#8c8c8c"  # mid grey, like the paused Play symbol
MAX_SEED = 2**31 - 1  # the largest a QSpinBox holds; any seed from 0 up works
P_SLIDER_WIDTH = 200  # px; the bias slider
# The wall modes' radio buttons: (WalkParams.wall_mode, label).
WALL_MODE_BUTTONS = (("reflect", "Reflect"), ("absorb", "Absorb"))


class ConfigureDialog(QDialog):
    """The data set's settings: the wall (on or off, what it does - reflect the walks or
    absorb them - and its position), the bias P(right) (the chance of a +1 step, 0-100% in 1%
    steps; P(left) = 1 - P(right)) and the random seed. Opens with the current values; OK
    regenerates the data if any of them changed, as the note says.

        Configure
        Wall   [x] Enabled   (*) Reflect  ( ) Absorb
               Position [ -80 ]
        Bias   P(left) 50%  ----|----  P(right) 50%
        Seed   [   42 ]
        (data will be regenerated)
                                    [OK] [Cancel]

    The wall's mode and position are greyed out while it's off. The slider has the main
    window's look (gui/style.py); moving it right raises P(right).
    """

    def __init__(self, params: WalkParams, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure")

        # Wall: on/off and its mode on the first line, its position on the next.
        self.wall_on = QCheckBox("Enabled")
        self.wall_on.setChecked(params.wall_enabled)
        self.mode_buttons = QButtonGroup(self)
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.wall_on)
        mode_row.addSpacing(12)
        for mode, label in WALL_MODE_BUTTONS:
            button = QRadioButton(label)
            button.setChecked(mode == params.wall_mode)
            button.setProperty("wall_mode", mode)
            self.mode_buttons.addButton(button)
            mode_row.addWidget(button)
        mode_row.addStretch(1)
        self.position_label = QLabel("Position")
        self.position = QSpinBox()
        self.position.setRange(MIN_WALL, MAX_WALL)
        self.position.setValue(params.wall_value)
        self.position.setToolTip(f"From {MIN_WALL} to {MAX_WALL}")
        position_row = QHBoxLayout()
        position_row.addWidget(self.position_label)
        position_row.addWidget(self.position)
        position_row.addStretch(1)
        self.wall_on.toggled.connect(self._enable_wall_settings)
        self._enable_wall_settings(params.wall_enabled)

        # Bias: P(left) at the left end, P(right) at the right.
        self.p_slider = QSlider(Qt.Orientation.Horizontal)
        self.p_slider.setRange(0, 100)
        self.p_slider.setValue(round(params.p_right * 100))
        self.p_slider.setFixedSize(P_SLIDER_WIDTH, SLIDER_HEIGHT)
        self.p_slider.setStyleSheet(SLIDER_STYLE)
        self.p_left_label = QLabel()
        self.p_right_label = QLabel()
        # Fixed to the widest text, so the slider doesn't shift as the numbers change.
        for label_widget, text in (
            (self.p_left_label, "P(left) 100%"),
            (self.p_right_label, "P(right) 100%"),
        ):
            label_widget.setFixedWidth(label_widget.fontMetrics().horizontalAdvance(text))
        self.p_left_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.p_slider.valueChanged.connect(self._show_percentages)
        self._show_percentages(self.p_slider.value())
        bias_row = QHBoxLayout()
        bias_row.addWidget(self.p_left_label)
        bias_row.addWidget(self.p_slider)
        bias_row.addWidget(self.p_right_label)
        bias_row.addStretch(1)

        # Seed.
        self.seed = QSpinBox()
        self.seed.setRange(0, MAX_SEED)
        self.seed.setValue(params.seed)
        seed_row = QHBoxLayout()
        seed_row.addWidget(self.seed)
        seed_row.addStretch(1)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        rows = (("Wall", mode_row), ("", position_row), ("Bias", bias_row), ("Seed", seed_row))
        for row, (name, controls) in enumerate(rows):
            grid.addWidget(QLabel(name), row, 0)
            grid.addLayout(controls, row, 1)

        note = QLabel(REGENERATES_NOTE)
        note.setStyleSheet(f"color: {NOTE_COLOR};")
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addSpacing(6)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _enable_wall_settings(self, enabled: bool) -> None:
        for widget in (self.position, self.position_label, *self.mode_buttons.buttons()):
            widget.setEnabled(enabled)

    def _show_percentages(self, percent: int) -> None:
        self.p_left_label.setText(f"P(left) {100 - percent}%")
        self.p_right_label.setText(f"P(right) {percent}%")

    def wall_mode(self) -> str:
        """The chosen wall mode: "reflect" or "absorb"."""
        checked = self.mode_buttons.checkedButton()
        return str(checked.property("wall_mode")) if checked else "reflect"

    def values(self) -> dict[str, Any]:
        """The chosen settings, by their WalkParams names, for dataclasses.replace(). P(right)
        runs from 0 to 1 in whole percentages, so 50% is exactly 0.5."""
        return {
            "wall_enabled": self.wall_on.isChecked(),
            "wall_mode": self.wall_mode(),
            "wall_value": self.position.value(),
            "p_right": self.p_slider.value() / 100,
            "seed": self.seed.value(),
        }
