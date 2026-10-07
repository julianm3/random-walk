"""Default values and limits shared by the simulation core and the GUI."""

# Shared parameters
DEFAULT_RUNS = 10_000
DEFAULT_STEPS = 1000
DEFAULT_WALL = -30  # default wall location, editable in the UI
DEFAULT_SLOPE = 0.0  # default bias angle theta (degrees), editable in the UI
MIN_SLOPE = -90.0
MAX_SLOPE = 90.0
MAX_RUNS_INPUT = 100_000_000  # upper bound the RUNS box accepts (MAX_JUMPS usually binds first)
MAX_JUMPS = 50_000_000  # RUNS * STEPS limit, to avoid running out of memory
MAX_STEPS = 200_000  # separate cap: simulate() loops once per step, so this bounds that loop

# Playback
FPS = 30  # "real time" is 1 simulated step per rendered frame at this rate
SLOW_SECONDS = 300  # "slow" condenses the whole timeline to this many seconds
FAST_SECONDS = 30  # "fast" condenses the whole timeline to this many seconds
FAST_BOOST = 4.0  # fast-forward/reverse: this multiple of whatever the speed slider is set to
MIN_SPEED = 0.01  # steps/sec floor for the speed slider and presets

# Animation display
DEFAULT_MAX_LINES = 200  # spaghetti-plot cap for "All Paths"
MAX_LINES_CAP = 5000  # upper bound a user can type into that cap
HIST_X_MAX = 0.3  # fixed x-axis cap for "Evolving Histogram"
