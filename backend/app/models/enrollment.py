import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.student import Student


class Grade(enum.StrEnum):
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D = "D"
    F = "F"


class Enrollment(IdMixin, TimestampMixin, Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", "semester"),)

    # Deleting a student deletes their enrollments (FR-4.4), in the database itself.
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    # Format (YYYY-Spring|Summer|Fall) is validated by the schema/service layer (T4.1).
    semester: Mapped[str] = mapped_column(String(20))
    # NULL means "not graded yet" (FR-6.5).
    grade: Mapped[Grade | None] = mapped_column(
        # Stored as VARCHAR + CHECK (not a native enum) so SQLite and PostgreSQL match.
        Enum(
            Grade,
            name="grade",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            length=2,
            values_callable=lambda members: [member.value for member in members],
        )
    )

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")

    def __repr__(self) -> str:
        return (
            f"<Enrollment id={self.id} student_id={self.student_id} "
            f"course_id={self.course_id} semester={self.semester!r}>"
        )
