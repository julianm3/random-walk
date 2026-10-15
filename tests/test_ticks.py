import pytest

from random_walk.ticks import nice_step, nice_ticks, tick_label


@pytest.mark.parametrize(
    ("span", "max_ticks", "expected"),
    [(258, 13, 20), (258, 12, 50), (258, 3, 100), (10, 10, 1), (1, 5, 0.2), (0.07, 7, 0.01)],
)
def test_nice_step_is_1_2_or_5_times_a_power_of_ten(span, max_ticks, expected):
    assert nice_step(span, max_ticks) == pytest.approx(expected)


def test_nice_step_respects_minimum():
    assert nice_step(4, 20, min_step=1) == 1  # 0.2 would be nicer, but data is integer


def test_ticks_for_the_walk_range():
    assert nice_ticks(-127, 131, 6) == [-100, -50, 0, 50, 100]


def test_ticks_include_zero_and_stay_in_range():
    ticks = nice_ticks(-17, 15, 8)
    assert 0 in ticks
    assert all(-17 <= t <= 15 for t in ticks)
    steps = {round(b - a, 9) for a, b in zip(ticks, ticks[1:], strict=False)}
    assert len(steps) == 1


def test_ticks_include_exact_endpoints():
    assert nice_ticks(0, 100, 5) == [0, 20, 40, 60, 80, 100]


def test_reversed_and_degenerate_ranges():
    assert nice_ticks(50, -50, 2) == [-50, 0, 50]
    assert nice_ticks(3, 3, 5, min_step=1) == [3]


def test_no_negative_zero():
    assert str(nice_ticks(-1, 1, 2)[1]) == "0.0"


@pytest.mark.parametrize(
    ("value", "label"), [(100.0, "100"), (-50, "-50"), (0.0, "0"), (0.25, "0.25")]
)
def test_tick_label(value, label):
    assert tick_label(value) == label
