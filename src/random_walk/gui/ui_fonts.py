"""The interface font: Source Code Pro, bundled in gui/fonts/ (Regular and Bold).

Licence: SIL OFL 1.1 with Reserved Font Name "Source" (gui/fonts/SourceCodePro-OFL.txt). It's
bundled unmodified - a modified version (even a subset) would have to be renamed.
"""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

FAMILY = "Source Code Pro"
FONT_FILES = ("SourceCodePro-Regular.ttf", "SourceCodePro-Bold.ttf")

_registered = False
_base_size = 9.0  # pt; replaced by the platform's UI font size on registration


def register() -> None:
    """Load the bundled font files into Qt (once). Needs a QApplication."""
    global _registered, _base_size
    if _registered:
        return
    _base_size = QApplication.font().pointSizeF()
    fonts_dir = files("random_walk.gui") / "fonts"
    for filename in FONT_FILES:
        if QFontDatabase.addApplicationFontFromData((fonts_dir / filename).read_bytes()) < 0:
            raise RuntimeError(f"could not load bundled font {filename}")
    _registered = True


def ui_font(point_size: float | None = None) -> QFont:
    """The interface font at `point_size`, or at the platform's usual UI size."""
    register()
    font = QFont(FAMILY)
    font.setPointSizeF(point_size if point_size is not None else _base_size)
    return font
