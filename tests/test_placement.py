import pytest

from random_walk.placement import legend_side


def test_stays_while_its_corner_is_clear():
    assert legend_side("right", covered_left=500, covered_right=0) == "right"
    assert legend_side("left", covered_left=0, covered_right=500) == "left"


def test_moves_to_the_clearly_emptier_corner():
    assert legend_side("right", covered_left=0, covered_right=300) == "left"
    assert legend_side("left", covered_left=300, covered_right=100) == "right"


@pytest.mark.parametrize(("left", "right"), [(100, 100), (80, 100), (51, 100)])
def test_stays_when_the_other_corner_is_not_clearly_emptier(left, right):
    # Hysteresis: a centred bell brushing both corners doesn't make the box flicker.
    assert legend_side("right", covered_left=left, covered_right=right) == "right"


def test_switch_threshold_is_half():
    assert legend_side("right", covered_left=50, covered_right=100) == "left"
