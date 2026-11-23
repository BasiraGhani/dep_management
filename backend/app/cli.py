"""Command-line tools.

    python -m app.cli seed-admin   # create the first admin from FIRST_ADMIN_* settings
    python -m app.cli seed-demo    # create realistic demo data and one login per role

Both commands are idempotent: every row is looked up by its unique key first,
so running them again creates nothing new and changes nothing that exists.
Run `alembic upgrade head` before seeding.
"""

import argparse
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models import (
    Course,
    Department,
    Enrollment,
    Grade,
    Student,
    StudentStatus,
    Teacher,
    TeacherTitle,
    User,
    UserRole,
)
from app.schemas.auth import PASSWORD_MIN_LENGTH

# ---------------------------------------------------------------------------
# seed-admin
# ---------------------------------------------------------------------------


class SeedError(Exception):
    """A seed command can't run (bad configuration or conflicting data)."""


def seed_admin(db: Session, settings: Settings) -> bool:
    """Create the first admin from FIRST_ADMIN_USERNAME / FIRST_ADMIN_PASSWORD (FR-1.5).

    Returns True if the admin was created, False if it already existed (its
    password is left unchanged). Raises SeedError if the settings are missing or
    the username belongs to a non-admin account.
    """
    username = (settings.first_admin_username or "").strip().lower()
    password = settings.first_admin_password or ""
    if not username or not password:
        raise SeedError("Set FIRST_ADMIN_USERNAME and FIRST_ADMIN_PASSWORD (e.g. in backend/.env)")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise SeedError(f"FIRST_ADMIN_PASSWORD must be at least {PASSWORD_MIN_LENGTH} characters")

    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        if existing.role is not UserRole.ADMIN:
            raise SeedError(
                f"User {username!r} exists but is a {existing.role.value}, not an admin"
            )
        return False

    db.add(User(username=username, password_hash=hash_password(password), role=UserRole.ADMIN))
    db.commit()
    return True


# ---------------------------------------------------------------------------
# seed-demo
# ---------------------------------------------------------------------------

DEMO_PASSWORD = "demo-password"
CURRENT_SEMESTER = "2026-Fall"
PREVIOUS_SEMESTER = "2026-Spring"
STUDENTS_PER_DEPARTMENT = 20
COURSES_PER_STUDENT = 2

# code, name, building, phone, teachers (first one is the head), courses
DEMO_DEPARTMENTS = [
    (
        "CS",
        "Computer Science",
        "Turing Hall",
        "+1 555 0100",
        [
            ("Ada", "Lovelace", TeacherTitle.PROFESSOR),
            ("Alan", "Kay", TeacherTitle.ASSOCIATE_PROFESSOR),
            ("Grace", "Hopper", TeacherTitle.ASSISTANT_PROFESSOR),
            ("Linus", "Pauling", TeacherTitle.LECTURER),
        ],
        [
            ("CS101", "Introduction to Programming", 4),
            ("CS201", "Data Structures", 4),
            ("CS301", "Databases", 3),
            ("CS350", "Web Development", 3),
        ],
    ),
    (
        "MATH",
        "Mathematics",
        "Noether Building",
        "+1 555 0200",
        [
            ("Emmy", "Noether", TeacherTitle.PROFESSOR),
            ("Srinivasa", "Ramanujan", TeacherTitle.ASSOCIATE_PROFESSOR),
            ("Katherine", "Johnson", TeacherTitle.LECTURER),
        ],
        [
            ("MATH101", "Calculus I", 4),
            ("MATH201", "Linear Algebra", 3),
            ("MATH250", "Discrete Mathematics", 3),
            ("MATH301", "Probability and Statistics", 3),
        ],
    ),
    (
        "PHYS",
        "Physics",
        "Curie Laboratory",
        "+1 555 0300",
        [
            ("Marie", "Curie", TeacherTitle.PROFESSOR),
            ("Richard", "Feynman", TeacherTitle.ASSOCIATE_PROFESSOR),
            ("Lise", "Meitner", TeacherTitle.ASSISTANT_PROFESSOR),
        ],
        [
            ("PHYS101", "Mechanics", 4),
            ("PHYS201", "Electricity and Magnetism", 4),
            ("PHYS301", "Quantum Physics", 3),
            ("PHYS310", "Thermodynamics", 3),
        ],
    ),
]

STUDENT_FIRST_NAMES = [
    "Amira", "Bilal", "Chen", "Dana", "Elif", "Farid", "Gita", "Hassan", "Ines", "Jonas",
    "Kemal", "Layla", "Mateo", "Nadia", "Omar", "Priya", "Quinn", "Rosa", "Samir", "Tara",
]  # fmt: skip
STUDENT_LAST_NAMES = [
    "Ahmadi", "Brown", "Costa", "Diallo", "Evans", "Fischer", "Garcia", "Haddad", "Ito", "Jansen",
    "Khan", "Larsen", "Moreau", "Novak", "Okafor", "Petrov", "Quraishi", "Rossi", "Silva", "Tanaka",
]  # fmt: skip
GRADES = [Grade.A, Grade.A_MINUS, Grade.B_PLUS, Grade.B, Grade.B_MINUS, Grade.C_PLUS, Grade.C]


@dataclass
class SeedReport:
    """What a seed-demo run created (zeros on a repeat run)."""

    created: dict[str, int] = field(default_factory=dict)
    logins: list[tuple[str, UserRole]] = field(default_factory=list)

    def count(self, kind: str) -> None:
        self.created[kind] = self.created.get(kind, 0) + 1


def _get_or_create_department(
    db: Session, report: SeedReport, code: str, name: str, building: str, phone: str
) -> Department:
    department = db.scalar(select(Department).where(Department.code == code))
    if department is None:
        department = Department(code=code, name=name, building=building, phone=phone)
        db.add(department)
        db.flush()
        report.count("departments")
    return department


def _get_or_create_teacher(
    db: Session,
    report: SeedReport,
    department: Department,
    first: str,
    last: str,
    title: TeacherTitle,
) -> Teacher:
    email = f"{first}.{last}@uni.example".lower()
    teacher = db.scalar(select(Teacher).where(Teacher.email == email))
    if teacher is None:
        teacher = Teacher(
            first_name=first,
            last_name=last,
            email=email,
            title=title,
            department_id=department.id,
            hire_date=date(2015, 9, 1),
        )
        db.add(teacher)
        db.flush()
        report.count("teachers")
    return teacher


def _get_or_create_student(
    db: Session, report: SeedReport, department: Department, index: int
) -> Student:
    student_no = f"{department.code}{2026_000 + index + 1}"
    student = db.scalar(select(Student).where(Student.student_no == student_no))
    if student is None:
        first = STUDENT_FIRST_NAMES[index % len(STUDENT_FIRST_NAMES)]
        last = STUDENT_LAST_NAMES[(index * 7 + len(department.code)) % len(STUDENT_LAST_NAMES)]
        year = index % 4 + 1
        # Most students are active; a few have other statuses (only active ones enroll, BR-4).
        status = {17: StudentStatus.GRADUATED, 18: StudentStatus.SUSPENDED}.get(
            index, StudentStatus.ACTIVE
        )
        student = Student(
            student_no=student_no,
            first_name=first,
            last_name=last,
            email=f"{first}.{last}.{student_no}@student.uni.example".lower(),
            department_id=department.id,
            year=year,
            status=status,
            enrollment_date=date(2027 - year, 9, 1),
            date_of_birth=date(2007 - year, 1 + index % 12, 1 + index % 28),
        )
        db.add(student)
        db.flush()
        report.count("students")
    return student


def _get_or_create_course(
    db: Session,
    report: SeedReport,
    department: Department,
    teacher: Teacher | None,
    code: str,
    title: str,
    credits: int,
) -> Course:
    course = db.scalar(select(Course).where(Course.code == code))
    if course is None:
        course = Course(
            code=code,
            title=title,
            description=f"{title}, offered by the {department.name} department.",
            credits=credits,
            capacity=40,
            department_id=department.id,
            teacher_id=teacher.id if teacher else None,  # same department (BR-2)
        )
        db.add(course)
        db.flush()
        report.count("courses")
    return course


def _get_or_create_enrollment(
    db: Session,
    report: SeedReport,
    student: Student,
    course: Course,
    semester: str,
    grade: Grade | None,
) -> None:
    exists = db.scalar(
        select(Enrollment.id).where(
            Enrollment.student_id == student.id,
            Enrollment.course_id == course.id,
            Enrollment.semester == semester,
        )
    )
    if exists is None:
        db.add(
            Enrollment(student_id=student.id, course_id=course.id, semester=semester, grade=grade)
        )
        report.count("enrollments")


def _get_or_create_login(
    db: Session,
    report: SeedReport,
    username: str,
    role: UserRole,
    teacher: Teacher | None = None,
    student: Student | None = None,
) -> None:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        db.add(
            User(
                username=username,
                password_hash=hash_password(DEMO_PASSWORD),
                role=role,
                teacher_id=teacher.id if teacher else None,
                student_id=student.id if student else None,
            )
        )
        report.count("users")
    report.logins.append((username, role))


def seed_demo(db: Session) -> SeedReport:
    """Create the demo dataset (see module docstring); safe to run repeatedly.

    3 departments, 10 teachers (the first in each department is its head),
    60 students, 12 courses, enrollments for active students (graded in
    PREVIOUS_SEMESTER, mostly ungraded in CURRENT_SEMESTER) and one login per role.
    """
    report = SeedReport()
    rng = random.Random(2026)  # fixed seed: the same grades on every machine
    seeded: dict[str, tuple[list[Teacher], list[Student]]] = {}

    for code, name, building, phone, teacher_specs, course_specs in DEMO_DEPARTMENTS:
        department = _get_or_create_department(db, report, code, name, building, phone)
        teachers = [_get_or_create_teacher(db, report, department, *t) for t in teacher_specs]
        head = teachers[0]
        if department.head_id is None:
            department.head_id = head.id  # the HOD role is set on the login below (BR-6)

        courses = [
            _get_or_create_course(db, report, department, teachers[i % len(teachers)], *spec)
            for i, spec in enumerate(course_specs)
        ]
        students = [
            _get_or_create_student(db, report, department, i)
            for i in range(STUDENTS_PER_DEPARTMENT)
        ]

        for i, student in enumerate(students):
            if student.status is not StudentStatus.ACTIVE:
                continue
            for k in range(COURSES_PER_STUDENT):
                past = courses[(i + k) % len(courses)]
                current = courses[(i + k + 2) % len(courses)]
                _get_or_create_enrollment(
                    db, report, student, past, PREVIOUS_SEMESTER, rng.choice(GRADES)
                )
                # A few current-semester grades are already in; the rest are pending.
                fall_grade = rng.choice(GRADES) if i % 5 == 0 else None
                _get_or_create_enrollment(
                    db, report, student, current, CURRENT_SEMESTER, fall_grade
                )

        seeded[code] = (teachers, students)

    # One login per role, all in Computer Science: its head, a teacher who is
    # not the head, and its first (active) student.
    cs_teachers, cs_students = seeded["CS"]
    _get_or_create_login(db, report, "demo.admin", UserRole.ADMIN)
    _get_or_create_login(db, report, "demo.hod", UserRole.HOD, teacher=cs_teachers[0])
    _get_or_create_login(db, report, "demo.teacher", UserRole.TEACHER, teacher=cs_teachers[1])
    _get_or_create_login(db, report, "demo.student", UserRole.STUDENT, student=cs_students[0])

    db.commit()
    return report


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def _print_demo_report(report: SeedReport) -> None:
    created = ", ".join(f"{n} {kind}" for kind, n in report.created.items()) or "nothing new"
    print(f"Demo data: created {created}.")
    print(f"\nDemo logins (password for all: {DEMO_PASSWORD}):")
    for username, role in report.logins:
        print(f"  {role.value:<8} {username}")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for `python -m app.cli`. Returns the process exit code."""
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed-admin", help="create the first admin from FIRST_ADMIN_* settings")
    commands.add_parser("seed-demo", help="create demo data and one login per role")
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        try:
            if args.command == "seed-admin":
                settings = get_settings()
                created = seed_admin(db, settings)
                username = (settings.first_admin_username or "").strip().lower()
                verb = "Created" if created else "Already exists:"
                print(f"{verb} admin {username!r}.")
            else:
                _print_demo_report(seed_demo(db))
        except SeedError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
