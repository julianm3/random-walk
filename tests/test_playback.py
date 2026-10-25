import pytest

from random_walk.config import FAST_BOOST, FAST_SECONDS, FPS, MIN_SPEED, SLOW_SECONDS
from random_walk.playback import Playback


def started(n=101, speed=10.0, now=0.0):
    pb = Playback()
    pb.start(n, now)
    pb.set_speed(speed)
    return pb


def test_new_playback_is_empty():
    pb = Playback()
    assert pb.n == 0 and not pb.playing
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


def test_zero_dt_first_tick_does_not_pause():
    # Regression: "Play does nothing at the start".
    pb = started()
    pb.tick(0.0)
    assert pb.playing


def test_playing_forward_stops_at_the_end():
    pb = started(n=11, speed=10.0)
    assert pb.tick(5.0) == 10
    assert pb.frame == 10.0 and not pb.playing


def test_reverse_stops_at_the_start():
    pb = started(n=11, speed=10.0)
    pb.jump_to(5)
    pb.reverse(now=0.0)
    pb.tick(0.3)
    assert pb.frame == pytest.approx(2.0)
    pb.tick(10.0)
    assert pb.frame == 0.0 and not pb.playing


def test_fast_forward_boosts_speed():
    pb = started(speed=10.0)
    pb.fast(1, now=0.0)
    pb.tick(0.5)
    assert pb.frame == pytest.approx(10.0 * FAST_BOOST * 0.5)


def test_play_at_end_rewinds_to_start():
    pb = started(n=11)
    pb.finish()
    pb.play(now=0.0)
    assert pb.frame == 0.0 and pb.playing


def test_replaying_two_frames_redraws_the_end():
    # Regression: after rewinding from the end, reaching it again returned None (it still
    # counted as drawn), so a 0 -> 1 animation never showed frame 1.
    pb = Playback()
    pb.start(2, 0.0, autoplay=False)
    pb.finish()
    pb.play(now=0.0)
    assert pb.tick(0.0) == 0
    assert pb.tick(1.0) == 1 and not pb.playing


def test_reverse_at_start_rewinds_to_end():
    pb = started(n=11)
    pb.restart()
    pb.reverse(now=0.0)
    assert pb.frame == 10.0 and pb.direction == -1


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
    assert Playback().finish() is None


def test_step_moves_one_frame():
    pb = started(n=11)
    pb.jump_to(4)
    assert pb.step(1) == 5
    assert pb.step(-1) == 4


def test_restore_pauses_and_forces_redraw():
    pb = started(n=11)
    pb.tick(0.0)
    pb.restore(21, 20.0)
    assert not pb.playing
    assert pb.tick(1.0) == 20


def test_reset_clears_timeline_but_keeps_speed():
    pb = started(speed=12.5)
    pb.reset()
    assert pb.n == 0 and pb.frame == 0.0 and pb.base_speed == 12.5


@pytest.mark.parametrize(
    ("name", "expected"),
    [("real", float(FPS)), ("slow", 3000 / SLOW_SECONDS), ("fast", 3000 / FAST_SECONDS)],
)
def test_presets(name, expected):
    pb = Playback()
    pb.start(3000, 0.0)
    assert pb.apply_preset(name) == pytest.approx(expected)
    assert pb.matching_preset() == name
    assert pb.speed_touched


def test_untouched_preset_is_not_the_users_choice():
    pb = Playback()
    pb.start(3000, 0.0)
    pb.apply_preset("fast", touched=False)
    assert not pb.speed_touched


def test_preset_speed_has_a_floor():
    pb = Playback()
    pb.start(2, 0.0)
    assert pb.apply_preset("slow") == MIN_SPEED


def test_slider_speed_matches_no_preset():
    pb = started(n=3000, speed=17.0)
    assert pb.matching_preset() is None
    assert pb.speed_touched


def test_speed_slider_max():
    pb = Playback()
    pb.start(10, 0.0)
    assert pb.speed_slider_max() == FPS * 2
    pb.start(30_000, 0.0)
    assert pb.speed_slider_max() == 30_000 / FAST_SECONDS * 2
