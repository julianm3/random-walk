import numpy as np
import pytest

from random_walk import theory


@pytest.mark.parametrize(
    ("theta", "expected"),
    [(0, 0.5), (90, 0.0), (-90, 1.0), (30, 0.25), (-30, 0.75)],
)
def test_p_right_matches_slope_formula(theta, expected):
    assert theory.p_right(theta) == pytest.approx(expected)


def test_positive_theta_biases_left():
    assert theory.p_right(10) < 0.5 < theory.p_right(-10)


@pytest.mark.parametrize("theta", [0, 15, -45, 60])
def test_final_mean_and_sd(theta):
    steps = 400
    rad = np.radians(theta)
    assert theory.final_mean(steps, theta) == pytest.approx(-steps * np.sin(rad))
    assert theory.final_sd(steps, theta) == pytest.approx(np.sqrt(steps) * abs(np.cos(rad)))


def test_final_sd_scales_with_abs_cos_theta():
    base = theory.final_sd(100, 0)
    for theta in (20, -20, 60):
        expected = base * abs(np.cos(np.radians(theta)))
        assert theory.final_sd(100, theta) == pytest.approx(expected)


@pytest.mark.parametrize("theta", [90, -90])
def test_final_sd_is_exactly_zero_when_fully_biased(theta):
    assert theory.final_sd(1000, theta) == 0


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
    assert theory.wall_curve_valid(0)
    assert not theory.wall_curve_valid(5)
    assert not theory.wall_curve_valid(-0.1)
