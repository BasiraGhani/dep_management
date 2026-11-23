"""Unit tests for the GPA service (T4.2, FR-6.6)."""

import pytest

from app.models import Grade
from app.services.gpa import GRADE_POINTS, calculate_gpa

G = Grade


def test_no_results_is_null() -> None:
    assert calculate_gpa([]) is None


def test_no_grades_is_null() -> None:
    """Enrolled but nothing graded yet: no GPA, which is not the same as 0.0."""
    assert calculate_gpa([(None, 3), (None, 4)]) is None


def test_all_f_is_zero() -> None:
    assert calculate_gpa([(G.F, 3), (G.F, 4), (G.F, 1)]) == 0.0


def test_mixed_credits_are_weighted() -> None:
    # A (4.0) x 4 credits + C (2.0) x 2 credits = 20 points / 6 credits = 3.333...
    assert calculate_gpa([(G.A, 4), (G.C, 2)]) == 3.33


def test_weighting_differs_from_a_plain_average() -> None:
    # Plain average of 4.0 and 0.0 would be 2.0; weighted by 5 and 1 credits it's 3.33.
    assert calculate_gpa([(G.A, 5), (G.F, 1)]) == 3.33


def test_ungraded_enrollments_are_ignored() -> None:
    assert calculate_gpa([(G.B, 3), (None, 6)]) == 3.0


def test_rounds_half_up_to_two_decimals() -> None:
    # (4.0 x 4 + 3.0 x 3 + 0.0 x 1) / 8 = 3.125 -> 3.13 (banker's rounding would give 3.12)
    assert calculate_gpa([(G.A, 4), (G.B, 3), (G.F, 1)]) == 3.13


@pytest.mark.parametrize(
    ("grade", "points"),
    [
        (G.A, 4.0),
        (G.A_MINUS, 3.7),
        (G.B_PLUS, 3.3),
        (G.B, 3.0),
        (G.B_MINUS, 2.7),
        (G.C_PLUS, 2.3),
        (G.C, 2.0),
        (G.C_MINUS, 1.7),
        (G.D, 1.0),
        (G.F, 0.0),
    ],
)
def test_each_grade_uses_the_architecture_points(grade: Grade, points: float) -> None:
    assert calculate_gpa([(grade, 3)]) == points


def test_every_grade_has_points() -> None:
    assert set(GRADE_POINTS) == set(Grade)
