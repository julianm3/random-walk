"""Media-control symbols for buttons, drawn with a bundled font.

The font is a subset of Noto Sans Symbols 2 (SIL OFL 1.1, licence in
gui/fonts/NotoSansSymbols2-OFL.txt) holding just the transport symbols U+23E9-U+23FA, with its
line height tightened around them so they centre well in buttons. It's built by
tools/make_symbol_font.py. Bundling it keeps the symbols identical on every platform rather
than depending on whichever system font Qt falls back to.
"""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtGui import QFont, QFontDatabase

# Unicode gives some of these characters emoji presentation by default (U+23E9 and U+23EA
# here), and the OS then draws them from its colour emoji font, ignoring ours. Appending the
# text presentation selector U+FE0E asks for the plain text glyph instead.
TEXT_PRESENTATION = chr(0xFE0E)  # VARIATION SELECTOR-15

SKIP_TO_START = chr(0x23EE)  # BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR
SKIP_TO_END = chr(0x23ED)  # BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR
FAST_REVERSE = chr(0x23EA) + TEXT_PRESENTATION  # BLACK LEFT-POINTING DOUBLE TRIANGLE
FAST_FORWARD = chr(0x23E9) + TEXT_PRESENTATION  # BLACK RIGHT-POINTING DOUBLE TRIANGLE
PLAY = chr(0x23F5)  # BLACK MEDIUM RIGHT-POINTING TRIANGLE
PAUSE = chr(0x23F8)  # DOUBLE VERTICAL BAR
PLAY_PAUSE = chr(0x23EF)  # BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR

FONT_FILE = "NotoSansSymbols2-Media.ttf"
POINT_SIZE = 22

_family: str | None = None


def symbol_font(point_size: float = POINT_SIZE) -> QFont:
    """The symbol font at `point_size`. Registers it with Qt on first use, so it needs a
    QApplication to exist already."""
    global _family
    if _family is None:
        data = (files("random_walk.gui") / "fonts" / FONT_FILE).read_bytes()
        font_id = QFontDatabase.addApplicationFontFromData(data)
        if font_id < 0:
            raise RuntimeError(f"could not load bundled font {FONT_FILE}")
        _family = QFontDatabase.applicationFontFamilies(font_id)[0]
    font = QFont(_family)
    font.setPointSizeF(point_size)
    return font
