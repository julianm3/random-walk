"""Timeline playback state: play/pause/reverse/fast/step/scrub and playback speed.

Pure Python with no GUI imports. The GUI owns one Playback per timeline, feeds it the current
time on every rendered frame, and redraws whatever frame it reports back. Times are in
seconds; frames run 0..n-1.
"""

from __future__ import annotations

from random_walk.config import FAST_BOOST, FAST_SECONDS, FPS, MIN_SPEED, SLOW_SECONDS

# Preset name -> seconds the whole timeline is condensed into (None means "real time": one
# step per frame at FPS).
PRESETS: dict[str, float | None] = {"real": None, "slow": SLOW_SECONDS, "fast": FAST_SECONDS}


class Playback:
    def __init__(self) -> None:
        self.n = 0  # number of frames (0..n-1); 0 until something has been started
        self.frame = 0.0  # current, possibly fractional, frame position
        self.base_speed = float(FPS)  # frames/sec, set by the speed slider or a preset
        self.boost = 1.0  # temporary multiplier while fast-forward/reverse is engaged
        self.direction = 1
        self.playing = False
        self.last_time = 0.0
        self.last_drawn = -1
        self.speed_touched = False  # has the user explicitly picked a speed? (vs. the default)

    @property
    def current_frame(self) -> int:
        return int(round(self.frame))

    # --- (re)loading a timeline ---------------------------------------------------------

    def start(self, n: int, now: float, autoplay: bool = True) -> None:
        """A new timeline of `n` frames: rewind to 0 and, unless told otherwise, start playing."""
        self.n = n
        self.frame = 0.0
        self.last_drawn = -1
        self.direction = 1
        self.boost = 1.0
        self.last_time = now
        self.playing = autoplay and n > 1

    def restore(self, n: int, frame: float) -> None:
        """Show an existing timeline paused at `frame`, forcing a redraw on the next tick."""
        self.n = n
        self.frame = frame
        self.playing = False
        self.last_drawn = -1

    def reset(self) -> None:
        """Back to the empty, nothing-started state (speed settings are kept)."""
        self.restore(0, 0.0)

    # --- per-frame update ---------------------------------------------------------------

    def tick(self, now: float) -> int | None:
        """Move playback forward/backward in real time.

        Returns the integer frame to redraw if it changed since the last draw, else None.
        """
        if self.n == 0:
            return None  # nothing has been started yet - nothing to draw
        if self.playing and self.n > 1:
            dt = now - self.last_time
            self.frame += dt * self.base_speed * self.boost * self.direction
            # Only treat hitting 0 as "rewound past the start" while actually playing
            # backwards. Otherwise, starting fresh at frame 0 while playing forward - where dt
            # can be exactly 0.0 on the first tick, since the GUI clock is cached per frame -
            # would immediately re-pause playback before it ever moved ("Play does nothing at
            # the start").
            if self.direction < 0 and self.frame <= 0:
                self.frame = 0.0
                self.playing = False
            elif self.direction > 0 and self.frame >= self.n - 1:
                self.frame = float(self.n - 1)
                self.playing = False
            else:
                self.frame = max(0.0, min(self.frame, self.n - 1))
        self.last_time = now

        frame_int = self.current_frame
        if frame_int != self.last_drawn:
            self.last_drawn = frame_int
            return frame_int
        return None

    # --- transport controls -------------------------------------------------------------

    def play(self, now: float) -> None:
        self._run(1, 1.0, now)

    def reverse(self, now: float) -> None:
        self._run(-1, 1.0, now)

    def fast(self, direction: int, now: float) -> None:
        """Fast-forward (direction=1) or fast-reverse (direction=-1)."""
        self._run(direction, FAST_BOOST, now)

    def pause(self) -> None:
        self.playing = False

    def jump_to(self, frame_int: int) -> int | None:
        """Pause and move to an exact (clamped) frame. Returns the frame to redraw, or None if
        nothing has been started."""
        self.playing = False
        if self.n == 0:
            return None
        frame_int = max(0, min(frame_int, self.n - 1))
        self.frame = float(frame_int)
        self.last_drawn = frame_int
        return frame_int

    def seek(self, frame: float) -> None:
        """Pause at a (clamped) fractional frame, e.g. one mapped back from another scale, so
        playback resumes from exactly there. Counts as drawn: the next tick redraws only if
        the frame moves on."""
        self.playing = False
        if self.n == 0:
            return
        self.frame = max(0.0, min(frame, float(self.n - 1)))
        self.last_drawn = self.current_frame

    def step(self, delta: int) -> int | None:
        return self.jump_to(self.current_frame + delta)

    def restart(self) -> int | None:
        return self.jump_to(0)

    def finish(self) -> int | None:
        return self.jump_to(self.n - 1)

    def _run(self, direction: int, boost: float, now: float) -> None:
        self._rewind_if_at_boundary(direction)
        self.direction = direction
        self.boost = boost
        self.playing = True
        self.last_time = now

    def _rewind_if_at_boundary(self, direction: int) -> None:
        """Playing toward the end you're already sitting at restarts from the other end,
        rather than resuming and immediately auto-pausing again on the first tick."""
        if self.n == 0:
            return
        if direction > 0 and self.frame >= self.n - 1:
            self.frame = 0.0
        elif direction < 0 and self.frame <= 0:
            self.frame = float(self.n - 1)
        else:
            return
        # The frame drawn last was the end just left; forget it, or on a two-frame timeline
        # reaching that end again would look already drawn and never be redrawn.
        self.last_drawn = -1

    # --- speed --------------------------------------------------------------------------

    def set_speed(self, speed: float) -> None:
        """The user picked a speed directly (the slider)."""
        self.base_speed = speed
        self.boost = 1.0
        self.speed_touched = True

    def apply_preset(self, name: str, touched: bool = True) -> float:
        """Set the speed from a named preset and return it.

        `touched=False` is for the internal default-to-Fast-on-start case, which shouldn't
        count as the user's own choice.
        """
        duration = PRESETS[name]
        speed = float(FPS) if duration is None else self.n / duration
        speed = max(speed, MIN_SPEED)
        self.base_speed = speed
        self.boost = 1.0
        if touched:
            self.speed_touched = True
        return speed

    def matching_preset(self) -> str | None:
        """Which preset (if any) the current base_speed matches, for when the speed was set
        some other way (the slider, or a stale preset after the timeline length changed)."""
        candidates = {"real": float(FPS)}
        if self.n > 1:
            candidates["slow"] = self.n / SLOW_SECONDS
            candidates["fast"] = self.n / FAST_SECONDS
        for name, value in candidates.items():
            if value > 0 and abs(self.base_speed - value) / value < 1e-6:
                return name
        return None

    def speed_slider_max(self) -> float:
        return max(FPS, self.n / FAST_SECONDS) * 2
