"""create departments, teachers and students

Revision ID: 39d61678c351
Revises:
Create Date: 2026-11-23 20:00:24.620729

departments.head_id -> teachers.id and teachers.department_id -> departments.id
reference each other, so the head_id foreign key is added after both tables exist
(and dropped first on downgrade). This keeps the migration valid on PostgreSQL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "39d61678c351"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("building", sa.String(length=80), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("head_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_departments")),
        sa.UniqueConstraint("code", name=op.f("uq_departments_code")),
        sa.UniqueConstraint("name", name=op.f("uq_departments_name")),
    )
    op.create_index(op.f("ix_departments_head_id"), "departments", ["head_id"])

    op.create_table(
        "teachers",
        sa.Column("first_name", sa.String(length=60), nullable=False),
        sa.Column("last_name", sa.String(length=60), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column(
            "title",
            sa.Enum(
                "lecturer",
                "assistant_professor",
                "associate_professor",
                "professor",
                name="title",
                native_enum=False,
                create_constraint=True,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_teachers_department_id_departments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teachers")),
        sa.UniqueConstraint("email", name=op.f("uq_teachers_email")),
    )
    op.create_index(op.f("ix_teachers_department_id"), "teachers", ["department_id"])

    op.create_table(
        "students",
        sa.Column("student_no", sa.String(length=20), nullable=False),
        sa.Column("first_name", sa.String(length=60), nullable=False),
        sa.Column("last_name", sa.String(length=60), nullable=False),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "graduated",
                "suspended",
                "withdrawn",
                name="status",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("enrollment_date", sa.Date(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("year BETWEEN 1 AND 6", name=op.f("ck_students_year_range")),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name=op.f("fk_students_department_id_departments"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_students")),
        sa.UniqueConstraint("email", name=op.f("uq_students_email")),
        sa.UniqueConstraint("student_no", name=op.f("uq_students_student_no")),
    )
    op.create_index(op.f("ix_students_department_id"), "students", ["department_id"])

    # Both tables exist now, so the circular head_id FK can be added.
    # (Batch mode: SQLite can't ALTER TABLE ADD CONSTRAINT, so the table is rebuilt.)
    with op.batch_alter_table("departments") as batch_op:
        batch_op.create_foreign_key(
            op.f("fk_departments_head_id_teachers"), "teachers", ["head_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("departments") as batch_op:
        batch_op.drop_constraint(op.f("fk_departments_head_id_teachers"), type_="foreignkey")

    op.drop_index(op.f("ix_students_department_id"), table_name="students")
    op.drop_table("students")
    op.drop_index(op.f("ix_teachers_department_id"), table_name="teachers")
    op.drop_table("teachers")
    op.drop_index(op.f("ix_departments_head_id"), table_name="departments")
    op.drop_table("departments")
