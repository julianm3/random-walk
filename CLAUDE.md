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
  simulation yet. (The summary box was removed in v0.3.1, at the user's request.)
- Slider look (user's choices): style sheet with a 1 px track (`SLIDER_TRACK_WIDTH`), black
  left of the handle, light grey (#d3d3d3) right of it, and a thin black bar handle (4 px wide,
  23 px tall = track + 2 x `SLIDER_HANDLE_OVERHANG`, the "playhead" look). The handle is
  clipped to the widget, hence SLIDER_HEIGHT = 24. A style sheet replaces native drawing, so
  any slider styling must go in SLIDER_STYLE.
- Animation modes (v0.3.1), picked by the selector ("Steps", "Trials"; `set_mode()`). Each
  mode has its own core `Playback`, driven by one `QTimer` (`TICK_MS` 15) that runs only
  while playing; `MainWindow.playback` is the current mode's. Switching modes pauses and
  restores that mode's sliders and position (Steps: the playhead in `step_playback` and
  `steps_trials`; Trials: `trials_shown`). Play at the end replays from the start.
- Step controls and keyboard (v0.3.2). The buttons either side of Play/Pause are Step Back /
  Step Forward (`step_by()`), keeping the ⏪/⏩ symbols (the user's choice over U+23F4/5;
  `symbols.STEP_BACK/STEP_FORWARD`). A step is one step in Steps mode and one trial in Trials
  mode: it moves `playhead_slider` (Steps or Trials slider), whose handler pauses and shows
  it, so stepping while playing pauses first; it stops at the ends. Held, the buttons repeat
  at the keyboard's delay and rate (`keyboard_repeat()`: Qt's
  `keyboardAutoRepeatRateF`, 32/s here; the delay from Windows' SPI_GETKEYBOARDDELAY, 500 ms
  here). Keys (`KEY_ACTIONS`): Space play/pause (repeats ignored), Left/Right step (repeat
  while held), Home/End jump like the ⏮/⏭ buttons. `MainWindow.eventFilter`, installed on
  the QApplication, takes them before any widget (a focused button would take Space, a
  focused slider the arrows), swallows the releases too (a button clicks on Space release),
  and leaves them alone with Ctrl/Alt/Meta or when a QLineEdit/QAbstractSpinBox has focus
  (for step 4's typed values).
  - Steps mode (`STEPS_DRAWING`, `show_step()`): the Steps slider (0-1000) is the PLAYHEAD,
    as in v0.2.5: it follows playback (signals blocked), and moving it or its jump buttons
    pauses and shows that step. It starts at 1000 (the whole run); Play always runs to step
    1000 at 30 steps/s, from 0 again if at the end. The Trials slider (0-10,000, starts at
    10,000) is the number N of first trials taking part (`Drawing.trials`); moving it pauses.
    Tried and rejected (the user, after trying it): the Steps slider as the END step of a
    shorter run - it lost the playhead, and nothing showed the current step. The step and x
    axes stay still. The density is recounted
    per N (`density_grid` on paths[:N], up to ~85 ms); while the Trials slider is dragged
    `WalkView.hold_density` keeps the last count and it recounts on release.
  - Probability axis in Steps mode (`probability_from_theory`): top = max(theory peak x
    (1 + `THEORY_HEADROOM` 0.18), tallest bar), not rounded; ticks are the round values below
    it. At N = 10,000 the theory term always wins, so the bell keeps a constant height (peak
    at 85% of the axis) and the tick labels slide; at small N the axis follows the tallest
    bar (some jumping, nothing clipped - the user's choice). Tried and rejected for 10,000:
    sizing from the tallest bar alone (flickered) and rounding the theory-based top to a tick
    (bars popped ~15% at each of 23 changes). 0.18 is the smallest headroom with no clipped
    bar (worst: 17% above the curve, step 975).
  - Trials mode (`TRIALS_DRAWING`, `show_trials()`): the Steps slider sets the step S whose
    positions are counted (`trials_step`, starts at 1000; v0.3.3 - it was locked at 1000
    before, the user wanted e.g. "40 trials at 250 steps"). Moving it pauses and redraws;
    the theory curve and axis are for step S. The Trials slider is the playhead: it starts
    at 0, follows playback (signals blocked) and scrubs; Play always continues to 10,000
    (the user chose this over making it an end count, which would lose the playhead).
    Play grows the histogram to 10,000 trials in `TRIALS_PLAY_SECONDS` (30 s)
    = `TRIAL_FRAMES` (900) frames, paced by `pacing.TrialRamp` (core, tested): count(f) =
    (e^(kf) - 1)/k, k ~ 0.0042, so 1 trial a frame at first, ~600 after 10 s, ~40 a frame at
    the end (the user chose this over a constant ~11/frame). Scrubbing uses
    `Playback.seek(ramp.frame_for(k))` to resume exactly there. The probability axis is fixed
    to the histogram of all 10,000 trials at step S and its theory peak
    (`probability_from_full`, `WalkView._all_fractions_at`; 0-0.03 at step 1000, 0-0.055 at
    250), so early bars are cut off at the top (the user's choice, as in the old prototype).
  - The first frame is drawn before the clock starts (it may count the density grid), so no
    steps are skipped. Density images are cached for the last `DENSITY_CACHE_SIZE` (4)
    (trials, step) pairs only.
- Wall (v0.3.4). Right-click the drawing area for a menu (`_show_drawing_menu`; for now just
  "Wall..."). `gui/dialogs.py` `WallDialog`: "Wall on" checkbox, Position spin box
  (`MIN_WALL` -120 to `MAX_WALL` -1, default -30; disabled while off), the grey note
  "(Regenerates animation data)" (`REGENERATES_NOTE`, the user's wording), OK/Cancel - one
  dialog so on + position regenerate once (the user may add more there later). No dragging
  the wall (the user's decision). OK calls `MainWindow.regenerate(params)`: pauses, swaps
  `self.params` (a `WalkParams`, now with `seed`), and re-simulates only if `_data_key`
  changed (a new position while the wall is off just gets stored), with a wait cursor;
  both modes keep their slider positions. `generate_data()` uses a fresh
  `np.random.default_rng(params.seed)` (seed 42 = the same start-up data as before).
  Regenerating with the wall takes ~0.53 s including the first density image.
  - `simulate_paths` builds positions step-major and returns the transposed view (Fortran
    order): the wall loop reads contiguous rows, 0.8 -> 0.4 s, values identical (tested
    against a step-by-step reference); no wall stays 0.3 s (cumsum through the transposed
    view; a contiguous copy took 0.6 s). paths[:, k] is now contiguous, so the density
    grid dropped from ~130 to ~50 ms. The random draws (`choice`) are ~0.25 s of it; a faster
    draw would change the seeded data, so it was left.
  - `WalkView.set_paths(..., wall=)`: the theory curve is hidden while the wall is on; the
    x range starts `WALL_MARGIN` (6, even so the 2-wide density columns start at the wall)
    positions left of it; a 1 px grey (`WALL_COLOR` #8c8c8c) vertical line is drawn at
    wall - 1, the left edge of the lowest bar (the bin centred on the wall), not through it.
  - Probability axis without a theory curve (wall on, step 0, p = 0 or 1) in Steps mode:
    top = the tallest bar from this step to the last x (1 + `BAR_HEADROOM` 0.05)
    (`WalkView.tallest_from()`, a suffix max of each step's tallest bar, taken from the
    density count - at one step every walk shares a parity, so each 2-wide cell is one
    bin). It only shrinks as a run plays forward: no flicker, nothing cut off, the same
    when scrubbing. The user agreed to "follow the tallest bar but only grow"; that would
    have stuck at step 0's 100% bar, so the shrinking form was built instead (to be tuned
    after trying it). Trials mode keeps its rule (all trials at the step).
- Legend (v0.3.5): checkable "Legend" in the drawing menu (`set_legend`, `legend_on`, OFF at
  start-up). With the wall on it still shows steps, trials, mean and sd, but no theory
  values (`legend_lines(..., with_theory=False)`; the theory is for no wall) - the user's
  choice, replacing the plan's "greyed out and hidden while the wall is on".
  `Drawing.legend` draws a box at the plot's top-RIGHT (the user moved it from top-left;
  `LEGEND_INSET` 6, `LEGEND_PADDING` 4, 1 px `LEGEND_BORDER_COLOR` #8c8c8c, window-colour
  background at `LEGEND_OPACITY` 0.85) with three monospaced lines, the step and trial
  numbers first (the user asked for them):
      steps     250  trials      40
      mean    -3.60  theory    0.00
      sd      15.20  theory   15.81
  for the counted trials at the current step (Steps mode) or the trials so far at the chosen
  step (Trials mode), every frame (~0.08 ms). Core: `simulation.legend_stats()` (step,
  trials = number of positions, population sd as `position_stats`; None with nothing
  counted) and `legend_lines()` ("-" for no value, never "-0.00"), both tested.
- Exact values (v0.3.3): right-click either slider, in either mode (it pauses), to open
  `ValueEditor`, a frameless Popup QSpinBox (no arrows) just above the handle
  (`EDITOR_GAP` 2 px), sized to the widest number, holding the value with the text selected.
  Enter moves the slider there (`setValue`, so its handlers run as if dragged); Esc or a
  click outside closes it unchanged; its validator refuses numbers out of range. While it's
  open the key filter leaves Space/arrows/Home/End to it (focus is in its QLineEdit).
  `SliderRow.edit_value()` opens it; `set_mode()` also moves the selector, so modes set
  from code show there.
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
  `currentIndexChanged(int)`. In the window its labels are "Steps", "Trials"
  (`SELECTOR_LABELS`, mode indexes `STEPS_MODE`/`TRIALS_MODE`). Placed between the drawing
  area and the top slider.
- Vertical spacing below the drawing area: selector, two slider rows and player controls in
  one zero-spacing layout with exact gaps, all `CONTROL_GAP` = 12 px except
  `SELECTOR_TOP_GAP` = 18 (drawing area -> selector, including the window layout's
  `WINDOW_SPACING` 8; no internal padding there), giving visibly even gaps of about 18-22 px.
  Bottom margin 24 px.
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
- `walk_view.Drawing` describes what the drawing area shows: independent `density`, `walks`
  and `histogram` parts, plus `trials` (count only the first N trials for the density and
  histogram; default all), `histogram_color` (default light grey), `histogram_opacity`
  (default 1), `walk_color` (default: one palette colour per walk), `walk_opacity` (default
  1), `at_step` (show the set as it stood at that step; default the last),
  `histogram_in_front` (default behind), `theory`, `probability_from_theory` and
  `probability_from_full`; the axes are always painted last. Steps mode's bars are light grey
  at `OVERLAY_BAR_OPACITY` (0.6) in front, so the density shows through. The temporary
  "Drawing:" dropdown and its static drawings (walks, overlays) were removed in v0.3.1;
  walk drawing (`walks`, `set_walk_count()`) is kept in WalkView though no mode uses it.
- Histogram: positions of the counted trials in width-2 parity bins (`parity_bins`,
  `fractions_at`), light grey bars (#d3d3d3, 1 px gaps) whose heights are each bin's share of
  the trials (sum 1). Without walks or density the left step axis is hidden; a probability
  axis on the right runs from 0 to the first round value above the tallest bar (or the
  theory curve's peak) unless a `probability_from_*` rule applies. Both modes also show the
  theory curve (`Drawing.theory`, for the shown step): a 1 px light red (#F08080) line,
  the normal density (mean n(2p - 1), sd sqrt(4p(1 - p) n), from theory.py) times the
  bin width 2, so it matches the bars' per-bin probabilities; `set_paths()` takes the
  simulation's p_right for it. Room for both side axes is always
  reserved (the right side: the wider of the full histogram's labels and the current
  drawing's), so the plot (and every x position) is identical in every drawing.
- Density image (Steps mode): `simulation.density_grid()` counts walks per (step, 2-wide
  position bin) - 1001 x 130 for the default set, ~50 ms per N, one column of paths at a time
  to keep memory low - and `normalize_rows()` scales each step to its own busiest cell (raw
  counts run from 10,000 at step 0 to ~275 at step 1000). `WalkView.density_image()` turns
  it into a cached greyscale QImage (background to `DENSITY_DARKEST` #222222, short of
  black; shade raised to `DENSITY_GAMMA` 0.3 so sparse cells show - both the user's choice),
  drawn stretched with nearest-neighbour scaling:
  ~5 ms per repaint. Use this, not thousands of polylines (~3-4 s), for many walks.
- Drawing performance: never build QPolygonF from per-point QPointF objects (~1 us each; 200
  walks took ~290 ms per repaint). `walk_view.polygon_from_arrays()` fills the polygon's
  storage through a numpy view (shiboken6 VoidPtr, as pyqtgraph does), ~100x faster, with a
  per-point fallback; 200 translucent walks repainted in ~70 ms, mostly Qt's own line drawing.
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
    │   ├── theory.py          # final mean/sd for p_right, normal and half-normal curves
    │   ├── simulation.py      # simulate, simulate_paths, summarize, parity_bins (numpy only)
    │   ├── playback.py        # Playback timeline state machine (no GUI imports)
    │   ├── ticks.py           # nice_ticks(): round-number axis ticks (no GUI imports)
    │   ├── pacing.py          # TrialRamp: Trials mode's slow-then-fast trial counts
    │   ├── cli.py             # entry point: imports the GUI lazily and runs it
    │   └── gui/               # PySide6 GUI: the only package that imports Qt
    │       ├── app.py         # create_app() (light scheme), run()
    │       ├── main_window.py # MainWindow: layout from the sketches
    │       ├── symbols.py     # symbol_font(), SKIP_TO_START/SKIP_TO_END
    │       ├── ui_fonts.py    # the interface font (Source Code Pro)
    │       ├── position_selector.py  # PositionSelector custom widget
    │       ├── walk_view.py   # WalkView: the drawing area, plots walks
    │       ├── dialogs.py     # WallDialog (right-click menu dialogs)
    │       └── fonts/         # bundled fonts, each with its licence file
    ├── tests/                 # core only: theory, simulation, params, playback, ticks, pacing
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

- Step is +1 with probability p = P(right) (`p_right`, 0 to 1, default 0.5), -1 with
  P(left) = 1 - p. p > 0.5 drifts right, p < 0.5 drifts left. (v0.3.0 replaced the old slope
  angle theta, P(right) = 0.5 - 0.5 sin(theta); p = 0.5 draws the same walks as theta = 0.)
- Wall: a step below WALL is reflected, position -> 2*WALL - position (equivalently
  WALL + abs(position - WALL)). It is NOT a clamp. The reflect rule preserves parity; clamp
  does not, and we dropped clamp deliberately.
- Parity: without a wall, or with the reflecting wall, final positions all share the parity of
  STEPS, so histogram bins are width 2. Bin width 1 leaves every other bin empty.
- Theory curve, no wall: Normal(mean = STEPS*(2p - 1), sd = sqrt(4p(1 - p)*STEPS)).
  Per-step mean is 2p - 1, per-step variance is 4p(1 - p).
- At p = 0 or 1 the sd is exactly 0 (the walk is deterministic, ending at -/+STEPS), and
  `summarize()` and `WalkView.theory_curve()` hide the curve, with or without a wall.
- Theory curve, wall: half-normal approximation, sd = sqrt(STEPS). Valid only at p = 0.5
  (reflection principle needs a driftless walk). `summarize()` hides it when p != 0.5; the
  GUI (`WalkView.theory_curve()`) hides the curve whenever the wall is on (agreed plan).
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

1. **Bias probability.** DONE in v0.3.0: `p_right` (float, 0 to 1) replaced theta in the
   core, GUI, tests and docs. Unused DPG-era config constants were removed at the same time.
2. **Selector modes and slider limits.** DONE in v0.3.1 (see "Animation modes" above): Steps
   and Trials modes, summary box and temporary Drawing dropdown removed. The legend (step 5)
   should update per trial in Trials mode.
3. **Step controls and keyboard.** DONE in v0.3.2 (see "Step controls and keyboard" above),
   plus Home/End.
4. **Exact slider values.** DONE in v0.3.3 (see "Exact values" above), along with the Steps
   slider choosing the counted step in Trials mode.
5. **Display-area right-click menu**, split into three increments (agreed 2026-10-25):
   - v0.3.4 DONE: the menu and "Wall..." (see "Wall" above).
   - v0.3.5 DONE: the legend (see "Legend" above).
   - v0.3.6: Regenerate...: a dialog with a seed field (default 42 = the start-up data) and a
     P(right) slider, 0-100% in 1% steps, default 50%, labelled "P(right) 60%  P(left) 40%";
     keeps the wall setting; goes through `MainWindow.regenerate()`.

### Open decisions (ask the user when the step comes up)

- None at the moment (the wall question was settled and built in v0.3.4).

### Ways of working

- The increments above are ticket-shaped (scope, acceptance criteria, dependencies). Steps 1 and
  2 must go in order; after 2, steps 3-5 are independent. The user is interested in a
  ticket/multi-agent workflow: plan tickets first; work mainly in sequence, with agents for side
  work (code review, pytest-qt tests, docs) and possibly parallel worktrees for steps 3-4.
  Nearly every step edits main_window.py, so parallel work risks merge conflicts.

## Open items
- Memory: `simulate_paths` at MAX_JUMPS allocates two int64 (runs, steps) arrays (~400 MB
  each).