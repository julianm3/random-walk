"""Dialogs opened from the drawing area's right-click menu."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from random_walk.config import MAX_WALL, MIN_WALL

REGENERATES_NOTE = "(Regenerates animation data)"
NOTE_COLOR = "#8c8c8c"  # mid grey, like the paused Play symbol


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

        note = QLabel(REGENERATES_NOTE)
        note.setStyleSheet(f"color: {NOTE_COLOR};")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.wall_on)
        layout.addLayout(position_row)
        layout.addSpacing(6)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _enable_position(self, enabled: bool) -> None:
        self.position.setEnabled(enabled)
        self.position_label.setEnabled(enabled)

    def values(self) -> tuple[bool, int]:
        """(wall on, position) as chosen."""
        return self.wall_on.isChecked(), self.position.value()
