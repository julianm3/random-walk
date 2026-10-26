import pytest

from random_walk.config import DEFAULT_SEED, MAX_JUMPS, MAX_STEPS
from random_walk.params import WalkParams, validate


def test_valid_params_have_no_error():
    assert validate(10_000, 1000, 0.5) is None
    assert validate(1, 1, 0) is None
    assert validate(1, 1, 1) is None


@pytest.mark.parametrize(("runs", "steps"), [(0, 10), (10, 0), (-1, 5)])
def test_runs_and_steps_must_be_positive(runs, steps):
    assert validate(runs, steps, 0.5) == "RUNS and STEPS must be at least 1"


def test_total_jumps_limit():
    assert validate(MAX_JUMPS, 2, 0.5) == f"RUNS x STEPS is too large (max {MAX_JUMPS:,})"
    assert validate(MAX_JUMPS // 100, 100, 0.5) is None


def test_steps_limit():
    assert validate(1, MAX_STEPS + 1, 0.5) == f"STEPS is too large (max {MAX_STEPS:,})"


@pytest.mark.parametrize("p_right", [-0.01, 1.01, 50])
def test_p_right_range(p_right):
    assert validate(10, 10, p_right) == "P(right) must be between 0 and 1"


def test_wall_is_none_when_disabled():
    assert WalkParams(10, 10, False, -30, 0.5).wall is None
    assert WalkParams(10, 10, True, -30, 0.5).wall == -30


def test_seed_defaults_and_counts_for_equality():
    assert WalkParams(10, 10, False, -30, 0.5).seed == DEFAULT_SEED
    assert WalkParams(10, 10, False, -30, 0.5, seed=7) != WalkParams(10, 10, False, -30, 0.5)


def test_params_work_as_cache_key():
    a = WalkParams(10, 10, True, -30, 0.5)
    assert a == WalkParams(10, 10, True, -30, 0.5)
    assert a != WalkParams(10, 10, True, -29, 0.5)
    assert len({a, WalkParams(10, 10, True, -30, 0.5)}) == 1
