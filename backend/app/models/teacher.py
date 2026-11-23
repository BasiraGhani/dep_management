import enum
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department


class TeacherTitle(enum.StrEnum):
    LECTURER = "lecturer"
    ASSISTANT_PROFESSOR = "assistant_professor"
    ASSOCIATE_PROFESSOR = "associate_professor"
    PROFESSOR = "professor"


class Teacher(IdMixin, TimestampMixin, Base):
    __tablename__ = "teachers"

    first_name: Mapped[str] = mapped_column(String(60))
    last_name: Mapped[str] = mapped_column(String(60))
    email: Mapped[str] = mapped_column(String(120), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    title: Mapped[TeacherTitle] = mapped_column(
        # Stored as VARCHAR + CHECK (not a native enum) so SQLite and PostgreSQL match.
        Enum(
            TeacherTitle,
            name="title",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            length=30,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    hire_date: Mapped[date | None]

    department: Mapped["Department"] = relationship(
        back_populates="teachers", foreign_keys=[department_id]
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """Emails are stored lowercase, which makes uniqueness case-insensitive (BR-1)."""
        return value.strip().lower()

    def __repr__(self) -> str:
        return f"<Teacher id={self.id} email={self.email!r}>"
