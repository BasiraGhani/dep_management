"""SQLAlchemy models, one module per table.

Every model is imported here so `Base.metadata` is complete for Alembic.
"""

from app.models.department import Department
from app.models.student import Student, StudentStatus
from app.models.teacher import Teacher, TeacherTitle

__all__ = ["Department", "Student", "StudentStatus", "Teacher", "TeacherTitle"]
