import math

import pytest

from random_walk.pacing import TrialRamp, growth_rate


def test_growth_rate_solves_the_end_condition():
    k = growth_rate(900, 10_000)
    assert math.expm1(k * 900) / k == pytest.approx(10_000, rel=1e-9)
    assert k == pytest.approx(0.0041, abs=0.0002)


def test_growth_rate_is_zero_when_linear_is_enough():
    assert growth_rate(900, 900) == 0
    assert growth_rate(900, 50) == 0


def test_ramp_runs_from_zero_to_total():
    ramp = TrialRamp(900, 10_000)
    assert ramp.count_at(0) == 0
    assert ramp.count_at(900) == 10_000
    assert ramp.count_at(-5) == 0 and ramp.count_at(2000) == 10_000


def test_ramp_starts_at_one_trial_a_frame_and_speeds_up():
    ramp = TrialRamp(900, 10_000)
    assert [ramp.count_at(f) for f in range(4)] == [0, 1, 2, 3]
    counts = [ramp.count_at(f) for f in range(901)]
    steps = [b - a for a, b in zip(counts, counts[1:], strict=False)]
    assert min(steps) >= 0  # never goes backwards
    assert steps[-1] > 30  # ~40 trials a frame at the end


def test_frame_for_inverts_count_at():
    ramp = TrialRamp(900, 10_000)
    for count in (0, 1, 7, 580, 5000, 10_000):
        assert ramp.count_at(ramp.frame_for(count)) == count


@pytest.mark.parametrize(("frames", "total"), [(900, 300), (10, 10), (900, 0)])
def test_linear_ramp_when_total_is_small(frames, total):
    ramp = TrialRamp(frames, total)
    assert ramp.count_at(0) == 0 and ramp.count_at(frames) == total
    if total:
        assert ramp.count_at(frames / 2) == round(total / 2)
        assert ramp.frame_for(total) == frames
