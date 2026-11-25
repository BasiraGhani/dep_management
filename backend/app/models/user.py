import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.teacher import Teacher


class UserRole(enum.StrEnum):
    ADMIN = "admin"
    HOD = "hod"
    TEACHER = "teacher"
    STUDENT = "student"


class User(IdMixin, TimestampMixin, Base):
    """A login account.

    Which link a role may have (admin: none; hod/teacher: teacher_id; student:
    student_id) is enforced by the service layer, per ARCHITECTURE §2.
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        # Stored as VARCHAR + CHECK (not a native enum) so SQLite and PostgreSQL match.
        Enum(
            UserRole,
            name="role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            length=10,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), unique=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), unique=True)

    teacher: Mapped["Teacher | None"] = relationship(back_populates="user")
    student: Mapped["Student | None"] = relationship(back_populates="user")

    @property
    def linked_name(self) -> str | None:
        """The linked teacher's or student's name ("First Last"); None for admins."""
        person = self.teacher or self.student
        return f"{person.first_name} {person.last_name}" if person else None

    @validates("username")
    def _normalize_username(self, _key: str, value: str) -> str:
        """Usernames are stored lowercase, which makes uniqueness case-insensitive (BR-1)."""
        return value.strip().lower()

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
