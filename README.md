# random-walk

An interactive explorer for 1D random walks. Each walk takes STEPS jumps of +1 or -1, with an
optional slope bias and an optional reflecting wall. The app runs thousands of walks and shows
the results as a static histogram and as several animations.

## Features

- **Shared parameters:** RUNS, STEPS, an optional reflecting WALL, and a SLOPE bias (theta,
  -90 to 90 degrees).
- **Static tab:** a histogram of final positions, with the theoretical curve overlaid.
- **Animation tab:** four views on one shared timeline, each with play, pause, reverse,
  fast-forward, step and scrub controls:
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
    gui/             Dear PyGui front end: app, controls, transport, static and animation tabs
tests/               unit tests for everything outside gui/
docs/                theory and design notes
legacy/              the original single-file app, kept for reference
```

See [docs/theory.md](docs/theory.md) for the maths and
[docs/design-notes.md](docs/design-notes.md) for how the code is organised.

## License

MIT. See [LICENSE](LICENSE).
