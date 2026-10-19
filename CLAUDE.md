# CLAUDE.md

Project notes for Claude Code. Read this first in every session.

## What this project is

An interactive 1D random walk explorer in Python. The user picks how many steps and trials to
animate, an optional reflecting WALL, and the left/right bias as the probability of stepping
right. A minimalist UI switches between two animation modes:

- **Steps**: all the chosen trials advance step by step, showing the evolving step density and
  histogram (the animation implemented in v0.2.5).
- **Trials**: the histogram of final positions grows as trials are added one by one.

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
  10000 Trials") under it on the right, and a fixed-size (640x24 px) slider 0-1000 centred
  below, with left/right buttons that jump it to its limits. Nothing is connected to the
  simulation yet.
- Slider look (user's choices): style sheet with a 1 px track (`SLIDER_TRACK_WIDTH`), black
  left of the handle, light grey (#d3d3d3) right of it, and a thin black bar handle (4 px wide,
  23 px tall = track + 2 x `SLIDER_HANDLE_OVERHANG`, the "playhead" look). The handle is
  clipped to the widget, hence SLIDER_HEIGHT = 24. A style sheet replaces native drawing, so
  any slider styling must go in SLIDER_STYLE.
- Animation (Play/Pause): `MainWindow.play()/pause()` drive the core `Playback` (1001 frames,
  "real time" 30 steps/s, ~33 s) from a `QTimer` (`TICK_MS` 15) that runs only while playing.
  Each frame shows `ANIMATION_DRAWING` (Overlay 4) with `at_step` = the current step. The
  position and step axes stay still; the probability axis top follows the theory peak
  continuously (`Drawing.probability_from_theory`: top = peak x (1 + `THEORY_HEADROOM` 0.18),
  not rounded; ticks are the round values below it), so the bell keeps a constant height
  (peak at 85% of the axis) and the tick labels slide instead. Tried and rejected: sizing from
  the tallest bar (flickered as bar noise crossed tick boundaries) and rounding the theory-
  based top to a tick (bars popped by ~15% at each of 23 changes). 0.18 is the smallest
  headroom with no clipped bar (worst: 17% above the curve, step 975). The first frame is drawn
  before the clock starts (it counts the density grid) so no steps are skipped. The Steps
  slider (0-1000) follows the animation (updated with signals blocked) and moving it, or its
  jump buttons, pauses and shows that step; choosing a drawing pauses too. Trials slider:
  0-10,000, starts at 10,000, not connected. Fast reverse/forward not connected. Density
  images are cached for the last `DENSITY_CACHE_SIZE` (4) steps only.
- Slider labels: "Steps" (top row) and "Trials" (bottom), `SLIDER_LABELS`, 8 pt, right-aligned
  left of each row's first button. `SliderRow` mirrors the label with an equal invisible
  spacer on the right so the centred sliders don't move; both labels share the widest's
  width so the rows align. This raised the minimum window width from 796 to 892 px.
- Button symbols (⏮ U+23EE, ⏭ U+23ED, 22 pt) come from a bundled Noto Sans Symbols 2
  subset, loaded by `gui/symbols.py`. Buttons size themselves to the symbol. Rebuild the font
  with `tools/make_symbol_font.py`; keep `NotoSansSymbols2-OFL.txt` next to it.
- Interface font: Source Code Pro (chosen after comparing it with DejaVu Sans Mono and the
  system font), bundled Regular + Bold in `gui/fonts/`. `gui/ui_fonts.py` registers it;
  `ui_fonts.ui_font(size)` gives it at a size and `MainWindow.apply_fonts()` applies it
  everywhere (the symbol buttons keep Noto). The comparison dropdown, the `--font` option and
  DejaVu Sans Mono were removed; the CLI now has just `--help` and `--version`.
- Increment 3 (GUI_2): a second slider row (class `SliderRow`, an exact copy of the first) and
  centred player controls ⏪ ⏵/⏸ ⏩ below. The bottom section has its own zero-spacing
  layout so the gap constants are the exact gaps; the window layout's
  8 px spacing is otherwise added next to `addSpacing()` gaps. Play/Pause is a plain button
  that swaps its symbol (a checkable button gets a blue highlight in the Windows 11 style),
  fixed to the wider symbol's width. It shows the combined ⏯ (`COMBINED_PLAY_PAUSE`); its
  symbol is grey (#8c8c8c) while paused, black on hover and while playing, via
  `HoverColorButton` (palette swap on enter/leave, keeping the native look). Still no
  simulation connections.
- Increment 4 (sketch `customControl.pdf`): `gui/position_selector.py` - `PositionSelector`,
  a custom-painted row of N circles (default 3) joined by a line; the selected one has a dot
  half the diameter that slides between positions (QVariantAnimation, 180 ms). All black,
  transparent circles, no hover effect. Select by clicking a circle or its label only (no
  drag, no keyboard). Constructor parameters: labels, diameter, spacing (edge-to-edge,
  a minimum: widened so the widest label fits, keeping all gaps equal), label_gap. Emits
  `currentIndexChanged(int)`. In the window its labels are "Walk", "Trials", "Both"
  (`SELECTOR_LABELS`). Placed between the summary box and the top slider.
- Vertical spacing below the drawing area: summary box (8 px under it, via the window
  layout), then summary, selector, two slider rows and player controls in one zero-spacing
  layout with exact gaps, all `CONTROL_GAP` = 12 px except `SELECTOR_TOP_GAP` = 18 (no
  internal padding there), giving visibly even gaps of about 18-22 px. Bottom margin 24 px.
- Increment 5: data and drawing. At startup `MainWindow.generate_data()` simulates the default
  set (10,000 trials x 1000 steps, no wall) with the seeded default generator. `gui/walk_view.py`
  (`WalkView`, a QFrame replacing the empty drawing area) draws the first N trials
  (`set_walk_count()`; default 1), each in its own colour (`WALK_COLORS`: black, then the colour-blind-safe Okabe-Ito
  palette; trial 1 drawn last so it's on top), bottom (step 0) to top
  (last step). x spans the whole set's min..max position over all trials and steps (wider
  than the final positions' range); both axes stretch to the plot area, rescaling on resize.
  `walk_points()` does the scaling.
- Axes (black, 1 px, labels 8 pt via `AXIS_POINT_SIZE`): x along the bottom of the walk area
  (position; step 0 sits on it), ticks down; y up the left side (step 0 to the last step),
  ticks left, labels right-aligned. The walk area shrinks to fit both axes' labels. Tick
  values come from the core module `ticks.py` (`nice_ticks()`: steps of 1/2/5 x 10^n,
  tested in tests/test_ticks.py), thinned to keep x ticks >= `MIN_TICK_SPACING` (65 px;
  gives every 20 at the default size) and y ticks >= `MIN_Y_TICK_SPACING` (40 px) apart.
- TEMPORARY drawing selector: a "Drawing:" dropdown at the window's top left switches what the
  drawing area shows. `DRAWINGS` in main_window.py maps entries to `walk_view.Drawing`s:
  "Draw 1" (default) and "Draw 5" (first N walks), "Full Histogram", "Overlay 1" (histogram
  behind the first walk, both side axes shown), "Overlay 2" (the first 200 walks over a
  histogram of just those walks' final positions, shares in multiples of 0.005), "Overlay 3"
  (density image of all 10,000 walks with the full histogram), "Overlay 4" (Overlay 3 at
  step 50 - `at_step=50`: density only up to step 50, histogram of the positions there,
  same step and x axes; the probability axis fits that histogram, 0-0.12).
  In Overlays 2-4 the bars are light
  grey at `OVERLAY_BAR_OPACITY` (0.6) in front, so the walks or density show through. Overlay
  2's walks are all in the density grey (`DENSITY_DARKEST`) at `OVERLAY_WALK_OPACITY` (0.25), so
  overlaps build up darker like the density shading. A `Drawing` has independent `density`,
  `walks` and `histogram` parts, plus `histogram_from_walks` (count only the drawn walks),
  `histogram_color` (default light grey), `histogram_opacity` (default 1), `walk_color`
  (default: one palette colour per walk), `walk_opacity` (default 1), `at_step` (show the
  set as it stood at that step; default the last) and
  `histogram_in_front` (default behind); the axes
  are always painted last. `MainWindow.set_drawing()`
  applies one. Remove it once the drawing choices are settled.
- Full Histogram: final positions of all trials in width-2 parity bins (`parity_bins`,
  `fractions_at`), light grey bars (#d3d3d3, 1 px gaps) whose heights are each bin's share of
  the trials (sum 1). The left step axis is hidden; a probability axis on the right runs from
  0 to the first round value above the tallest bar (or the theory curve's peak). Full
  Histogram, Overlay 3 and Overlay 4 also show the theory curve (`Drawing.theory`, for the
  shown step - so Overlay 4's is the step-50 curve): a 1 px light red (#F08080) line,
  the normal density (mean -n sin(theta), sd sqrt(n)|cos(theta)|, from theory.py) times the
  bin width 2, so it matches the bars' per-bin probabilities; `set_paths()` takes the
  simulation's theta for it. Room for both side axes is always
  reserved (the right side: the wider of the full histogram's labels and the current
  drawing's), so the plot (and every x position) is identical in every drawing.
- Density image (Overlay 3): `simulation.density_grid()` counts walks per (step, 2-wide
  position bin) - 1001 x 130 for the default set, ~0.1 s once, one column of paths at a time
  to keep memory low - and `normalize_rows()` scales each step to its own busiest cell (raw
  counts run from 10,000 at step 0 to ~275 at step 1000). `WalkView.density_image()` turns
  it into a cached greyscale QImage (background to `DENSITY_DARKEST` #222222, short of
  black; shade raised to `DENSITY_GAMMA` 0.3 so sparse cells show - both the user's choice),
  drawn stretched with nearest-neighbour scaling:
  ~5 ms per repaint. Use this, not thousands of polylines (~3-4 s), for many walks.
- Drawing performance: never build QPolygonF from per-point QPointF objects (~1 us each; 200
  walks took ~290 ms per repaint). `walk_view.polygon_from_arrays()` fills the polygon's
  storage through a numpy view (shiboken6 VoidPtr, as pyqtgraph does), ~100x faster, with a
  per-point fallback; Overlay 2 repaints in ~70 ms, mostly Qt's own line drawing.
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
    │   ├── ticks.py           # nice_ticks(): round-number axis ticks (no GUI imports)
    │   ├── cli.py             # entry point: imports the GUI lazily and runs it
    │   └── gui/               # PySide6 GUI: the only package that imports Qt
    │       ├── app.py         # create_app() (light scheme), run()
    │       ├── main_window.py # MainWindow: layout from the sketches
    │       ├── symbols.py     # symbol_font(), SKIP_TO_START/SKIP_TO_END
    │       ├── ui_fonts.py    # the interface font (Source Code Pro)
    │       ├── position_selector.py  # PositionSelector custom widget
    │       ├── walk_view.py   # WalkView: the drawing area, plots walks
    │       └── fonts/         # bundled fonts, each with its licence file
    ├── tests/                 # core only: theory, simulation, params, playback, ticks
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
  pass a seeded one. The module default is seeded with `config.DEFAULT_SEED` (42), so the app
  sees the same data every launch; tests must not rely on the default's sequence.
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

## Next steps (agreed 2026-10-19; build in this order, one increment each)

The data set stays fixed at 10,000 trials x 1000 steps; the sliders choose subsets of it, and
Regenerate changes only the seed and P(right).

1. **Bias probability.** Replace the slope theta with p = P(right) throughout the core
   (theory.py, simulation.py, params.py, config.py `DEFAULT_SLOPE`, `WalkView.set_paths(theta=)`),
   the tests and docs/theory.md. New physics: step +1 with probability p, -1 with 1 - p; per-step
   mean 2p - 1, variance 4p(1 - p); theory Normal(mean = n(2p - 1), sd = sqrt(4p(1 - p) n)).
   NOTE the sign: p > 0.5 drifts right (positive theta drifted left). At p = 0 or 1 the sd is
   exactly 0: hide the theory curve (as at theta = +/-90 now). Rewrite the Physics section.
2. **Selector modes and slider limits.** Selector becomes two positions, "Steps" and "Trials"
   (remove "Both"; "Walk" -> "Steps").
   - Steps mode = the current animation. The Steps slider sets the END step (at 250 the
     animation runs steps 0 -> 250); the Trials slider sets how many trials take part (the
     first N of the 10,000).
   - Trials mode: the Steps slider is locked at 1000 and the Trials slider goes to 0; Play
     grows the final-position histogram from 0 to 10,000 trials in about 30 s (~11 trials per
     frame at 30 fps). No step data in this view. The legend (step 5) updates per trial.
   - Then remove the temporary Drawing dropdown and the static drawings it lists.
3. **Step controls and keyboard.** Fast reverse/forward become Step Back / Step Forward, using
   the small triangles U+23F4 / U+23F5 (already in the bundled symbol font); the slider rows keep
   their jump buttons. A "step" is one step in Steps mode and one trial in Trials mode. Space
   toggles Play/Pause, handled at window level so a focused button can't swallow it. Left/Right
   arrows step back/forward one; holding a key repeats at the system's key auto-repeat rate.
4. **Exact slider values.** Right-click either slider to type the number of steps or trials.
5. **Display-area right-click menu.**
   - Wall on/off, default -30; wall position from -120 (fixed minimum) to -1. Hide the theory
     curve while the wall is on.
   - Legend on/off: current MEAN and sd vs. the theoretical values; disabled while the wall is on.
   - Regenerate...: a dialog with a seed field and a P(right) slider, 0-100% in 1% steps,
     default 50%; P(left) = 1 - P(right).

### Open decisions (ask the user when the step comes up)

- **Step progress in Steps mode** (step 2): with the Steps slider now marking the end, show the
  current step by (a) the summary box counting up, e.g. "Step 137 of 250, 10000 Trials"
  (suggested), (b) a marker on the Steps slider track, or (c) moving the handle during playback
  and returning it to the chosen end afterwards.
- **Trials-mode pacing** (step 2): (a) constant ~11 trials per frame, or (b) start at 1 trial per
  frame and speed up, still ~30 s overall, so the early sparse histogram can be watched.
- **Wall changes** (step 5): a wall changes the walks, so re-simulating is needed (~1 s). Do it
  automatically on toggling/moving the wall, or only on Regenerate?
- **Summary box**: whether its text follows the sliders.

### Ways of working

- The increments above are ticket-shaped (scope, acceptance criteria, dependencies). Steps 1 and
  2 must go in order; after 2, steps 3-5 are independent. The user is interested in a
  ticket/multi-agent workflow: plan tickets first; work mainly in sequence, with agents for side
  work (code review, pytest-qt tests, docs) and possibly parallel worktrees for steps 3-4.
  Nearly every step edits main_window.py, so parallel work risks merge conflicts.

## Open items
- Memory: `simulate_paths` at MAX_JUMPS allocates two int64 (runs, steps) arrays (~400 MB
  each).
- Remove Drawing pulldown when no longer needed