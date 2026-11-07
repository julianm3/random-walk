# CLAUDE.md

Project notes for Claude Code. Read this first in every session.

## What this project is

An interactive 1D random walk explorer in Python. A seeded data set of 10,000 trials x 1000
steps (+1 or -1) is simulated at start-up and animated in a PySide6 (Qt 6) window, light theme
only. The GUI was built incrementally from the user's sketches (`docs/sketches/`) and is
complete as of v0.3.7; README.md describes it for users, docs/design-notes.md the structure.

Packaged as `src/random_walk` (hatchling, Python 3.11+, MIT), at `c:\dev\random-walk`
(outside OneDrive, to avoid sync problems with git), hosted on GitHub. Versioning: `version`
in pyproject.toml plus a git tag per release; keep `__version__` in
`src/random_walk/__init__.py` in sync. Each change the user accepts gets the next patch
version (v0.3.x).

## Working with the user

- The user runs git: suggest the commands (add, commit, tag, push), never commit or push.
- Before each new piece of work, outline the approach and ask the open questions, each with
  a recommendation. Don't start building until the user answers.
- The user decides UI questions by trying the app in person; build, verify, then let them
  judge. When they reject something after trying it, record it under "Tried and rejected".
- Verify every change before reporting it: ruff, mypy, pytest, and the GUI driven invisibly
  (see Testing). Screenshots and measured numbers are welcome.
- Explain Python idioms when asked; read the current file before citing line numbers.
- GUI tests (pytest-qt) only when the user asks for them.

## How the GUI works

`random-walk` / `py -m random_walk` -> `cli.main()` -> `gui.app.run()` -> `MainWindow`.

- **Window** (`gui/main_window.py`, opens at `INITIAL_SIZE` 800 x 900, minimum ~716 px
  wide): title top right; the drawing area (`WalkView`) takes the spare space; below it, in
  one zero-spacing layout with exact gaps (`CONTROL_GAP` 6, `SELECTOR_TOP_GAP` = CONTROL_GAP
  + 6, which includes `WINDOW_SPACING` 8):
  - `_build_control_block()` (v0.3.9): the Steps / Trials selector, vertical with its labels
    on the left (`PositionSelector(vertical=True, label_side="left")` - the user's choice),
    `SELECTOR_GAP` 6 px left of two `SliderRow`s (jump-to-start, 500 px slider, jump-to-end;
    no text labels: the selector's labels name the sliders). Each circle is level with its
    row: the rows are spaced so their pitch equals the selector's circle pitch (set by
    `SELECTOR_SPACING` 8; gap = pitch - row height), and whichever first centre is higher
    is pushed down. Selector + rows are centred as one group under the drawing area.
  - The player controls (step back, Play/Pause, step forward) below, with Play/Pause under
    the centre of the plot's x axis, not the frame's (the side labels differ in width, ~3.5
    px): `WalkView.plotSpanChanged(left, right)` -> `_centre_player_controls()`, which sets
    one of two invisible spacers (normally 0) to twice the offset. Measured: exact at start,
    after resizing, in both modes, with the wall; no jitter over a run.
  The user tuned the sizes by hand in v0.3.8 (from 640 px sliders, gaps of 12, 22 pt symbols
  and a 1000 x 760 window).
- **Selector** (`gui/position_selector.py`): labels below the circles by default; with
  exactly two positions `labels_beside` (v0.3.8) puts them either side, vertically centred,
  the circles just `spacing` apart; `vertical` (v0.3.9) stacks the circles top to bottom
  with every label on `label_side` ("left" or "right", default right), any number of
  positions, `spacing` growing so multi-line labels don't collide. Clicking a label or
  circle selects it. Raises ValueError for `labels_beside` with other than two positions,
  `vertical` with `labels_beside`, or `label_side` without `vertical`.
  `position_centre(i)` and `position_pitch()` let other widgets line up with the circles.
- **Modes** (`set_mode()`; each with its own `Playback`, one `QTimer` while playing):
  - Steps (`STEPS_DRAWING`, `show_step()`): the Steps slider (0-1000, starts at 1000) is the
    playhead; Play runs to step 1000 at 30 steps/s, from 0 again if at the end. The Trials
    slider (0-10,000) is the number of first trials taking part (`Drawing.trials`). Density
    image of those walks up to the step, histogram of their positions in front (opacity 0.6),
    theory curve.
  - Trials (`TRIALS_DRAWING`, `show_trials()`): the Trials slider is the playhead (starts at
    0); the Steps slider picks the step whose positions are counted (`trials_step`). Play
    grows the histogram to 10,000 in 30 s (900 frames), paced by `pacing.TrialRamp`:
    count(f) = (e^(kf) - 1)/k, 1 trial a frame at first, ~40 at the end. Scrubbing uses
    `Playback.seek(ramp.frame_for(k))`.
  - Moving any slider pauses. Each mode restores its own sliders and position on return.
    Playhead sliders follow playback with signals blocked (`set_quietly`).
- **Probability axis**:
  - Steps mode, with a theory curve: top = max(peak x (1 + `THEORY_HEADROOM` 0.18), tallest
    bar), not rounded, ticks the round values below - the bell keeps a steady height and the
    labels slide. 0.18 is the smallest headroom with no bar cut off at 10,000 trials.
  - Steps mode, no curve (wall on, step 0, P(right) 0 or 1): top = the tallest bar from this
    step to the end x 1.05 (`WalkView.tallest_from()`, a suffix max of `trace_grid`'s peaks:
    each step's busiest position, as width-2 parity bins hold one position). Only shrinks as a
    run plays: no flicker, nothing cut off.
  - Trials mode: fixed to all 10,000 trials at the chosen step and its theory peak
    (`probability_from_full`); early bars are cut off at the top, by the user's choice.
- **Controls**: step buttons = one step (Steps mode) or one trial (Trials mode), repeating
  while held at the keyboard's delay and rate (`keyboard_repeat()`). Keys (`KEY_ACTIONS`):
  Space play/pause, Left/Right step, Home/End jump. `MainWindow.eventFilter` is installed on
  the QApplication so a focused button or slider can't take them; it swallows the releases
  too, and leaves the keys alone with Ctrl/Alt/Meta or when a QLineEdit/QAbstractSpinBox has
  focus. `closeEvent` removes the filter (left installed, it was called during interpreter
  shutdown with already-deleted layouts: "Internal C++ object already deleted").
- **Right-click a slider**: `ValueEditor`, a frameless popup QSpinBox above the handle; Enter
  sets the slider (its handlers run as if dragged), Esc or a click outside cancels.
- **Right-click the drawing** (`_show_drawing_menu`):
  - Wall... (`WallDialog`): on/off and position (-120 to -1, default -30), with the grey note
    "(Regenerates animation data)" (the user's wording). One dialog so on + position
    regenerate once; the user may add more there later.
  - Legend (off at start-up): box in a top corner (`LEGEND_*` constants), monospaced lines
    from `simulation.legend_lines()`: steps and trials; mean and sd, beside the theory's
    unless the wall is on; P(right) when it isn't 50%. Starts top-right; moves to the other
    top corner when the bars crowd its corner but not the other (`placement.legend_side()`,
    switches only if the other corner is covered at most half as much - hysteresis).
  - Regenerate... (`RegenerateDialog`): seed and P(right) slider (0-100% in 1% steps,
    labelled "P(right) 60%" / "P(left) 40%"), opening with the current values.
- **Regenerating**: `MainWindow.regenerate(params)` pauses, stores the new `WalkParams`, and
  re-simulates only if `_data_key` changed (a new wall position while the wall is off is just
  stored), under a wait cursor; both modes keep their slider positions. ~0.3 s, ~0.4 s with
  the wall, plus ~50 ms for the first density image.
- **Drawing** (`gui/walk_view.py`): what's shown is a frozen `Drawing` built per frame. Room
  for both side axes is always reserved, so x positions never move. With the wall on: no
  theory curve, the x range starts `WALL_MARGIN` 6 positions left of the wall, and a grey
  line marks it at wall - 1 (the lowest bar's left edge). Walk drawing (`Drawing.walks`) is
  still there, though no mode uses it.
- **Density traces** (v0.4.0, the user's report: a lone walk at 20 after 100 steps showed
  as a bar 2 positions wide, shifted half a position): `simulation.trace_grid()` counts, per
  stretch between steps k and k + 1, the walks whose line crosses each unit interval
  [x, x + 1] (every step moves one position, so exactly one interval). The image spans
  exactly from position lo, step 0: each walk is a chain of cells meeting at its exact
  positions, a thin line. No combing: walks going up start on one parity, going down on the
  other. ~75 ms per count (once per number of trials; held while the Trials slider is
  dragged, `hold_density`). The same pass gives `peaks` for the axis. The plot is shorter
  than 1000 rows, so the image is squeezed to the plot's pixel height by taking the darkest
  step in each pixel row (`_combined_rows`, cached per count and height, DENSITY_GAMMA
  applied there); dropping rows (Qt's nearest-neighbour scaling) cut gaps in a lone walk's
  line. Shaded per row (`DENSITY_DARKEST` #222222, `DENSITY_GAMMA` 0.3, the user's choices).
  Frame repaint ~25 ms (v0.3.9 ~23). The histogram keeps its width-2 bins (correct, the
  user confirmed). `simulation.density_grid()` (2-wide position bins) is no longer used.
- **Look**: Source Code Pro everywhere (`gui/ui_fonts.py`), button symbols from a bundled Noto
  Sans Symbols 2 subset (`gui/symbols.py`, `POINT_SIZE` 16; the buttons size themselves to
  it, so it sets the slider rows' height). Sliders: 16 px tall (`SLIDER_HEIGHT`), 1 px track,
  black left of the handle, light grey right, 4 x 15 px black bar handle (track + 2 x
  `SLIDER_HANDLE_OVERHANG` 7; keep SLIDER_HEIGHT at least that or it's clipped)
  (`gui/style.py`, shared by the window and the
  dialogs; a style sheet replaces native drawing, so all slider styling goes in
  `SLIDER_STYLE`). Play/Pause shows the combined symbol, grey while paused, black on hover
  and while playing (`HoverColorButton`).

## Tried and rejected

Don't propose these again without a new reason.

- The Steps slider as the END step of a shorter run: it lost the playhead and nothing showed
  the current step. A Trials end count likewise; both sliders stay playheads.
- A summary box ("1000 Steps, 10000 Trials" / "Step 137 of 250"): removed.
- Locking the Steps slider in Trials mode: the user wants "40 trials at 250 steps".
- Dragging the wall: it's set in the dialog, and each change regenerates once.
- A "Random seed" button in the Regenerate dialog.
- Probability axis from the tallest bar alone at 10,000 trials (flickered); theory-based top
  rounded to a tick (bars popped ~15% at each change); an axis that only grows (would stick
  at step 0's 100% bar).
- A constant ~11 trials a frame in Trials mode (rushed past the sparse early histogram).
- The small triangles U+23F4/U+23F5 for the step buttons: they keep ⏪/⏩.

## Physics (keep these exact)

- Step is +1 with probability p = P(right) (`p_right`, 0 to 1, default 0.5), -1 otherwise.
  p > 0.5 drifts right. (v0.3.0 replaced a slope angle theta; p = 0.5 gives the same walks
  as theta = 0 did.)
- Wall: a step below WALL is reflected, position -> 2*WALL - position (equivalently
  WALL + |position - WALL|). NOT a clamp: reflecting keeps parity, clamping doesn't.
- Parity: with or without the wall, positions after n steps share n's parity, so histogram
  bins are width 2 (`parity_bins`). Width 1 leaves every other bin empty.
- Theory, no wall: Normal(mean = n(2p - 1), sd = sqrt(4p(1 - p) n)); per step mean 2p - 1,
  variance 4p(1 - p). At p = 0 or 1 the sd is exactly 0 and the curve is hidden.
- Theory, wall: the core's half-normal (sd sqrt(n)) is valid only at p = 0.5 and misfits a
  wall away from the start, so the GUI hides the curve whenever the wall is on.
  docs/theory.md has the derivations and the folded-normal fix.

## Architecture rules

- Qt code lives only in `gui/`. Nothing in the core imports Qt (`cli.py` imports the GUI
  inside `main()`). Logic worth testing goes in the core, where tests need no display.
- `simulate()` / `simulate_paths()` take an optional `rng`. The GUI passes a fresh
  `np.random.default_rng(params.seed)`; seed 42, P(right) 50%, no wall is the start-up data
  (hash starting 5525f7151cfc - check it after touching the simulation).
- `simulate_paths()` builds positions step-major and returns the transposed view (Fortran
  order): the wall loop and per-step reads are contiguous. Values must stay identical (tested
  against a step-by-step reference). Its random draws (`choice`, ~0.25 s) are kept as they
  are: a faster draw would change the seeded data.
- The data set's settings travel as one frozen `WalkParams` (`params.py`, with `seed`);
  validate with `params.validate()`.
- Animations are driven by `playback.Playback` (`tick(now)` returns the frame to redraw), one
  per timeline. Draw the first frame before starting the clock (it may count the density).
- Performance: never build QPolygonF from per-point QPointF objects; use
  `polygon_from_arrays()` (~100x faster). Show many walks as the density image, not
  polylines.

## Testing and checks

    py -m pytest           # core only, no display needed
    ruff check . && ruff format .
    py -m mypy             # needs `pip install mypy`

- `tests/` covers the core (theory, simulation, params, playback, ticks, pacing, placement).
  No GUI tests or CI yet; pytest-qt only when asked.
- To check the GUI, drive it invisibly on the real Windows platform:
  `widget.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)`, `show()`, process events,
  `widget.grab().save(...)`. The `offscreen` platform has no fonts. After a mode change wait
  ~0.3 s before grabbing (the selector's dot slides for 180 ms). Keep popups off screen too
  (set the attribute in a patched `show`). Put such scripts in the scratchpad, not the repo.
- README screenshots (`docs/screenshot-*.png`): default data, legend on; Steps mode at step
  400, Trials mode (via `position_selector.setCurrentIndex`) at 1,500 trials. Retake them
  after visible changes.
- mypy: don't pin `python_version` to 3.11 (numpy 2.5's stubs don't resolve for it).

## Pitfalls

- Line endings are LF (`.gitattributes`). Python's `write_text` on Windows writes CRLF:
  pass `newline="\n"`, or use the Edit/Write tools. Check with `git ls-files --eol`.
- Git Bash mangles quotes in inline Python heredocs and `sed` patterns. For anything beyond a
  one-line change use the Edit tool, or a script file in the scratchpad - and check that it
  cut where intended before running ruff.
- Emoji presentation: U+23E9/U+23EA and some other symbols draw as colour emoji on Windows
  whatever the font; append U+FE0E (`symbols.TEXT_PRESENTATION`). Check any new symbol.
- A file once reverted on disk to an old commit's version mid-session (likely an editor tab).
  If a file looks wrong, compare it with `git hash-object` against the commits before
  touching it.
- A Qt layout not yet in a window reports a sizeHint height of 0: measure its widgets'
  sizeHints instead (`SliderRow.height()`), as the window is built before it's shown.
- On Windows PowerShell, quote git refs with braces: `'v0.3.8^{}'` (a bare `{}` becomes a
  script block, which git sees as `-encodedCommand ...`).

## Layout

    src/random_walk/
        config.py      defaults and limits      params.py     WalkParams, validate()
        theory.py      mean, sd, curves         simulation.py walks, histograms, density, legend
        playback.py    Playback timeline        pacing.py     TrialRamp (Trials mode)
        placement.py   legend corner            ticks.py      nice_ticks()
        cli.py         entry point
        gui/  app.py, main_window.py, walk_view.py, dialogs.py, style.py, symbols.py,
              ui_fonts.py, position_selector.py, fonts/ (each font with its licence)
    tests/     core tests            tools/  font scripts (".[tools]" extra)
    docs/      theory.md, design-notes.md, sketches/, screenshot-*.png
    legacy/    the original single-file app: reference only, don't edit or import

The previous Dear PyGui GUI is on the `ui_prototype` branch (tag `dpg-final`): reference only,
don't merge it back.

## Dependencies and licences

numpy (>=2.0), PySide6-Essentials (>=6.8). Dev: pytest, ruff. Tools extra: dearpygui,
fonttools. Optional: mypy. Check new dependencies against the MIT licence: PySide6 (LGPLv3) is
fine; avoid GPL-only Qt modules (Qt Charts, Qt Data Visualization, Qt Graphs).

Bundled fonts (SIL OFL 1.1; ship each licence file alongside; none may be sold on its own):
- Noto Sans Symbols 2 subset: no Reserved Font Name, so subsetting was OK. Rebuild with
  `tools/make_symbol_font.py`.
- Source Code Pro: Reserved Font Name "Source" (Adobe). Bundle unmodified; changing it would
  require renaming.

## Ideas / backlog

Nothing is planned. Ask the user what comes next. Candidates mentioned so far:
- GUI tests with pytest-qt, starting from the checks done by script for each feature, and
  CI (ruff, mypy, pytest on a Windows runner).
- A theory curve with the wall at 50%: the folded normal in docs/theory.md.
- Memory: `simulate_paths` holds two int64 (trials, steps) arrays, three with the wall
  (~80 MB each at 10,000 x 1000; ~400 MB each at `MAX_JUMPS`).
- A CHANGELOG.md, if the user wants one.
