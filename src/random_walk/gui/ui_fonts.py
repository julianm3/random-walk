"""Candidate fonts for the interface text, bundled in gui/fonts/ for comparison.

TEMPORARY (font evaluation): once a font is chosen, keep only that one here and remove the
others, their licences, the window's font selector and the --font option.

Licences: DejaVu Sans Mono - Bitstream Vera licence + public domain (DejaVu-LICENSE.txt);
Source Code Pro - SIL OFL 1.1 with Reserved Font Name "Source" (SourceCodePro-OFL.txt). Both
are bundled unmodified: modified versions would have to be renamed.
"""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

SYSTEM = "System default"

# Display name -> bundled font files (empty for the platform's own UI font).
CANDIDATES: dict[str, tuple[str, ...]] = {
    SYSTEM: (),
    "DejaVu Sans Mono": ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf"),
    "Source Code Pro": ("SourceCodePro-Regular.ttf", "SourceCodePro-Bold.ttf"),
}

# Short names for the --font command-line option.
CLI_NAMES = {"system": SYSTEM, "dejavu": "DejaVu Sans Mono", "source": "Source Code Pro"}

_registered = False
_system_font: QFont | None = None


def register() -> None:
    """Load the bundled candidate fonts into Qt (once) and remember the system UI font.
    Needs a QApplication."""
    global _registered, _system_font
    if _registered:
        return
    _system_font = QApplication.font()
    fonts_dir = files("random_walk.gui") / "fonts"
    for filenames in CANDIDATES.values():
        for filename in filenames:
            if QFontDatabase.addApplicationFontFromData((fonts_dir / filename).read_bytes()) < 0:
                raise RuntimeError(f"could not load bundled font {filename}")
    _registered = True


def ui_font(name: str, point_size: float | None = None) -> QFont:
    """The candidate font `name`, at `point_size` or the system UI font's size."""
    register()
    assert _system_font is not None
    font = QFont(_system_font) if name == SYSTEM else QFont(name)
    font.setPointSizeF(point_size if point_size is not None else _system_font.pointSizeF())
    return font
