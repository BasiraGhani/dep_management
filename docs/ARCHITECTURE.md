# Architecture — University Department Management System

## 1. Overview

```
┌─────────────────────────┐   HTTPS / JSON + JWT   ┌──────────────────────────┐   SQLAlchemy   ┌──────────────┐
│ Frontend                │ ─────────────────────▶ │ Backend                  │ ─────────────▶ │ Database     │
│ React + TS (Vite)       │ ◀───────────────────── │ FastAPI                  │ ◀───────────── │ SQLite / PG  │
│ :5173                   │                        │ :8000                    │                │              │
└─────────────────────────┘                        └──────────────────────────┘                └──────────────┘
```

Backend layers: **router** (HTTP, parsing, status codes) → **service** (business rules, permissions) → **model** (ORM).

## 2. Data model

All tables have `id` (integer primary key), `created_at` and `updated_at` (UTC timestamps).

### users
| Column | Type | Notes |
|---|---|---|
| username | str(50) | unique, case-insensitive |
| password_hash | str | argon2 |
| role | enum | `admin`, `hod`, `teacher`, `student` |
| is_active | bool | default true |
| teacher_id | FK → teachers.id | nullable, unique |
| student_id | FK → students.id | nullable, unique |

Constraint: `admin` has neither link; `hod` and `teacher` have only `teacher_id`; `student` has only `student_id`. The service layer enforces this.

### departments
| Column | Type | Notes |
|---|---|---|
| code | str(10) | unique, uppercase (e.g. `CS`) |
| name | str(120) | unique |
| description | text | nullable |
| building | str(80) | nullable |
| phone | str(30) | nullable |
| head_id | FK → teachers.id | nullable; must belong to this department (BR-3) |

### teachers
| Column | Type | Notes |
|---|---|---|
| first_name, last_name | str(60) | |
| email | str(120) | unique |
| phone | str(30) | nullable |
| title | enum | `lecturer`, `assistant_professor`, `associate_professor`, `professor` |
| department_id | FK → departments.id | required |
| hire_date | date | nullable |

### students
| Column | Type | Notes |
|---|---|---|
| student_no | str(20) | unique |
| first_name, last_name | str(60) | |
| email | str(120) | unique |
| phone | str(30) | nullable |
| date_of_birth | date | nullable |
| department_id | FK → departments.id | required |
| year | int | 1–6 |
| status | enum | `active`, `graduated`, `suspended`, `withdrawn` |
| enrollment_date | date | |

### courses
| Column | Type | Notes |
|---|---|---|
| code | str(15) | unique, uppercase (e.g. `CS101`) |
| title | str(150) | |
| description | text | nullable |
| credits | int | 1–6 |
| capacity | int | default 40, ≥ 1 |
| department_id | FK → departments.id | required |
| teacher_id | FK → teachers.id | nullable; same department (BR-2) |

### enrollments
| Column | Type | Notes |
|---|---|---|
| student_id | FK → students.id | on delete cascade |
| course_id | FK → courses.id | |
| semester | str(20) | format `YYYY-Spring`, `YYYY-Summer` or `YYYY-Fall` |
| grade | enum | nullable; `A, A-, B+, B, B-, C+, C, C-, D, F` |

Unique: (`student_id`, `course_id`, `semester`).

GPA points: A 4.0, A- 3.7, B+ 3.3, B 3.0, B- 2.7, C+ 2.3, C 2.0, C- 1.7, D 1.0, F 0.0.

### Relationships

```
departments 1───* teachers
departments 1───* students
departments 1───* courses
departments *───1 teachers      (head_id)
teachers    1───* courses       (teacher_id)
students    *───* courses       via enrollments
users       1───1 teachers | students   (optional)
```

## 3. API contract

Base path: `/api/v1`. Every endpoint except `/auth/login` and `/health` requires `Authorization: Bearer <token>`.

List endpoints accept `search`, `skip` and `limit`, plus the filters shown, and return `{ "items": [...], "total": int }`.

| Method | Path | Purpose | Allowed roles |
|---|---|---|---|
| GET | `/health` | Health check | public |
| POST | `/auth/login` | Username/password → `{access_token, token_type}` | public |
| GET | `/auth/me` | Current user + linked record | all |
| POST | `/auth/change-password` | Change own password | all |
| GET | `/users` | List users (`role`, `is_active`) | admin |
| POST | `/users` | Create user | admin |
| PATCH | `/users/{id}` | Activate, deactivate, change role or links | admin |
| POST | `/users/{id}/reset-password` | Set a temporary password | admin |
| GET | `/departments` | List | all |
| POST | `/departments` | Create | admin |
| GET | `/departments/{id}` | Detail + counts | all |
| PATCH | `/departments/{id}` | Update | admin, hod (own) |
| DELETE | `/departments/{id}` | Delete (409 if it has dependents) | admin |
| GET | `/teachers` | List (`department_id`, `title`) | all |
| POST | `/teachers` | Create (+ optional account) | admin, hod (own dept) |
| GET | `/teachers/{id}` | Detail + courses | all |
| PATCH | `/teachers/{id}` | Update | admin, hod (own dept), teacher (self, contact fields) |
| DELETE | `/teachers/{id}` | Delete (409 if it has dependents) | admin |
| GET | `/students` | List (`department_id`, `year`, `status`) | admin, hod (own dept), teacher (own courses) |
| POST | `/students` | Create (+ optional account) | admin, hod (own dept) |
| GET | `/students/{id}` | Detail + enrollments + GPA | admin, hod (own dept), teacher (own courses), student (self) |
| PATCH | `/students/{id}` | Update | admin, hod (own dept), student (self, contact fields) |
| DELETE | `/students/{id}` | Delete (cascades enrollments) | admin, hod (own dept) |
| GET | `/courses` | List (`department_id`, `teacher_id`) | all |
| POST | `/courses` | Create | admin, hod (own dept) |
| GET | `/courses/{id}` | Detail + enrolled students (roster hidden from students) | all |
| PATCH | `/courses/{id}` | Update | admin, hod (own dept), teacher (own, description only) |
| DELETE | `/courses/{id}` | Delete (409 if it has enrollments) | admin, hod (own dept) |
| GET | `/enrollments` | List (`student_id`, `course_id`, `semester`) | scoped by role |
| POST | `/enrollments` | Enroll a student | admin, hod (own dept) |
| DELETE | `/enrollments/{id}` | Unenroll | admin, hod (own dept) |
| PATCH | `/enrollments/{id}/grade` | Set grade | admin, hod (own dept), teacher (own course) |
| PUT | `/courses/{id}/grades` | Bulk set grades `[{enrollment_id, grade}]` | admin, hod (own dept), teacher (own course) |
| GET | `/dashboard` | Role-specific stats | all |
| GET | `/export/{resource}.csv` | CSV export (`students`, `teachers`, `courses`) | admin, hod (own dept) |

Error body: `{ "detail": "message" }`. Validation errors use FastAPI's default 422 format.

## 4. Frontend pages and routes

| Route | Page | Roles |
|---|---|---|
| `/login` | Login | public |
| `/` | Dashboard (role-specific) | all |
| `/departments` · `/departments/:id` | Department list · detail | all |
| `/teachers` · `/teachers/:id` | Teacher list · detail | all |
| `/students` · `/students/:id` | Student list · detail | admin, hod, teacher |
| `/courses` · `/courses/:id` | Course list · detail (roster + grades) | all |
| `/courses/:id/grades` | Bulk grade entry | admin, hod, teacher (own) |
| `/users` | User management | admin |
| `/profile` | My profile + change password | all |
| `*` | 404 | all |

Layout: a sidebar with menu items filtered by role, a top bar with the user's name, role and logout, and the page content area. Create and edit forms open in modal dialogs or on their own pages, whichever is simpler and consistent.

## 5. Folder structure

```
dept-system/
├── CLAUDE.md
├── TASKS.md
├── README.md
├── docs/
├── docker-compose.yml                 (Phase 8)
├── .github/workflows/ci.yml           (Phase 0)
├── backend/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml                 (ruff, mypy, pytest config)
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py                    (app factory, CORS, routers)
│   │   ├── config.py                  (pydantic-settings)
│   │   ├── database.py                (engine, session, Base)
│   │   ├── models/                    (one file per table)
│   │   ├── schemas/                   (one file per resource)
│   │   ├── services/                  (business logic + permissions)
│   │   ├── routers/                   (one file per resource)
│   │   ├── core/
│   │   │   ├── security.py            (hashing, JWT)
│   │   │   ├── deps.py                (get_db, get_current_user, require_roles)
│   │   │   └── permissions.py         (scope helpers)
│   │   └── cli.py                     (seed admin, seed demo data)
│   └── tests/
│       ├── conftest.py                (test DB, client, users per role)
│       └── test_<resource>.py
└── frontend/
    ├── package.json
    ├── .env.example                   (VITE_API_URL)
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx                    (routes)
        ├── api/                       (axios client + one file per resource)
        ├── types/                     (mirrors backend schemas)
        ├── hooks/                     (TanStack Query hooks)
        ├── auth/                      (AuthContext, ProtectedRoute, RoleGate)
        ├── components/                (Layout, DataTable, FormField, ConfirmDialog, Toast…)
        ├── pages/
        └── test/                      (setup + test utils)
```
