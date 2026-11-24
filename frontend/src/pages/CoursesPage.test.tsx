import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { createCourse, listCourses } from '../api/courses';
import { listDepartments } from '../api/departments';
import { listTeachers, type TeacherFilters } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import { apiError, cs101Detail, csDepartment, kayDetail, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type {
  CourseOut,
  CurrentUserOut,
  DepartmentOut,
  TeacherPublicOut,
  UserRole,
} from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/courses');
vi.mock('../api/departments');
vi.mock('../api/teachers');

const math: DepartmentOut = { ...csDepartment, id: 4, code: 'MATH', name: 'Mathematics' };
const teacher = (
  id: number,
  first: string,
  last: string,
  department_id: number,
): TeacherPublicOut => ({
  id,
  first_name: first,
  last_name: last,
  title: 'lecturer',
  email: `${first.toLowerCase()}@uni.example`,
  department_id,
});
const kay = teacher(2, 'Alan', 'Kay', 3);
const hopper = teacher(5, 'Grace', 'Hopper', 3);
const noether = teacher(9, 'Emmy', 'Noether', 4);
const courses: CourseOut[] = [
  cs101Detail,
  {
    ...cs101Detail,
    id: 21,
    code: 'MATH201',
    title: 'Linear Algebra',
    department_id: 4,
    teacher_id: null,
    credits: 3,
    capacity: 30,
  },
];
const hodOfCs: CurrentUserOut = { ...meFor('hod'), teacher: { ...kayDetail, department_id: 3 } };

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment, math], total: 2 });
  vi.mocked(listCourses).mockResolvedValue({ items: courses, total: 2 });
  vi.mocked(listTeachers).mockImplementation((params: TeacherFilters = {}) => {
    const all = [kay, hopper, noether];
    const items = params.department_id
      ? all.filter((t) => t.department_id === params.department_id)
      : all;
    return Promise.resolve({ items, total: items.length });
  });
});
afterEach(() => {
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}
const as = (role: UserRole) => {
  logIn(meFor(role));
};
const optionsOf = (select: HTMLElement) =>
  within(select)
    .getAllByRole('option')
    .map((o) => o.textContent);

describe('CoursesPage list', () => {
  it('lists courses with department, teacher, credits and capacity', async () => {
    as('student');
    renderApp('/courses');

    const table = await screen.findByRole('table', { name: 'Courses' });
    expect(within(table).getByRole('link', { name: 'CS101' })).toHaveAttribute(
      'href',
      '/courses/11',
    );
    await waitFor(() => {
      expect(within(table).getByRole('cell', { name: 'Alan Kay' })).toBeInTheDocument();
    });
    const algebra = within(table)
      .getByRole('cell', { name: 'Linear Algebra' })
      .closest('tr') as HTMLElement;
    expect(
      within(algebra)
        .getAllByRole('cell')
        .map((c) => c.textContent),
    ).toEqual(['MATH201', 'Linear Algebra', 'MATH', 'Unassigned', '3', '30']);
  });

  it('filters by department and teacher; the teacher filter follows the department', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/courses');
    await screen.findByRole('table', { name: 'Courses' });
    await waitFor(() => {
      expect(optionsOf(screen.getByLabelText('Teacher'))).toEqual([
        'All teachers',
        'Alan Kay',
        'Grace Hopper',
        'Emmy Noether',
      ]);
    });

    await user.selectOptions(screen.getByLabelText('Department'), 'CS — Computer Science');
    await waitFor(() => {
      expect(optionsOf(screen.getByLabelText('Teacher'))).toEqual([
        'All teachers',
        'Alan Kay',
        'Grace Hopper',
      ]);
    });
    await user.selectOptions(screen.getByLabelText('Teacher'), 'Grace Hopper');

    await waitFor(() => {
      expect(listCourses).toHaveBeenLastCalledWith({
        search: undefined,
        department_id: 3,
        teacher_id: 5,
        skip: 0,
        limit: 20,
      });
    });
  });

  it('changing the department filter clears a teacher from another department', async () => {
    as('admin');
    const user = userEvent.setup();
    renderApp('/courses');
    await screen.findByRole('table', { name: 'Courses' });
    await waitFor(() => {
      expect(optionsOf(screen.getByLabelText('Teacher'))).toContain('Emmy Noether');
    });
    await user.selectOptions(screen.getByLabelText('Teacher'), 'Emmy Noether');

    await user.selectOptions(screen.getByLabelText('Department'), 'CS — Computer Science');

    expect(screen.getByLabelText('Teacher')).toHaveValue('');
  });

  it('searches by code or title', async () => {
    as('student');
    const user = userEvent.setup();
    renderApp('/courses');
    await screen.findByRole('table', { name: 'Courses' });

    await user.type(screen.getByLabelText('Search courses'), 'algebra');

    await waitFor(() => {
      expect(listCourses).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: 'algebra', skip: 0 }),
      );
    });
  });

  it.each([
    ['admin', true],
    ['hod', true],
    ['teacher', false],
    ['student', false],
  ] as const)('"New course" for %s: %s', async (role, shown) => {
    as(role);
    renderApp('/courses');
    await screen.findByRole('table', { name: 'Courses' });
    expect(screen.queryByRole('button', { name: 'New course' }) !== null).toBe(shown);
  });
});

describe('Course form (create)', () => {
  async function open(me: CurrentUserOut) {
    logIn(me);
    const user = userEvent.setup();
    renderApp('/courses');
    await user.click(await screen.findByRole('button', { name: 'New course' }));
    return { user, dialog: screen.getByRole('dialog', { name: 'New course' }) };
  }

  it('the teacher list only shows teachers of the chosen department (BR-2)', async () => {
    const { user, dialog } = await open(meFor('admin'));
    expect(optionsOf(within(dialog).getByLabelText('Teacher'))).toEqual(['No teacher yet']);

    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');
    await waitFor(() => {
      expect(optionsOf(within(dialog).getByLabelText('Teacher'))).toEqual([
        'No teacher yet',
        'Alan Kay',
        'Grace Hopper',
      ]);
    });
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'MATH — Mathematics');
    await waitFor(() => {
      expect(optionsOf(within(dialog).getByLabelText('Teacher'))).toEqual([
        'No teacher yet',
        'Emmy Noether',
      ]);
    });
  });

  it('changing the department resets the teacher choice', async () => {
    const { user, dialog } = await open(meFor('admin'));
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');
    await waitFor(() => {
      expect(optionsOf(within(dialog).getByLabelText('Teacher'))).toContain('Grace Hopper');
    });
    await user.selectOptions(within(dialog).getByLabelText('Teacher'), 'Grace Hopper');
    expect(within(dialog).getByLabelText('Teacher')).toHaveValue('5');

    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'MATH — Mathematics');

    expect(within(dialog).getByLabelText('Teacher')).toHaveValue('');
    // What matters is what gets saved: no teacher from the old department (BR-2).
    vi.mocked(createCourse).mockResolvedValue({ ...cs101Detail, id: 30 });
    await user.type(within(dialog).getByLabelText(/Code/), 'MATH999');
    await user.type(within(dialog).getByLabelText(/Title/), 'Seminar');
    await user.click(within(dialog).getByRole('button', { name: 'Create course' }));
    expect(createCourse).toHaveBeenCalledWith(
      expect.objectContaining({ department_id: 4, teacher_id: null }),
    );
  });

  it('creates a course with a teacher from its department', async () => {
    vi.mocked(createCourse).mockResolvedValue({ ...cs101Detail, id: 30 });
    const { user, dialog } = await open(meFor('admin'));
    await user.type(within(dialog).getByLabelText(/Code/), 'cs350');
    await user.type(within(dialog).getByLabelText(/Title/), 'Web Development');
    await user.type(within(dialog).getByLabelText('Description'), 'HTTP and HTML');
    await user.selectOptions(within(dialog).getByLabelText(/Credits/), '4');
    const capacity = within(dialog).getByLabelText(/Capacity/);
    await user.clear(capacity);
    await user.type(capacity, '35');
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');
    await waitFor(() => {
      expect(optionsOf(within(dialog).getByLabelText('Teacher'))).toContain('Alan Kay');
    });
    await user.selectOptions(within(dialog).getByLabelText('Teacher'), 'Alan Kay');

    await user.click(within(dialog).getByRole('button', { name: 'Create course' }));

    expect(createCourse).toHaveBeenCalledWith({
      code: 'cs350',
      title: 'Web Development',
      description: 'HTTP and HTML',
      credits: 4,
      capacity: 35,
      teacher_id: 2,
      department_id: 3,
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Course CS350 created');
  });

  it('defaults to 3 credits, capacity 40 and no teacher', async () => {
    vi.mocked(createCourse).mockResolvedValue({ ...cs101Detail, id: 30 });
    const { user, dialog } = await open(meFor('admin'));
    await user.type(within(dialog).getByLabelText(/Code/), 'CS999');
    await user.type(within(dialog).getByLabelText(/Title/), 'Seminar');
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');

    await user.click(within(dialog).getByRole('button', { name: 'Create course' }));

    expect(createCourse).toHaveBeenCalledWith(
      expect.objectContaining({ credits: 3, capacity: 40, teacher_id: null, description: null }),
    );
  });

  it('a HOD only creates courses in their own department', async () => {
    const { dialog } = await open(hodOfCs);
    await waitFor(() => {
      expect(optionsOf(within(dialog).getByLabelText(/Department/))).toEqual([
        'CS — Computer Science',
      ]);
    });
    await waitFor(() => {
      expect(optionsOf(within(dialog).getByLabelText('Teacher'))).toEqual([
        'No teacher yet',
        'Alan Kay',
        'Grace Hopper',
      ]);
    });
  });

  it('validates before calling the API', async () => {
    const { user, dialog } = await open(meFor('admin'));
    await user.type(within(dialog).getByLabelText(/Code/), 'CS 101');
    const capacity = within(dialog).getByLabelText(/Capacity/);
    await user.clear(capacity);
    await user.type(capacity, '0');

    await user.click(within(dialog).getByRole('button', { name: 'Create course' }));

    for (const message of [
      'Letters, digits and dashes only',
      'Enter a title',
      'Between 1 and 1000',
      'Choose a department',
    ]) {
      expect(await within(dialog).findByText(message)).toBeInTheDocument();
    }
    expect(createCourse).not.toHaveBeenCalled();
  });

  it.each([
    ["A course with code 'CS101' already exists", /Code/],
    [
      "Emmy Noether is not in department CS; a course's teacher must belong to the course's department",
      'Teacher',
    ],
  ])('shows "%s" under its field', async (message, field) => {
    vi.mocked(createCourse).mockRejectedValue(
      apiError(message.includes('code') ? 409 : 422, message),
    );
    const { user, dialog } = await open(meFor('admin'));
    await user.type(within(dialog).getByLabelText(/Code/), 'CS101');
    await user.type(within(dialog).getByLabelText(/Title/), 'Programming');
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'CS — Computer Science');

    await user.click(within(dialog).getByRole('button', { name: 'Create course' }));

    expect(await within(dialog).findByText(message)).toBeInTheDocument();
    expect(within(dialog).getByLabelText(field)).toHaveAttribute('aria-invalid', 'true');
  });
});
