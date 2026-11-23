"""SQLAlchemy models, one module per table.

Every model is imported here so `Base.metadata` is complete for Alembic.
"""

from app.models.course import Course
from app.models.department import Department
from app.models.enrollment import Enrollment, Grade
from app.models.student import Student, StudentStatus
from app.models.teacher import Teacher, TeacherTitle
from app.models.user import User, UserRole

__all__ = [
    "Course",
    "Department",
    "Enrollment",
    "Grade",
    "Student",
    "StudentStatus",
    "Teacher",
    "TeacherTitle",
    "User",
    "UserRole",
]
