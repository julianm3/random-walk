# Design notes

How the code is organised and why.

## Layers

    config.py      constants: defaults, limits, playback speeds
    params.py      WalkParams + validate()                 \
    theory.py      closed-form formulas                     |  core: numpy only, no GUI,
    simulation.py  simulate / simulate_paths / summarize    |  fully unit-tested
    playback.py    Playback timeline state machine         /
    cli.py         entry point
    gui/           PySide6 (Qt) GUI, being rebuilt; the only package that imports Qt

The rule: Qt code lives only in `gui/`. Anything with logic worth testing
(validation, physics, histogram summaries, playback timing) lives in the core, where its
tests need no display. That split is what lets the GUI be replaced without touching the core.

## The GUI: being rebuilt

A new GUI is being built incrementally in PySide6, light theme, from the user's sketches.
`cli.main()` imports it lazily (so the core never loads Qt) and runs `gui.app.run()`, which
creates the `QApplication` and shows `gui.main_window.MainWindow`. So far the window has the
first sketch's layout only: title, an empty drawing area that takes all spare space, a summary
label, and a fixed-width slider row kept centred by stretches on both sides.

The previous Dear PyGui GUI is on the `ui_prototype` branch (tag `dpg-final`). It had a Static
tab (one histogram, no timeline) and an Animation tab whose four modes shared one plot and one
set of transport controls. Its design notes describe that layout in detail.

The core is designed to support whichever toolkit comes next:

- **Parameters:** the GUI reads its shared controls in one place, validates them with
  `params.validate()`, and passes them on as a `WalkParams`.
- **Playback:** `Playback` is a plain object driven by time values the GUI passes in
  (`tick(now)`). It returns the integer frame to redraw, or None, and never touches widgets,
  so a timer in any toolkit can drive it. Its edge cases are unit-tested directly: the dt = 0
  first tick, auto-stop at either end, rewind when you press Play at the end, and preset
  matching.
- **Caching:** a view keeps its simulated data with the `WalkParams` it came from as the key
  (frozen and hashable). Replaying with unchanged params reuses the data instead of
  re-simulating.

## Randomness

`simulate()` and `simulate_paths()` take an optional `rng: numpy.random.Generator`. Tests pass
seeded generators. The GUI uses the module default, seeded with config.DEFAULT_SEED so the
app shows the same data every launch. Two calls with
identically seeded generators consume random numbers identically, so
`simulate_paths(...)[:, -1]` equals `simulate(...)`.

## History

- The app began as a single file, now at `legacy/random-walk-vibe.py` for reference.
- v0.1.0 refactored it into this package with a Dear PyGui GUI that reproduced its behaviour
  exactly. That was checked by driving both through the same scripted session with seeded
  generators and comparing every visible widget value.
- That GUI was then moved to the `ui_prototype` branch (tag `dpg-final`) so a completely new
  GUI can be built on `main`.
