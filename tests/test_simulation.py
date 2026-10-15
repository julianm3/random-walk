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
    a = simulate(100, 50, wall=-5, theta=10, rng=rng(7))
    b = simulate(100, 50, wall=-5, theta=10, rng=rng(7))
    np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("wall", [None, -5, 0, 3])
@pytest.mark.parametrize("theta", [0, 25, -40])
def test_paths_end_where_simulate_does(wall, theta):
    finals = simulate(200, 60, wall=wall, theta=theta, rng=rng())
    paths = simulate_paths(200, 60, wall=wall, theta=theta, rng=rng())
    np.testing.assert_array_equal(paths[:, -1], finals)


def test_steps_are_plus_or_minus_one_without_wall():
    paths = simulate_paths(100, 50, wall=None, rng=rng())
    assert set(np.unique(np.diff(paths, axis=1))) <= {-1, 1}


# --- the slope -----------------------------------------------------------------------------


@pytest.mark.parametrize("theta", [0, 30, -30, 70])
def test_empirical_p_right_matches_slope_formula(theta):
    n = 200_000
    first_steps = simulate(n, 1, wall=None, theta=theta, rng=rng())
    p_hat = (first_steps == 1).mean()
    p = 0.5 - 0.5 * np.sin(np.radians(theta))
    assert abs(p_hat - p) < 5 * np.sqrt(p * (1 - p) / n)


def test_theta_minus_90_always_steps_right():
    np.testing.assert_array_equal(simulate(10, 25, wall=None, theta=-90, rng=rng()), 25)


def test_theta_plus_90_always_steps_left():
    np.testing.assert_array_equal(simulate(10, 25, wall=None, theta=90, rng=rng()), -25)


@pytest.mark.parametrize("theta", [0, 30, -60])
def test_mean_and_sd_match_theory(theta):
    steps, runs = 400, 20_000
    finals = simulate(runs, steps, wall=None, theta=theta, rng=rng())
    rad = np.radians(theta)
    sd = np.sqrt(steps) * abs(np.cos(rad))
    assert finals.mean() == pytest.approx(-steps * np.sin(rad), abs=5 * sd / np.sqrt(runs))
    assert finals.std() == pytest.approx(sd, rel=0.03)


# --- the wall ------------------------------------------------------------------------------


@pytest.mark.parametrize("wall", [-10, -1, 0])
@pytest.mark.parametrize("theta", [0, 45])
def test_positions_never_fall_below_wall(wall, theta):
    paths = simulate_paths(500, 200, wall=wall, theta=theta, rng=rng())
    assert paths.min() >= wall


def test_wall_above_start_is_crossed_on_the_first_step():
    # The walk starts at 0, below a positive wall; every position after step 0 is above it.
    paths = simulate_paths(500, 50, wall=3, rng=rng())
    assert paths[:, 1:].min() >= 3


def test_wall_reflects_rather_than_clamps():
    # Always stepping left into a wall at 0: -1 reflects to +1, then back to 0, and so on.
    # A clamp would stick at 0 instead.
    paths = simulate_paths(3, 6, wall=0, theta=90, rng=rng())
    np.testing.assert_array_equal(paths, np.tile([0, 1, 0, 1, 0, 1, 0], (3, 1)))


# --- parity --------------------------------------------------------------------------------


@pytest.mark.parametrize("steps", [99, 100])
@pytest.mark.parametrize("wall", [None, -7, 0, 4])
def test_final_positions_share_parity_of_steps(steps, wall):
    finals = simulate(1000, steps, wall=wall, theta=20, rng=rng())
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
    finals = simulate(500, 100, wall=-10, theta=15, rng=rng())
    assert not summarize(finals, 100, True, -10, theta=15).show_curve


@pytest.mark.filterwarnings("error")  # no divide-by-zero warnings from the curve formulas
@pytest.mark.parametrize("theta", [90, -90])
@pytest.mark.parametrize("wall_enabled", [False, True])
def test_summarize_hides_curve_when_fully_biased(theta, wall_enabled):
    # Regression: at +/-90 the sd is 0, and the curve used to spike to ~1e14, swamping the
    # histogram when the plot axes were fitted to it.
    finals = simulate(200, 100, wall=-10 if wall_enabled else None, theta=theta, rng=rng())
    s = summarize(finals, 100, wall_enabled, wall_value=-10, theta=theta)
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
    assert s.stats == "mean = 0.00, sd = 1.63 (theory: -0.00, 1.41), min = -2, max = 2"
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
