# CLAUDE.md

Project notes for Claude Code. Read this first in every session.

## What this project is

An interactive 1D random walk explorer in Python. Users set RUNS, STEPS, an optional reflecting
WALL, and a SLOPE bias (theta, -90 to 90 degrees). The app shows a final-position histogram
and animated views: Distribution, Single Walk, Evolving Histogram, All Paths.

Packaged as `src/random_walk` (hatchling, Python 3.11+, MIT). The repo is at
`c:\dev\random-walk` (outside OneDrive, to avoid sync problems with git) and is hosted on
GitHub. Versioning: a fixed `version` in pyproject.toml plus git tags for milestones. Keep
`__version__` in `src/random_walk/__init__.py` in sync with it. The user runs git themselves:
suggest commands, don't commit or push.

## GUI status: being rebuilt

A completely new GUI is being built incrementally in **PySide6** (Qt 6, via the
`PySide6-Essentials` package), light theme only, following the user's sketches, kept in
`docs/sketches/GUI_<n>.pdf` (black = layout, blue boxes = the user's notes). `random-walk` /
`py -m random_walk` run `random_walk.cli.main()`, which opens it.

- Increment 1 (GUI_1, released as v0.2.0): window titled "Random Walk", title label top right,
  an empty drawing area that grows with the window, a plain-text summary box ("1000 Steps,
  10000 Times") under it on the right, and a fixed-size (640x24 px) slider 0-1000 centred
  below, with left/right buttons that jump it to its limits. Nothing is connected to the
  simulation yet.
- Slider look (user's choices): style sheet with a black track left of the handle, light grey
  (#d3d3d3) right of it, and a thin black bar handle (4x22 px, the "playhead" look). The
  handle is clipped to the widget, hence SLIDER_HEIGHT = 24. A style sheet replaces native
  drawing, so any slider styling must go in SLIDER_STYLE.
- Button symbols (⏮ U+23EE, ⏭ U+23ED, 22 pt) come from a bundled Noto Sans Symbols 2
  subset, loaded by `gui/symbols.py`. Buttons size themselves to the symbol. Rebuild the font
  with `tools/make_symbol_font.py`; keep `NotoSansSymbols2-OFL.txt` next to it.
- Increment 2 (in progress): choosing the interface font. Candidates DejaVu Sans Mono and
  Source Code Pro are bundled (Regular + Bold) in `gui/fonts/` and listed in
  `gui/ui_fonts.py`. TEMPORARY comparison aids: a "Font:" dropdown at the window's top
  left and `random-walk --font {system,dejavu,source}`. The app starts in Source Code Pro
  (`ui_fonts.DEFAULT`, the user's current preference). Once chosen, keep only that font
  (and its licence), and remove the dropdown, the --font option and the other candidates.
- Increment 3 (GUI_2): a second slider row (class `SliderRow`, an exact copy of the first) and
  centred player controls ⏪ ⏵/⏸ ⏩ below. The bottom section has its own zero-spacing
  layout so `SLIDER_GAP` (36) and `CONTROLS_GAP` (24) are the exact gaps; the window layout's
  8 px spacing is otherwise added next to `addSpacing()` gaps. Play/Pause is a plain button
  that swaps its symbol (a checkable button gets a blue highlight in the Windows 11 style),
  fixed to the wider symbol's width. It shows the combined ⏯ (`COMBINED_PLAY_PAUSE`); its
  symbol is grey (#8c8c8c) while paused, black on hover and while playing, via
  `HoverColorButton` (palette swap on enter/leave, keeping the native look). Still no
  simulation connections.
- Emoji pitfall: U+23E9/U+23EA (and a few other symbols) have emoji presentation by default,
  so Windows draws them as colour emoji regardless of the font set. Append U+FE0E
  (`symbols.TEXT_PRESENTATION`) to force the plain glyph. Check any new symbol for this.
- The user evaluates each increment before logic or GUI tests are added. Ask clarifying
  questions before each increment; don't add pytest-qt tests until asked.
- Plotting will probably use pyqtgraph (MIT); not added yet.

The previous Dear PyGui GUI is preserved on the **`ui_prototype`** branch (tag `dpg-final`),
with its own CLAUDE.md covering Dear PyGui quirks and headless testing. Use it as a reference
for features and behaviour; don't merge it back. The original single-file app also remains at
`legacy/random-walk-vibe.py` for reference only. Don't edit it or import from it.

## Layout

    random-walk/
    ├── pyproject.toml, README.md, LICENSE, CLAUDE.md
    ├── src/random_walk/
    │   ├── config.py          # DEFAULT_* values, limits, playback speeds
    │   ├── params.py          # WalkParams (frozen dataclass) + validate()
    │   ├── theory.py          # p_right, final mean/sd, normal and half-normal curves
    │   ├── simulation.py      # simulate, simulate_paths, summarize, parity_bins (numpy only)
    │   ├── playback.py        # Playback timeline state machine (no GUI imports)
    │   ├── cli.py             # entry point: imports the GUI lazily and runs it
    │   └── gui/               # PySide6 GUI: the only package that imports Qt
    │       ├── app.py         # create_app() (light scheme), run()
    │       ├── main_window.py # MainWindow: layout from the sketches
    │       ├── symbols.py     # symbol_font(), SKIP_TO_START/SKIP_TO_END
    │       ├── ui_fonts.py    # candidate interface fonts (temporary, for comparison)
    │       └── fonts/         # bundled fonts, each with its licence file
    ├── tests/                 # core only: theory, simulation, params, playback
    ├── tools/                 # font scripts: explorer (dearpygui), symbol subset builder
    │   └── fonts/             # downloaded fonts, git-ignored
    ├── docs/theory.md, docs/design-notes.md, docs/sketches/ (GUI sketches)
    └── legacy/random-walk-vibe.py

## Commands

    py -m venv .venv && .venv\Scripts\activate
    py -m pip install -e ".[dev]"          # add ,tools for the scripts in tools/
    random-walk            # or: py -m random_walk
    py -m pytest
    ruff check . && ruff format .
    py -m mypy             # optional; needs `pip install mypy`

Run the package with `-m` or the console script, never by pointing at a file inside `src/`.
Code is formatted with `ruff format` (line length 100). Use type hints throughout.

## Dependencies

numpy (>=2.0), PySide6-Essentials (>=6.8). Dev: pytest, ruff. Tools extra: dearpygui,
fonttools. Optional: mypy.

When choosing GUI libraries, check licences against the MIT project licence. PySide6 is LGPLv3
and fine as a dependency; avoid GPL-only Qt modules (Qt Charts, Qt Data Visualization,
Qt Graphs). pyqtgraph is MIT. Bundled fonts need their licence file shipped alongside.

Bundled fonts and their licences (all fine for an MIT project; none may be sold on its own):

- Noto Sans Symbols 2 (subset): SIL OFL 1.1, no Reserved Font Name, so modifying it was OK.
- DejaVu Sans Mono: Bitstream Vera licence + public domain changes (+ Arev glyphs).
  Modified versions must be renamed (no "Bitstream"/"Vera"/"Arev" in the name). Bundle
  unmodified.
- Source Code Pro: SIL OFL 1.1 with Reserved Font Name "Source" (Adobe trademark).
  Subsetting or other changes would require renaming it. Bundle unmodified.

## Physics (keep these exact)

- Step is +1 or -1. P(right) = 0.5 - 0.5*sin(theta), P(left) = 1 - P(right).
  Positive theta biases left, negative biases right.
- Wall: a step below WALL is reflected, position -> 2*WALL - position (equivalently
  WALL + abs(position - WALL)). It is NOT a clamp. The reflect rule preserves parity; clamp
  does not, and we dropped clamp deliberately.
- Parity: without a wall, or with the reflecting wall, final positions all share the parity of
  STEPS, so histogram bins are width 2. Bin width 1 leaves every other bin empty.
- Theory curve, no wall: Normal(mean = -STEPS*sin(theta), sd = sqrt(STEPS)*|cos(theta)|).
  Per-step mean is -sin(theta), per-step variance is cos^2(theta).
- At theta = +/-90 the sd is exactly 0 (computed as sqrt(STEPS*(1 - sin^2)), never via cos,
  which is ~6e-17 at 90 degrees) and `summarize()` hides the curve, with or without a wall.
- Theory curve, wall: half-normal approximation, sd = sqrt(STEPS). Valid only at theta = 0
  (reflection principle needs a driftless walk). Hidden when theta != 0.
- docs/theory.md has the derivations and the known limitations (see Open items).

## Architecture rules

- Qt code lives only in `gui/`. Nothing in the core imports Qt (`cli.py` imports the GUI
  inside `main()`); logic worth testing belongs in the core, where tests need no display.
- `simulate()`/`simulate_paths()` take an optional `rng: np.random.Generator`. Tests always
  pass a seeded one. The GUI uses the unseeded module default.
- Validate the shared parameters with `params.validate()` and pass them around as a
  `WalkParams`. Read the shared controls in one place only.
- Drive animations with `playback.Playback`: the GUI's timer calls `tick(now)` and redraws the
  frame it returns. One Playback per timeline.
- Cache simulated data per view, keyed by the `WalkParams` it came from (frozen, hashable), so
  replaying with unchanged params doesn't re-simulate.

## Testing rules

- `tests/` covers the core only and needs no display. GUI tests (pytest-qt, headless) are
  planned but on hold until the user asks; there is no CI yet.
- To check the GUI visually without a window popping up, render it invisibly with the real
  Windows platform: `widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)`, `show()`,
  process events, then `widget.grab().save(...)`. The `offscreen` platform has no fonts
  (text renders as boxes) and reports no colour scheme.
- Behaviour of the new GUI can be compared against `ui_prototype` or the legacy app by seeding
  the generator (`random_walk.simulation._default_rng = np.random.default_rng(seed)`).
- mypy: don't pin `python_version` to 3.11. numpy 2.5's stubs don't resolve for that target.

## Open items

- Continue the new GUI from the user's sketches; then add pytest-qt tests and CI (GitHub
  Actions) when the user asks.
- Planned: a seed control in the UI.
- Known physics issue (see docs/theory.md): the wall curve is a half-normal centred on the
  wall and ignores that the walk starts at 0; the folded normal phi(y) + phi(2w - y) is the
  correct large-STEPS curve at theta = 0.
- Memory: `simulate_paths` at MAX_JUMPS allocates two int64 (runs, steps) arrays (~400 MB
  each).
