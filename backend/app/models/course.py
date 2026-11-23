from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.enrollment import Enrollment
    from app.models.teacher import Teacher

DEFAULT_CAPACITY = 40


class Course(IdMixin, TimestampMixin, Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("credits BETWEEN 1 AND 6", name="credits_range"),
        CheckConstraint("capacity >= 1", name="capacity_positive"),
    )

    code: Mapped[str] = mapped_column(String(15), unique=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    credits: Mapped[int]
    capacity: Mapped[int] = mapped_column(
        default=DEFAULT_CAPACITY, server_default=str(DEFAULT_CAPACITY)
    )
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    # BR-2 (teacher belongs to the course's department) is a service rule.
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), index=True)

    department: Mapped["Department"] = relationship(back_populates="courses")
    teacher: Mapped["Teacher | None"] = relationship(back_populates="courses")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course")

    @validates("code")
    def _normalize_code(self, _key: str, value: str) -> str:
        """Codes are stored uppercase, which makes uniqueness case-insensitive (BR-1)."""
        return value.strip().upper()

    def __repr__(self) -> str:
        return f"<Course id={self.id} code={self.code!r}>"
