import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { getDepartment, listDepartments } from '../api/departments';
import { deleteTeacher, getTeacher, listTeachers, updateTeacher } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import { apiError, csDepartment, csDepartmentDetail, kayDetail, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CurrentUserOut, DepartmentOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/teachers');

const math: DepartmentOut = { ...csDepartment, id: 4, code: 'MATH', name: 'Mathematics' };
const hodOf = (departmentId: number): CurrentUserOut => ({
  ...meFor('hod'),
  teacher_id: 50,
  teacher: { ...kayDetail, id: 50, department_id: departmentId },
});
/** meFor('teacher') is teacher 2 = Alan Kay, the teacher on this page. */
const kayHimself = meFor('teacher');
const otherTeacher: CurrentUserOut = { ...meFor('teacher'), teacher_id: 77 };

beforeEach(() => {
  clearToken();
  vi.mocked(getTeacher).mockResolvedValue(kayDetail);
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment, math], total: 2 });
  vi.mocked(listTeachers).mockResolvedValue({ items: [], total: 0 });
});
afterEach(() => {
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}

describe('TeacherDetailPage', () => {
  it('shows the teacher, their department and the courses they teach', async () => {
    logIn(meFor('admin'));
    renderApp('/teachers/2');

    expect(await screen.findByRole('heading', { name: 'Alan Kay' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Computer Science' })).toHaveAttribute(
      'href',
      '/departments/3',
    );
    expect(screen.getByText('555-0102')).toBeInTheDocument();
    expect(screen.getByText('2015-09-01')).toBeInTheDocument();
    expect(screen.getByText('Has a login account')).toBeInTheDocument();
    const courses = screen.getByRole('region', { name: 'Courses taught' });
    expect(within(courses).getByRole('link', { name: 'CS101 Programming' })).toHaveAttribute(
      'href',
      '/courses/11',
    );
  });

  it('shows students the public fields only', async () => {
    logIn(meFor('student'));
    const { id, first_name, last_name, title, email, department_id, courses } = kayDetail;
    const publicKay = { id, first_name, last_name, title, email, department_id, courses };
    vi.mocked(getTeacher).mockResolvedValue(publicKay);
    renderApp('/teachers/2');

    expect(await screen.findByRole('heading', { name: 'Alan Kay' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'alan@uni.example' })).toBeInTheDocument();
    for (const hidden of ['Phone', 'Hire date', 'Login account']) {
      expect(screen.queryByText(hidden)).not.toBeInTheDocument();
    }
  });

  it('says when a teacher teaches nothing', async () => {
    logIn(meFor('admin'));
    vi.mocked(getTeacher).mockResolvedValue({ ...kayDetail, courses: [], user_id: null });
    renderApp('/teachers/2');

    expect(await screen.findByText('Not teaching any courses yet.')).toBeInTheDocument();
    expect(screen.getByText('No account')).toBeInTheDocument();
  });

  it('shows the 404 message for a missing teacher', async () => {
    logIn(meFor('admin'));
    vi.mocked(getTeacher).mockRejectedValue(apiError(404, 'Teacher not found'));
    renderApp('/teachers/999');

    expect(await screen.findByRole('alert')).toHaveTextContent('Teacher not found');
  });

  it.each([
    ['admin', meFor('admin'), 'Edit', true],
    ['HOD of their department', hodOf(3), 'Edit', false],
    ['HOD of another department', hodOf(4), null, false],
    ['the teacher themselves', kayHimself, 'Edit my contact details', false],
    ['another teacher', otherTeacher, null, false],
    ['student', meFor('student'), null, false],
  ] as const)('%s: edit=%s delete=%s', async (_who, me, editLabel, canDelete) => {
    logIn(me);
    renderApp('/teachers/2');
    await screen.findByRole('heading', { name: 'Alan Kay' });

    const buttons = screen.queryAllByRole('button', { name: /^Edit/ }).map((b) => b.textContent);
    expect(buttons).toEqual(editLabel ? [editLabel] : []);
    expect(screen.queryByRole('button', { name: 'Delete' }) !== null).toBe(canDelete);
  });
});

describe('Teacher form (edit)', () => {
  it('a teacher edits only their own email and phone', async () => {
    logIn(kayHimself);
    vi.mocked(updateTeacher).mockResolvedValue(kayDetail);
    const user = userEvent.setup();
    renderApp('/teachers/2');

    await user.click(await screen.findByRole('button', { name: 'Edit my contact details' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit my contact details' });
    expect(within(dialog).getAllByRole('textbox').length).toBe(2); // email + phone
    for (const hidden of [/First name/, /Title/, /Department/, 'Hire date']) {
      expect(within(dialog).queryByLabelText(hidden)).not.toBeInTheDocument();
    }
    const phone = within(dialog).getByLabelText('Phone');
    await user.clear(phone);
    await user.type(phone, '555-4242');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateTeacher).toHaveBeenCalledWith(2, { email: 'alan@uni.example', phone: '555-4242' });
  });

  it("a HOD edits a teacher of their department but can't move them", async () => {
    logIn(hodOf(3));
    vi.mocked(updateTeacher).mockResolvedValue(kayDetail);
    const user = userEvent.setup();
    renderApp('/teachers/2');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit Alan Kay' });
    const department = within(dialog).getByLabelText(/Department/);
    await waitFor(() => {
      expect(
        within(department)
          .getAllByRole('option')
          .map((o) => o.textContent),
      ).toEqual(['CS — Computer Science']);
    });
    await user.selectOptions(within(dialog).getByLabelText(/Title/), 'Professor');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    const body = vi.mocked(updateTeacher).mock.calls[0]?.[1];
    expect(body).toMatchObject({ title: 'professor', first_name: 'Alan' });
    expect(body).not.toHaveProperty('department_id');
  });

  it('an admin can move a teacher to another department', async () => {
    logIn(meFor('admin'));
    vi.mocked(updateTeacher).mockResolvedValue(kayDetail);
    const user = userEvent.setup();
    renderApp('/teachers/2');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit Alan Kay' });
    await waitFor(() => {
      expect(
        within(within(dialog).getByLabelText(/Department/)).getAllByRole('option'),
      ).toHaveLength(3);
    });
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'MATH — Mathematics');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateTeacher).toHaveBeenCalledWith(2, expect.objectContaining({ department_id: 4 }));
  });

  it('shows a 409 for a move that would break a rule at the top of the form', async () => {
    logIn(meFor('admin'));
    vi.mocked(updateTeacher).mockRejectedValue(
      apiError(409, 'This teacher heads department CS; appoint another head first'),
    );
    const user = userEvent.setup();
    renderApp('/teachers/2');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit Alan Kay' });
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(await within(dialog).findByText(/appoint another head first/)).toBeInTheDocument();
  });
});

describe('Teacher delete', () => {
  it("shows the server's 409 reasons when a teacher can't be deleted", async () => {
    logIn(meFor('admin'));
    const message =
      "Teacher can't be deleted: they head department CS and teach 1 course and have a login account (delete it first: DELETE /users/{id})";
    vi.mocked(deleteTeacher).mockRejectedValue(apiError(409, message));
    const user = userEvent.setup();
    renderApp('/teachers/2');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(
      within(screen.getByRole('dialog', { name: 'Delete Alan Kay?' })).getByRole('button', {
        name: 'Delete',
      }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByRole('heading', { name: 'Alan Kay' })).toBeInTheDocument();
  });

  it('deletes after confirmation and returns to the list', async () => {
    logIn(meFor('admin'));
    vi.mocked(deleteTeacher).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderApp('/teachers/2');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('table', { name: 'Teachers' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Alan Kay deleted');
  });
});
