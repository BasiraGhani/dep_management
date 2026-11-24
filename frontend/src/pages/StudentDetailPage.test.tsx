import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { getDepartment, listDepartments } from '../api/departments';
import { deleteStudent, getStudent, listStudents, updateStudent } from '../api/students';
import { clearToken, setToken } from '../auth/token';
import {
  amiraDetail,
  apiError,
  csDepartment,
  csDepartmentDetail,
  kayDetail,
  meFor,
} from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CurrentUserOut, DepartmentOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/students');

const math: DepartmentOut = { ...csDepartment, id: 4, code: 'MATH', name: 'Mathematics' };
const hodOf = (departmentId: number): CurrentUserOut => ({
  ...meFor('hod'),
  teacher: { ...kayDetail, department_id: departmentId },
});

beforeEach(() => {
  clearToken();
  vi.mocked(getStudent).mockResolvedValue(amiraDetail);
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment, math], total: 2 });
  vi.mocked(listStudents).mockResolvedValue({ items: [], total: 0 });
});
afterEach(() => {
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}

describe('StudentDetailPage', () => {
  it('shows the profile, enrollments with grades, and the GPA', async () => {
    logIn(meFor('teacher'));
    renderApp('/students/1');

    expect(await screen.findByRole('heading', { name: 'Amira Costa' })).toBeInTheDocument();
    expect(screen.getByText('CS2026001 · Year 1 · Active')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Computer Science' })).toHaveAttribute(
      'href',
      '/departments/3',
    );
    for (const text of ['555-0110', '2006-01-01', '2026-09-01', 'Has a login account']) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
    const table = screen.getByRole('table', { name: 'Enrollments and grades' });
    expect(
      within(table)
        .getAllByRole('row')
        .slice(1)
        .map((r) =>
          within(r)
            .getAllByRole('cell')
            .map((c) => c.textContent),
        ),
    ).toEqual([
      ['CS101 Programming', '2026-Spring', '4', 'A'],
      ['CS201 Data Structures', '2026-Fall', '4', 'Not graded'],
    ]);
    expect(screen.getByText('4.00')).toBeInTheDocument();
  });

  it('shows "not graded yet" and an empty state for a new student', async () => {
    logIn(meFor('admin'));
    vi.mocked(getStudent).mockResolvedValue({
      ...amiraDetail,
      enrollments: [],
      gpa: null,
      user_id: null,
    });
    renderApp('/students/1');

    expect(await screen.findByText('not graded yet')).toBeInTheDocument();
    expect(screen.getByText('Not enrolled in any course.')).toBeInTheDocument();
    expect(screen.getByText('No account')).toBeInTheDocument();
  });

  it("shows the server's 403 to someone outside the student's scope", async () => {
    logIn(meFor('teacher'));
    vi.mocked(getStudent).mockRejectedValue(apiError(403, "You can't view this student"));
    renderApp('/students/9');

    expect(await screen.findByRole('alert')).toHaveTextContent("You can't view this student");
  });

  it.each([
    ['admin', meFor('admin'), true],
    ['HOD of their department', hodOf(3), true],
    ['HOD of another department', hodOf(4), false],
    ['teacher (read-only)', meFor('teacher'), false],
  ] as const)('%s: can manage = %s', async (_who, me, canManage) => {
    logIn(me);
    renderApp('/students/1');
    await screen.findByRole('heading', { name: 'Amira Costa' });

    expect(screen.queryByRole('button', { name: 'Edit' }) !== null).toBe(canManage);
    expect(screen.queryByRole('button', { name: 'Delete' }) !== null).toBe(canManage);
  });
});

describe('FR-4.4 delete with confirmation', () => {
  it('the confirmation says the enrollments are deleted too', async () => {
    logIn(meFor('admin'));
    const user = userEvent.setup();
    renderApp('/students/1');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));

    expect(screen.getByRole('dialog', { name: 'Delete Amira Costa?' })).toHaveTextContent(
      "Amira Costa and their 2 enrollments (with grades) will be deleted. This can't be undone.",
    );
    expect(deleteStudent).not.toHaveBeenCalled(); // nothing happens until confirmed
  });

  it('deletes after confirming and returns to the list', async () => {
    logIn(hodOf(3));
    vi.mocked(deleteStudent).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderApp('/students/1');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));

    expect(deleteStudent).toHaveBeenCalledWith(1);
    expect(await screen.findByRole('table', { name: 'Students' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Amira Costa deleted');
  });

  it("shows the server's 409 when the student still has a login account", async () => {
    logIn(meFor('admin'));
    const message =
      "Student can't be deleted: they have a login account (delete it first: DELETE /users/{id})";
    vi.mocked(deleteStudent).mockRejectedValue(apiError(409, message));
    const user = userEvent.setup();
    renderApp('/students/1');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByRole('heading', { name: 'Amira Costa' })).toBeInTheDocument();
  });
});

describe('FR-4.1 edit', () => {
  it('an admin edits any field, including the department', async () => {
    logIn(meFor('admin'));
    vi.mocked(updateStudent).mockResolvedValue(amiraDetail);
    const user = userEvent.setup();
    renderApp('/students/1');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit Amira Costa' });
    expect(within(dialog).queryByText('Login account')).not.toBeInTheDocument(); // create only
    await waitFor(() => {
      expect(
        within(within(dialog).getByLabelText(/Department/)).getAllByRole('option'),
      ).toHaveLength(3);
    });
    await user.selectOptions(within(dialog).getByLabelText(/Year of study/), 'Year 2');
    await user.selectOptions(within(dialog).getByLabelText(/Status/), 'Graduated');
    await user.selectOptions(within(dialog).getByLabelText(/Department/), 'MATH — Mathematics');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateStudent).toHaveBeenCalledWith(1, {
      student_no: 'CS2026001',
      first_name: 'Amira',
      last_name: 'Costa',
      email: 'amira@student.uni.example',
      phone: '555-0110',
      date_of_birth: '2006-01-01',
      year: 2,
      status: 'graduated',
      enrollment_date: '2026-09-01',
      department_id: 4,
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Amira Costa updated');
  });

  it("a HOD edits their department's student but never moves them", async () => {
    logIn(hodOf(3));
    vi.mocked(updateStudent).mockResolvedValue(amiraDetail);
    const user = userEvent.setup();
    renderApp('/students/1');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit Amira Costa' });
    await user.selectOptions(within(dialog).getByLabelText(/Status/), 'Suspended');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    const body = vi.mocked(updateStudent).mock.calls[0]?.[1];
    expect(body).toMatchObject({ status: 'suspended' });
    expect(body).not.toHaveProperty('department_id');
  });
});
