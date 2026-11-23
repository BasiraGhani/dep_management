"""create courses, enrollments and users

Revision ID: 1ea42b617be5
Revises: 39d61678c351
Create Date: 2026-11-23 20:16:07.942120

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ea42b617be5"
down_revision: str | Sequence[str] | None = "39d61678c351"
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
        "courses",
        sa.Column("code", sa.String(length=15), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), server_default="40", nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("capacity >= 1", name=op.f("ck_courses_capacity_positive")),
        sa.CheckConstraint("credits BETWEEN 1 AND 6", name=op.f("ck_courses_credits_range")),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], name=op.f("fk_courses_department_id_departments")
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["teachers.id"], name=op.f("fk_courses_teacher_id_teachers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("code", name=op.f("uq_courses_code")),
    )
    op.create_index(op.f("ix_courses_department_id"), "courses", ["department_id"])
    op.create_index(op.f("ix_courses_teacher_id"), "courses", ["teacher_id"])

    op.create_table(
        "enrollments",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("semester", sa.String(length=20), nullable=False),
        sa.Column(
            "grade",
            sa.Enum(
                "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F",
                name="grade",
                native_enum=False,
                create_constraint=True,
                length=2,
            ),
            nullable=True,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_enrollments_course_id_courses")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
            name=op.f("fk_enrollments_student_id_students"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollments")),
        sa.UniqueConstraint(
            "student_id",
            "course_id",
            "semester",
            name=op.f("uq_enrollments_student_id_course_id_semester"),
        ),
    )
    op.create_index(op.f("ix_enrollments_course_id"), "enrollments", ["course_id"])

    op.create_table(
        "users",
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "admin",
                "hod",
                "teacher",
                "student",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=10,
            ),
            nullable=False,
        ),
        # sa.true() renders as TRUE on PostgreSQL and 1 on SQLite.
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["student_id"], ["students.id"], name=op.f("fk_users_student_id_students")
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["teachers.id"], name=op.f("fk_users_teacher_id_teachers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("student_id", name=op.f("uq_users_student_id")),
        sa.UniqueConstraint("teacher_id", name=op.f("uq_users_teacher_id")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_index(op.f("ix_enrollments_course_id"), table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index(op.f("ix_courses_teacher_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_department_id"), table_name="courses")
    op.drop_table("courses")
