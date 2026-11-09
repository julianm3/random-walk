from random_walk.config import DEFAULT_SEED
from random_walk.params import WalkParams


def test_wall_is_none_when_disabled():
    assert WalkParams(10, 10, False, -30, 0.5).wall is None
    assert WalkParams(10, 10, True, -30, 0.5).wall == -30


def test_wall_mode_defaults_to_reflect_and_absorbing_needs_the_wall_on():
    assert WalkParams(10, 10, True, -30, 0.5).wall_mode == "reflect"
    assert not WalkParams(10, 10, True, -30, 0.5).absorbing
    assert WalkParams(10, 10, True, -30, 0.5, wall_mode="absorb").absorbing
    assert not WalkParams(10, 10, False, -30, 0.5, wall_mode="absorb").absorbing


def test_seed_defaults_and_counts_for_equality():
    assert WalkParams(10, 10, False, -30, 0.5).seed == DEFAULT_SEED
    assert WalkParams(10, 10, False, -30, 0.5, seed=7) != WalkParams(10, 10, False, -30, 0.5)


def test_params_work_as_cache_key():
    a = WalkParams(10, 10, True, -30, 0.5)
    assert a == WalkParams(10, 10, True, -30, 0.5)
    assert a != WalkParams(10, 10, True, -29, 0.5)
    assert len({a, WalkParams(10, 10, True, -30, 0.5)}) == 1


def test_same_walks_ignores_wall_settings_while_the_wall_is_off():
    off = WalkParams(10, 10, False, -30, 0.5)
    assert off.same_walks(WalkParams(10, 10, False, -50, 0.5, wall_mode="absorb"))
    assert not off.same_walks(WalkParams(10, 10, True, -30, 0.5))


def test_same_walks_sees_every_setting_the_walks_depend_on():
    on = WalkParams(10, 10, True, -30, 0.5)
    assert on.same_walks(WalkParams(10, 10, True, -30, 0.5))
    for other in (
        WalkParams(11, 10, True, -30, 0.5),
        WalkParams(10, 11, True, -30, 0.5),
        WalkParams(10, 10, True, -31, 0.5),
        WalkParams(10, 10, True, -30, 0.6),
        WalkParams(10, 10, True, -30, 0.5, seed=7),
        WalkParams(10, 10, True, -30, 0.5, wall_mode="absorb"),
    ):
        assert not on.same_walks(other)
