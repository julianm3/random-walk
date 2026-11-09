"""Timeline playback state: play, pause and jumping to a frame, in real time.

Pure Python with no GUI imports. The GUI owns one Playback per timeline, feeds it the current
time on every rendered frame, and redraws whatever frame it reports back. Times are in
seconds; frames run 0..n-1, played forward at FPS frames a second.
"""

from __future__ import annotations

from random_walk.config import FPS


class Playback:
    def __init__(self) -> None:
        self.n = 0  # number of frames (0..n-1); 0 until something has been started
        self.frame = 0.0  # current, possibly fractional, frame position
        self.speed = float(FPS)  # frames a second
        self.playing = False
        self.last_time = 0.0
        self.last_drawn = -1

    @property
    def current_frame(self) -> int:
        return int(round(self.frame))

    def start(self, n: int, now: float, autoplay: bool = True) -> None:
        """A new timeline of `n` frames: rewind to 0 and, unless told otherwise, start playing."""
        self.n = n
        self.frame = 0.0
        self.last_drawn = -1
        self.last_time = now
        self.playing = autoplay and n > 1

    def tick(self, now: float) -> int | None:
        """Move playback forward in real time, stopping at the last frame.

        Returns the integer frame to redraw if it changed since the last draw, else None.
        """
        if self.n == 0:
            return None  # nothing has been started yet - nothing to draw
        if self.playing and self.n > 1:
            self.frame += (now - self.last_time) * self.speed
            if self.frame >= self.n - 1:
                self.frame = float(self.n - 1)
                self.playing = False
        self.last_time = now

        frame_int = self.current_frame
        if frame_int != self.last_drawn:
            self.last_drawn = frame_int
            return frame_int
        return None

    def play(self, now: float) -> None:
        """Play from the current frame - or from the start again if at the last frame, rather
        than resuming and stopping straight away."""
        if self.n > 0 and self.frame >= self.n - 1:
            self.frame = 0.0
            # The frame drawn last was the end just left; forget it, or on a two-frame
            # timeline reaching that end again would look already drawn and never be redrawn.
            self.last_drawn = -1
        self.playing = True
        self.last_time = now

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
