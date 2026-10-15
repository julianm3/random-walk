# random-walk

An interactive explorer for 1D random walks. Each walk takes STEPS jumps of +1 or -1, with an
optional slope bias and an optional reflecting wall. The app runs thousands of walks and shows
the results as a histogram and as several animations.

> **The GUI is being rebuilt** in PySide6 (Qt), one step at a time. On this branch (`main`),
> `random-walk` opens an early version: it simulates a seeded data set (10,000 walks of
> 1000 steps) and draws it - walks, histograms and a density view, picked from a temporary
> Drawing menu. The controls below the drawing aren't connected yet. The previous Dear
> PyGui interface is on the [`ui_prototype`](https://github.com/julianm3/random-walk/tree/ui_prototype) branch
> (tag `dpg-final`):
>
> ```powershell
> git checkout ui_prototype
> ```

## Features (previous GUI, to be carried into the new one)

- **Shared parameters:** RUNS, STEPS, an optional reflecting WALL, and a SLOPE bias (theta,
  -90 to 90 degrees).
- **Histogram:** final positions, with the theoretical curve overlaid.
- **Animations** on a shared timeline, with play, pause, reverse, fast-forward, step and scrub
  controls:
  - *Distribution*: runs are added one at a time to a growing histogram.
  - *Single Walk*: watch one chosen walk (the max, the min, or the nth) step by step.
  - *Evolving Histogram*: where every walk is, at each step.
  - *All Paths*: every walk's path drawn together.

## Getting started

You need Python 3.11 or newer. On Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -e ".[dev]"
random-walk            # or: py -m random_walk
```

## Development

```powershell
py -m pytest           # run the tests
ruff check .           # lint
ruff format .          # format
```

Type hints are used throughout. mypy is optional: `py -m pip install mypy`, then `py -m mypy`.

## Project layout

```
src/random_walk/
    config.py        default values and limits
    params.py        WalkParams and its validation
    simulation.py    simulate, simulate_paths, summarize (numpy only)
    theory.py        slope formula, normal and half-normal curves
    playback.py      timeline playback state (no GUI imports)
    cli.py           command-line entry point
    gui/             PySide6 (Qt) interface, in progress
tests/               unit tests for the core
tools/               font exploration scripts (pip install -e ".[tools]")
docs/                theory and design notes; sketches/ holds the GUI sketches
legacy/              the original single-file app, kept for reference
```

See [docs/theory.md](docs/theory.md) for the maths and
[docs/design-notes.md](docs/design-notes.md) for how the code is organised.

## License

MIT. See [LICENSE](LICENSE).
