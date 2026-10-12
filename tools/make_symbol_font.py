"""Build src/random_walk/gui/fonts/NotoSansSymbols2-Media.ttf from the full Noto font.

    py tools/make_symbol_font.py [path/to/NotoSansSymbols2-Regular.ttf]

The source defaults to tools/fonts/NotoSansSymbols2-Regular.ttf (git-ignored; from
https://github.com/google/fonts/tree/main/ofl/notosanssymbols2). Needs the `tools` extra
(fontTools). The output is bundled with the PySide6 GUI (loaded by gui/symbols.py) together
with the font's licence, gui/fonts/NotoSansSymbols2-OFL.txt (copy it from tools/fonts/ if
missing).

Two changes from the original, both permitted by its SIL Open Font License (which declares no
Reserved Font Name):

1. Subset to the transport symbols only (U+23E9-U+23EF, U+23F4-U+23FA), about 6 KB.
2. Tighten the vertical metrics to a band around those symbols. The original line (-630 to
   1069 units) is ~3x taller than the symbols (70 to 606), so toolkits that centre a text
   line in a button (Dear ImGui did; Qt does too) place the symbols off-centre or need an
   oversized button. With the line hugging the symbols, they centre in a normal button.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "tools" / "fonts" / "NotoSansSymbols2-Regular.ttf"
OUTPUT = ROOT / "src" / "random_walk" / "gui" / "fonts" / "NotoSansSymbols2-Media.ttf"

UNICODES = [*range(0x23E9, 0x23EF + 1), *range(0x23F4, 0x23FA + 1)]
MARGIN = 0.12  # padding above and below the symbols, as a fraction of their height


def symbol_band(font: TTFont) -> tuple[int, int]:
    """The lowest yMin and highest yMax over every glyph the font maps."""
    glyf = font["glyf"]
    glyphs = [glyf[name] for name in font.getBestCmap().values()]
    return min(g.yMin for g in glyphs), max(g.yMax for g in glyphs)


def tighten_metrics(font: TTFont) -> tuple[int, int]:
    y_min, y_max = symbol_band(font)
    pad = round((y_max - y_min) * MARGIN)
    ascent, descent = y_max + pad, y_min - pad  # descent may be positive: the band is all
    hhea, os2 = font["hhea"], font["OS/2"]  # above the baseline, which is fine
    hhea.ascent, hhea.descent, hhea.lineGap = ascent, descent, 0
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = ascent, descent, 0
    os2.usWinAscent, os2.usWinDescent = max(ascent, 0), max(-descent, 0)
    return ascent, descent


def main() -> None:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not source.exists():
        sys.exit(f"Source font not found: {source} - see this script's docstring.")

    font = TTFont(source)
    subsetter = subset.Subsetter(subset.Options())
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    ascent, descent = tighten_metrics(font)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    font.save(OUTPUT)

    mapped = " ".join(f"U+{cp:04X}" for cp in sorted(font.getBestCmap()))
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size:,} bytes)")
    print(f"  line: ascent {ascent}, descent {descent} (was 1069, -630)")
    print(f"  glyphs: {mapped}")


if __name__ == "__main__":
    main()
