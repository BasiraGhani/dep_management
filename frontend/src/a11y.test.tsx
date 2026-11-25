/**
 * Every form control and button on every page (and in every form dialog) has an
 * accessible name, so each one is labelled for screen readers (T7.4).
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from './api/auth';
import { getCourse, listCourses } from './api/courses';
import { getDashboard } from './api/dashboard';
import { getDepartment, listDepartments } from './api/departments';
import { getStudent, listStudents } from './api/students';
import { getTeacher, listTeachers } from './api/teachers';
import { listUsers } from './api/users';
import { clearToken, setToken } from './auth/token';
import {
  amiraDetail,
  cs101Detail,
  csDepartment,
  csDepartmentDetail,
  csTeachers,
  kayDetail,
  meFor,
} from './test/fixtures';
import { renderApp } from './test/render';
import type { UserRole } from './types';

vi.mock('./api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('./api/courses');
vi.mock('./api/dashboard');
vi.mock('./api/departments');
vi.mock('./api/teachers');
vi.mock('./api/students');
vi.mock('./api/users');
vi.mock('./api/enrollments');
vi.mock('./api/export');

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(getTeacher).mockResolvedValue(kayDetail);
  vi.mocked(listStudents).mockResolvedValue({ items: [amiraDetail], total: 1 });
  vi.mocked(getStudent).mockResolvedValue(amiraDetail);
  vi.mocked(listCourses).mockResolvedValue({ items: [cs101Detail], total: 1 });
  vi.mocked(getCourse).mockResolvedValue(cs101Detail);
  vi.mocked(listUsers).mockResolvedValue({
    items: [
      {
        id: 11,
        username: 'alan.kay',
        role: 'teacher',
        is_active: true,
        teacher_id: 2,
        student_id: null,
        linked_name: 'Alan Kay',
        created_at: '2026-09-01T10:00:00Z',
        updated_at: '2026-09-01T10:00:00Z',
      },
    ],
    total: 1,
  });
  vi.mocked(getDashboard).mockResolvedValue({
    role: 'admin',
    totals: { departments: 1, teachers: 2, students: 1, courses: 1 },
    students_per_department: [
      { department_id: 3, code: 'CS', name: 'Computer Science', students: 1 },
    ],
    recent_enrollments: [],
  });
});
afterEach(() => {
  vi.clearAllMocks();
});

/** The controls that have no accessible name, described so a failure says which. */
function unlabelled(root: HTMLElement): string[] {
  const controls = root.querySelectorAll<HTMLElement>(
    'input:not([type=hidden]), select, textarea, button, a[href]',
  );
  return Array.from(controls)
    .filter((el) => {
      try {
        expect(el).toHaveAccessibleName();
        return false;
      } catch {
        return true;
      }
    })
    .map((el) => el.outerHTML.slice(0, 120));
}

async function open(path: string, role: UserRole, ready: string) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(meFor(role));
  const user = userEvent.setup();
  renderApp(path);
  await screen.findByRole('heading', { level: 1, name: ready });
  await waitFor(() => {
    expect(screen.queryByText(/^Loading/)).not.toBeInTheDocument();
  });
  return user;
}

const PAGES: [path: string, role: UserRole, heading: string][] = [
  ['/', 'admin', 'Welcome, demo.admin'],
  ['/departments', 'admin', 'Departments'],
  ['/departments/3', 'admin', 'Computer Science (CS)'],
  ['/teachers', 'admin', 'Teachers'],
  ['/teachers/2', 'admin', 'Alan Kay'],
  ['/students', 'admin', 'Students'],
  ['/students/1', 'admin', 'Amira Costa'],
  ['/courses', 'admin', 'Courses'],
  ['/courses/11', 'admin', 'CS101 Programming'],
  ['/courses/11/grades', 'admin', 'Grades: CS101 Programming'],
  ['/users', 'admin', 'User management'],
  ['/profile', 'teacher', 'My profile'],
  ['/profile', 'student', 'My profile'],
];

describe('every control on every page has a name', () => {
  it.each(PAGES)('%s as %s', async (path, role, heading) => {
    await open(path, role, heading);
    expect(unlabelled(document.body)).toEqual([]);
  });
});

const FORMS: [path: string, role: UserRole, heading: string, button: string, prepare?: string][] = [
  ['/departments', 'admin', 'Departments', 'New department'],
  ['/teachers', 'admin', 'Teachers', 'New teacher', 'account'],
  ['/students', 'admin', 'Students', 'New student', 'account'],
  ['/courses', 'admin', 'Courses', 'New course'],
  ['/departments/3', 'admin', 'Computer Science (CS)', 'Edit'],
  ['/teachers/2', 'admin', 'Alan Kay', 'Edit'],
  ['/students/1', 'admin', 'Amira Costa', 'Edit'],
  ['/courses/11', 'admin', 'CS101 Programming', 'Edit'],
  ['/users', 'admin', 'User management', 'New account', 'student'],
  ['/users', 'admin', 'User management', 'Edit alan.kay'],
  ['/profile', 'teacher', 'My profile', 'Edit my contact details'],
  ['/profile', 'student', 'My profile', 'Edit my contact details'],
];

describe('every control in every form dialog has a name', () => {
  it.each(FORMS)('%s as %s: %s', async (path, role, heading, button, prepare) => {
    const user = await open(path, role, heading);
    await user.click(screen.getByRole('button', { name: button }));
    const dialog = screen.getByRole('dialog');
    if (prepare === 'account') {
      await user.click(within(dialog).getByRole('checkbox', { name: /Create a login account/ }));
    }
    if (prepare === 'student') {
      await user.selectOptions(within(dialog).getByLabelText(/^Role/), 'Student');
    }
    expect(unlabelled(dialog)).toEqual([]);
  });
});
