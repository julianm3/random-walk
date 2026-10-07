# Design notes

How the code is organised and why.

## Layers

    config.py      constants: defaults, limits, playback speeds
    params.py      WalkParams + validate()                 \
    theory.py      closed-form formulas                     |  core: numpy only, no GUI,
    simulation.py  simulate / simulate_paths / summarize    |  fully unit-tested
    playback.py    Playback timeline state machine         /
    gui/           Dear PyGui: the only package that imports dearpygui

The rule: nothing outside `gui/` imports `dearpygui`. Anything with logic worth testing
(validation, physics, histogram summaries, playback timing) lives in the core, where its
tests need no display.

## The GUI

- `gui/app.py`: `build_ui()` creates the context, viewport and widgets and draws the Static
  tab's defaults. `main()` is `build_ui()` plus the render loop. The split lets a headless
  harness drive the real UI frame by frame.
- `gui/controls.py`: the shared RUNS/STEPS/WALL/SLOPE panel. `read_shared_params()` is the
  only place those widgets are read. It returns `(WalkParams, None)` or `(None, error)`.
- `gui/static_tab.py`: one histogram and a Run button, with no timeline.
- `gui/transport.py`: `Transport` wires one `Playback` to its widgets (buttons, speed slider,
  presets, scrubber) and redraws on each frame change.
- `gui/animation_tab.py`: `AnimationTab` holds the four modes, which share one plot and one
  `Transport`.

### Playback

`Playback` is a plain object driven by time values the GUI passes in (`tick(now)`). It
returns the integer frame to redraw, or None. It never touches widgets, so its edge cases are
unit-tested directly: the dt = 0 first tick, auto-stop at either end, rewind when you press
Play at the end, and preset matching.

`Transport.advance()` is called once per rendered frame, from an item-visible handler on the
primary window, and returns early while its plot is hidden.

### Caching

Each animation mode keeps its last simulated data in `AnimationTab.data[mode]`, with a
`cache_key`. The key is the `WalkParams` the data was simulated with; it is frozen and
hashable. Play resumes without re-simulating when the current params equal the key. Single
Walk reuses one batch of paths across Add Walk clicks, so "max" and "min" come from the same
population.

### Widget tags

Widgets use string tags (`"anim_plot"`, `"anim_scrub"`, ...) rather than stored ids. Transport
tags are namespaced by prefix: `Transport("anim", ...)` owns `anim_play_pause`, `anim_speed`,
`anim_scrub` and `anim_preset_*`.

## Randomness

`simulate()` and `simulate_paths()` take an optional `rng: numpy.random.Generator`. Tests pass
seeded generators. The GUI uses the module default, which is unseeded. Two calls with
identically seeded generators consume random numbers identically, so
`simulate_paths(...)[:, -1]` equals `simulate(...)`.

## History

The app began as a single file, now at `legacy/random-walk-vibe.py` for reference. The
package refactor reproduces its behaviour exactly. That was checked by driving both through
the same scripted session with seeded generators and comparing every visible widget value.
