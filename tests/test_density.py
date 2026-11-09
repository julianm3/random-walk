import numpy as np

from random_walk.data import WalkData
from random_walk.density import DensityShading


def lone_walk(steps=400):
    # One walk going right then back left: a single thin line through the grid.
    up = np.arange(steps // 2 + 1)
    path = np.concatenate([up, up[-2::-1]])
    return WalkData.from_paths(path[None, :])


def test_count_only_recounts_for_another_number_of_trials():
    data = WalkData.from_paths(np.array([[0, 1, 2], [0, -1, 0]]))
    density = DensityShading(data, -1, 2, 1.0)
    assert not density.counted
    assert density.count(2) and density.counted
    assert not density.count(2)
    assert density.count(1)


def test_rows_blank_the_steps_not_yet_reached():
    data = lone_walk(10)
    density = DensityShading(data, *data.span, 1.0)
    density.count(1)
    rows = density.rows(last=4)
    assert rows.shape == (10, 5)
    assert (rows[:4].max(axis=1) == 1).all()
    assert (rows[4:] == 0).all()


def test_gamma_lifts_the_sparse_cells():
    data = WalkData.from_paths(np.array([[0, 1]] * 4 + [[0, -1]]))
    density = DensityShading(data, -1, 1, 0.5)
    density.count(5)
    assert np.allclose(density.rows(last=1)[0], [0.25**0.5, 1.0])


def test_squeezed_rows_leave_no_gaps_in_a_lone_walk():
    # 400 steps into 150 pixel rows: every row still holds the walk (the darkest step wins);
    # dropping rows instead would leave gaps where its cells were skipped.
    data = lone_walk(400)
    density = DensityShading(data, *data.span, 0.3)
    density.count(1)
    rows = density.rows(last=400, height=150)
    assert rows.shape[0] == 150
    assert (rows.max(axis=1) == 1).all()


def test_squeezed_rows_show_the_current_steps_of_a_pixel_row():
    data = lone_walk(400)
    density = DensityShading(data, *data.span, 1.0)
    density.count(1)
    rows = density.rows(last=201, height=100)  # pixel row 50 covers steps 200 to 203
    assert (rows[:50].max(axis=1) == 1).all()
    assert rows[50].max() == 1  # step 200, already reached, shows
    assert (rows[51:] == 0).all()
    assert np.array_equal(rows[50], density.rows(last=201)[200])


def test_tallest_from_is_a_suffix_maximum_of_the_tallest_bars():
    # Both walks at 0 at step 0 (share 1), then apart (1/2 each), then together at step 4.
    data = WalkData.from_paths(np.array([[0, 1, 2, 1, 0], [0, -1, -2, -1, 0]]))
    density = DensityShading(data, *data.span, 1.0)
    density.count(2)
    assert list(density.tallest_from()) == [1.0, 1.0, 1.0, 1.0, 1.0]
    density.count(1)
    assert list(density.tallest_from()) == [1.0] * 5
    data = WalkData.from_paths(np.array([[0, 1, 2], [0, -1, -2]]))
    density = DensityShading(data, *data.span, 1.0)
    density.count(2)
    assert list(density.tallest_from()) == [1.0, 0.5, 0.5]
