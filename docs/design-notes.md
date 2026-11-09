# Design notes

How the code is organised and why.

## Layers

    config.py      constants: defaults, limits, frame rate
    params.py      WalkParams: the settings                \
    data.py        WalkData: the data set, generate()       |
    theory.py      closed-form formulas                     |
    simulation.py  walks, histograms, traces, legend        |  core: numpy only, no GUI,
    density.py     the density image's shading              |  fully unit-tested
    playback.py    Playback timeline state machine          |
    pacing.py      Trials mode's slow-then-fast counts      |
    placement.py   which corner the legend goes in          |
    ticks.py       round-number axis ticks                 /
    cli.py         entry point
    gui/           PySide6 (Qt) GUI; the only package that imports Qt

The rule: Qt code lives only in `gui/`. Anything with logic worth testing (physics,
statistics, the density shading, playback timing, pacing, placement) lives in the core,
where its tests need no display. The GUI draws: it turns the core's numbers into pixels.

`data.generate(params)` builds a `WalkData` - every walk's positions, and with an absorbing
wall each walk's contact step - and answers the questions the drawing asks of it: which walks
are still going at a step, and each histogram bar's share of the counted trials.

## The GUI

`cli.main()` imports the GUI lazily (so the core never loads Qt) and runs `gui.app.run()`,
which creates the `QApplication` and shows `gui.main_window.MainWindow`.

- **`MainWindow`** holds the controls: the Steps / Trials selector (a vertical
  `PositionSelector`, its circles lined up with the two `SliderRow`s to its right, whose
  names its labels give), the step and Play/Pause buttons (Play/Pause under the centre of the
  plot's x axis, which `WalkView` reports), and the right-click menu on the drawing. It owns
  the data set's settings as one `WalkParams` (`self.params`) and an application-wide key
  filter, so Space and the arrow keys work whatever has the focus.
- **`WalkView`** is the drawing area. What it shows is described by a frozen `Drawing`
  (density, histogram, theory curve, legend, which step, how many trials); the window builds
  one per frame. Room for both side axes is always reserved, so x positions never move.
- **`dialogs.py`** has the Configure dialog; **`style.py`** the slider style it
  shares with the window; **`widgets.py`** the window's small widgets (`SliderRow`, the
  right-click `ValueEditor`, `HoverColorButton`, the symbol buttons) and the system's key
  repeat timing.

### The two modes

Each mode has its own `Playback`, driven by one `QTimer` while playing. Steps mode's timeline
is the 1001 steps; Trials mode's is 900 frames (30 s), which `pacing.TrialRamp` turns into
trial counts, 1 a frame at first and about 40 at the end. In each mode one slider is the
playhead (Steps, or Trials in Trials mode) and follows playback with its signals blocked;
the other is a setting (the number of trials, or the step counted). Switching modes pauses
and restores the other mode's sliders and position.

### Regenerating

The Configure dialog changes `self.params` through `MainWindow.regenerate()`, which
re-simulates (`data.generate`) only if something the walks depend on changed
(`WalkParams.same_walks`: trials, steps, wall, its mode while on, P(right), seed); a new wall
position while the wall is off is just stored. It takes about 0.3 s without the wall and
0.4-0.5 s with it, plus ~50 ms for the first density image.
Both modes keep their slider positions.

### Drawing speed

- Density: `simulation.trace_grid()` counts, between each pair of steps, how many walks'
  lines cross each unit interval between positions, once per number of trials;
  `density.DensityShading` shades it (squeezed to the plot's height by taking the darkest
  step per pixel row, so no walk's line gets gaps), and `WalkView` turns that into a small
  greyscale image and stretches it. Each walk is
  drawn exactly, as a thin line through its positions, and both parities fill every row, so
  there's no combing. Far faster than drawing thousands of lines.
- The same pass gives each step's tallest histogram bar, which sizes the probability axis
  when there's no theory curve to follow.
- Polylines are filled straight from numpy arrays (`polygon_from_arrays`), about 100x faster
  than building one `QPointF` per point.

## Randomness

`simulate()` and `simulate_paths()` take an optional `rng: numpy.random.Generator`. Tests pass
seeded generators. The GUI creates a fresh `numpy.random.default_rng(params.seed)` for every
data set, so equal settings always give the same walks; the defaults (seed 42, P(right) 50%,
no wall) give the data the app starts with.

`simulate_paths()` builds the positions step by step in a (steps, trials) array and returns
its transposed view, so the wall's per-step loop and the per-step reads (density,
histograms) work on contiguous memory. The values are identical to the simple row-by-row
version (tested).

## History

- The app began as a single Python file. v0.1.0 refactored it into this package, with a
  Dear PyGui GUI that reproduced its behaviour exactly (checked by driving both through the
  same scripted session with seeded generators).
- From v0.2.0 a new PySide6 GUI was built from the user's sketches (`docs/sketches/`): v0.2.x
  laid out the window and drawing, v0.3.0 replaced the slope angle with P(right), v0.3.1 to
  v0.3.9 added the two modes, the controls, the wall, the legend and the final layout, v0.4.x
  the exact traces and the absorbing wall.
- v0.5.x cleaned up: dead code removed, data generation and the density shading moved into
  the core, and the original file, the font scripts and the Dear PyGui branch removed. All
  are still in git history: the original file and the font scripts up to tag v0.5.1, the
  last Dear PyGui version at commit 7a45562, just before v0.2.0.

See CHANGELOG.md for each version.
