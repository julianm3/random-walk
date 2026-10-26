import numpy as np
import pytest

from random_walk.simulation import (
    density_grid,
    fractions_at,
    normalize_rows,
    parity_bins,
    simulate,
    simulate_paths,
    summarize,
)


def rng(seed=12345):
    return np.random.default_rng(seed)


# --- shapes and consistency ---------------------------------------------------------------


def test_simulate_shape():
    assert simulate(50, 20, wall=None, rng=rng()).shape == (50,)


def test_simulate_paths_shape_and_start():
    paths = simulate_paths(50, 20, wall=None, rng=rng())
    assert paths.shape == (50, 21)
    assert (paths[:, 0] == 0).all()


def test_seeded_runs_are_reproducible():
    a = simulate(100, 50, wall=-5, p_right=0.4, rng=rng(7))
    b = simulate(100, 50, wall=-5, p_right=0.4, rng=rng(7))
    np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("wall", [None, -5, 0, 3])
@pytest.mark.parametrize("p_right", [0.5, 0.3, 0.8])
def test_paths_end_where_simulate_does(wall, p_right):
    finals = simulate(200, 60, wall=wall, p_right=p_right, rng=rng())
    paths = simulate_paths(200, 60, wall=wall, p_right=p_right, rng=rng())
    np.testing.assert_array_equal(paths[:, -1], finals)


def test_steps_are_plus_or_minus_one_without_wall():
    paths = simulate_paths(100, 50, wall=None, rng=rng())
    assert set(np.unique(np.diff(paths, axis=1))) <= {-1, 1}


# --- the bias ------------------------------------------------------------------------------


@pytest.mark.parametrize("p_right", [0.5, 0.25, 0.75, 0.9])
def test_empirical_p_right_matches(p_right):
    n = 200_000
    first_steps = simulate(n, 1, wall=None, p_right=p_right, rng=rng())
    p_hat = (first_steps == 1).mean()
    assert abs(p_hat - p_right) < 5 * np.sqrt(p_right * (1 - p_right) / n)


def test_p_right_one_always_steps_right():
    np.testing.assert_array_equal(simulate(10, 25, wall=None, p_right=1, rng=rng()), 25)


def test_p_right_zero_always_steps_left():
    np.testing.assert_array_equal(simulate(10, 25, wall=None, p_right=0, rng=rng()), -25)


@pytest.mark.parametrize("p_right", [0.5, 0.75, 0.2])
def test_mean_and_sd_match_theory(p_right):
    steps, runs = 400, 20_000
    finals = simulate(runs, steps, wall=None, p_right=p_right, rng=rng())
    sd = np.sqrt(4 * p_right * (1 - p_right) * steps)
    assert finals.mean() == pytest.approx(steps * (2 * p_right - 1), abs=5 * sd / np.sqrt(runs))
    assert finals.std() == pytest.approx(sd, rel=0.03)


def test_fair_walk_unchanged_from_slope_version():
    # Guard: p_right = 0.5 must draw the same walks as the old theta = 0 (p = 0.5 - 0.5 sin 0),
    # so the app's seeded data set did not change when the slope was replaced.
    expected = np.random.default_rng(3).choice([-1, 1], size=(20, 30), p=[0.5, 0.5])
    np.testing.assert_array_equal(simulate(20, 30, wall=None, rng=rng(3)), expected.sum(axis=1))


# --- the wall ------------------------------------------------------------------------------


@pytest.mark.parametrize("wall", [-10, -1, 0])
@pytest.mark.parametrize("p_right", [0.5, 0.15])
def test_positions_never_fall_below_wall(wall, p_right):
    paths = simulate_paths(500, 200, wall=wall, p_right=p_right, rng=rng())
    assert paths.min() >= wall


@pytest.mark.parametrize("wall", [None, -3, 0, 2])
@pytest.mark.parametrize("p_right", [0.5, 0.3])
def test_paths_match_a_step_by_step_reference(wall, p_right):
    # simulate_paths builds the array step-major for speed; every position must still follow
    # the plain rule: add the jump, then mirror anything below the wall back above it.
    jumps = np.random.default_rng(5).choice([-1, 1], size=(40, 30), p=[1 - p_right, p_right])
    expected = np.zeros((40, 31), dtype=np.int64)
    for k in range(30):
        nxt = expected[:, k] + jumps[:, k]
        expected[:, k + 1] = nxt if wall is None else np.where(nxt < wall, 2 * wall - nxt, nxt)
    paths = simulate_paths(40, 30, wall=wall, p_right=p_right, rng=rng(5))
    np.testing.assert_array_equal(paths, expected)


def test_wall_above_start_is_crossed_on_the_first_step():
    # The walk starts at 0, below a positive wall; every position after step 0 is above it.
    paths = simulate_paths(500, 50, wall=3, rng=rng())
    assert paths[:, 1:].min() >= 3


def test_wall_reflects_rather_than_clamps():
    # Always stepping left into a wall at 0: -1 reflects to +1, then back to 0, and so on.
    # A clamp would stick at 0 instead.
    paths = simulate_paths(3, 6, wall=0, p_right=0, rng=rng())
    np.testing.assert_array_equal(paths, np.tile([0, 1, 0, 1, 0, 1, 0], (3, 1)))


# --- parity --------------------------------------------------------------------------------


@pytest.mark.parametrize("steps", [99, 100])
@pytest.mark.parametrize("wall", [None, -7, 0, 4])
def test_final_positions_share_parity_of_steps(steps, wall):
    finals = simulate(1000, steps, wall=wall, p_right=0.35, rng=rng())
    assert (finals % 2 == steps % 2).all()


def test_parity_bins_are_width_two_and_centred_on_values():
    values = np.array([-3, 1, 5, 7])
    edges = parity_bins(values)
    assert (np.diff(edges) == 2).all()
    centers = edges[:-1] + 1
    assert set(values) <= set(centers)
    assert centers.min() == values.min() and centers.max() == values.max()


# --- summaries -----------------------------------------------------------------------------


def test_summarize_density_sums_to_one():
    finals = simulate(5000, 100, wall=None, rng=rng())
    s = summarize(finals, 100, wall_enabled=False)
    assert (s.counts * 2).sum() == pytest.approx(1.0)


def test_summarize_curve_spans_data_without_wall():
    finals = simulate(5000, 100, wall=None, rng=rng())
    s = summarize(finals, 100, wall_enabled=False)
    assert s.show_curve
    assert s.curve_x[0] == finals.min() and s.curve_x[-1] == finals.max()
    assert len(s.curve_x) == len(s.curve_y) == 400


def test_summarize_curve_starts_at_wall():
    finals = simulate(5000, 100, wall=-10, rng=rng())
    s = summarize(finals, 100, wall_enabled=True, wall_value=-10)
    assert s.show_curve
    assert s.curve_x[0] == -10


def test_summarize_hides_wall_curve_when_biased():
    finals = simulate(500, 100, wall=-10, p_right=0.4, rng=rng())
    assert not summarize(finals, 100, True, -10, p_right=0.4).show_curve


@pytest.mark.filterwarnings("error")  # no divide-by-zero warnings from the curve formulas
@pytest.mark.parametrize("p_right", [0, 1])
@pytest.mark.parametrize("wall_enabled", [False, True])
def test_summarize_hides_curve_when_fully_biased(p_right, wall_enabled):
    # At p_right = 0 or 1 the sd is 0, and a curve would divide by zero (it once spiked to
    # ~1e14, swamping the histogram when the plot axes were fitted to it).
    finals = simulate(200, 100, wall=-10 if wall_enabled else None, p_right=p_right, rng=rng())
    s = summarize(finals, 100, wall_enabled, wall_value=-10, p_right=p_right)
    assert not s.show_curve
    assert np.isfinite(s.curve_y).all() and s.curve_y.max() == 0
    assert (s.counts * 2).sum() == pytest.approx(1.0)


def test_summarize_respects_fixed_bins_and_curve_range():
    finals = simulate(500, 100, wall=None, rng=rng())
    bins = np.arange(-101, 102, 2)
    s = summarize(finals, 100, False, bins=bins, curve_x_range=(-50, 50))
    assert len(s.centers) == len(bins) - 1
    assert s.curve_x[0] == -50 and s.curve_x[-1] == 50


def test_summarize_stats_line():
    finals = np.array([-2, 0, 2])
    s = summarize(finals, 2, wall_enabled=False)
    assert s.stats == "mean = 0.00, sd = 1.63 (theory: 0.00, 1.41), min = -2, max = 2"
    wall_stats = summarize(finals, 2, wall_enabled=True, wall_value=-2).stats
    assert wall_stats == "mean = 0.00, sd = 1.63, min = -2, max = 2"


def test_fractions_at_sums_to_one():
    positions = np.array([0, 0, 2, -2, 2])
    centers, fractions = fractions_at(positions, parity_bins(positions))
    np.testing.assert_array_equal(centers, [-2, 0, 2])
    np.testing.assert_allclose(fractions, [0.2, 0.4, 0.4])


# --- density grid ----------------------------------------------------------------------------


def test_density_grid_counts_walks_per_step_and_bin():
    paths = np.array([[0, 1, 2], [0, -1, 0], [0, 1, 0]])  # 3 walks, 2 steps
    grid = density_grid(paths, lo=-1, hi=2)
    # bins of 2: [-1, 1) and [1, 3)
    np.testing.assert_array_equal(grid, [[3, 0], [1, 2], [2, 1]])


def test_density_grid_rows_sum_to_walk_count():
    paths = simulate_paths(500, 40, wall=None, rng=rng())
    grid = density_grid(paths, int(paths.min()), int(paths.max()))
    assert grid.shape[0] == 41
    assert (grid.sum(axis=1) == 500).all()


def test_density_grid_has_no_empty_parity_columns():
    # Width-2 bins hold one even and one odd position, so neither parity leaves gaps.
    paths = simulate_paths(2000, 50, wall=None, rng=rng())
    grid = density_grid(paths, int(paths.min()), int(paths.max()))
    middle = grid[50, 5:-5]
    assert (middle > 0).all()


def test_normalize_rows_scales_each_row_to_its_peak():
    grid = np.array([[0, 4, 2], [0, 0, 0], [1, 1, 3]])
    np.testing.assert_allclose(normalize_rows(grid), [[0, 1, 0.5], [0, 0, 0], [1 / 3, 1 / 3, 1]])
