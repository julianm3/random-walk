# CLAUDE.md

Project notes for Claude Code. Read this first in every session.

## What this project is

An interactive 1D random walk explorer in Python. Users set RUNS, STEPS, an optional reflecting
WALL, and a SLOPE bias (theta, -90 to 90 degrees). The app shows a final-position histogram
(Static tab) and four animated views (Animation tab): Distribution, Single Walk, Evolving
Histogram, All Paths.

Packaged as `src/random_walk` (hatchling, Python 3.11+, MIT). The original single-file app
lives at `legacy/random-walk-vibe.py` for reference only. Don't edit it or import from it. The
repo is at `c:\dev\random-walk` (outside OneDrive, to avoid sync problems with git) and is
hosted on GitHub. Versioning: a fixed `version` in pyproject.toml plus git tags for milestones.
Keep `__version__` in `src/random_walk/__init__.py` in sync with it.

## Layout

    random-walk/
    ├── pyproject.toml, README.md, LICENSE, CLAUDE.md
    ├── src/random_walk/
    │   ├── config.py          # DEFAULT_* values, limits, playback speeds
    │   ├── params.py          # WalkParams (frozen dataclass) + validate()
    │   ├── theory.py          # p_right, final mean/sd, normal and half-normal curves
    │   ├── simulation.py      # simulate, simulate_paths, summarize, parity_bins (numpy only)
    │   ├── playback.py        # Playback timeline state machine (no GUI imports)
    │   └── gui/               # the only package that imports dearpygui
    │       ├── app.py         # build_ui(), main()
    │       ├── controls.py    # shared RUNS/STEPS/WALL/SLOPE panel, read_shared_params()
    │       ├── transport.py   # Transport: wires a Playback to its buttons/sliders
    │       ├── static_tab.py
    │       └── animation_tab.py  # AnimationTab: the four modes
    ├── tests/                 # core only: theory, simulation, params, playback
    ├── docs/theory.md, docs/design-notes.md
    └── legacy/random-walk-vibe.py

## Commands

    py -m venv .venv && .venv\Scripts\activate
    py -m pip install -e ".[dev]"
    random-walk            # or: py -m random_walk
    py -m pytest
    ruff check . && ruff format .
    py -m mypy             # optional; needs `pip install mypy`

Run the package with `-m` or the console script, never by pointing at a file inside `src/`.
Code is formatted with `ruff format` (line length 100). Use type hints throughout.

## Dependencies

numpy (>=2.0), dearpygui. Dev: pytest, ruff. Optional: mypy.

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

- Nothing outside `gui/` imports dearpygui. Logic worth testing belongs in the core.
- `simulate()`/`simulate_paths()` take an optional `rng: np.random.Generator`. Tests always
  pass a seeded one. The GUI uses the unseeded module default.
- Shared controls (RUNS, STEPS, WALL, SLOPE) are read only through
  `gui.controls.read_shared_params()`, which validates via `params.validate()` and returns
  `(WalkParams, None)` or `(None, error)`. Don't read these widgets directly anywhere else.
- One `Playback`/`Transport` per timeline. There is one, prefix "anim", owned by
  `AnimationTab`. Don't re-introduce per-mode playback state.
- Caching: each animation mode stores its data in `AnimationTab.data[mode]` with a `cache_key`
  that is the `WalkParams` it was simulated from. Play resumes without re-simulating when the
  current params equal the key.
- Keep the Static tab simple. It has no timeline.

## Dear PyGui rules learned the hard way

- Callback signature: DPG counts a callback's parameters and passes that many positional args.
  Never use `lambda s, a, u, t=tab:`. Pass `user_data=` instead. Bound methods work. Use
  either no parameters or exactly `(self, sender, app_data, user_data)`; both are verified.
- Don't use `on_enter=True` on input widgets. It discards uncommitted typed values when focus
  moves to Run. Use a global key-press handler instead.
- Item visibility handlers only fire while the item is visible. The tick handler is bound to
  the primary window, and `Transport.advance()` checks plot visibility itself. Don't bind to
  individual plots.
- `get_axis_limits` and similar queries can return stale values until a frame has rendered.
  Render a frame before asserting on them.
- Axis limits are float32 internally. Compare with a tolerance.
- `dpg.output_frame_buffer` writes asynchronously. Render a few frames after calling it.
- Plot axes must be populated before `add_line_series(parent=...)` if a handler depends on them.
  Tab contents that are not selected are not laid out, so `get_item_rect_size` returns [0, 0].

## Testing rules

- `tests/` covers the core only and needs no display. GUI testing is deferred: the approach
  is still to be chosen, and there is no CI yet.
- For headless GUI checks, call `gui.app.build_ui()` (no render loop), drive it with
  `dpg.render_dearpygui_frame()`, then `dpg.destroy_context()`. If you call `main()` instead,
  `dpg.start_dearpygui` and `dpg.destroy_context` must BOTH be patched to no-ops first.
  Patching only the first makes `main()` destroy the context itself, and later frame renders
  then crash.
- To exercise an animation tab, switch the outer tab bar to it first. Hidden tabs do not tick.
- Behaviour-preserving changes can be checked against the legacy app by seeding both
  (`legacy.rng = ...`, `random_walk.simulation._default_rng = ...`), running the same actions,
  and comparing widget values.
- mypy: don't pin `python_version` to 3.11. numpy 2.5's stubs don't resolve for that target.

## Open items

- Planned: a seed control in the UI.
- Known physics issue (see docs/theory.md): the wall curve is a half-normal centred on the
  wall and ignores that the walk starts at 0; the folded normal phi(y) + phi(2w - y) is the
  correct large-STEPS curve at theta = 0.
- Memory: `simulate_paths` at MAX_JUMPS allocates two int64 (runs, steps) arrays (~400 MB
  each).
- Decide on a GUI testing approach and on CI (GitHub Actions).
