import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.enrollment import Enrollment
    from app.models.user import User


class StudentStatus(enum.StrEnum):
    ACTIVE = "active"
    GRADUATED = "graduated"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


class Student(IdMixin, TimestampMixin, Base):
    __tablename__ = "students"
    __table_args__ = (CheckConstraint("year BETWEEN 1 AND 6", name="year_range"),)

    student_no: Mapped[str] = mapped_column(String(20), unique=True)
    first_name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str] = mapped_column(String(60))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    date_of_birth: Mapped[date | None]
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    year: Mapped[int]
    status: Mapped[StudentStatus] = mapped_column(
        # Stored as VARCHAR + CHECK (not a native enum) so SQLite and PostgreSQL match.
        Enum(
            StudentStatus,
            name="status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            length=20,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    enrollment_date: Mapped[date]

    department: Mapped["Department"] = relationship(back_populates="students")
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        passive_deletes=True,  # the database's ON DELETE CASCADE removes the rows (FR-4.4)
    )
    user: Mapped["User | None"] = relationship(back_populates="student")

    @validates("student_no")
    def _normalize_student_no(self, _key: str, value: str) -> str:
        """Student numbers are stored uppercase: uniqueness is case-insensitive (BR-1)."""
        return value.strip().upper()

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """Emails are stored lowercase, which makes uniqueness case-insensitive (BR-1)."""
        return value.strip().lower()

    def __repr__(self) -> str:
        return f"<Student id={self.id} student_no={self.student_no!r}>"
