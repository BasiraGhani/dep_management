from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.database import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.student import Student
    from app.models.teacher import Teacher


class Department(IdMixin, TimestampMixin, Base):
    __tablename__ = "departments"

    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    building: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(30))
    # departments <-> teachers reference each other, so this FK is added after both
    # tables exist (use_alter). BR-3 (head belongs to this department) is a service rule.
    head_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", use_alter=True), index=True
    )

    head: Mapped["Teacher | None"] = relationship(
        foreign_keys=[head_id],
        post_update=True,  # lets a department and its head be inserted in one flush
    )
    teachers: Mapped[list["Teacher"]] = relationship(
        back_populates="department", foreign_keys="Teacher.department_id"
    )
    students: Mapped[list["Student"]] = relationship(back_populates="department")

    @validates("code")
    def _normalize_code(self, _key: str, value: str) -> str:
        """Codes are stored uppercase, which makes uniqueness case-insensitive (BR-1)."""
        return value.strip().upper()

    def __repr__(self) -> str:
        return f"<Department id={self.id} code={self.code!r}>"
