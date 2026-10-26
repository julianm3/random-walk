"""Default values and limits shared by the simulation core and the GUI."""

# Shared parameters
DEFAULT_RUNS = 10_000
DEFAULT_STEPS = 1000
DEFAULT_WALL = -30  # default wall location, editable in the UI
MIN_WALL = -120  # lowest wall position the Wall dialog accepts
MAX_WALL = -1  # highest: just left of the start
DEFAULT_P_RIGHT = 0.5  # default probability of a +1 step, editable in the UI
DEFAULT_SEED = 42  # seeds the default random generator, so every run sees the same data
MAX_JUMPS = 50_000_000  # RUNS * STEPS limit, to avoid running out of memory
MAX_STEPS = 200_000  # separate cap: simulate() loops once per step, so this bounds that loop

# Playback
FPS = 30  # "real time" is 1 simulated step per rendered frame at this rate
SLOW_SECONDS = 300  # "slow" condenses the whole timeline to this many seconds
FAST_SECONDS = 30  # "fast" condenses the whole timeline to this many seconds
FAST_BOOST = 4.0  # fast-forward/reverse: this multiple of whatever the speed slider is set to
MIN_SPEED = 0.01  # steps/sec floor for the speed slider and presets
TRIALS_PLAY_SECONDS = 30  # Trials mode grows the histogram to every trial in this time
