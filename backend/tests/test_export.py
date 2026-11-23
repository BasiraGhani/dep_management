"""Tests for GET /export/{resource}.csv (T4.5, FR-9.1).

Admin exports every row; a HOD only their department (user decision). The list
filters apply. `world`:
    dept A (DEPA): head HA (`hod`), teacher TA; courses A1 (TA), A2 (HA)
                   students: amy (year 1, active), al (year 2, suspended)
    dept B (DEPB): teacher TB; course B1 (TB); student bea (year 1, active)
"""

import csv
import io
from dataclasses import dataclass

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Department, StudentStatus, Teacher, TeacherTitle, User, UserRole
from app.services.export import safe_cell
from tests.conftest import Factory
from tests.helpers import auth_headers

STUDENT_HEADER = [
    "id", "student_no", "first_name", "last_name", "email", "phone",
    "date_of_birth", "department", "year", "status", "enrollment_date",
]  # fmt: skip
TEACHER_HEADER = [
    "id", "first_name", "last_name", "email", "phone", "title", "department", "hire_date",
]  # fmt: skip
COURSE_HEADER = ["id", "code", "title", "credits", "capacity", "department", "teacher"]


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    teacher_a: Teacher
    admin: User
    hod: User
    teacher: User
    student: User


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    head_a = factory.teacher(
        dept_a, first_name="Hedy", last_name="Head", title=TeacherTitle.PROFESSOR
    )
    teacher_a = factory.teacher(dept_a, first_name="Tom", last_name="Teach")
    teacher_b = factory.teacher(dept_b, first_name="Bea", last_name="Brown")
    dept_a.head_id = head_a.id
    factory.course(dept_a, teacher=teacher_a, code="A1", title="Algebra")
    factory.course(dept_a, teacher=head_a, code="A2", title="Biology")
    factory.course(dept_b, teacher=teacher_b, code="B1", title="Chemistry")
    amy = factory.student(dept_a, first_name="Amy", last_name="Ash", student_no="A001", year=1)
    factory.student(
        dept_a, first_name="Al", last_name="Ames", student_no="A002", year=2,
        status=StudentStatus.SUSPENDED, phone="+1 555 0100",
    )  # fmt: skip
    factory.student(dept_b, first_name="Bea", last_name="Bird", student_no="B001", year=1)
    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        teacher_a=teacher_a,
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head_a),
        teacher=factory.user(UserRole.TEACHER, teacher=teacher_a),
        student=factory.user(UserRole.STUDENT, student=amy),
    )
    session.commit()
    return world


def export(client: TestClient, user: User, resource: str, **params: object) -> httpx.Response:
    response: httpx.Response = client.get(
        f"/api/v1/export/{resource}.csv", params=params, headers=auth_headers(user)
    )
    return response


def rows(response: httpx.Response) -> list[list[str]]:
    assert response.status_code == 200, response.text
    return list(csv.reader(io.StringIO(response.text)))


def column(response: httpx.Response, name: str) -> list[str]:
    header, *data = rows(response)
    index = header.index(name)
    return [row[index] for row in data]


# ===================================================== format


@pytest.mark.parametrize(
    ("resource", "header"),
    [("students", STUDENT_HEADER), ("teachers", TEACHER_HEADER), ("courses", COURSE_HEADER)],
)
def test_csv_has_a_header_row_and_download_headers(
    client: TestClient, world: World, resource: str, header: list[str]
) -> None:
    response = export(client, world.admin, resource)

    assert rows(response)[0] == header
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == f'attachment; filename="{resource}.csv"'


def test_student_rows_contain_the_record(client: TestClient, world: World) -> None:
    header, *data = rows(export(client, world.admin, "students", search="A002"))
    record = dict(zip(header, data[0], strict=True))

    assert record | {"id": "", "email": ""} == {
        "id": "",
        "student_no": "A002",
        "first_name": "Al",
        "last_name": "Ames",
        "email": "",
        "phone": "+1 555 0100",  # a phone number isn't mistaken for a formula
        "date_of_birth": "",
        "department": "DEPA",
        "year": "2",
        "status": "suspended",
        "enrollment_date": "2026-09-01",
    }


def test_course_rows_name_the_teacher(client: TestClient, world: World) -> None:
    response = export(client, world.admin, "courses")
    assert column(response, "teacher") == ["Tom Teach", "Hedy Head", "Bea Brown"]
    assert column(response, "department") == ["DEPA", "DEPA", "DEPB"]


def test_empty_result_is_just_the_header(client: TestClient, world: World) -> None:
    assert rows(export(client, world.admin, "students", search="nobody")) == [STUDENT_HEADER]


# ===================================================== filters (same as the list endpoints)


@pytest.mark.parametrize(
    ("params", "numbers"),
    [
        ({}, ["A002", "A001", "B001"]),  # ordered by last name, like the list
        ({"year": 1}, ["A001", "B001"]),
        ({"status": "suspended"}, ["A002"]),
        ({"department_id": "B"}, ["B001"]),
        ({"search": "bird"}, ["B001"]),
        ({"year": 1, "department_id": "A"}, ["A001"]),
    ],
)
def test_student_filters(
    client: TestClient, world: World, params: dict[str, object], numbers: list[str]
) -> None:
    ids = {"A": world.dept_a.id, "B": world.dept_b.id}
    resolved = {k: ids.get(str(v), v) for k, v in params.items()}

    assert column(export(client, world.admin, "students", **resolved), "student_no") == numbers


@pytest.mark.parametrize(
    ("params", "names"),
    [
        ({}, ["Brown", "Head", "Teach"]),
        ({"title": "professor"}, ["Head"]),
        ({"search": "tom"}, ["Teach"]),
        ({"department_id": "B"}, ["Brown"]),
    ],
)
def test_teacher_filters(
    client: TestClient, world: World, params: dict[str, object], names: list[str]
) -> None:
    resolved = {k: (world.dept_b.id if v == "B" else v) for k, v in params.items()}
    assert column(export(client, world.admin, "teachers", **resolved), "last_name") == names


@pytest.mark.parametrize(
    ("params", "codes"),
    [
        ({}, ["A1", "A2", "B1"]),
        ({"search": "chem"}, ["B1"]),
        ({"teacher_id": "TA"}, ["A1"]),
        ({"department_id": "A"}, ["A1", "A2"]),
    ],
)
def test_course_filters(
    client: TestClient, world: World, params: dict[str, object], codes: list[str]
) -> None:
    refs = {"TA": world.teacher_a.id, "A": world.dept_a.id}
    resolved = {k: refs.get(str(v), v) for k, v in params.items()}
    assert column(export(client, world.admin, "courses", **resolved), "code") == codes


def test_filters_that_do_not_apply_are_ignored(client: TestClient, world: World) -> None:
    response = export(client, world.admin, "courses", year=3, title="professor")
    assert column(response, "code") == ["A1", "A2", "B1"]


@pytest.mark.parametrize("params", [{"year": 9}, {"status": "expelled"}, {"title": "dean"}])
def test_invalid_filters_are_rejected(
    client: TestClient, world: World, params: dict[str, object]
) -> None:
    assert export(client, world.admin, "students", **params).status_code == 422


def test_unknown_resource_is_rejected(client: TestClient, world: World) -> None:
    assert export(client, world.admin, "grades").status_code == 422


# ===================================================== who may export, and which rows


@pytest.mark.parametrize(
    ("resource", "key", "values"),
    [
        ("students", "student_no", ["A002", "A001"]),
        ("teachers", "last_name", ["Head", "Teach"]),
        ("courses", "code", ["A1", "A2"]),
    ],
)
def test_hod_exports_only_their_department(
    client: TestClient, world: World, resource: str, key: str, values: list[str]
) -> None:
    assert column(export(client, world.hod, resource), key) == values


def test_hod_cannot_widen_the_export_with_a_filter(client: TestClient, world: World) -> None:
    response = export(client, world.hod, "students", department_id=world.dept_b.id)
    assert rows(response) == [STUDENT_HEADER]


def test_hod_whose_head_role_is_stale_cannot_export(
    client: TestClient, session: Session, factory: Factory, world: World
) -> None:
    world.dept_a.head_id = factory.teacher(world.dept_a).id
    session.commit()

    response = export(client, world.hod, "students")

    assert response.status_code == 403
    assert response.json() == {"detail": "You can only export the department you head"}


@pytest.mark.parametrize("role", ["teacher", "student"])
@pytest.mark.parametrize("resource", ["students", "teachers", "courses"])
def test_teachers_and_students_cannot_export(
    client: TestClient, world: World, role: str, resource: str
) -> None:
    response = export(client, getattr(world, role), resource)

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_export_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get("/api/v1/export/students.csv").status_code == 401


# ===================================================== CSV injection


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ('=HYPERLINK("http://x")', '\'=HYPERLINK("http://x")'),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
        ("-2+3", "'-2+3"),  # spreadsheets evaluate this, so it is neutralised too
        ("-12.5", "-12.5"),  # a plain negative number stays as it is
        ("-x", "'-x"),
        ("+1 (555) 010-2030", "+1 (555) 010-2030"),
        ("Plain text", "Plain text"),
        (None, ""),
        (42, "42"),
    ],
)
def test_cells_that_spreadsheets_would_run_are_neutralised(value: object, written: str) -> None:
    assert safe_cell(value) == written


def test_a_formula_in_a_name_is_neutralised_in_the_export(
    client: TestClient, factory: Factory, world: World
) -> None:
    factory.student(world.dept_a, first_name="=1+1", last_name="Zed")

    names = column(export(client, world.admin, "students", search="Zed"), "first_name")

    assert names == ["'=1+1"]
