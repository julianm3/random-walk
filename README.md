# random-walk

An interactive explorer for 1D random walks. Every walk starts at 0 and takes 1000 steps of
+1 or -1. The app simulates 10,000 of these walks (trials) and animates them, so you can watch
the spread of positions grow and compare it with what the theory predicts. You can bias the
steps to one side, put a reflecting wall in the way, and pick any subset of the trials and
steps to look at.

![Steps mode: 10,000 trials at step 400, with the density of the walks and the histogram of
their positions](docs/screenshot-steps.png)

## Features

- **Steps mode:** the chosen trials advance step by step. A grey density image shows where
  the walks have been, and the histogram shows where they are now.
- **Trials mode:** the histogram of positions at a chosen step grows one trial at a time,
  slowly at first and then faster, filling in under the theory curve.
- **Theory curve:** the normal distribution the positions should follow, in red.
- **Legend:** the step, the number of trials, and their measured mean and standard deviation
  beside the theoretical values. It moves to whichever top corner the bars leave free.
- **Reflecting wall:** a barrier the walks bounce off, at any position from -120 to -1.
- **Bias and seed:** regenerate the walks with a different random seed, or a different
  P(right), the chance of each step going right.

![Trials mode: the histogram of 1,500 trials' final positions under the theory
curve](docs/screenshot-trials.png)

## Getting started

You need Python 3.11 or newer. On Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -e ".[dev]"
random-walk            # or: py -m random_walk
```

The app is built with PySide6 (Qt) and has been tested on Windows 11.

## Using the app

Pick a mode with the **Steps / Trials** selector under the drawing. The two sliders do
different jobs in each mode:

| Slider | Steps mode | Trials mode |
|---|---|---|
| **Steps** | The current step (the playhead): it moves as the animation plays, and you can drag it | The step whose positions are counted |
| **Trials** | How many trials take part (the first N of the 10,000) | How many trials are in the histogram so far (the playhead) |

Each mode remembers its own slider settings when you switch back and forth. The buttons at
the ends of each slider jump it to its start or end.

**Right-click a slider** to type an exact value, and press Enter.

**Right-click the drawing** for:

- **Wall...:** turn the reflecting wall on or off and set its position. This regenerates
  the walks.
- **Legend:** show or hide the legend.
- **Regenerate...:** choose a new random seed and P(right). The default, seed 42 at 50%,
  is the data the app starts with.

The buttons under the sliders step back, play or pause, and step forward. A step is one
step in Steps mode and one trial in Trials mode.

| Key | Action |
|---|---|
| Space | Play / pause |
| Left / Right | Step back / forward (hold to repeat) |
| Home / End | Jump to the start / end |

## What you're looking at

- **Grey shading (Steps mode):** how many walks were at each position at each step, from
  step 0 at the bottom up to the current step. Each step is shaded on its own scale, so the
  darkest cell in every row is where most of that step's walks were.
- **Light grey bars:** the histogram, each bar's share of the trials, against the
  probability axis on the right.
- **Red curve:** the theoretical distribution after that many steps, a normal curve with mean
  n(2p - 1) and standard deviation sqrt(4p(1 - p)n), where p is P(right). It's hidden while
  the wall is on, since a wall's effect has no simple formula in general, and when every
  step goes the same way (P(right) of 0% or 100%).
- **Grey vertical line:** the wall, when it's on.

See [docs/theory.md](docs/theory.md) for the derivations.

## Development

```powershell
py -m pytest           # run the tests (the simulation core, no display needed)
ruff check .           # lint
ruff format .          # format
```

Type hints are used throughout. mypy is optional: `py -m pip install mypy`, then `py -m mypy`.

## Project layout

```
src/random_walk/
    config.py        default values and limits
    params.py        WalkParams (the data set's settings) and its validation
    simulation.py    simulating walks, histograms, density counts, legend values (numpy only)
    theory.py        mean and sd for the bias, normal and half-normal curves
    playback.py      animation timeline: play, pause, step, scrub (no GUI imports)
    pacing.py        Trials mode's slow-then-fast trial counts
    placement.py     which top corner the legend goes in
    ticks.py         round-number axis ticks
    cli.py           command-line entry point
    gui/             the PySide6 (Qt) interface
        main_window.py   the window, its controls and keyboard
        walk_view.py     the drawing area
        dialogs.py       the Wall and Regenerate dialogs
        fonts/           bundled fonts, each with its licence
tests/               unit tests for the core
tools/               font scripts (pip install -e ".[tools]")
docs/                theory and design notes; sketches/ holds the GUI sketches
legacy/              the original single-file app, kept for reference
```

See [docs/design-notes.md](docs/design-notes.md) for how the code is organised.

## History

An earlier interface, built with Dear PyGui, is on the
[`ui_prototype`](https://github.com/julianm3/random-walk/tree/ui_prototype) branch (tag
`dpg-final`). It used a slope angle for the bias rather than P(right).

## Licence

MIT. See [LICENSE](LICENSE).

The app uses [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) under the LGPLv3, and
bundles two fonts under the SIL Open Font License 1.1, with their licences in
`src/random_walk/gui/fonts/`:

- [Source Code Pro](https://github.com/adobe-fonts/source-code-pro), by Adobe, for all text.
- A subset of [Noto Sans Symbols 2](https://github.com/notofonts/symbols), by Google, for
  the button symbols.
