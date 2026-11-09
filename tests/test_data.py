import numpy as np

from random_walk.data import WalkData, generate
from random_walk.params import WalkParams
from random_walk.simulation import absorb_steps, simulate_paths


def test_generate_is_seeded_by_the_params():
    params = WalkParams(200, 50, False, -10, 0.5, seed=3)
    a, b = generate(params), generate(params)
    assert np.array_equal(a.paths, b.paths)
    expected = simulate_paths(200, 50, None, 0.5, np.random.default_rng(3))
    assert np.array_equal(a.paths, expected)
    assert a.ends is None and a.wall is None
    assert (a.trials, a.steps) == (200, 50)


def test_generate_reflects_off_the_wall():
    data = generate(WalkParams(200, 100, True, -5, 0.5))
    assert data.paths.min() >= -5
    assert data.ends is None and data.wall == -5


def test_generate_absorbing_wall_keeps_the_free_walks_and_their_contact_steps():
    params = WalkParams(200, 100, True, -5, 0.5, wall_mode="absorb")
    data = generate(params)
    free = simulate_paths(200, 100, None, 0.5, np.random.default_rng(params.seed))
    assert np.array_equal(data.paths, free)
    assert data.ends is not None
    assert np.array_equal(data.ends, absorb_steps(free, -5))
    assert data.span[0] == -5  # traces stop at the wall (some walk reaches it)


def test_default_data_set_is_unchanged():
    import hashlib

    data = generate(WalkParams(10_000, 1000, False, -80, 0.5, 42))
    assert hashlib.sha256(data.paths.tobytes()).hexdigest().startswith("5525f7151cfc")


def absorbed_example() -> WalkData:
    # Walk 0 reaches the wall (-2) at step 2; walk 1 never does.
    paths = np.array([[0, -1, -2, -1], [0, 1, 2, 3]])
    return WalkData.from_paths(paths, wall=-2, ends=absorb_steps(paths, -2))


def test_going_and_ended_follow_the_contact_step():
    data = absorbed_example()
    assert list(data.going(2, 1)) == [-1, 1]
    assert list(data.going(2, 2)) == [2]  # walk 0 ends at its contact step
    assert (data.ended(2, 1), data.ended(2, 2), data.ended(1, 3)) == (0, 1, 1)
    assert WalkData.from_paths(np.zeros((3, 2), dtype=np.int64)).ended(3, 1) is None


def test_shares_are_of_all_counted_trials_not_the_survivors():
    data = absorbed_example()
    centres, shares = data.shares_at(2, 3)
    assert list(centres) == [3] and list(shares) == [0.5]
    assert data.shares_at(1, 3)[1].size == 0  # nothing going: empty
    centres, shares = data.shares_at(2, 1)
    assert list(centres) == [-1, 1] and shares.sum() == 1.0
