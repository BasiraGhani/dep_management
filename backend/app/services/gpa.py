"""GPA calculation (FR-6.6): 4.0 scale, weighted by credits, graded enrollments only."""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from app.models.enrollment import Grade

# ARCHITECTURE §2.
GRADE_POINTS: dict[Grade, Decimal] = {
    Grade.A: Decimal("4.0"),
    Grade.A_MINUS: Decimal("3.7"),
    Grade.B_PLUS: Decimal("3.3"),
    Grade.B: Decimal("3.0"),
    Grade.B_MINUS: Decimal("2.7"),
    Grade.C_PLUS: Decimal("2.3"),
    Grade.C: Decimal("2.0"),
    Grade.C_MINUS: Decimal("1.7"),
    Grade.D: Decimal("1.0"),
    Grade.F: Decimal("0.0"),
}


def calculate_gpa(results: Iterable[tuple[Grade | None, int]]) -> float | None:
    """GPA from (grade, credits) pairs, rounded half-up to 2 decimals.

    Ungraded results (grade None) are ignored. Returns None when nothing is
    graded, so "no GPA yet" is different from a GPA of 0.0 (all F).
    """
    points = Decimal(0)
    credits = 0
    for grade, course_credits in results:
        if grade is None:
            continue
        points += GRADE_POINTS[grade] * course_credits
        credits += course_credits
    if credits == 0:
        return None
    return float((points / credits).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
