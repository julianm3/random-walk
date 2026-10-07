"""Interactive 1D random walk - originally a Dear PyGui port of walk_app.py, now developed
independently (see walk_app.py for the earlier shared wall/reflect/theory logic, but this
file is no longer kept in sync with it).

Two tabs:
  Static    - one histogram of final positions (the original, non-animated behaviour).
  Animation - one shared plot and one shared timeline, with a dropdown choosing which of four
              displays is currently shown:
                Distribution       - runs are added one at a time to a growing histogram.
                Single Walk        - pick one walk (max/min ending point, or the nth one) and
                                      watch its position step by step. Multiple walks can be
                                      added and compared; each stays on screen until Clear.
                Evolving Histogram - a histogram of every walk's CURRENT position, evolving as
                                      the steps progress.
                All Paths          - every walk's own path animating together (capped, for
                                      render performance).
              These four used to be three separate tabs (with "Evolving Histogram"/"All Paths"
              nested as a sub-choice of the third); they're flattened into peers of one
              dropdown now, sharing a single plot and a single playback engine instead of each
              duplicating their own.

Both tabs share one RUNS/STEPS/WALL/SLOPE control panel at the top. The Animation tab's
playback engine (play/pause/step/fast-forward/reverse, a speed slider, Real/Slow/Fast presets
and a scrubber) - see new_tab_state()/advance()/the transport_* functions - is written
generically over a "tab" key, a holdover from when there were three independent instances of
it; now there's exactly one, keyed "anim".
"""
import numpy as np
import dearpygui.dearpygui as dpg

DEFAULT_RUNS = 10_000
DEFAULT_STEPS = 1000
DEFAULT_WALL = -30         # default wall location, editable in the UI
DEFAULT_SLOPE = 0.0        # default bias angle theta (degrees), editable in the UI
MAX_JUMPS = 50_000_000     # RUNS * STEPS limit, to avoid running out of memory
MAX_STEPS = 200_000        # separate cap: simulate() loops once per step, so this bounds that loop

FPS = 30                   # "real time" is 1 simulated step per rendered frame at this rate
SLOW_SECONDS = 300          # "slow" condenses the whole timeline to this many seconds
FAST_SECONDS = 30           # "fast" condenses the whole timeline to this many seconds
DEFAULT_MAX_LINES = 200     # spaghetti-plot cap for "All Paths"
MAX_LINES_CAP = 5000        # upper bound a user can type into that cap
HIST_X_MAX = 0.3            # fixed x-axis cap for "Evolving Histogram" (see _apply_mode_visuals)

rng = np.random.default_rng()


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate(runs, steps, wall=DEFAULT_WALL, theta=DEFAULT_SLOPE):
    """Return final positions of `runs` walks of `steps` jumps of +1 or -1.

    `theta` (degrees, -90 to 90) biases the walk: P(right) = 0.5 - 0.5*sin(theta), so
    P(left) = 0.5 + 0.5*sin(theta). Positive theta biases left, negative biases right;
    theta=0 is the unbiased 50/50 case, and +/-90 make the walk fully one-directional.

    If `wall` is a number, a step that would take the position below it is mirrored back
    above it instead: position -> 2*wall - position. If `wall` is None, the walk is
    unrestricted (the simple case).
    """
    p_right = 0.5 - 0.5 * np.sin(np.radians(theta))
    jumps = rng.choice([-1, 1], size=(runs, steps), p=[1 - p_right, p_right])
    if wall is None:
        return jumps.sum(axis=1)

    positions = np.zeros(runs, dtype=np.int64)
    for i in range(steps):
        positions += jumps[:, i]
        np.abs(positions - wall, out=positions)  # fold anything below the wall back above it
        positions += wall
    return positions


def simulate_paths(runs, steps, wall=DEFAULT_WALL, theta=DEFAULT_SLOPE):
    """Like simulate(), but returns the whole position history, not just the final one.

    Shape (runs, steps + 1): column 0 is the starting position (always 0), column k is the
    position after k steps - so paths[:, -1] is exactly what simulate() would have returned.
    Used by the Single Walk and the two All-Walks-style animations, which need to see the
    path, not just where it ended up.
    """
    p_right = 0.5 - 0.5 * np.sin(np.radians(theta))
    jumps = rng.choice([-1, 1], size=(runs, steps), p=[1 - p_right, p_right])
    paths = np.zeros((runs, steps + 1), dtype=np.int64)
    if wall is None:
        np.cumsum(jumps, axis=1, out=paths[:, 1:])
    else:
        for i in range(steps):
            paths[:, i + 1] = paths[:, i] + jumps[:, i]
            np.abs(paths[:, i + 1] - wall, out=paths[:, i + 1])
            paths[:, i + 1] += wall
    return paths


def summarize(finals, steps, wall_enabled, wall_value=DEFAULT_WALL, theta=DEFAULT_SLOPE,
              bins=None, curve_x_range=None):
    """Given an array of final positions, return what a histogram plot needs: bin centers/
    counts, the theory curve's x/y, whether to show that curve, and a one-line stats string.

    `bins` and `curve_x_range` can be fixed externally (rather than derived from `finals`)
    so the axes don't jump around when `finals` is a growing prefix of a larger run, as in
    the distribution animation.
    """
    if bins is None:
        bins = np.arange(finals.min() - 1, finals.max() + 2, 2)
    counts, edges = np.histogram(finals, bins=bins, density=True)
    centers = edges[:-1] + 1

    # Per-step mean = -sin(theta), per-step variance = cos^2(theta) (from p_right = 0.5 -
    # 0.5*sin(theta) above); both reduce to the unbiased case's 0 and 1 at theta=0.
    theta_rad = np.radians(theta)
    mean_theory = -steps * np.sin(theta_rad)
    sigma = np.sqrt(steps) * abs(np.cos(theta_rad))

    x_lo, x_hi = curve_x_range if curve_x_range is not None else (
        (wall_value, finals.max()) if wall_enabled else (finals.min(), finals.max()))

    show_curve = True
    if wall_enabled:
        # Large-STEPS approximation: distance above the wall ~ half-normal(sigma = sqrt(STEPS)).
        # Only derived (via the reflection principle) for a driftless walk, so only valid at
        # theta=0 - a biased walk reflected off a wall is a materially different, more involved
        # problem, and this curve would just be wrong for it. Hide it rather than show a guess.
        show_curve = theta == 0
        x = np.linspace(x_lo, x_hi, 400)
        curve = (2 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-((x - wall_value) ** 2) / (2 * sigma ** 2))
    else:
        # Theory: final position is approximately Normal(mean_theory, sigma) - see above.
        x = np.linspace(x_lo, x_hi, 400)
        curve = np.exp(-(x - mean_theory) ** 2 / (2 * sigma ** 2)) / (sigma * np.sqrt(2 * np.pi))

    stats = f"mean = {finals.mean():.2f}, sd = {finals.std():.2f}"
    if not wall_enabled:
        stats += f" (theory: {mean_theory:.2f}, {sigma:.2f})"
    stats += f", min = {finals.min()}, max = {finals.max()}"

    return centers, counts, x, curve, stats, show_curve


def compute(runs, steps, wall_enabled, wall_value=DEFAULT_WALL, theta=DEFAULT_SLOPE):
    """Run the simulation and return everything the static plot and stats line need."""
    wall = wall_value if wall_enabled else None
    finals = simulate(runs, steps, wall, theta)
    centers, counts, x, curve, stats, show_curve = summarize(
        finals, steps, wall_enabled, wall_value, theta)

    title = f"{runs:,} walks of {steps:,} steps"
    if wall_enabled:
        title += f", wall at {wall_value}"
    if theta != 0:
        title += f", slope = {theta:g} deg"

    return centers, counts, x, curve, stats, title, show_curve


def read_shared_params():
    """Read + validate the shared RUNS/STEPS/WALL/SLOPE controls.

    Returns (runs, steps, wall_enabled, wall_value, theta, error). On failure, error is a
    message to display and the other fields are None.
    """
    runs = dpg.get_value("runs_input")
    steps = dpg.get_value("steps_input")
    if runs < 1 or steps < 1:
        return None, None, None, None, None, "RUNS and STEPS must be at least 1"
    if runs * steps > MAX_JUMPS:
        return None, None, None, None, None, f"RUNS x STEPS is too large (max {MAX_JUMPS:,})"
    if steps > MAX_STEPS:
        return None, None, None, None, None, f"STEPS is too large (max {MAX_STEPS:,})"

    theta = dpg.get_value("slope_input")
    if not -90 <= theta <= 90:
        return None, None, None, None, None, "SLOPE must be between -90 and 90 degrees"

    wall_enabled = dpg.get_value("wall_checkbox")
    wall_value = dpg.get_value("wall_input")
    return runs, steps, wall_enabled, wall_value, theta, None


# ---------------------------------------------------------------------------
# Static tab (unchanged behaviour, just reading shared params through the helper above)
# ---------------------------------------------------------------------------

def run_callback():
    runs, steps, wall_enabled, wall_value, theta, error = read_shared_params()
    if error:
        dpg.set_value("stats_text", error)
        return

    centers, counts, x, curve, stats, title, show_curve = compute(
        runs, steps, wall_enabled, wall_value, theta)

    # View rotated 90 degrees clockwise from the original vertical histogram: position moves
    # from the x-axis to the y-axis (with the y-axis inverted, so increasing position points
    # down the screen, not up - that's what makes it clockwise rather than counterclockwise),
    # density from y to x. Dear PyGui's horizontal bar series takes (length, category) as
    # (x, y) - i.e. density is x, position is y - the opposite order from the vertical case.
    dpg.set_value("hist_series", [counts.tolist(), centers.tolist()])
    dpg.set_value("curve_series", [curve.tolist(), x.tolist()])
    dpg.configure_item("curve_series", show=show_curve)

    if wall_enabled:
        top = max(counts.max(), curve.max() if show_curve else 0) * 1.15
        dpg.set_value("wall_series", [[0, top], [wall_value, wall_value]])
        dpg.configure_item("wall_series", show=True)
    else:
        dpg.configure_item("wall_series", show=False)

    dpg.set_value("stats_text", stats)
    print(f"RUNS={runs}, STEPS={steps}: {stats}")
    dpg.configure_item("plot", label=title)

    dpg.fit_axis_data("x_axis")
    dpg.fit_axis_data("y_axis")


def run_on_enter(sender, key):
    """Run the Static tab when Enter/Return is pressed, anywhere - including with nothing
    focused and nothing changed, to simply repeat the current test again.

    Deliberately not using add_input_int's own on_enter=True: that flag also changes how the
    widget commits its value (discarding a typed-but-unconfirmed edit on any focus loss other
    than Enter), which is the bug already fixed once. This is a global key handler instead.
    """
    if key in (dpg.mvKey_Return, dpg.mvKey_NumPadEnter):
        run_callback()


# ---------------------------------------------------------------------------
# Shared playback engine for the Animation tab
# ---------------------------------------------------------------------------

# Keyed by tab name; historically three independent entries ("dist"/"single"/"all"), one per
# tab. Now there's exactly one, "anim" - this whole section is otherwise untouched, since it
# was already written generically over a `tab` key rather than hardcoding which one.
_tabs = {}
_preset_active_theme = None  # set once in main(); highlights whichever Real/Slow/Fast is active


def new_tab_state(redraw):
    return {
        "n": 0,               # number of frames (0..n-1); 0 until Start/Add has run once
        "frame": 0.0,         # current, possibly fractional, frame position
        "base_speed": FPS,    # steps/sec, set by the speed slider or a preset button
        "boost": 1.0,         # temporary multiplier while fast-forward/reverse is engaged
        "direction": 1,
        "playing": False,
        "last_time": 0.0,
        "last_drawn": -1,
        "redraw": redraw,     # callable(frame_int) -> None
        "data": None,         # per-tab payload, set by that tab's Start/Add callback
        "speed_touched": False,  # has the user explicitly picked a speed? (vs. the default)
    }


TAB_PLOTS = {"anim": "anim_plot"}


def advance(tab):
    """Called every rendered frame (see tick_all()) to move playback forward/backward in real
    time and redraw whenever the integer frame changes.

    Checks its own tab's plot visibility rather than relying on a handler bound to that plot:
    a handler bound directly to single_plot was once observed to never fire at all on the very
    first walk added to it (empty axis with no series yet when the handler was registered),
    while the exact same mechanism worked fine for plots that always start with at least one
    series already present. Binding instead to the primary window - which is visible from
    before any of this exists - sidesteps that dependency entirely."""
    st = _tabs[tab]
    if st["n"] == 0:
        return  # nothing has been started yet - nothing to draw
    if not dpg.is_item_visible(TAB_PLOTS[tab]):
        return  # the Animation tab isn't the one currently open - stay paused, save CPU too
    now = dpg.get_total_time()
    if st["playing"] and st["n"] > 1:
        dt = now - st["last_time"]
        st["frame"] += dt * st["base_speed"] * st["boost"] * st["direction"]
        # Only treat hitting 0 as "rewound past the start" while actually playing backwards.
        # Otherwise, starting fresh at frame 0 while playing forward - where dt can land at
        # exactly 0.0 on the very first tick if it lands in the same frame as the Play click,
        # since get_total_time() is cached per frame - left frame sitting at exactly 0, which
        # used to match this check regardless of direction and immediately re-paused playback
        # before it ever moved. That's the bug behind "Play does nothing at the start."
        if st["direction"] < 0 and st["frame"] <= 0:
            st["frame"] = 0.0
            st["playing"] = False
        elif st["direction"] > 0 and st["frame"] >= st["n"] - 1:
            st["frame"] = float(st["n"] - 1)
            st["playing"] = False
        else:
            st["frame"] = max(0.0, min(st["frame"], st["n"] - 1))
        _sync_play_pause_label(tab)  # playing can have just auto-stopped at either end above
    st["last_time"] = now

    frame_int = int(round(st["frame"]))
    if frame_int != st["last_drawn"]:
        st["redraw"](frame_int)
        st["last_drawn"] = frame_int
    scrub_tag = f"{tab}_scrub"
    if dpg.does_item_exist(scrub_tag):
        dpg.set_value(scrub_tag, st["frame"])


def _sync_play_pause_label(tab):
    """Keeps the combined Play/Pause button's text matching actual playback state - needed
    because `playing` can flip to False on its own (reaching either end of the timeline), not
    just from clicking the button itself."""
    tag = f"{tab}_play_pause"
    if dpg.does_item_exist(tag):
        dpg.set_item_label(tag, "Pause" if _tabs[tab]["playing"] else "Play")


def _jump_to(tab, frame_int):
    """Step/scrub/Restart/Finish helper: pause, move to an exact frame, redraw immediately."""
    st = _tabs[tab]
    st["playing"] = False
    _sync_play_pause_label(tab)
    if st["n"] == 0:
        return  # nothing has been started yet - nothing to draw
    frame_int = max(0, min(frame_int, st["n"] - 1))
    st["frame"] = float(frame_int)
    st["redraw"](frame_int)
    st["last_drawn"] = frame_int
    dpg.set_value(f"{tab}_scrub", st["frame"])


def _rewind_if_at_boundary(tab, direction):
    """Pressing Play/Reverse/FF/FR while already sitting at the end it would play toward
    should restart from the other end, not just resume-and-immediately-re-stop (which is
    what happens otherwise: advance() sees frame already at that boundary and auto-pauses
    again on the very first tick). This matters more now that switching to a mode you've
    already run restores it at its finished frame - the first Play after that would
    otherwise silently do nothing."""
    st = _tabs[tab]
    if st["n"] == 0:
        return
    if direction > 0 and st["frame"] >= st["n"] - 1:
        st["frame"] = 0.0
    elif direction < 0 and st["frame"] <= 0:
        st["frame"] = float(st["n"] - 1)


def transport_play(sender, app_data, tab):
    _rewind_if_at_boundary(tab, 1)
    st = _tabs[tab]
    st["direction"] = 1
    st["boost"] = 1.0
    st["playing"] = True
    st["last_time"] = dpg.get_total_time()
    _sync_play_pause_label(tab)


def transport_reverse(sender, app_data, tab):
    _rewind_if_at_boundary(tab, -1)
    st = _tabs[tab]
    st["direction"] = -1
    st["boost"] = 1.0
    st["playing"] = True
    st["last_time"] = dpg.get_total_time()
    _sync_play_pause_label(tab)


def transport_pause(sender, app_data, tab):
    _tabs[tab]["playing"] = False
    _sync_play_pause_label(tab)


def transport_play_pause(sender, app_data, tab):
    """The combined Play/Pause button: pauses if currently playing, otherwise plays - using
    whatever "play" means for this tab (plain resume/start, or the Animation tab's
    play-or-start override), via the play_fn stashed by build_transport()."""
    st = _tabs[tab]
    if st["playing"]:
        transport_pause(sender, app_data, tab)
    else:
        st["play_fn"](sender, app_data, tab)
    _sync_play_pause_label(tab)


def transport_restart(sender, app_data, tab):
    _jump_to(tab, 0)


def transport_finish(sender, app_data, tab):
    _jump_to(tab, _tabs[tab]["n"] - 1)


def transport_fast(tab, direction):
    _rewind_if_at_boundary(tab, direction)
    st = _tabs[tab]
    st["direction"] = direction
    st["boost"] = 4.0  # fast-forward/reverse: 4x whatever the speed slider is currently set to
    st["playing"] = True
    st["last_time"] = dpg.get_total_time()
    _sync_play_pause_label(tab)


def transport_ff(sender, app_data, tab):
    transport_fast(tab, 1)


def transport_fr(sender, app_data, tab):
    transport_fast(tab, -1)


def transport_step_fwd(sender, app_data, tab):
    _jump_to(tab, int(round(_tabs[tab]["frame"])) + 1)


def transport_step_back(sender, app_data, tab):
    _jump_to(tab, int(round(_tabs[tab]["frame"])) - 1)


def highlight_preset(tab, which):
    """Gives whichever of the Real/Slow/Fast buttons matches `which` ("real"/"slow"/"fast"/
    None) the highlighted theme, and clears it from the other two."""
    for name in ("real", "slow", "fast"):
        tag = f"{tab}_preset_{name}"
        if dpg.does_item_exist(tag):
            dpg.bind_item_theme(tag, _preset_active_theme if name == which else 0)


def _matching_preset(tab):
    """Which preset (if any) the tab's current base_speed matches, for when the speed was
    set some other way (the slider, or a stale highlight after STEPS/RUNS changed)."""
    st = _tabs[tab]
    candidates = {"real": float(FPS)}
    if st["n"] > 1:
        candidates["slow"] = st["n"] / SLOW_SECONDS
        candidates["fast"] = st["n"] / FAST_SECONDS
    for name, value in candidates.items():
        if value > 0 and abs(st["base_speed"] - value) / value < 1e-6:
            return name
    return None


def transport_speed_changed(sender, app_data, tab):
    _tabs[tab]["base_speed"] = app_data
    _tabs[tab]["boost"] = 1.0
    _tabs[tab]["speed_touched"] = True
    highlight_preset(tab, _matching_preset(tab))


def _set_speed_from_duration(tab, duration, preset_name, touched=True):
    """duration=None means "real time" (1 step per frame at FPS); otherwise the whole
    timeline (0..n-1) is condensed into that many seconds. `touched=False` is for the
    internal default-to-Fast-on-Start case, which shouldn't count as the user's own choice."""
    st = _tabs[tab]
    speed = float(FPS) if duration is None else st["n"] / duration
    speed = max(speed, 0.01)
    st["base_speed"] = speed
    st["boost"] = 1.0
    if touched:
        st["speed_touched"] = True
    if dpg.does_item_exist(f"{tab}_speed"):
        dpg.set_value(f"{tab}_speed", speed)
    highlight_preset(tab, preset_name)


def transport_preset_real(sender, app_data, tab):
    _set_speed_from_duration(tab, None, "real")


def transport_preset_slow(sender, app_data, tab):
    _set_speed_from_duration(tab, SLOW_SECONDS, "slow")


def transport_preset_fast(sender, app_data, tab):
    _set_speed_from_duration(tab, FAST_SECONDS, "fast")


def transport_scrub(sender, app_data, tab):
    _jump_to(tab, int(round(app_data)))


def build_transport(tab, play_callback=None):
    """The play/pause/step/speed/scrubber row.

    `play_callback` overrides what the combined Play/Pause button's "play" side does
    (defaults to the plain resume/start behaviour in transport_play) - the Animation tab uses
    this to make Play also act as Start for three of its four modes, which have no separate
    Start button."""
    _tabs[tab]["play_fn"] = play_callback or transport_play
    with dpg.group(horizontal=True):
        dpg.add_button(label="Restart", callback=transport_restart, user_data=tab)
        dpg.add_button(label="Step Back", callback=transport_step_back, user_data=tab)
        dpg.add_button(label="Reverse", callback=transport_reverse, user_data=tab)
        dpg.add_button(label="Play", tag=f"{tab}_play_pause",
                        callback=transport_play_pause, user_data=tab)
        dpg.add_button(label="Fast Fwd", callback=transport_ff, user_data=tab)
        dpg.add_button(label="Step Fwd", callback=transport_step_fwd, user_data=tab)
        dpg.add_button(label="Jump to Finish", callback=transport_finish, user_data=tab)
        dpg.add_text("  speed")
        dpg.add_slider_float(tag=f"{tab}_speed", default_value=FPS, min_value=0.01,
                              max_value=FPS * 4, width=140, format="%.1f/s",
                              callback=transport_speed_changed, user_data=tab)
        dpg.add_button(label="Real", tag=f"{tab}_preset_real",
                        callback=transport_preset_real, user_data=tab)
        dpg.add_button(label="Slow", tag=f"{tab}_preset_slow",
                        callback=transport_preset_slow, user_data=tab)
        dpg.add_button(label="Fast", tag=f"{tab}_preset_fast",
                        callback=transport_preset_fast, user_data=tab)
    dpg.add_slider_float(tag=f"{tab}_scrub", default_value=0.0, min_value=0, max_value=1,
                          width=-1, clamped=True, callback=transport_scrub, user_data=tab)


def tick_all(sender=None, app_data=None, user_data=None):
    """Called once per rendered frame, bound to the always-visible primary window (see
    bind_tick_handler() below for why not to the plot itself)."""
    advance("anim")


def bind_tick_handler():
    with dpg.item_handler_registry(tag="tick_handler_registry"):
        dpg.add_item_visible_handler(callback=tick_all)
    dpg.bind_item_handler_registry("primary", "tick_handler_registry")


def start_playback(tab, n, autoplay=True):
    """Common bookkeeping whenever a tab (re)starts: reset the frame/scrub range and, unless
    told otherwise, begin playing immediately at whatever speed is currently set."""
    st = _tabs[tab]
    st["n"] = n
    st["frame"] = 0.0
    st["last_drawn"] = -1
    st["direction"] = 1
    st["boost"] = 1.0
    st["last_time"] = dpg.get_total_time()
    st["playing"] = autoplay and n > 1
    _sync_play_pause_label(tab)
    dpg.configure_item(f"{tab}_scrub", max_value=max(n - 1, 1))
    dpg.configure_item(f"{tab}_speed", max_value=max(FPS, n / FAST_SECONDS) * 2)
    if not st["speed_touched"]:
        # Default to Fast until the user explicitly picks a speed; once they have, respect
        # that choice across subsequent Start/Add Walk clicks rather than resetting it.
        _set_speed_from_duration(tab, FAST_SECONDS, "fast", touched=False)
    else:
        # n may have changed (different STEPS/RUNS), which changes what Slow/Fast even mean -
        # refresh the highlight to match, in case it now does (or no longer does) line up.
        highlight_preset(tab, _matching_preset(tab))


# ---------------------------------------------------------------------------
# Animation tab: one shared plot and timeline; a dropdown selects which of four displays
# (Distribution / Single Walk / Evolving Histogram / All Paths) is currently showing.
# ---------------------------------------------------------------------------

ANIM_MODES = ["Distribution", "Single Walk", "Evolving Histogram", "All Paths"]

# Each mode's simulated data, cached independently - None until that mode has been run at
# least once. Keeping these separate (rather than one shared blob) means switching modes
# never loses anything, and re-running a mode with unchanged RUNS/STEPS/WALL/SLOPE just
# resumes instead of re-simulating (each has its own "cache_key" for that check).
_anim_data = {mode: None for mode in ANIM_MODES}


def _cache_key(runs, steps, wall_enabled, wall_value, theta):
    return (runs, steps, wall_enabled, wall_value, theta)


def current_anim_mode():
    return dpg.get_value("anim_mode")


# --- Distribution: runs added one at a time to a growing histogram -------------------------

def _start_distribution():
    runs, steps, wall_enabled, wall_value, theta, error = read_shared_params()
    if error:
        dpg.set_value("anim_stats_text", error)
        return

    finals = simulate(runs, steps, wall_value if wall_enabled else None, theta)
    bins = np.arange(finals.min() - 1, finals.max() + 2, 2)
    curve_x_range = (wall_value, finals.max()) if wall_enabled else (finals.min(), finals.max())

    # Fixed, once, from the COMPLETE data set, so the axes stay put while the animation
    # plays - otherwise the view would keep rescaling as each new run comes in.
    _, full_counts, _, full_curve, _, full_show_curve = summarize(
        finals, steps, wall_enabled, wall_value, theta, bins=bins, curve_x_range=curve_x_range)
    x_max = max(full_counts.max(), full_curve.max() if full_show_curve else 0) * 1.15

    title = f"{runs:,} walks of {steps:,} steps - building up run by run"
    _anim_data["Distribution"] = {
        "finals": finals, "steps": steps, "wall_enabled": wall_enabled,
        "wall_value": wall_value, "theta": theta, "bins": bins, "curve_x_range": curve_x_range,
        "cache_key": _cache_key(runs, steps, wall_enabled, wall_value, theta),
        "n": runs + 1, "x_max": x_max, "y_lo": bins.min(), "y_hi": bins.max(), "title": title,
    }
    dpg.configure_item("anim_plot", label=title)
    _apply_mode_visuals("Distribution")
    start_playback("anim", runs + 1)
    _redraw_distribution(0)
    _tabs["anim"]["last_drawn"] = 0


def _redraw_distribution(frame_int):
    data = _anim_data["Distribution"]
    if data is None:
        return
    finals_all = data["finals"]
    included = finals_all[:frame_int]

    if frame_int < 2:
        dpg.set_value("anim_hist_series", [[], []])
        dpg.configure_item("anim_curve_series", show=False)
        dpg.configure_item("anim_wall_series", show=False)
        dpg.set_value("anim_stats_text", f"{frame_int} of {len(finals_all)} runs so far")
        return

    centers, counts, x, curve, stats, show_curve = summarize(
        included, data["steps"], data["wall_enabled"], data["wall_value"], data["theta"],
        bins=data["bins"], curve_x_range=data["curve_x_range"])

    dpg.set_value("anim_hist_series", [counts.tolist(), centers.tolist()])
    dpg.set_value("anim_curve_series", [curve.tolist(), x.tolist()])
    dpg.configure_item("anim_curve_series", show=show_curve)

    if data["wall_enabled"]:
        top = max(counts.max(), curve.max() if show_curve else 0) * 1.15
        dpg.set_value("anim_wall_series", [[0, top], [data["wall_value"], data["wall_value"]]])
        dpg.configure_item("anim_wall_series", show=True)
    else:
        dpg.configure_item("anim_wall_series", show=False)

    dpg.set_value("anim_stats_text", f"{frame_int} of {len(finals_all)} runs so far - {stats}")


# --- Single Walk: one walk at a time, each kept on screen once drawn -----------------------

def _finish_active_single_walk():
    """If a walk is mid-reveal, snap it to fully drawn before starting a new one, so
    previously selected walks always end up completely shown rather than half-drawn."""
    data = _anim_data["Single Walk"]
    if data and data["active_tag"] is not None:
        path = data["active_path"]
        dpg.set_value(data["active_tag"], [list(range(len(path))), path.tolist()])


def add_walk(sender=None, app_data=None, user_data=None):
    runs, steps, wall_enabled, wall_value, theta, error = read_shared_params()
    if error:
        dpg.set_value("anim_stats_text", error)
        return

    mode = dpg.get_value("sw_mode")
    n = dpg.get_value("sw_n")
    if mode == "nth walk" and not 1 <= n <= runs:
        dpg.set_value("anim_stats_text", f"N must be between 1 and {runs}")
        return

    data = _anim_data["Single Walk"]
    if data is None:
        data = {"active_tag": None, "active_path": None, "counter": 0, "line_tags": [],
                "y_lo": None, "y_hi": None, "cache_key": None, "paths": None,
                "n": 0, "steps": 0}
        _anim_data["Single Walk"] = data

    # Reuse the same simulated batch across Add-Walk clicks (so "max" and "min" are the
    # actual max and min of one shared population, not two unrelated ones) unless RUNS/STEPS/
    # WALL/SLOPE have changed since the last click.
    cache_key = _cache_key(runs, steps, wall_enabled, wall_value, theta)
    if data["cache_key"] != cache_key:
        data["paths"] = simulate_paths(runs, steps, wall_value if wall_enabled else None, theta)
        data["cache_key"] = cache_key
    paths = data["paths"]

    finals = paths[:, -1]
    if mode == "max ending point":
        idx = int(np.argmax(finals))
    elif mode == "min ending point":
        idx = int(np.argmin(finals))
    else:
        idx = n - 1
    path = paths[idx]

    _finish_active_single_walk()

    data["counter"] += 1
    tag = f"sw_line_{data['counter']}"
    dpg.add_line_series([0], [0], label=f"walk #{idx + 1} ({mode})", tag=tag, parent="anim_y_axis")
    data["line_tags"].append(tag)
    data["active_tag"] = tag
    data["active_path"] = path
    data["steps"] = steps
    data["n"] = steps + 1
    data["title"] = f"{runs:,} walks of {steps:,} steps"

    lo, hi = int(path.min()), int(path.max())
    data["y_lo"] = lo if data["y_lo"] is None else min(data["y_lo"], lo)
    data["y_hi"] = hi if data["y_hi"] is None else max(data["y_hi"], hi)

    dpg.set_value("anim_stats_text", f"walk #{idx + 1} ({mode}): final position = {path[-1]}")
    dpg.configure_item("anim_plot", label=data["title"])
    _apply_mode_visuals("Single Walk")
    start_playback("anim", steps + 1)
    _redraw_single(0)
    _tabs["anim"]["last_drawn"] = 0


def _redraw_single(frame_int):
    data = _anim_data["Single Walk"]
    if data is None or data["active_tag"] is None:
        return
    path = data["active_path"][:frame_int + 1]
    dpg.set_value(data["active_tag"], [list(range(len(path))), path.tolist()])


def clear_single(sender=None, app_data=None, user_data=None):
    data = _anim_data["Single Walk"]
    if data is not None:
        for tag in data["line_tags"]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
    _anim_data["Single Walk"] = None
    st = _tabs["anim"]
    st["n"] = 0
    st["playing"] = False
    st["frame"] = 0.0
    st["last_drawn"] = -1
    _sync_play_pause_label("anim")
    dpg.set_axis_limits_auto("anim_x_axis")
    dpg.set_axis_limits_auto("anim_y_axis")
    dpg.set_value("anim_stats_text", "")


# --- Evolving Histogram: a histogram of every walk's current position, over steps ----------

def _start_histogram():
    runs, steps, wall_enabled, wall_value, theta, error = read_shared_params()
    if error:
        dpg.set_value("anim_stats_text", error)
        return

    paths = simulate_paths(runs, steps, wall_value if wall_enabled else None, theta)
    # Fixed bins from the global min/max seen across every step of every walk, so the view
    # doesn't keep rescaling as the spread grows over time.
    bins = np.arange(paths.min() - 1, paths.max() + 2, 2)

    title = f"{runs:,} walks of {steps:,} steps"
    _anim_data["Evolving Histogram"] = {
        "paths": paths, "bins": bins, "wall_enabled": wall_enabled, "wall_value": wall_value,
        "steps": steps, "cache_key": _cache_key(runs, steps, wall_enabled, wall_value, theta),
        "n": steps + 1, "y_lo": bins.min(), "y_hi": bins.max(), "title": title,
    }
    dpg.configure_item("anim_plot", label=title)
    _apply_mode_visuals("Evolving Histogram")
    start_playback("anim", steps + 1)
    _redraw_histogram(0)
    _tabs["anim"]["last_drawn"] = 0


def _redraw_histogram(frame_int):
    data = _anim_data["Evolving Histogram"]
    if data is None:
        return
    column = data["paths"][:, frame_int]
    counts, edges = np.histogram(column, bins=data["bins"])  # raw counts, not density
    fractions = counts / len(column)  # each bin's share of all walks - sums to 1.0
    centers = edges[:-1] + 1
    dpg.set_value("anim_hist_series", [fractions.tolist(), centers.tolist()])

    if data["wall_enabled"]:
        dpg.set_value("anim_wall_series", [[0, HIST_X_MAX], [data["wall_value"], data["wall_value"]]])
        dpg.configure_item("anim_wall_series", show=True)
    else:
        dpg.configure_item("anim_wall_series", show=False)

    dpg.set_value("anim_stats_text",
                  f"step {frame_int} of {data['steps']}: mean = {column.mean():.2f}, sd = {column.std():.2f}")


# --- All Paths: every walk's own path animating together (capped for render performance) ---

def _start_paths():
    runs, steps, wall_enabled, wall_value, theta, error = read_shared_params()
    if error:
        dpg.set_value("anim_stats_text", error)
        return

    max_lines = dpg.get_value("ap_max_lines")
    paths = simulate_paths(runs, steps, wall_value if wall_enabled else None, theta)
    count = min(runs, max_lines)
    sample_idx = np.linspace(0, runs - 1, count).astype(int)

    old = _anim_data["All Paths"]
    if old is not None:
        for tag in old["line_tags"]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

    # Start each line with just its first point; _redraw_paths() grows them frame by frame -
    # the x-axis is static, so this can't just be a full line revealed via a moving axis
    # limit (the cheaper trick this used before being split out into its own mode) - each
    # line's own data has to grow instead.
    line_tags = []
    for k, idx in enumerate(sample_idx):
        tag = f"ap_line_{k}"
        dpg.add_line_series([0], [int(paths[idx, 0])], tag=tag, parent="anim_y_axis")
        line_tags.append(tag)

    title = f"{runs:,} walks of {steps:,} steps ({count} shown)"
    _anim_data["All Paths"] = {
        "paths": paths, "line_tags": line_tags, "sample_idx": sample_idx, "steps": steps,
        "cache_key": _cache_key(runs, steps, wall_enabled, wall_value, theta),
        "n": steps + 1, "y_lo": paths.min(), "y_hi": paths.max(), "title": title,
    }
    dpg.configure_item("anim_plot", label=title)
    _apply_mode_visuals("All Paths")
    start_playback("anim", steps + 1)
    _redraw_paths(0)
    _tabs["anim"]["last_drawn"] = 0


def _redraw_paths(frame_int):
    data = _anim_data["All Paths"]
    if data is None:
        return
    xs = list(range(frame_int + 1))
    for tag, idx in zip(data["line_tags"], data["sample_idx"]):
        dpg.set_value(tag, [xs, data["paths"][idx, :frame_int + 1].tolist()])
    column = data["paths"][:, frame_int]
    dpg.set_value("anim_stats_text",
                  f"step {frame_int} of {data['steps']}: mean = {column.mean():.2f}, sd = {column.std():.2f}")


# --- Mode dispatch: one dropdown, one Play button, one redraw callback ----------------------

_STARTERS = {
    "Distribution": _start_distribution,
    "Evolving Histogram": _start_histogram,
    "All Paths": _start_paths,
}
_REDRAWERS = {
    "Distribution": _redraw_distribution,
    "Single Walk": _redraw_single,
    "Evolving Histogram": _redraw_histogram,
    "All Paths": _redraw_paths,
}
_X_LABELS = {
    "Distribution": "probability density",
    "Single Walk": "step",
    "Evolving Histogram": "fraction of walks",
    "All Paths": "step",
}


def redraw_anim(frame_int):
    _REDRAWERS[current_anim_mode()](frame_int)


def play_or_start_anim(sender, app_data, tab):
    """What the combined Play/Pause button's "play" side does for the Animation tab: Single
    Walk has its own dedicated Add Walk button for starting something new, so Play there is
    always a plain resume. The other three modes have no separate Start button - Play
    (re)simulates if there's no data yet, or RUNS/STEPS/WALL/SLOPE changed since last time;
    otherwise it's a plain resume too (same pattern as the old Distribution-only version)."""
    mode = current_anim_mode()
    if mode == "Single Walk":
        transport_play(sender, app_data, tab)
        return
    runs, steps, wall_enabled, wall_value, theta, error = read_shared_params()
    data = _anim_data[mode]
    cache_key = None if error else _cache_key(runs, steps, wall_enabled, wall_value, theta)
    if error or data is None or data["cache_key"] != cache_key:
        _STARTERS[mode]()
    else:
        transport_play(sender, app_data, tab)


def _apply_mode_visuals(mode):
    """Shows/hides this mode's controls and series, and sets the axis labels/ranges - shared
    by each mode's own _start_*()/add_walk() (right after it (re)computes data) and by the
    dropdown's on_anim_mode_changed() (which may have no data yet for the newly chosen mode)."""
    data = _anim_data[mode]

    dpg.configure_item("sw_controls", show=(mode == "Single Walk"))
    dpg.configure_item("ap_controls", show=(mode == "All Paths"))
    dpg.configure_item("anim_x_axis", label=_X_LABELS[mode])

    is_bar_mode = mode in ("Distribution", "Evolving Histogram")
    dpg.configure_item("anim_hist_series", show=is_bar_mode and data is not None)
    dpg.configure_item("anim_curve_series", show=False)  # only _redraw_distribution re-shows it
    dpg.configure_item("anim_wall_series", show=False)   # only the two histogram redraws do

    sw_data = _anim_data["Single Walk"]
    for tag in (sw_data["line_tags"] if sw_data else []):
        dpg.configure_item(tag, show=(mode == "Single Walk"))
    ap_data = _anim_data["All Paths"]
    for tag in (ap_data["line_tags"] if ap_data else []):
        dpg.configure_item(tag, show=(mode == "All Paths"))

    if data is not None:
        if mode == "Distribution":
            dpg.set_axis_limits("anim_x_axis", 0, data["x_max"])
        elif mode == "Evolving Histogram":
            dpg.set_axis_limits("anim_x_axis", 0, HIST_X_MAX)
        else:
            dpg.set_axis_limits("anim_x_axis", 0, data["steps"])
        dpg.set_axis_limits("anim_y_axis", data["y_lo"], data["y_hi"])
    else:
        # Nothing simulated for this mode yet - a reasonable placeholder until Play/Add Walk.
        if mode == "Evolving Histogram":
            dpg.set_axis_limits("anim_x_axis", 0, HIST_X_MAX)
        elif mode in ("Single Walk", "All Paths"):
            dpg.set_axis_limits("anim_x_axis", 0, DEFAULT_STEPS)
        else:
            dpg.set_axis_limits_auto("anim_x_axis")
        dpg.set_axis_limits_auto("anim_y_axis")


def on_anim_mode_changed(sender=None, app_data=None, user_data=None):
    """Switching modes always pauses and shows that mode's last known state: Single Walk's
    walks are genuinely persistent (the whole point of that mode), so it's restored exactly
    as left; the other three re-show their last completed run (if any) rather than replaying
    it, since replaying is just one Play click away and that click is cheap (cache_key skips
    re-simulating when RUNS/STEPS/WALL/SLOPE haven't changed)."""
    mode = current_anim_mode()
    data = _anim_data[mode]
    st = _tabs["anim"]
    st["n"] = data["n"] if data else 0
    st["frame"] = float(st["n"] - 1) if data else 0.0
    st["playing"] = False
    st["last_drawn"] = -1
    dpg.configure_item("anim_scrub", max_value=max(st["n"] - 1, 1))
    dpg.set_value("anim_scrub", st["frame"])
    _sync_play_pause_label("anim")
    _apply_mode_visuals(mode)
    if data is not None:
        dpg.configure_item("anim_plot", label=data["title"])
        redraw_anim(int(round(st["frame"])))
    else:
        dpg.configure_item("anim_plot", label="")
        dpg.set_value("anim_stats_text", "")


# ---------------------------------------------------------------------------
# UI assembly
# ---------------------------------------------------------------------------

def build_preset_theme():
    """A distinct button theme used to highlight whichever of Real/Slow/Fast is active."""
    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 120, 200), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 140, 220), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (30, 100, 180), category=dpg.mvThemeCat_Core)
    return theme


def main():
    global _preset_active_theme
    dpg.create_context()
    _preset_active_theme = build_preset_theme()
    dpg.create_viewport(title="Random Walk (Dear PyGui)", width=1050, height=800)

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=run_on_enter)

    _tabs["anim"] = new_tab_state(redraw_anim)

    with dpg.window(tag="primary"):
        # Shared parameters, used by every tab.
        with dpg.group(horizontal=True):
            # label="" (a separate add_text instead) puts the label to the LEFT of each box -
            # add_input_int's own label always renders to its right.
            dpg.add_text("RUNS")
            dpg.add_input_int(default_value=DEFAULT_RUNS, tag="runs_input",
                               width=120, min_value=1, min_clamped=True, max_value=100_000_000)
            dpg.add_text("STEPS")
            dpg.add_input_int(default_value=DEFAULT_STEPS, tag="steps_input",
                               width=120, min_value=1, min_clamped=True, max_value=MAX_STEPS)
            dpg.add_checkbox(label="enable wall", default_value=False, tag="wall_checkbox")
            dpg.add_text("WALL")
            dpg.add_input_int(default_value=DEFAULT_WALL, tag="wall_input", width=90)
            dpg.add_text("SLOPE")
            dpg.add_input_float(default_value=DEFAULT_SLOPE, tag="slope_input", width=100,
                                 min_value=-90, max_value=90, min_clamped=True, max_clamped=True,
                                 format="%.1f")
        dpg.add_separator()

        with dpg.tab_bar():
            with dpg.tab(label="Static"):
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Run", callback=run_callback)
                dpg.add_text("", tag="stats_text")
                dpg.add_spacer(height=4)
                with dpg.plot(label="", tag="plot", height=-1, width=-1):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="probability density", tag="x_axis")
                    with dpg.plot_axis(dpg.mvYAxis, label="final position", tag="y_axis", invert=True):
                        dpg.add_bar_series([], [], weight=2.0, horizontal=True,
                                            label="simulation", tag="hist_series")
                        dpg.add_line_series([], [], label="theory", tag="curve_series")
                        dpg.add_line_series([], [], label="wall", tag="wall_series", show=False)

            with dpg.tab(label="Animation"):
                with dpg.group(horizontal=True):
                    dpg.add_text("Show")
                    dpg.add_combo(ANIM_MODES, default_value="Distribution", tag="anim_mode",
                                  width=200, callback=on_anim_mode_changed)
                with dpg.group(horizontal=True, tag="sw_controls", show=False):
                    dpg.add_radio_button(["max ending point", "min ending point", "nth walk"],
                                          default_value="max ending point", tag="sw_mode",
                                          horizontal=True)
                    dpg.add_text("N")
                    dpg.add_input_int(default_value=1, tag="sw_n", width=90,
                                       min_value=1, min_clamped=True)
                    dpg.add_button(label="Add Walk", callback=add_walk)
                    dpg.add_button(label="Clear", callback=clear_single)
                with dpg.group(horizontal=True, tag="ap_controls", show=False):
                    dpg.add_text("max lines")
                    dpg.add_input_int(default_value=DEFAULT_MAX_LINES, tag="ap_max_lines",
                                       width=100, min_value=1, max_value=MAX_LINES_CAP,
                                       min_clamped=True, max_clamped=True)
                dpg.add_text("", tag="anim_stats_text")
                with dpg.plot(label="", tag="anim_plot", height=-60, width=-1):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="probability density", tag="anim_x_axis")
                    with dpg.plot_axis(dpg.mvYAxis, label="final position", tag="anim_y_axis", invert=True):
                        dpg.add_bar_series([], [], weight=2.0, horizontal=True,
                                            label="simulation", tag="anim_hist_series")
                        dpg.add_line_series([], [], label="theory", tag="anim_curve_series")
                        dpg.add_line_series([], [], label="wall", tag="anim_wall_series", show=False)
                build_transport("anim", play_callback=play_or_start_anim)

    bind_tick_handler()

    # Show these defaults up front, before Play/Add Walk has ever been pressed, rather than
    # only once the first run actually sets them.
    highlight_preset("anim", "fast")
    on_anim_mode_changed()

    dpg.set_primary_window("primary", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    run_callback()  # draw the Static tab's defaults on startup

    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
