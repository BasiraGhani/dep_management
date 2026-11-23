"""Role-specific dashboard figures (FR-7.1–FR-7.4).

* admin: totals, students per department and recent enrollments, everywhere
* hod: the same figures for the department they head
* teacher: their courses with enrolled and ungraded counts (all semesters)
* student: their enrollments with grades, and their GPA

Every figure is computed with aggregate queries, so the cost doesn't grow with
the number of rows shown.
"""

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.permissions import managed_department_id
from app.models import Course, Department, Enrollment, Student, Teacher, User, UserRole
from app.schemas.common import CourseBrief
from app.schemas.dashboard import (
    AdminDashboard,
    DepartmentRef,
    DepartmentStudents,
    HodDashboard,
    StudentDashboard,
    TeacherCourseStats,
    TeacherDashboard,
    Totals,
)
from app.schemas.enrollment import EnrollmentOut
from app.schemas.student import StudentEnrollmentOut
from app.services.gpa import calculate_gpa

RECENT_ENROLLMENTS = 10


def _count(db: Session, model: type[Teacher | Student | Course], dept: int | None) -> int:
    query = select(func.count()).select_from(model)
    if dept is not None:
        query = query.where(model.department_id == dept)
    return db.scalar(query) or 0


def _totals(db: Session, dept: int | None) -> Totals:
    departments = select(func.count()).select_from(Department)
    if dept is not None:
        departments = departments.where(Department.id == dept)
    return Totals(
        departments=db.scalar(departments) or 0,
        teachers=_count(db, Teacher, dept),
        students=_count(db, Student, dept),
        courses=_count(db, Course, dept),
    )


def _students_per_department(db: Session, dept: int | None) -> list[DepartmentStudents]:
    query = (
        select(Department.id, Department.code, Department.name, func.count(Student.id))
        .outerjoin(Student, Student.department_id == Department.id)
        .group_by(Department.id, Department.code, Department.name)
        .order_by(Department.code)
    )
    if dept is not None:
        query = query.where(Department.id == dept)
    return [
        DepartmentStudents(department_id=i, code=code, name=name, students=n)
        for i, code, name, n in db.execute(query)
    ]


def _recent_enrollments(db: Session, dept: int | None) -> list[EnrollmentOut]:
    query = (
        select(Enrollment)
        .join(Course, Course.id == Enrollment.course_id)
        .options(joinedload(Enrollment.student), joinedload(Enrollment.course))
        .order_by(Enrollment.created_at.desc(), Enrollment.id.desc())
        .limit(RECENT_ENROLLMENTS)
    )
    if dept is not None:
        query = query.where(Course.department_id == dept)
    return [EnrollmentOut.model_validate(e) for e in db.scalars(query)]


def admin_dashboard(db: Session) -> AdminDashboard:
    return AdminDashboard(
        totals=_totals(db, None),
        students_per_department=_students_per_department(db, None),
        recent_enrollments=_recent_enrollments(db, None),
    )


def hod_dashboard(db: Session, user: User) -> HodDashboard:
    dept_id = managed_department_id(user)
    department = db.get(Department, dept_id) if dept_id is not None else None
    if department is None:  # the account no longer heads a department
        return HodDashboard(
            department=None,
            totals=Totals(departments=0, teachers=0, students=0, courses=0),
            students_per_department=[],
            recent_enrollments=[],
        )
    return HodDashboard(
        department=DepartmentRef(id=department.id, code=department.code, name=department.name),
        totals=_totals(db, department.id),
        students_per_department=_students_per_department(db, department.id),
        recent_enrollments=_recent_enrollments(db, department.id),
    )


def teacher_dashboard(db: Session, user: User) -> TeacherDashboard:
    if user.teacher_id is None:
        return TeacherDashboard(courses=[])
    enrolled = func.count(Enrollment.id)
    # The outer join yields one all-NULL row for a course without enrollments; it
    # must not count as an ungraded enrollment, hence the Enrollment.id check.
    is_ungraded = and_(Enrollment.id.is_not(None), Enrollment.grade.is_(None))
    ungraded = func.coalesce(func.sum(case((is_ungraded, 1), else_=0)), 0)
    rows = db.execute(
        select(Course, enrolled, ungraded)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .where(Course.teacher_id == user.teacher_id)
        .group_by(Course.id)
        .order_by(Course.code)
    ).all()
    return TeacherDashboard(
        courses=[
            TeacherCourseStats(
                course=CourseBrief.model_validate(course),
                capacity=course.capacity,
                enrolled=n_enrolled,
                ungraded=n_ungraded,
            )
            for course, n_enrolled, n_ungraded in rows
        ]
    )


def student_dashboard(db: Session, user: User) -> StudentDashboard:
    if user.student_id is None:
        return StudentDashboard(enrollments=[], gpa=None, graded_credits=0)
    enrollments = db.scalars(
        select(Enrollment)
        .where(Enrollment.student_id == user.student_id)
        .options(joinedload(Enrollment.course))
        .order_by(Enrollment.id)
    ).all()
    results = [(e.grade, e.course.credits) for e in enrollments]
    return StudentDashboard(
        enrollments=[StudentEnrollmentOut.model_validate(e) for e in enrollments],
        gpa=calculate_gpa(results),
        graded_credits=sum(credits for grade, credits in results if grade is not None),
    )


def dashboard_for(
    db: Session, user: User
) -> AdminDashboard | HodDashboard | TeacherDashboard | StudentDashboard:
    """The dashboard payload for the user's role."""
    if user.role is UserRole.ADMIN:
        return admin_dashboard(db)
    if user.role is UserRole.HOD:
        return hod_dashboard(db, user)
    if user.role is UserRole.TEACHER:
        return teacher_dashboard(db, user)
    return student_dashboard(db, user)
