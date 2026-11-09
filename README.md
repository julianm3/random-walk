# random-walk

Random walks start at zero and jump either left or right.
 - Steps mode, watch how 10,000 walks evolve over 1,000 steps (think of it as an upside-down [Galton Board](https://en.wikipedia.org/wiki/Galton_board))
 - Trials mode, watch the histogram evolve as more walks are added.

Hit play to start. Right-click the display area to add a wall, change the left / right probability, etc.

**Steps Mode**  
10,000 trials at step 400, showing density and histogram of
their positions
![Steps mode: 10,000 trials at step 400, with the density of the walks and the histogram of
their positions](docs/screenshot-steps.png)

**Trials Mode**  
Histogram of 1,500 Trials after 1000 steps each
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

Pick a mode **Steps** or **Trials** 

| Slider | Steps mode | Trials mode |
|---|---|---|
| **Steps** | The current step (the playhead) | How many steps completed in each trial (e.g. histogram of 1,000 trials after 20 steps each) |
| **Trials** | How many trials (the first N of the 10,000) | How many trials are in the histogram so far (the playhead) |

Each mode remembers its own slider settings when you switch back and forth. The buttons at
the ends of each slider jump it to its start or end.

**Right-click a slider** to type an exact value.

**Right-click the drawing** to configure the simulation.

**Key Bindings**

| Key | Action |
|---|---|
| Space | Play / pause |
| Left / Right | Step back / forward (hold to repeat) |
| Home / End | Jump to the start / end |

## Features

- **Steps mode:** the chosen trials advance step by step. A grey density image shows where
  the walks have been, and the histogram shows where they are now.
- **Trials mode:** the histogram of positions at a chosen step grows one trial at a time,
  slowly at first and then faster, filling in under the theory curve.
- **Theory curve:** the normal distribution the positions should follow, in red.
- **Legend:** the step, the number of trials, and their measured mean and standard deviation
  beside the theoretical values.
- **Seed:** regenerate the walks with a different random seed
- **Reflecting wall:** a barrier the walks bounce off
- **Absorbing wall:** a barrier that stops any walk that touches it
- **Bias, P(right):** the chance of each step going right

## What you're looking at

- **Grey shading (Steps mode):** the walks' paths, from step 0 at the bottom up to the
  current step. Each walk is traced exactly through its positions, and where many paths
  overlap the shading builds up darker. Each step is shaded on its own scale, so the darkest
  part of every row is where most of that step's walks passed. With only a few trials you
  can follow each walk as a thin line.
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
    params.py        WalkParams: the data set's settings
    data.py          the data set: generated from WalkParams, walks still going, bar shares
    simulation.py    simulating walks, histograms, trace counts, legend values (numpy only)
    density.py       the density image's shading, squeezed to the plot's height
    theory.py        mean and sd for the bias, the normal curve
    playback.py      animation timeline: play, pause, jump (no GUI imports)
    pacing.py        Trials mode's slow-then-fast trial counts
    placement.py     which top corner the legend goes in
    ticks.py         round-number axis ticks
    cli.py           command-line entry point
    gui/             the PySide6 (Qt) interface
        main_window.py   the window, its controls and keyboard
        widgets.py       slider rows, the value editor, symbol buttons
        walk_view.py     the drawing area
        dialogs.py       the Configure dialog

        fonts/           bundled fonts, each with its licence
tests/               unit tests for the core
docs/                theory and design notes; sketches/ holds the GUI sketches
CHANGELOG.md         log of changes
```

See [docs/design-notes.md](docs/design-notes.md) for how the code is organised.

## Licence

MIT. See [LICENSE](LICENSE).

The app uses [PySide6](https://doc.qt.io/qtforpython-6/) (Qt for Python) under the LGPLv3, and
bundles two fonts under the SIL Open Font License 1.1, with their licences in
`src/random_walk/gui/fonts/`:

- [Source Code Pro](https://github.com/adobe-fonts/source-code-pro), by Adobe, for all text.
- A subset of [Noto Sans Symbols 2](https://github.com/notofonts/symbols), by Google, for
  the button symbols.
