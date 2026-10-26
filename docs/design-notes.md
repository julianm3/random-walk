# Design notes

How the code is organised and why.

## Layers

    config.py      constants: defaults, limits, playback speeds
    params.py      WalkParams + validate()                 \
    theory.py      closed-form formulas                     |
    simulation.py  walks, histograms, density, legend      |  core: numpy only, no GUI,
    playback.py    Playback timeline state machine          |  fully unit-tested
    pacing.py      Trials mode's slow-then-fast counts      |
    placement.py   which corner the legend goes in          |
    ticks.py       round-number axis ticks                 /
    cli.py         entry point
    gui/           PySide6 (Qt) GUI; the only package that imports Qt

The rule: Qt code lives only in `gui/`. Anything with logic worth testing (validation,
physics, statistics, playback timing, pacing, placement) lives in the core, where its tests
need no display.

## The GUI

`cli.main()` imports the GUI lazily (so the core never loads Qt) and runs `gui.app.run()`,
which creates the `QApplication` and shows `gui.main_window.MainWindow`.

- **`MainWindow`** holds the controls: the Steps / Trials selector (`PositionSelector`), two
  `SliderRow`s, the step and Play/Pause buttons, and the right-click menu on the drawing. It
  owns the data set's settings as one `WalkParams` (`self.params`) and an application-wide
  key filter, so Space and the arrow keys work whatever has the focus.
- **`WalkView`** is the drawing area. What it shows is described by a frozen `Drawing`
  (density, histogram, theory curve, legend, which step, how many trials); the window builds
  one per frame. Room for both side axes is always reserved, so x positions never move.
- **`dialogs.py`** has the Wall and Regenerate dialogs; **`style.py`** the slider style they
  share with the window.

### The two modes

Each mode has its own `Playback`, driven by one `QTimer` while playing. Steps mode's timeline
is the 1001 steps; Trials mode's is 900 frames (30 s), which `pacing.TrialRamp` turns into
trial counts, 1 a frame at first and about 40 at the end. In each mode one slider is the
playhead (Steps, or Trials in Trials mode) and follows playback with its signals blocked;
the other is a setting (the number of trials, or the step counted). Switching modes pauses
and restores the other mode's sliders and position.

### Regenerating

The Wall and Regenerate dialogs change `self.params` through `MainWindow.regenerate()`, which
re-simulates only if something the walks depend on changed (`_data_key`: trials, steps,
wall, P(right), seed); a new wall position while the wall is off is just stored. It takes
about 0.3 s without the wall and 0.4 s with it, plus ~50 ms for the first density image.
Both modes keep their slider positions.

### Drawing speed

- Density: `simulation.density_grid()` counts walks per (step, 2-wide position bin) once per
  number of trials; `WalkView` shades it into a small greyscale image and stretches it. Far
  faster than drawing thousands of lines.
- The same count gives each step's tallest histogram bar, which sizes the probability axis
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

- The app began as a single file, now at `legacy/random-walk-vibe.py` for reference.
- v0.1.0 refactored it into this package with a Dear PyGui GUI that reproduced its behaviour
  exactly. That was checked by driving both through the same scripted session with seeded
  generators and comparing every visible widget value.
- That GUI moved to the `ui_prototype` branch (tag `dpg-final`), and a new PySide6 GUI was
  built on `main` from the user's sketches (`docs/sketches/`): v0.2.x laid out the window
  and drawing, v0.3.0 replaced the slope angle with P(right), and v0.3.1 to v0.3.7 added the
  two modes, the step buttons and keys, exact values, the wall, the legend and Regenerate.
