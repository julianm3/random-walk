"""Browse a font's glyphs as Dear PyGui renders them, on its default dark theme.

Exploration tool only - not part of the random_walk package. Needs the `tools` extra:
`py -m pip install -e ".[tools]"` (dearpygui, fonttools). Note that Dear PyGui draws only
the fonts it loads, with no fallback; Qt-style toolkits render differently.

Every .ttf/.otf in these folders appears in the Font list:

  tools/fonts/ (git-ignored downloads for exploring)
    promptfont.ttf                PromptFont, https://github.com/Shinmera/promptfont/releases
    NotoSansSymbols2-Regular.ttf  https://github.com/google/fonts/tree/main/ofl/notosanssymbols2
  src/random_walk/gui/fonts/ (fonts bundled with the app)
    SourceCodePro-*.ttf                       the app's interface font
    NotoSansSymbols2-Media.ttf                the app's button symbols

If a font has a sidecar "<name>.glyphs.json" in PromptFont's format (from its release, renamed
from glyphs.json), names, categories and tags come from that. Otherwise glyphs are read from
the font's character map (via fontTools), named from
the Unicode database and grouped by 256-character block ("U+23xx").

    py tools/font_explorer.py

Click a glyph for its details; "Copy" puts its Python escape (e.g. "\\u23ed") on the
clipboard. The sample row shows the selected glyph on a button next to normal text buttons,
and the sample text shows the whole font at the chosen size - useful for text fonts.

Known gap in PromptFont v1.10: glyphs.json lists "Sun" (U+2600), but the font has no such
glyph, so it draws as "?". The font also has ~320 characters glyphs.json doesn't list (mostly
accented Latin letters and punctuation), which aren't shown.
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

import dearpygui.dearpygui as dpg

ROOT = Path(__file__).resolve().parent.parent
FONT_DIRS = [ROOT / "tools" / "fonts", ROOT / "src" / "random_walk" / "gui" / "fonts"]
SAMPLE_TEXT = "Random Walk   1000 Steps, 10000 Times   0123456789   Il1| O0o {}[]() +-=*/"

SIZES = [13, 16, 20, 24, 32, 48]  # px; 13 matches the app's default font
DETAIL_SIZE = 96
COLUMNS = 8
ALL = "(all)"
SKIP_CATEGORIES = {"Cc", "Cf", "Zs", "Zl", "Zp"}  # controls and spaces: nothing to see

Glyph = dict[str, Any]

font_files: dict[str, Path] = {}  # file name -> path, across FONT_DIRS
current_file: Path | None = None
fonts: dict[tuple[Path, int], int | str] = {}  # (file, size) -> loaded font
glyph_cache: dict[Path, list[Glyph]] = {}
glyphs: list[Glyph] = []
selected: Glyph | None = None


# --- glyph lists -------------------------------------------------------------------------


def sidecar(font_file: Path) -> Path:
    return font_file.with_suffix(".glyphs.json")


def glyphs_from_sidecar(path: Path) -> list[Glyph]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def glyphs_from_cmap(font_file: Path) -> list[Glyph]:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        sys.exit(f'{font_file.name} has no glyphs.json sidecar: pip install -e ".[tools]"')
    result = []
    for cp in sorted(TTFont(font_file, lazy=True).getBestCmap()):
        char = chr(cp)
        if unicodedata.category(char) in SKIP_CATEGORIES:
            continue
        result.append(
            {
                "character": char,
                "code": f"U+{cp:04X}",
                "codepoint": cp,
                "category": f"U+{cp >> 8:02X}xx",
                "name": unicodedata.name(char, f"U+{cp:04X}").title(),
                "tags": [],
            }
        )
    return result


def load_glyphs(font_file: Path) -> list[Glyph]:
    if font_file not in glyph_cache:
        side = sidecar(font_file)
        glyph_cache[font_file] = (
            glyphs_from_sidecar(side) if side.exists() else glyphs_from_cmap(font_file)
        )
    return glyph_cache[font_file]


# --- helpers -----------------------------------------------------------------------------


def font(size: int) -> int | str:
    """The current font at `size`, loaded on first use."""
    assert current_file is not None
    key = (current_file, size)
    if key not in fonts:
        fonts[key] = dpg.add_font(str(current_file), size, parent="font_registry")
    return fonts[key]


def current_size() -> int:
    return int(dpg.get_value("size_combo"))


def label(glyph: Glyph) -> str:
    """The glyph as a button label. A bare "#" would vanish: Dear PyGui appends "##<id>" to
    labels, and "###" means "hide the label" to Dear ImGui."""
    char = glyph["character"]
    return f"{char} " if char.endswith("#") else char


def py_escape(codepoint: int) -> str:
    """Python string escape for a code point: \\uXXXX, or \\UXXXXXXXX above U+FFFF."""
    return f"\\u{codepoint:04x}" if codepoint <= 0xFFFF else f"\\U{codepoint:08x}"


def matches(glyph: Glyph, category: str, query: str) -> bool:
    if category != ALL and glyph["category"] != category:
        return False
    if not query:
        return True
    words = [glyph["name"], glyph["code"], glyph.get("code-name", ""), *glyph.get("tags", [])]
    return query.lower() in " ".join(words).lower()


# --- UI updates --------------------------------------------------------------------------


def rebuild_grid() -> None:
    """Re-create the glyph table for the current font, filter and size."""
    dpg.delete_item("grid_holder", children_only=True)
    category = dpg.get_value("category_combo")
    query = dpg.get_value("search_input").strip()
    shown = [g for g in glyphs if matches(g, category, query)]
    dpg.set_value("count_text", f"{len(shown)} of {len(glyphs)} glyphs")

    size = current_size()
    cell = max(64, size + 24)
    cell_font = font(size)
    with dpg.table(parent="grid_holder", header_row=False, policy=dpg.mvTable_SizingFixedFit):
        for _ in range(COLUMNS):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=cell + 40)
        for start in range(0, len(shown), COLUMNS):
            with dpg.table_row():
                for glyph in shown[start : start + COLUMNS]:
                    with dpg.group():
                        button = dpg.add_button(
                            label=label(glyph),
                            width=cell,
                            height=cell,
                            callback=on_select,
                            user_data=glyph,
                        )
                        dpg.bind_item_font(button, cell_font)
                        dpg.add_text(glyph["code"], color=(150, 150, 150))
                        dpg.add_text(glyph["name"][:14])
                        with dpg.tooltip(button):
                            dpg.add_text(f"{glyph['name']}  ({glyph['category']})")


def show_details() -> None:
    if selected is None:
        dpg.set_item_label("detail_glyph", "")
        dpg.set_item_label("sample_glyph", "")
        for tag in ("detail_code", "detail_meta", "detail_tags"):
            dpg.set_value(tag, "")
        dpg.set_value("detail_name", "Click a glyph below")
        return
    g = selected
    dpg.set_item_label("detail_glyph", label(g))
    dpg.set_value("detail_name", g["name"])
    dpg.set_value("detail_code", f'{g["code"]}   (Python: "{py_escape(g["codepoint"])}")')
    meta = f"category: {g['category']}"
    if g.get("code-name"):
        meta += f"   code-name: {g['code-name']}"
    dpg.set_value("detail_meta", meta)
    dpg.set_value("detail_tags", "tags: " + ", ".join(g["tags"]) if g.get("tags") else "")
    dpg.set_item_label("sample_glyph", label(g))
    dpg.bind_item_font("sample_glyph", font(current_size()))


def show_sample_text() -> None:
    dpg.set_value("sample_text", SAMPLE_TEXT)
    dpg.bind_item_font("sample_text", font(current_size()))


def select_font(font_file: Path) -> None:
    global current_file, glyphs, selected
    current_file = font_file
    glyphs = load_glyphs(font_file)
    selected = None
    categories = [ALL, *sorted({g["category"] for g in glyphs})]
    dpg.configure_item("category_combo", items=categories)
    dpg.set_value("category_combo", ALL)
    dpg.set_value("font_combo", font_file.name)
    dpg.bind_item_font("detail_glyph", font(DETAIL_SIZE))
    dpg.set_viewport_title(f"Font explorer - {font_file.name}")
    rebuild_grid()
    show_details()
    show_sample_text()


# --- callbacks ---------------------------------------------------------------------------


def on_font_changed(sender: Any, app_data: str, user_data: Any) -> None:
    select_font(font_files[app_data])


def on_select(sender: Any, app_data: Any, user_data: Glyph) -> None:
    global selected
    selected = user_data
    show_details()


def on_size_changed() -> None:
    rebuild_grid()
    show_details()
    show_sample_text()


def on_copy() -> None:
    if selected is not None:
        dpg.set_clipboard_text(py_escape(selected["codepoint"]))


# --- assembly ----------------------------------------------------------------------------


def find_fonts() -> dict[str, Path]:
    found = [p for d in FONT_DIRS for p in d.glob("*") if p.suffix.lower() in (".ttf", ".otf")]
    return {p.name: p for p in sorted(found, key=lambda p: p.name.lower())}


def build_ui() -> None:
    """Create the context, viewport and widgets (no render loop)."""
    font_files.clear()
    font_files.update(find_fonts())
    dpg.create_context()
    dpg.add_font_registry(tag="font_registry")
    dpg.create_viewport(title="Font explorer", width=1150, height=850)

    with dpg.window(tag="primary"):
        with dpg.group(horizontal=True):
            dpg.add_text("Font")
            dpg.add_combo(
                list(font_files),
                tag="font_combo",
                width=230,
                callback=on_font_changed,
            )
            dpg.add_text("Category")
            dpg.add_combo(
                [ALL], default_value=ALL, tag="category_combo", width=100, callback=rebuild_grid
            )
            dpg.add_text("Search")
            dpg.add_input_text(
                tag="search_input", width=160, callback=rebuild_grid, hint="name, tag or U+code"
            )
            dpg.add_text("Size")
            dpg.add_combo(
                [str(s) for s in SIZES],
                default_value=str(SIZES[0]),
                tag="size_combo",
                width=60,
                callback=on_size_changed,
            )
            dpg.add_text("", tag="count_text")
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_button(
                label="", tag="detail_glyph", width=DETAIL_SIZE + 24, height=DETAIL_SIZE + 24
            )
            with dpg.group():
                dpg.add_text("", tag="detail_name")
                dpg.add_text("", tag="detail_code")
                dpg.add_text("", tag="detail_meta")
                dpg.add_text("", tag="detail_tags", wrap=700)
                dpg.add_button(label="Copy Python escape", callback=on_copy)
                dpg.add_spacer(height=6)
                dpg.add_text("Sample row (app's default font + selected glyph at chosen size):")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Fast Fwd")
                    dpg.add_button(label="Step Fwd")
                    dpg.add_button(label="", tag="sample_glyph")
                    dpg.add_text("  speed")
        dpg.add_text("Sample text (selected font at chosen size):")
        dpg.add_text("", tag="sample_text")
        dpg.add_separator()

        with dpg.child_window(tag="grid_holder", border=False):
            pass

    select_font(next(iter(font_files.values())))
    dpg.set_primary_window("primary", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()


def main() -> None:
    if not find_fonts():
        sys.exit("No .ttf/.otf fonts found - see this script's docstring.")
    build_ui()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
