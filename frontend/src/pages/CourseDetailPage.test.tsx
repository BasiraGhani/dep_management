import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { deleteCourse, getCourse, listCourses, updateCourse } from '../api/courses';
import { getDepartment, listDepartments } from '../api/departments';
import { listStudents } from '../api/students';
import { listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import {
  apiError,
  cs101Detail,
  csDepartment,
  csDepartmentDetail,
  csTeachers,
  kayDetail,
  meFor,
} from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CurrentUserOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/courses');
vi.mock('../api/departments');
vi.mock('../api/teachers');
vi.mock('../api/students');
vi.mock('../api/enrollments');

const hodOf = (departmentId: number): CurrentUserOut => ({
  ...meFor('hod'),
  teacher_id: 50,
  teacher: { ...kayDetail, id: 50, department_id: departmentId },
});
/** meFor('teacher') is teacher 2 = Alan Kay, who teaches CS101. */
const kayHimself = meFor('teacher');
const otherTeacher: CurrentUserOut = { ...meFor('teacher'), teacher_id: 77 };

beforeEach(() => {
  clearToken();
  vi.mocked(getCourse).mockResolvedValue(cs101Detail);
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(listCourses).mockResolvedValue({ items: [], total: 0 });
  vi.mocked(listStudents).mockResolvedValue({ items: [], total: 0 });
});
afterEach(() => {
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}

describe('CourseDetailPage', () => {
  it('shows the course, its teacher and the roster with grades (FR-5.4)', async () => {
    logIn(kayHimself);
    renderApp('/courses/11');

    expect(await screen.findByRole('heading', { name: 'CS101 Programming' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Alan Kay, Associate Professor' })).toHaveAttribute(
      'href',
      '/teachers/2',
    );
    expect(screen.getByText('Variables, loops and functions.')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Computer Science' })).toBeInTheDocument();
    const roster = screen.getByRole('table', { name: 'Enrolled students and grades' });
    expect(
      within(roster)
        .getAllByRole('row')
        .slice(1)
        .map((r) =>
          within(r)
            .getAllByRole('cell')
            .map((c) => c.textContent),
        ),
    ).toEqual([
      ['Amira Costa', 'CS2026001', '2026-Spring', 'A'],
      ['Bo Diallo', 'CS2026007', '2026-Fall', 'Not graded'],
    ]);
    expect(screen.getByRole('heading', { name: 'Enrolled students (2)' })).toBeInTheDocument();
  });

  it('hides the roster from students', async () => {
    logIn(meFor('student'));
    vi.mocked(getCourse).mockResolvedValue({ ...cs101Detail, roster: null });
    renderApp('/courses/11');

    expect(await screen.findByRole('heading', { name: 'CS101 Programming' })).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    expect(screen.queryByText(/Enrolled students/)).not.toBeInTheDocument();
    expect(screen.queryByText('Bo Diallo')).not.toBeInTheDocument(); // a roster name
  });

  it('tells other staff who can see the class list', async () => {
    logIn(otherTeacher);
    vi.mocked(getCourse).mockResolvedValue({ ...cs101Detail, roster: null });
    renderApp('/courses/11');

    expect(
      await screen.findByText(/class list is visible to the course's teacher/),
    ).toBeInTheDocument();
  });

  it('shows an empty roster and an unassigned course', async () => {
    logIn(meFor('admin'));
    vi.mocked(getCourse).mockResolvedValue({
      ...cs101Detail,
      roster: [],
      teacher: null,
      teacher_id: null,
      description: null,
    });
    renderApp('/courses/11');

    expect(await screen.findByText('No students enrolled yet.')).toBeInTheDocument();
    expect(screen.getByText('No teacher assigned')).toBeInTheDocument();
    expect(screen.getByText('No description.')).toBeInTheDocument();
  });

  it.each([
    ['admin', meFor('admin'), 'Edit', true],
    ['HOD of the department', hodOf(3), 'Edit', true],
    ['HOD of another department', hodOf(4), null, false],
    ["the course's teacher", kayHimself, 'Edit description', false],
    ['another teacher', otherTeacher, null, false],
    ['student', meFor('student'), null, false],
  ] as const)('%s: edit=%s delete=%s', async (_who, me, editLabel, canDelete) => {
    logIn(me);
    renderApp('/courses/11');
    await screen.findByRole('heading', { name: 'CS101 Programming' });

    expect(screen.queryAllByRole('button', { name: /^Edit/ }).map((b) => b.textContent)).toEqual(
      editLabel ? [editLabel] : [],
    );
    expect(screen.queryByRole('button', { name: 'Delete' }) !== null).toBe(canDelete);
  });
});

describe('Course form (edit)', () => {
  it("the course's teacher edits the description only", async () => {
    logIn(kayHimself);
    vi.mocked(updateCourse).mockResolvedValue(cs101Detail);
    const user = userEvent.setup();
    renderApp('/courses/11');

    await user.click(await screen.findByRole('button', { name: 'Edit description' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit CS101' });
    for (const hidden of [/Code/, /Title/, /Credits/, /Capacity/, /Department/, 'Teacher']) {
      expect(within(dialog).queryByLabelText(hidden)).not.toBeInTheDocument();
    }
    const description = within(dialog).getByLabelText('Description');
    await user.clear(description);
    await user.type(description, 'Now with recursion.');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateCourse).toHaveBeenCalledWith(11, { description: 'Now with recursion.' });
  });

  it("a HOD edits their department's course and can reassign its teacher, but not move it", async () => {
    logIn(hodOf(3));
    vi.mocked(updateCourse).mockResolvedValue(cs101Detail);
    const user = userEvent.setup();
    renderApp('/courses/11');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit CS101' });
    expect(within(dialog).getByLabelText('Teacher')).toHaveValue('2'); // current teacher preselected
    await screen.findAllByRole('option', { name: 'Grace Hopper' });
    await user.selectOptions(within(dialog).getByLabelText('Teacher'), 'Grace Hopper');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    const body = vi.mocked(updateCourse).mock.calls[0]?.[1];
    expect(body).toMatchObject({ teacher_id: 5, code: 'CS101' });
    expect(body).not.toHaveProperty('department_id');
  });
});

describe('Course delete', () => {
  it("shows the server's 409 when the course has enrollments", async () => {
    logIn(meFor('admin'));
    const message = "Course CS101 can't be deleted while it has 2 enrollments. Remove them first.";
    vi.mocked(deleteCourse).mockRejectedValue(apiError(409, message));
    const user = userEvent.setup();
    renderApp('/courses/11');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(
      within(screen.getByRole('dialog', { name: 'Delete CS101?' })).getByRole('button', {
        name: 'Delete',
      }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByRole('heading', { name: 'CS101 Programming' })).toBeInTheDocument();
  });

  it('deletes after confirmation and returns to the list', async () => {
    logIn(hodOf(3));
    vi.mocked(deleteCourse).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderApp('/courses/11');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('table', { name: 'Courses' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Course CS101 deleted');
  });
});
