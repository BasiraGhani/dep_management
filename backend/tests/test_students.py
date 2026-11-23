"""Tests for the students API (T3.3): FR-4.1–FR-4.4, BR-1/7/8, the Students row of the
permission matrix and role scoping, with the T3.3 decisions (student self-edit = phone
and email; delete with a login account -> 409; students get 403 on the list).

`world`:
    dept A (DEPA): head HA (`hod` login) teaches A2; teacher TA (`teacher` login) teaches A1
    dept B (DEPB): teacher TB teaches B1
    students:
        alice  (A) enrolled in A1                 - `student` login
        adam   (A) not enrolled
        bella  (B) enrolled in A1 (cross-department)
        bruno  (B) enrolled in A2 (the HOD's own course) and B1
    plus an `admin` login

Who sees whom:
    admin   -> alice, adam, bella, bruno
    hod     -> alice, adam (own department) + bruno (own course A2)
    teacher -> alice, bella (enrolled in A1)
    student -> only alice, via the detail endpoint
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import cast

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Department, Enrollment, Grade, Student, StudentStatus, User, UserRole
from tests.conftest import Factory
from tests.helpers import auth_headers

URL = "/api/v1/students"
ROLES = ["admin", "hod", "teacher", "student"]


@dataclass
class World:
    dept_a: Department
    dept_b: Department
    alice: Student
    adam: Student
    bella: Student
    bruno: Student
    admin: User
    hod: User
    teacher: User
    student: User

    def user(self, role: str) -> User:
        return cast(User, getattr(self, role))

    def person(self, name: str) -> Student:
        return cast(Student, getattr(self, name))


@pytest.fixture
def world(session: Session, factory: Factory) -> World:
    dept_a = factory.department(code="DEPA", name="Department A")
    dept_b = factory.department(code="DEPB", name="Department B")
    head_a = factory.teacher(dept_a)
    dept_a.head_id = head_a.id
    teacher_a = factory.teacher(dept_a)
    teacher_b = factory.teacher(dept_b)
    a1 = factory.course(dept_a, teacher=teacher_a, code="A1")
    a2 = factory.course(dept_a, teacher=head_a, code="A2")
    b1 = factory.course(dept_b, teacher=teacher_b, code="B1")

    def student(dept: Department, first: str, last: str, number: str, **kw: object) -> Student:
        return factory.student(
            dept,
            first_name=first,
            last_name=last,
            student_no=number,
            email=f"{first.lower()}@uni.edu",
            **kw,
        )

    alice = student(dept_a, "Alice", "Anders", "A001", year=1, phone="555-0101")
    adam = student(dept_a, "Adam", "Archer", "A002", year=2, status=StudentStatus.SUSPENDED)
    bella = student(dept_b, "Bella", "Brown", "B001", year=3)
    bruno = student(dept_b, "Bruno", "Burke", "B002", year=4, status=StudentStatus.GRADUATED)
    for s, course, semester, grade in [
        (alice, a1, "2026-Fall", None),
        (bella, a1, "2026-Fall", None),
        (bruno, a2, "2026-Spring", Grade.B_PLUS),
        (bruno, b1, "2026-Spring", Grade.A),
    ]:
        session.add(
            Enrollment(student_id=s.id, course_id=course.id, semester=semester, grade=grade)
        )

    world = World(
        dept_a=dept_a,
        dept_b=dept_b,
        alice=alice,
        adam=adam,
        bella=bella,
        bruno=bruno,
        admin=factory.user(UserRole.ADMIN),
        hod=factory.user(UserRole.HOD, teacher=head_a),
        teacher=factory.user(UserRole.TEACHER, teacher=teacher_a),
        student=factory.user(UserRole.STUDENT, student=alice),
    )
    session.commit()
    return world


def new_student(department_id: int, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "student_no": "N001",
        "first_name": "Nina",
        "last_name": "New",
        "email": "nina@uni.edu",
        "department_id": department_id,
        "year": 1,
    }
    return payload | overrides


def patch(
    client: TestClient, user: User, student: Student, payload: Mapping[str, object]
) -> httpx.Response:
    response: httpx.Response = client.patch(
        f"{URL}/{student.id}", json=dict(payload), headers=auth_headers(user)
    )
    return response


def first_names(response: httpx.Response) -> list[str]:
    return [s["first_name"] for s in response.json()["items"]]


# ===================================================================== list scoping


@pytest.mark.parametrize(
    ("role", "visible"),
    [
        ("admin", ["Alice", "Adam", "Bella", "Bruno"]),
        ("hod", ["Alice", "Adam", "Bruno"]),  # own dept + own course A2
        ("teacher", ["Alice", "Bella"]),  # enrolled in A1
    ],
)
def test_list_is_scoped_by_role(
    client: TestClient, world: World, role: str, visible: list[str]
) -> None:
    response = client.get(URL, headers=auth_headers(world.user(role)))

    assert response.status_code == 200
    assert first_names(response) == visible  # ordered by last name
    assert response.json()["total"] == len(visible)


def test_students_cannot_list_students(client: TestClient, world: World) -> None:
    response = client.get(URL, headers=auth_headers(world.student))

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_list_requires_authentication(client: TestClient, world: World) -> None:
    assert client.get(URL).status_code == 401


def test_teacher_without_courses_sees_no_students(
    client: TestClient, factory: Factory, world: World
) -> None:
    idle = factory.user(UserRole.TEACHER, teacher=factory.teacher(world.dept_a))

    body = client.get(URL, headers=auth_headers(idle)).json()

    assert body == {"items": [], "total": 0}


def test_hod_with_a_stale_role_sees_only_students_in_own_courses(
    client: TestClient, session: Session, factory: Factory, world: World
) -> None:
    world.dept_a.head_id = factory.teacher(world.dept_a).id  # HA is no longer head
    session.commit()

    assert first_names(client.get(URL, headers=auth_headers(world.hod))) == ["Bruno"]


def test_filters_cannot_widen_the_scope(client: TestClient, world: World) -> None:
    params = {"department_id": world.dept_b.id}
    response = client.get(URL, params=params, headers=auth_headers(world.teacher))

    assert first_names(response) == ["Bella"]  # B students, but only those in A1


# ===================================================================== search, filters, pagination


@pytest.mark.parametrize(
    ("search", "visible"),
    [
        ("alice", ["Alice"]),  # first name
        ("ARCHER", ["Adam"]),  # last name, any case
        ("bella brown", ["Bella"]),  # full name
        ("bruno@uni", ["Bruno"]),  # email
        ("b00", ["Bella", "Bruno"]),  # student number
        ("nobody", []),
    ],
)
def test_search_by_name_email_or_student_number(
    client: TestClient, world: World, search: str, visible: list[str]
) -> None:
    response = client.get(URL, params={"search": search}, headers=auth_headers(world.admin))
    assert first_names(response) == visible


@pytest.mark.parametrize(
    ("params", "visible"),
    [
        ({"department_id": "DEPT_A"}, ["Alice", "Adam"]),
        ({"year": 3}, ["Bella"]),
        ({"status": "graduated"}, ["Bruno"]),
        ({"status": "active", "department_id": "DEPT_B"}, ["Bella"]),
    ],
)
def test_filters_by_department_year_and_status(
    client: TestClient, world: World, params: dict[str, object], visible: list[str]
) -> None:
    ids = {"DEPT_A": world.dept_a.id, "DEPT_B": world.dept_b.id}
    resolved = {k: ids.get(str(v), v) for k, v in params.items()}

    response = client.get(URL, params=resolved, headers=auth_headers(world.admin))

    assert first_names(response) == visible


def test_pagination(client: TestClient, world: World) -> None:
    response = client.get(URL, params={"skip": 1, "limit": 2}, headers=auth_headers(world.admin))

    assert first_names(response) == ["Adam", "Bella"]
    assert response.json()["total"] == 4


@pytest.mark.parametrize(
    "params", [{"year": 0}, {"year": 7}, {"status": "expelled"}, {"limit": 101}]
)
def test_invalid_filters_are_rejected(
    client: TestClient, world: World, params: dict[str, object]
) -> None:
    assert client.get(URL, params=params, headers=auth_headers(world.admin)).status_code == 422


# ===================================================================== detail scoping


@pytest.mark.parametrize(
    ("role", "allowed", "denied"),
    [
        ("admin", ["alice", "adam", "bella", "bruno"], []),
        ("hod", ["alice", "adam", "bruno"], ["bella"]),
        ("teacher", ["alice", "bella"], ["adam", "bruno"]),
        ("student", ["alice"], ["adam", "bella", "bruno"]),
    ],
)
def test_detail_is_scoped_by_role(
    client: TestClient, world: World, role: str, allowed: list[str], denied: list[str]
) -> None:
    for name in allowed:
        response = client.get(
            f"{URL}/{world.person(name).id}", headers=auth_headers(world.user(role))
        )
        assert response.status_code == 200, f"{role} should read {name}"
    for name in denied:
        response = client.get(
            f"{URL}/{world.person(name).id}", headers=auth_headers(world.user(role))
        )
        assert response.status_code == 403, f"{role} should not read {name}"
        assert response.json() == {"detail": "You can't view this student"}


def test_a_student_cannot_read_another_student(client: TestClient, world: World) -> None:
    response = client.get(f"{URL}/{world.bella.id}", headers=auth_headers(world.student))
    assert response.status_code == 403


def test_a_teacher_cannot_read_students_outside_their_courses(
    client: TestClient, world: World
) -> None:
    response = client.get(f"{URL}/{world.adam.id}", headers=auth_headers(world.teacher))
    assert response.status_code == 403


def test_detail_includes_enrollments_with_courses_and_account(
    client: TestClient, world: World
) -> None:
    body = client.get(f"{URL}/{world.bruno.id}", headers=auth_headers(world.admin)).json()

    assert [(e["course"]["code"], e["semester"], e["grade"]) for e in body["enrollments"]] == [
        ("A2", "2026-Spring", "B+"),
        ("B1", "2026-Spring", "A"),
    ]
    assert body["user_id"] is None
    assert body["status"] == "graduated"


def test_student_reads_own_detail(client: TestClient, world: World) -> None:
    body = client.get(f"{URL}/{world.alice.id}", headers=auth_headers(world.student)).json()

    assert body["student_no"] == "A001"
    assert [e["course"]["code"] for e in body["enrollments"]] == ["A1"]
    assert body["user_id"] == world.student.id


def test_detail_of_a_missing_student_is_404(client: TestClient, world: World) -> None:
    response = client.get(f"{URL}/999999", headers=auth_headers(world.student))

    assert response.status_code == 404
    assert response.json() == {"detail": "Student not found"}


# ===================================================================== create (FR-4.1–4.3)


def test_admin_creates_a_student_with_every_field(client: TestClient, world: World) -> None:
    payload = new_student(
        world.dept_b.id,
        student_no=" n001 ",
        email="Nina@UNI.edu",
        phone="555-0199",
        date_of_birth="2005-04-12",
        year=2,
        status="withdrawn",
        enrollment_date="2024-09-01",
    )
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 201
    body = response.json()
    assert (body["student_no"], body["email"]) == ("N001", "nina@uni.edu")
    assert (body["year"], body["status"], body["department_id"]) == (
        2,
        "withdrawn",
        world.dept_b.id,
    )
    assert (body["date_of_birth"], body["enrollment_date"]) == ("2005-04-12", "2024-09-01")


def test_create_defaults_to_active_and_enrolled_today(client: TestClient, world: World) -> None:
    body = client.post(
        URL, json=new_student(world.dept_a.id), headers=auth_headers(world.admin)
    ).json()

    assert body["status"] == "active"
    assert body["enrollment_date"] == date.today().isoformat()


def test_create_with_an_account_creates_a_student_login(
    client: TestClient, session: Session, world: World
) -> None:
    payload = new_student(
        world.dept_a.id, create_account={"username": "nina", "temp_password": "temporary-1"}
    )
    response = client.post(URL, json=payload, headers=auth_headers(world.admin))

    assert response.status_code == 201
    account = session.scalars(select(User).where(User.username == "nina")).one()
    assert (account.role, account.student_id) == (UserRole.STUDENT, response.json()["id"])
    login = client.post("/api/v1/auth/login", data={"username": "nina", "password": "temporary-1"})
    assert login.status_code == 200


def test_hod_creates_a_student_in_their_department(client: TestClient, world: World) -> None:
    payload = new_student(
        world.dept_a.id, create_account={"username": "nina", "temp_password": "temporary-1"}
    )
    assert client.post(URL, json=payload, headers=auth_headers(world.hod)).status_code == 201


def test_hod_cannot_create_a_student_in_another_department(
    client: TestClient, world: World
) -> None:
    response = client.post(URL, json=new_student(world.dept_b.id), headers=auth_headers(world.hod))

    assert response.status_code == 403
    assert response.json() == {"detail": "You can only add students to the department you head"}


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_create(client: TestClient, world: World, role: str) -> None:
    response = client.post(
        URL, json=new_student(world.dept_a.id), headers=auth_headers(world.user(role))
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"student_no": "a001"}, "Student number 'A001' already exists"),
        ({"email": "ALICE@uni.edu"}, "email 'alice@uni.edu' already exists"),
        (
            {"create_account": {"username": "STUDENT-TAKEN", "temp_password": "temporary-1"}},
            "already taken",
        ),
    ],
)
def test_duplicates_are_conflicts_and_create_nothing(
    client: TestClient,
    session: Session,
    world: World,
    overrides: dict[str, object],
    message: str,
) -> None:
    if "create_account" in overrides:
        world.student.username = "student-taken"
        session.commit()
    before = session.scalar(select(func.count()).select_from(Student))

    response = client.post(
        URL, json=new_student(world.dept_a.id, **overrides), headers=auth_headers(world.admin)
    )

    assert response.status_code == 409
    assert message in response.json()["detail"]
    assert session.scalar(select(func.count()).select_from(Student)) == before


def test_create_in_a_missing_department_is_rejected(client: TestClient, world: World) -> None:
    response = client.post(URL, json=new_student(999_999), headers=auth_headers(world.admin))

    assert response.status_code == 422
    assert response.json() == {"detail": "Department 999999 does not exist"}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"student_no": ""}, "student_no"),
        ({"student_no": "S" * 21}, "student_no"),
        ({"student_no": "S 01"}, "student_no"),
        ({"first_name": ""}, "first_name"),
        ({"email": "nina.uni.edu"}, "email"),
        ({"phone": "ring ring"}, "phone"),
        ({"year": 0}, "year"),
        ({"year": 7}, "year"),
        ({"status": "expelled"}, "status"),
        ({"date_of_birth": (date.today() + timedelta(days=1)).isoformat()}, "date_of_birth"),
        ({"enrollment_date": "2026-13-01"}, "enrollment_date"),
        ({"create_account": {"username": "n", "temp_password": "temporary-1"}}, "username"),
        ({"gpa": 4.0}, "gpa"),
    ],
)
def test_create_validates_fields(
    client: TestClient, world: World, overrides: dict[str, object], field: str
) -> None:
    response = client.post(
        URL, json=new_student(world.dept_a.id, **overrides), headers=auth_headers(world.admin)
    )

    assert response.status_code == 422
    assert field in {str(error["loc"][-1]) for error in response.json()["detail"]}


@pytest.mark.parametrize(
    "missing", ["student_no", "first_name", "last_name", "email", "department_id", "year"]
)
def test_create_requires_fields(client: TestClient, world: World, missing: str) -> None:
    payload = new_student(world.dept_a.id)
    del payload[missing]
    assert client.post(URL, json=payload, headers=auth_headers(world.admin)).status_code == 422


# ===================================================================== update


def test_admin_updates_any_field_including_department(client: TestClient, world: World) -> None:
    payload = {
        "year": 3,
        "status": "active",
        "department_id": world.dept_b.id,
        "student_no": "B009",
    }
    response = patch(client, world.admin, world.adam, payload)

    assert response.status_code == 200
    assert {k: response.json()[k] for k in payload} == payload


def test_hod_updates_a_student_of_their_department(client: TestClient, world: World) -> None:
    response = patch(client, world.hod, world.adam, {"status": "active", "year": 3})

    assert response.status_code == 200
    assert (response.json()["status"], response.json()["year"]) == ("active", 3)


def test_hod_cannot_move_a_student_out(client: TestClient, world: World) -> None:
    response = patch(client, world.hod, world.adam, {"department_id": world.dept_b.id})

    assert response.status_code == 403
    assert "can't move students" in response.json()["detail"]


def test_hod_cannot_edit_another_departments_student_even_in_own_course(
    client: TestClient, world: World
) -> None:
    """Teaching Bruno lets the HOD read his record, not edit it."""
    response = patch(client, world.hod, world.bruno, {"year": 4})

    assert response.status_code == 403
    assert response.json() == {"detail": "You can't edit this student"}


def test_teachers_cannot_edit_students(client: TestClient, world: World) -> None:
    response = patch(client, world.teacher, world.alice, {"phone": "555"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Not enough permissions"}


def test_student_updates_own_phone_and_email(client: TestClient, world: World) -> None:
    response = patch(
        client, world.student, world.alice, {"phone": "555-0202", "email": "Alice.A@uni.edu"}
    )

    assert response.status_code == 200
    assert (response.json()["phone"], response.json()["email"]) == ("555-0202", "alice.a@uni.edu")


@pytest.mark.parametrize(
    "payload",
    [
        {"year": 2},
        {"status": "graduated"},
        {"student_no": "A999"},
        {"phone": "555-1234", "last_name": "X"},
    ],
)
def test_student_cannot_change_other_fields(
    client: TestClient, world: World, payload: dict[str, object]
) -> None:
    response = patch(client, world.student, world.alice, payload)

    assert response.status_code == 403
    assert response.json()["detail"].startswith("You can only change your own phone and email")


def test_student_cannot_edit_another_student(client: TestClient, world: World) -> None:
    assert patch(client, world.student, world.adam, {"phone": "555"}).status_code == 403


def test_refused_update_changes_nothing(client: TestClient, session: Session, world: World) -> None:
    patch(client, world.student, world.alice, {"phone": "555-9999", "year": 6})

    session.refresh(world.alice)
    assert (world.alice.phone, world.alice.year) == ("555-0101", 1)


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        ({"email": "adam@UNI.edu"}, 409),
        ({"student_no": "b001"}, 409),
        ({"email": "alice@uni.edu"}, 200),  # own email: not a conflict
        ({"year": None}, 422),
        ({"department_id": 999_999}, 422),
    ],
)
def test_update_rules(
    client: TestClient, world: World, payload: dict[str, object], status_code: int
) -> None:
    assert patch(client, world.admin, world.alice, payload).status_code == status_code


def test_update_of_a_missing_student_is_404(client: TestClient, world: World) -> None:
    response = client.patch(f"{URL}/999999", json={"year": 2}, headers=auth_headers(world.admin))
    assert response.status_code == 404


# ===================================================================== delete (FR-4.4)


def enrollments_of(session: Session, student: Student) -> int:
    query = select(func.count()).select_from(Enrollment).where(Enrollment.student_id == student.id)
    return session.scalar(query) or 0


def test_admin_deletes_a_student_and_their_enrollments(
    client: TestClient, session: Session, world: World
) -> None:
    bruno_id = world.bruno.id
    assert enrollments_of(session, world.bruno) == 2

    response = client.delete(f"{URL}/{bruno_id}", headers=auth_headers(world.admin))

    assert response.status_code == 204
    remaining = (
        select(func.count()).select_from(Enrollment).where(Enrollment.student_id == bruno_id)
    )
    assert session.scalar(remaining) == 0
    assert client.get(f"{URL}/{bruno_id}", headers=auth_headers(world.admin)).status_code == 404


def test_hod_deletes_a_student_of_their_department(client: TestClient, world: World) -> None:
    assert (
        client.delete(f"{URL}/{world.adam.id}", headers=auth_headers(world.hod)).status_code == 204
    )


def test_hod_cannot_delete_another_departments_student(client: TestClient, world: World) -> None:
    response = client.delete(f"{URL}/{world.bruno.id}", headers=auth_headers(world.hod))

    assert response.status_code == 403
    assert "department you head" in response.json()["detail"]


def test_student_with_a_login_account_cannot_be_deleted(
    client: TestClient, session: Session, world: World
) -> None:
    response = client.delete(f"{URL}/{world.alice.id}", headers=auth_headers(world.admin))

    assert response.status_code == 409
    assert "have a login account" in response.json()["detail"]
    assert enrollments_of(session, world.alice) == 1  # nothing was deleted


@pytest.mark.parametrize("role", ["teacher", "student"])
def test_teachers_and_students_cannot_delete(client: TestClient, world: World, role: str) -> None:
    response = client.delete(f"{URL}/{world.adam.id}", headers=auth_headers(world.user(role)))
    assert response.status_code == 403


def test_delete_of_a_missing_student_is_404(client: TestClient, world: World) -> None:
    assert client.delete(f"{URL}/999999", headers=auth_headers(world.admin)).status_code == 404
