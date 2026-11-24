import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import {
  deleteDepartment,
  getDepartment,
  listDepartments,
  updateDepartment,
} from '../api/departments';
import { listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import { apiError, csDepartment, csDepartmentDetail, csTeachers, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { CurrentUserOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/teachers');

beforeEach(() => {
  clearToken();
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
});
afterEach(() => {
  vi.clearAllMocks();
});

function logIn(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
}
/** meFor('hod') is teacher 2 = the CS head in the fixtures. */
const headOfCs = meFor('hod');
const headOfOther: CurrentUserOut = { ...meFor('hod'), teacher_id: 99 };

describe('DepartmentDetailPage', () => {
  it('shows the head, counts, courses and teachers', async () => {
    logIn(meFor('student'));
    renderApp('/departments/3');

    expect(
      await screen.findByRole('heading', { name: 'Computer Science (CS)' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Turing Hall · +1 555 0100')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Alan Kay, Associate Professor' })).toHaveAttribute(
      'href',
      '/teachers/2',
    );
    const summary = screen.getByRole('region', { name: 'Summary' });
    for (const [label, value] of [
      ['Teachers', '2'],
      ['Students', '20'],
      ['Courses', '2'],
    ]) {
      expect(within(summary).getByText(label).previousSibling).toHaveTextContent(value);
    }
    const courses = screen.getByRole('region', { name: 'Courses' });
    expect(within(courses).getByRole('link', { name: 'CS101 Programming' })).toHaveAttribute(
      'href',
      '/courses/11',
    );
    const teachers = screen.getByRole('region', { name: 'Teachers' });
    expect(within(teachers).getByRole('link', { name: 'Grace Hopper' })).toHaveAttribute(
      'href',
      '/teachers/5',
    );
    expect(listTeachers).toHaveBeenCalledWith({ department_id: 3, limit: 100 });
  });

  it('handles a department without a head, courses or teachers', async () => {
    logIn(meFor('student'));
    vi.mocked(getDepartment).mockResolvedValue({
      ...csDepartmentDetail,
      head: null,
      head_id: null,
      courses: [],
      course_count: 0,
    });
    vi.mocked(listTeachers).mockResolvedValue({ items: [], total: 0 });
    renderApp('/departments/3');

    expect(await screen.findByText('No head appointed')).toBeInTheDocument();
    expect(screen.getByText('No courses yet.')).toBeInTheDocument();
    expect(await screen.findByText('No teachers yet.')).toBeInTheDocument();
  });

  it('shows the 404 message for a missing department', async () => {
    logIn(meFor('admin'));
    vi.mocked(getDepartment).mockRejectedValue(apiError(404, 'Department not found'));
    renderApp('/departments/999');

    expect(await screen.findByRole('alert')).toHaveTextContent('Department not found');
  });

  it.each([
    ['admin', meFor('admin'), true, true],
    ['HOD of this department', headOfCs, true, false],
    ['HOD of another department', headOfOther, false, false],
    ['teacher', meFor('teacher'), false, false],
    ['student', meFor('student'), false, false],
  ] as const)('%s: edit=%s delete=%s', async (_who, me, canEdit, canDelete) => {
    logIn(me);
    renderApp('/departments/3');
    await screen.findByRole('heading', { name: 'Computer Science (CS)' });

    expect(screen.queryByRole('button', { name: 'Edit' }) !== null).toBe(canEdit);
    expect(screen.queryByRole('button', { name: 'Delete' }) !== null).toBe(canDelete);
  });

  it("shows the server's 409 message when a department with dependents can't be deleted", async () => {
    logIn(meFor('admin'));
    const message =
      "Department CS can't be deleted while it has 2 teachers, 20 students, 2 courses. Move or delete them first.";
    vi.mocked(deleteDepartment).mockRejectedValue(apiError(409, message));
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    const dialog = screen.getByRole('dialog', { name: 'Delete CS?' });
    await user.click(within(dialog).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(deleteDepartment).toHaveBeenCalledWith(3);
    expect(screen.getByRole('heading', { name: 'Computer Science (CS)' })).toBeInTheDocument(); // still here
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('deletes after confirmation and returns to the list', async () => {
    logIn(meFor('admin'));
    vi.mocked(deleteDepartment).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete' }));

    expect(await screen.findByRole('table', { name: 'Departments' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Department CS deleted');
  });

  it('cancelling the confirmation deletes nothing', async () => {
    logIn(meFor('admin'));
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Delete' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));

    expect(deleteDepartment).not.toHaveBeenCalled();
  });
});

describe('Department form (edit)', () => {
  it('a HOD edits only description, building and phone of their department', async () => {
    logIn(headOfCs);
    vi.mocked(updateDepartment).mockResolvedValue({ ...csDepartment, building: 'East Wing' });
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit CS' });
    expect(within(dialog).queryByLabelText(/Code/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/^Name/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/Head of department/)).not.toBeInTheDocument();

    const building = within(dialog).getByLabelText('Building');
    await user.clear(building);
    await user.type(building, 'East Wing');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateDepartment).toHaveBeenCalledWith(3, {
      description: 'Programming and systems',
      building: 'East Wing',
      phone: '+1 555 0100',
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Department CS updated');
  });

  it('an admin edits every field and picks the head from the department teachers', async () => {
    logIn(meFor('admin'));
    vi.mocked(updateDepartment).mockResolvedValue({ ...csDepartment, head_id: 5 });
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit CS' });
    const head = within(dialog).getByLabelText(/Head of department/);
    await waitFor(() => {
      expect(
        within(head)
          .getAllByRole('option')
          .map((o) => o.textContent),
      ).toEqual(['No head', 'Alan Kay', 'Grace Hopper']);
    });
    expect(head).toHaveValue('2');

    await user.selectOptions(head, 'Grace Hopper');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateDepartment).toHaveBeenCalledWith(3, {
      code: 'CS',
      name: 'Computer Science',
      description: 'Programming and systems',
      building: 'Turing Hall',
      phone: '+1 555 0100',
      head_id: 5,
    });
  });

  it('clearing an optional field sends null', async () => {
    logIn(meFor('admin'));
    vi.mocked(updateDepartment).mockResolvedValue(csDepartment);
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit CS' });
    await user.clear(within(dialog).getByLabelText('Phone'));
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(updateDepartment).toHaveBeenCalledWith(3, expect.objectContaining({ phone: null }));
  });

  it('shows a 422 field error from the server under the field', async () => {
    logIn(meFor('admin'));
    vi.mocked(updateDepartment).mockRejectedValue(
      apiError(422, 'The head must be a teacher in this department'),
    );
    const user = userEvent.setup();
    renderApp('/departments/3');

    await user.click(await screen.findByRole('button', { name: 'Edit' }));
    const dialog = screen.getByRole('dialog', { name: 'Edit CS' });
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    expect(
      await within(dialog).findByText('The head must be a teacher in this department'),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText(/Head of department/)).toHaveAttribute(
      'aria-invalid',
      'true',
    );
  });
});
