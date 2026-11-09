import pytest

from random_walk.config import FPS
from random_walk.playback import Playback


def started(n=101, speed=10.0, now=0.0):
    pb = Playback()
    pb.start(n, now)
    pb.speed = speed
    return pb


def test_new_playback_is_empty():
    pb = Playback()
    assert pb.n == 0 and not pb.playing and pb.speed == FPS
    assert pb.tick(1.0) is None


def test_start_autoplays_from_zero():
    pb = Playback()
    pb.start(10, now=5.0)
    assert pb.playing and pb.frame == 0.0 and pb.last_time == 5.0


def test_start_without_autoplay_or_with_single_frame_is_paused():
    pb = Playback()
    pb.start(10, 0.0, autoplay=False)
    assert not pb.playing
    pb.start(1, 0.0)
    assert not pb.playing


def test_first_tick_draws_frame_zero_then_only_changes():
    pb = started(speed=10.0)
    assert pb.tick(0.0) == 0
    assert pb.tick(0.01) is None  # 0.1 frames: still rounds to 0
    assert pb.tick(0.1) == 1


def test_plays_in_real_time():
    pb = started(speed=10.0)
    pb.tick(0.0)
    pb.tick(0.35)
    assert pb.frame == pytest.approx(3.5)


def test_zero_dt_first_tick_does_not_pause():
    # Regression: "Play does nothing at the start".
    pb = started()
    pb.tick(0.0)
    assert pb.playing


def test_playing_stops_at_the_end():
    pb = started(n=11, speed=10.0)
    assert pb.tick(5.0) == 10
    assert pb.frame == 10.0 and not pb.playing


def test_play_continues_from_the_current_frame():
    pb = started(n=11, speed=10.0)
    pb.jump_to(4)
    pb.play(now=0.0)
    pb.tick(0.2)
    assert pb.frame == pytest.approx(6.0) and pb.playing


def test_play_at_end_rewinds_to_start():
    pb = started(n=11)
    pb.jump_to(10)
    pb.play(now=0.0)
    assert pb.frame == 0.0 and pb.playing


def test_replaying_two_frames_redraws_the_end():
    # Regression: after rewinding from the end, reaching it again returned None (it still
    # counted as drawn), so a 0 -> 1 animation never showed frame 1.
    pb = Playback()
    pb.start(2, 0.0, autoplay=False)
    pb.jump_to(1)
    pb.play(now=0.0)
    assert pb.tick(0.0) == 0
    assert pb.tick(1.0) == 1 and not pb.playing


def test_pause_stops_the_clock():
    pb = started(n=11, speed=10.0)
    pb.tick(0.0)
    pb.pause()
    pb.tick(1.0)
    assert pb.frame == 0.0


def test_jump_to_pauses_and_clamps():
    pb = started(n=11)
    assert pb.jump_to(50) == 10
    assert not pb.playing
    assert pb.jump_to(-3) == 0
    assert pb.last_drawn == 0


def test_seek_keeps_fractional_frame_and_clamps():
    pb = started(n=11)
    pb.seek(3.4)
    assert not pb.playing and pb.frame == 3.4 and pb.last_drawn == 3
    assert pb.tick(1.0) is None  # already drawn
    pb.seek(99.0)
    assert pb.frame == 10.0
    pb.seek(-1.0)
    assert pb.frame == 0.0


def test_jump_with_nothing_started_returns_none():
    assert Playback().jump_to(3) is None
