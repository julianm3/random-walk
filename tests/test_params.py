import pytest

from random_walk.config import MAX_JUMPS, MAX_STEPS
from random_walk.params import WalkParams, validate


def test_valid_params_have_no_error():
    assert validate(10_000, 1000, 0.0) is None
    assert validate(1, 1, -90) is None
    assert validate(1, 1, 90) is None


@pytest.mark.parametrize(("runs", "steps"), [(0, 10), (10, 0), (-1, 5)])
def test_runs_and_steps_must_be_positive(runs, steps):
    assert validate(runs, steps, 0) == "RUNS and STEPS must be at least 1"


def test_total_jumps_limit():
    assert validate(MAX_JUMPS, 2, 0) == f"RUNS x STEPS is too large (max {MAX_JUMPS:,})"
    assert validate(MAX_JUMPS // 100, 100, 0) is None


def test_steps_limit():
    assert validate(1, MAX_STEPS + 1, 0) == f"STEPS is too large (max {MAX_STEPS:,})"


@pytest.mark.parametrize("theta", [-90.1, 91])
def test_slope_range(theta):
    assert validate(10, 10, theta) == "SLOPE must be between -90 and 90 degrees"


def test_wall_is_none_when_disabled():
    assert WalkParams(10, 10, False, -30, 0.0).wall is None
    assert WalkParams(10, 10, True, -30, 0.0).wall == -30


def test_params_work_as_cache_key():
    a = WalkParams(10, 10, True, -30, 0.0)
    assert a == WalkParams(10, 10, True, -30, 0.0)
    assert a != WalkParams(10, 10, True, -29, 0.0)
    assert len({a, WalkParams(10, 10, True, -30, 0.0)}) == 1
