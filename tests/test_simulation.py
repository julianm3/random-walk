import numpy as np
import pytest

from random_walk.simulation import (
    LegendStats,
    absorb_steps,
    fractions_at,
    legend_lines,
    legend_stats,
    normalize_rows,
    parity_bins,
    simulate,
    simulate_paths,
    trace_grid,
    trace_span,
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
    steps, trials = 400, 20_000
    finals = simulate(trials, steps, wall=None, p_right=p_right, rng=rng())
    sd = np.sqrt(4 * p_right * (1 - p_right) * steps)
    assert finals.mean() == pytest.approx(steps * (2 * p_right - 1), abs=5 * sd / np.sqrt(trials))
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


def test_legend_stats_measure_and_compare_with_theory():
    s = legend_stats(np.array([-2, 0, 2, 4]), step=4, p_right=0.75)
    assert s.step == 4 and s.trials == 4
    assert s.mean == pytest.approx(1.0)
    assert s.sd == pytest.approx(np.sqrt(5))  # population sd (numpy's default)
    assert s.theory_mean == pytest.approx(2.0)  # 4 * (2 * 0.75 - 1)
    assert s.theory_sd == pytest.approx(np.sqrt(3))  # sqrt(4 * 0.75 * 0.25 * 4)


def test_legend_stats_with_nothing_counted():
    s = legend_stats(np.array([], dtype=np.int64), step=100, p_right=0.5)
    assert s.trials == 0 and s.mean is None and s.sd is None
    assert s.theory_mean == 0 and s.theory_sd == pytest.approx(10.0)


def test_legend_lines_align_and_format():
    lines = legend_lines(LegendStats(1000, 10_000, -0.8412, 31.2066, 0.0, 31.6228))
    assert lines == [
        "steps     1000  trials    10000",
        "mean     -0.84  theory     0.00",
        "sd       31.21  theory    31.62",
    ]
    assert len({len(line) for line in lines}) == 1  # columns line up
    zero = legend_lines(LegendStats(0, 1, -0.001, None, -0.0, 0.0))
    assert zero[1] == "mean      0.00  theory     0.00"
    assert legend_lines(LegendStats(5, 0, None, None, 0.0, 0.0))[2] == (
        "sd           -  theory     0.00"
    )


def test_legend_lines_fit_a_walk_all_one_way():
    # P(right) = 0: every walk ends at -1000 after 1000 steps; the columns must still line up.
    lines = legend_lines(LegendStats(1000, 10_000, -1000.0, 0.0, -1000.0, 0.0))
    assert lines[1] == "mean  -1000.00  theory -1000.00"
    assert len({len(line) for line in lines}) == 1


def test_legend_shows_p_right_only_when_not_half():
    assert len(legend_lines(LegendStats(250, 40, 1.0, 2.0, 0.0, 3.0, 0.5))) == 3
    lines = legend_lines(LegendStats(250, 40, 9.35, 6.1, 50.0, 15.49, 0.6))
    assert lines[3] == "P(right)   60%"
    assert lines[3].endswith("%") and len(lines[3]) == len("steps   ") + 6  # lines up with "250"
    assert legend_lines(LegendStats(5, 1, 5.0, 0.0, 5.0, 0.0, 1.0))[3] == "P(right)  100%"
    assert legend_lines(LegendStats(5, 1, -5.0, 0.0, -5.0, 0.0, 0.0))[3] == "P(right)    0%"
    wall = legend_lines(LegendStats(250, 40, 9.35, 6.1, 50.0, 15.49, 0.3), with_theory=False)
    assert wall[3] == "P(right)   30%"  # shown with the wall too: it describes the walks
    assert legend_stats(np.array([1, 3]), 3, 0.7).p_right == 0.7


def test_legend_lines_without_theory_for_the_wall():
    lines = legend_lines(LegendStats(250, 40, 9.35, 6.1, 0.0, 15.81), with_theory=False)
    assert lines == ["steps      250  trials       40", "mean      9.35", "sd        6.10"]


def test_legend_matches_simulated_walks():
    finals = simulate(20_000, 400, wall=None, p_right=0.6, rng=rng())
    s = legend_stats(finals, 400, 0.6)
    assert s.mean == pytest.approx(s.theory_mean, abs=5 * s.theory_sd / np.sqrt(20_000))
    assert s.sd == pytest.approx(s.theory_sd, rel=0.03)


def test_fractions_at_sums_to_one():
    positions = np.array([0, 0, 2, -2, 2])
    centers, fractions = fractions_at(positions, parity_bins(positions))
    np.testing.assert_array_equal(centers, [-2, 0, 2])
    np.testing.assert_allclose(fractions, [0.2, 0.4, 0.4])


# --- density grid ----------------------------------------------------------------------------


def test_trace_grid_puts_a_walk_in_the_intervals_it_crosses():
    # One walk: 0 -> 1 -> 2 -> 1 (positions), with lo = -1, hi = 2: intervals [-1,0], [0,1],
    # [1,2]. Step 0->1 crosses [0,1]; 1->2 crosses [1,2]; 2->1 crosses [1,2] again.
    segments, peaks = trace_grid(np.array([[0, 1, 2, 1]]), lo=-1, hi=2)
    np.testing.assert_array_equal(segments, [[0, 1, 0], [0, 0, 1], [0, 0, 1]])
    np.testing.assert_array_equal(peaks, [1, 1, 1, 1])


def test_trace_grid_rows_hold_every_walk_and_both_parities():
    paths = simulate_paths(2000, 60, wall=None, rng=rng())
    lo, hi = int(paths.min()), int(paths.max())
    segments, _ = trace_grid(paths, lo, hi)
    assert segments.shape == (60, hi - lo)
    assert (segments.sum(axis=1) == 2000).all()  # every walk crosses one interval per step
    # No combing: a busy row fills neighbouring columns of both parities, unlike positions.
    middle = segments[50, (0 - lo) - 5 : (0 - lo) + 5]
    assert (middle > 0).all()


def test_trace_grid_peaks_are_the_tallest_histogram_bar():
    paths = simulate_paths(500, 40, wall=-3, p_right=0.4, rng=rng())
    lo, hi = int(paths.min()), int(paths.max())
    _, peaks = trace_grid(paths, lo, hi)
    for step in (0, 1, 7, 40):
        _, fractions = fractions_at(paths[:, step], parity_bins(paths[:, step]))
        assert peaks[step] == round(fractions.max() * 500)


def test_absorb_steps_find_the_first_contact():
    paths = np.array(
        [
            [0, -1, -2, -1, -2, -3],  # touches the wall at -2 on step 2
            [0, 1, 2, 3, 4, 5],  # never does
            [0, -1, 0, -1, -2, -1],  # step 4
        ]
    )
    np.testing.assert_array_equal(absorb_steps(paths, wall=-2), [2, 6, 4])


def test_trace_span_ignores_positions_after_contact():
    paths = np.array([[0, -1, -2, -3, -4], [0, 1, 2, 1, 2]])
    assert trace_span(paths) == (-4, 2)
    assert trace_span(paths, absorbing_wall=-2) == (-2, 2)  # the first walk stops at the wall
    # No walk reaches the wall: the free minimum stands.
    assert trace_span(np.array([[0, 1, 0, -1]]), absorbing_wall=-5) == (-1, 1)


def test_trace_span_low_end_matches_the_traces():
    free = simulate_paths(500, 300, wall=None, rng=rng(4))
    ends = absorb_steps(free, wall=-12)
    lowest_on_trace = min(int(free[i, : ends[i] + 1].min()) for i in range(500))
    assert trace_span(free, absorbing_wall=-12)[0] == lowest_on_trace


def test_trace_grid_stops_absorbed_walks_at_the_wall():
    # Walk 1 touches the wall at -2 on step 2: its trace includes the segment from -1 down
    # to -2, then stops, and it leaves the peaks from step 2 on. Walk 2 never touches it.
    paths = np.array([[0, -1, -2, -3], [0, 1, 0, 1]])
    ends = absorb_steps(paths, wall=-2)
    segments, peaks = trace_grid(paths, lo=-2, hi=1, ends=ends)
    # intervals [-2,-1], [-1,0], [0,1]
    np.testing.assert_array_equal(segments, [[0, 1, 1], [1, 0, 1], [0, 0, 1]])
    np.testing.assert_array_equal(peaks, [2, 1, 1, 1])


def test_absorbed_walks_follow_the_free_walk_until_contact():
    free = simulate_paths(300, 200, wall=None, rng=rng(9))
    ends = absorb_steps(free, wall=-8)
    assert (ends < 201).any() and (ends == 201).any()  # some absorbed, some not
    for i in range(300):
        trace = free[i, : ends[i] + 1]
        assert trace[:-1].min() > -8 if ends[i] < 201 else trace.min() > -8
        if ends[i] < 201:
            assert trace[-1] == -8  # ends exactly on the wall


def test_legend_counts_ended_walks():
    lines = legend_lines(LegendStats(400, 8766, 2.5, 18.0, 0.0, 20.0, 0.5, ended=1234))
    assert lines[0] == "steps      400  trials     8766  absorbed     1234"
    assert legend_stats(np.array([1, 3]), 3, 0.5, ended=5).ended == 5
    assert legend_lines(LegendStats(1, 1, 1.0, 0.0, 1.0, 0.0))[0].endswith("1")  # no "ended"


def test_normalize_rows_scales_each_row_to_its_peak():
    grid = np.array([[0, 4, 2], [0, 0, 0], [1, 1, 3]])
    np.testing.assert_allclose(normalize_rows(grid), [[0, 1, 0.5], [0, 0, 0], [1 / 3, 1 / 3, 1]])
