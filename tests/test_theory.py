import numpy as np
import pytest

from random_walk import theory


@pytest.mark.parametrize(
    ("p_right", "mean", "sd"),
    [(0.5, 0, 20), (0.75, 200, np.sqrt(300)), (0.25, -200, np.sqrt(300)), (0.9, 320, 12)],
)
def test_final_mean_and_sd(p_right, mean, sd):
    # steps = 400: mean = n(2p - 1), sd = sqrt(4p(1 - p) n)
    assert theory.final_mean(400, p_right) == pytest.approx(mean)
    assert theory.final_sd(400, p_right) == pytest.approx(sd)


def test_p_right_above_half_drifts_right():
    assert theory.final_mean(100, 0.4) < 0 < theory.final_mean(100, 0.6)


def test_final_sd_is_symmetric_about_half():
    for p in (0.1, 0.3, 0.45):
        assert theory.final_sd(100, p) == pytest.approx(theory.final_sd(100, 1 - p))


@pytest.mark.parametrize(("p_right", "mean"), [(0.0, -1000), (1.0, 1000)])
def test_fully_biased_walk_is_deterministic(p_right, mean):
    assert theory.final_sd(1000, p_right) == 0
    assert theory.final_mean(1000, p_right) == mean


def test_normal_pdf_integrates_to_one():
    x = np.linspace(-200, 200, 20001)
    area = np.trapezoid(theory.normal_pdf(x, 5.0, 20.0), x)
    assert area == pytest.approx(1.0, abs=1e-6)


def test_half_normal_pdf_integrates_to_one_above_wall():
    wall = -30.0
    x = np.linspace(wall, wall + 400, 20001)
    area = np.trapezoid(theory.half_normal_pdf(x, wall, 25.0), x)
    assert area == pytest.approx(1.0, abs=1e-6)


def test_wall_curve_only_valid_without_drift():
    assert theory.wall_curve_valid(0.5)
    assert theory.wall_curve_valid(50 / 100)  # as the 0-100% slider will produce it
    assert not theory.wall_curve_valid(0.51)
    assert not theory.wall_curve_valid(0.49)
