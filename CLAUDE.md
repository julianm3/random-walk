# CLAUDE.md

Project notes for Claude Code. Read this first in every session.

## What this project is

An interactive 1D random walk explorer in Python. Users set RUNS, STEPS, an optional reflecting
WALL, and a SLOPE bias (theta, -90 to 90 degrees). The app shows a final-position histogram
and animated views: Distribution, Single Walk, Evolving Histogram, All Paths.

Packaged as `src/random_walk` (hatchling, Python 3.11+, MIT). The repo is at
`c:\dev\random-walk` (outside OneDrive, to avoid sync problems with git) and is hosted on
GitHub. Versioning: a fixed `version` in pyproject.toml plus git tags for milestones. Keep
`__version__` in `src/random_walk/__init__.py` in sync with it. The user runs git themselves:
suggest commands, don't commit or push.

## GUI status: being rebuilt

`main` currently has **no GUI**. A completely new GUI is being built incrementally;
the toolkit is still to be chosen (PySide6 + pyqtgraph has been discussed). Until it exists,
`random-walk` / `py -m random_walk` run `random_walk.cli.main()`, which prints a placeholder.
Wire the new GUI's launcher into `cli.main()`.

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
    │   ├── theory.py          # p_right, final mean/sd, normal and half-normal curves
    │   ├── simulation.py      # simulate, simulate_paths, summarize, parity_bins (numpy only)
    │   ├── playback.py        # Playback timeline state machine (no GUI imports)
    │   └── cli.py             # entry point (placeholder until the new GUI exists)
    ├── tests/                 # core only: theory, simulation, params, playback
    ├── tools/                 # font exploration scripts (dearpygui + fonttools; not packaged)
    │   └── fonts/             # downloaded fonts, git-ignored
    ├── docs/theory.md, docs/design-notes.md
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

numpy (>=2.0). Dev: pytest, ruff. Tools extra: dearpygui, fonttools. Optional: mypy.

When choosing GUI libraries, check licences against the MIT project licence. PySide6 is LGPLv3
and fine as a dependency; avoid GPL-only Qt modules (Qt Charts, Qt Data Visualization,
Qt Graphs). pyqtgraph is MIT. Bundled fonts need their licence file shipped alongside.

## Physics (keep these exact)

- Step is +1 or -1. P(right) = 0.5 - 0.5*sin(theta), P(left) = 1 - P(right).
  Positive theta biases left, negative biases right.
- Wall: a step below WALL is reflected, position -> 2*WALL - position (equivalently
  WALL + abs(position - WALL)). It is NOT a clamp. The reflect rule preserves parity; clamp
  does not, and we dropped clamp deliberately.
- Parity: without a wall, or with the reflecting wall, final positions all share the parity of
  STEPS, so histogram bins are width 2. Bin width 1 leaves every other bin empty.
- Theory curve, no wall: Normal(mean = -STEPS*sin(theta), sd = sqrt(STEPS)*|cos(theta)|).
  Per-step mean is -sin(theta), per-step variance is cos^2(theta).
- At theta = +/-90 the sd is exactly 0 (computed as sqrt(STEPS*(1 - sin^2)), never via cos,
  which is ~6e-17 at 90 degrees) and `summarize()` hides the curve, with or without a wall.
- Theory curve, wall: half-normal approximation, sd = sqrt(STEPS). Valid only at theta = 0
  (reflection principle needs a driftless walk). Hidden when theta != 0.
- docs/theory.md has the derivations and the known limitations (see Open items).

## Architecture rules

- GUI toolkit code lives only in `gui/` (to be recreated). Nothing in the core imports a GUI
  toolkit; logic worth testing belongs in the core, where tests need no display.
- `simulate()`/`simulate_paths()` take an optional `rng: np.random.Generator`. Tests always
  pass a seeded one. The GUI uses the unseeded module default.
- Validate the shared parameters with `params.validate()` and pass them around as a
  `WalkParams`. Read the shared controls in one place only.
- Drive animations with `playback.Playback`: the GUI's timer calls `tick(now)` and redraws the
  frame it returns. One Playback per timeline.
- Cache simulated data per view, keyed by the `WalkParams` it came from (frozen, hashable), so
  replaying with unchanged params doesn't re-simulate.

## Testing rules

- `tests/` covers the core only and needs no display. The GUI testing approach is to be chosen
  with the new toolkit (for Qt, pytest-qt can run headless); there is no CI yet.
- Behaviour of the new GUI can be compared against `ui_prototype` or the legacy app by seeding
  the generator (`random_walk.simulation._default_rng = np.random.default_rng(seed)`).
- mypy: don't pin `python_version` to 3.11. numpy 2.5's stubs don't resolve for that target.

## Open items

- Build the new GUI (incrementally), then decide on GUI tests and CI (GitHub Actions).
- Planned: a seed control in the UI.
- Known physics issue (see docs/theory.md): the wall curve is a half-normal centred on the
  wall and ignores that the walk starts at 0; the folded normal phi(y) + phi(2w - y) is the
  correct large-STEPS curve at theta = 0.
- Memory: `simulate_paths` at MAX_JUMPS allocates two int64 (runs, steps) arrays (~400 MB
  each).
