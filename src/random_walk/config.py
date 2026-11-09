"""Default values and limits shared by the simulation core and the GUI."""

# Shared parameters
DEFAULT_TRIALS = 10_000
DEFAULT_STEPS = 1000
DEFAULT_WALL = -80  # default wall location, editable in the UI
MIN_WALL = -120  # lowest wall position the Configure dialog accepts
MAX_WALL = -1  # highest: just left of the start
# What the wall does: "reflect" mirrors a step below it back above; "absorb" ends the walk
# when it reaches the wall (its trace stops there and it leaves the histogram).
WALL_MODES = ("reflect", "absorb")
DEFAULT_WALL_MODE = "reflect"
DEFAULT_P_RIGHT = 0.5  # default probability of a +1 step, editable in the UI
DEFAULT_SEED = 42  # seeds the default random generator, so every run sees the same data

# Playback
FPS = 30  # "real time" is 1 simulated step per rendered frame at this rate
TRIALS_PLAY_SECONDS = 30  # Trials mode grows the histogram to every trial in this time
