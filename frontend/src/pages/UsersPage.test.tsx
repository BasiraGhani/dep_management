import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getMe } from '../api/auth';
import { getStudent, listStudents } from '../api/students';
import { getTeacher, listTeachers } from '../api/teachers';
import { createUser, listUsers, resetPassword, updateUser } from '../api/users';
import { clearToken, setToken } from '../auth/token';
import { amiraDetail, apiError, csTeachers, kayDetail, meFor } from '../test/fixtures';
import { renderApp } from '../test/render';
import type { UserOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/users');
vi.mock('../api/teachers');
vi.mock('../api/students');

const account = (id: number, username: string, extra: Partial<UserOut> = {}): UserOut => ({
  id,
  username,
  role: 'admin',
  is_active: true,
  teacher_id: null,
  student_id: null,
  created_at: '2026-09-01T10:00:00Z',
  updated_at: '2026-09-01T10:00:00Z',
  ...extra,
});
const me = account(10, 'demo.admin'); // meFor('admin') has id 10
const kay = account(11, 'alan.kay', { role: 'teacher', teacher_id: 2 });
const amira = account(12, 'amira', { role: 'student', student_id: 1, is_active: false });

beforeEach(() => {
  clearToken();
  vi.mocked(listUsers).mockResolvedValue({ items: [me, kay, amira], total: 3 });
  vi.mocked(getTeacher).mockResolvedValue(kayDetail);
  vi.mocked(getStudent).mockResolvedValue(amiraDetail);
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(listStudents).mockResolvedValue({ items: [amiraDetail], total: 1 });
});
afterEach(() => {
  vi.clearAllMocks();
});

async function open() {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(meFor('admin'));
  const user = userEvent.setup();
  renderApp('/users');
  await screen.findByRole('table', { name: 'Users' });
  return user;
}
const rowOf = (username: string) =>
  within(screen.getByRole('table', { name: 'Users' }))
    .getByText(username)
    .closest('tr') as HTMLElement;

describe('list (FR-8.1)', () => {
  it('shows each account with role, linked record and status', async () => {
    await open();

    expect(rowOf('demo.admin')).toHaveTextContent('(you)');
    expect(rowOf('demo.admin')).toHaveTextContent('Administrator');
    expect(
      await within(rowOf('alan.kay')).findByRole('link', { name: 'Alan Kay' }),
    ).toHaveAttribute('href', '/teachers/2');
    expect(
      await within(rowOf('amira')).findByRole('link', { name: 'Amira Costa' }),
    ).toHaveAttribute('href', '/students/1');
    expect(rowOf('alan.kay')).toHaveTextContent('Active');
    expect(rowOf('amira')).toHaveTextContent('Deactivated');
  });

  it('you cannot deactivate your own account', async () => {
    await open();
    expect(
      within(rowOf('demo.admin')).queryByRole('button', { name: /activate/i }),
    ).not.toBeInTheDocument();
  });

  it('filters by search, role and status', async () => {
    const user = await open();

    await user.selectOptions(screen.getByLabelText('Role'), 'Student');
    await user.selectOptions(screen.getByLabelText('Status'), 'Deactivated');
    await user.type(screen.getByLabelText('Search users'), 'ami');

    await waitFor(() => {
      expect(listUsers).toHaveBeenLastCalledWith({
        search: 'ami',
        role: 'student',
        is_active: false,
        skip: 0,
        limit: 20,
      });
    });
  });

  it('says when nothing matches', async () => {
    const user = await open();
    vi.mocked(listUsers).mockResolvedValue({ items: [], total: 0 });

    await user.selectOptions(screen.getByLabelText('Role'), 'Head of department');

    expect(await screen.findByText('No accounts match these filters.')).toBeInTheDocument();
  });
});

describe('activate and deactivate (FR-8.1, FR-8.2)', () => {
  it('deactivating asks first', async () => {
    vi.mocked(updateUser).mockResolvedValue({ ...kay, is_active: false });
    const user = await open();

    await user.click(screen.getByRole('button', { name: 'Deactivate alan.kay' }));
    const dialog = screen.getByRole('dialog', { name: 'Deactivate alan.kay?' });
    expect(dialog).toHaveTextContent("won't be able to sign in");
    expect(updateUser).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole('button', { name: 'Deactivate' }));

    expect(updateUser).toHaveBeenCalledWith(11, { is_active: false });
    expect(await screen.findByRole('status')).toHaveTextContent('alan.kay deactivated');
    await waitFor(() => {
      expect(listUsers).toHaveBeenCalledTimes(2); // the list is refreshed
    });
  });

  it('reactivating is one click', async () => {
    vi.mocked(updateUser).mockResolvedValue({ ...amira, is_active: true });
    const user = await open();

    await user.click(screen.getByRole('button', { name: 'Reactivate amira' }));

    expect(updateUser).toHaveBeenCalledWith(12, { is_active: true });
    expect(await screen.findByRole('status')).toHaveTextContent('amira reactivated');
  });

  it("shows the server's message if it fails", async () => {
    vi.mocked(updateUser).mockRejectedValue(apiError(403, "You can't deactivate your own account"));
    const user = await open();

    await user.click(screen.getByRole('button', { name: 'Deactivate alan.kay' }));
    await user.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 'Deactivate' }),
    );

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "You can't deactivate your own account",
    );
  });
});

describe('reset password', () => {
  it('asks first, then shows the temporary password once', async () => {
    vi.mocked(resetPassword).mockResolvedValue({ temporary_password: 'Tmp-7Hq2-xK9p' });
    const user = await open();

    await user.click(screen.getByRole('button', { name: 'Reset password of alan.kay' }));
    const confirm = screen.getByRole('dialog', { name: 'Reset the password of alan.kay?' });
    await user.click(within(confirm).getByRole('button', { name: 'Reset password' }));

    expect(resetPassword).toHaveBeenCalledWith(11);
    const shown = await screen.findByRole('dialog', { name: 'Temporary password for alan.kay' });
    expect(within(shown).getByLabelText('Temporary password')).toHaveTextContent('Tmp-7Hq2-xK9p');
    expect(shown).toHaveTextContent('shown only now');

    await user.click(within(shown).getByRole('button', { name: 'Done' }));
    expect(screen.queryByText('Tmp-7Hq2-xK9p')).not.toBeInTheDocument();
  });

  it('copies the password to the clipboard', async () => {
    vi.mocked(resetPassword).mockResolvedValue({ temporary_password: 'Tmp-7Hq2-xK9p' });
    const user = await open();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText');

    await user.click(screen.getByRole('button', { name: 'Reset password of amira' }));
    await user.click(screen.getByRole('button', { name: 'Reset password' }));
    await user.click(await screen.findByRole('button', { name: 'Copy' }));

    expect(writeText).toHaveBeenCalledWith('Tmp-7Hq2-xK9p');
    expect(await screen.findByRole('status')).toHaveTextContent('Copied');
  });
});

describe('create an account (FR-8.1)', () => {
  async function openForm() {
    const user = await open();
    await user.click(screen.getByRole('button', { name: 'New account' }));
    const dialog = screen.getByRole('dialog', { name: 'New account' });
    await user.type(within(dialog).getByLabelText(/Username/), 'grace.h');
    await user.type(within(dialog).getByLabelText(/Temporary password/), 'temp-pass-123');
    return { user, dialog };
  }

  it('a teacher account is linked to the chosen teacher', async () => {
    vi.mocked(createUser).mockResolvedValue(
      account(20, 'grace.h', { role: 'teacher', teacher_id: 2 }),
    );
    const { user, dialog } = await openForm();

    await user.selectOptions(await within(dialog).findByLabelText(/^Teacher/), 'Kay, Alan');
    await user.click(within(dialog).getByRole('button', { name: 'Create account' }));

    expect(createUser).toHaveBeenCalledWith({
      username: 'grace.h',
      password: 'temp-pass-123',
      role: 'teacher',
      teacher_id: 2,
      student_id: null,
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Account grace.h created');
  });

  it('a student account is linked to a student found by search', async () => {
    vi.mocked(createUser).mockResolvedValue(
      account(21, 'grace.h', { role: 'student', student_id: 1 }),
    );
    const { user, dialog } = await openForm();

    await user.selectOptions(within(dialog).getByLabelText(/^Role/), 'Student');
    expect(within(dialog).queryByLabelText(/^Teacher/)).not.toBeInTheDocument();
    await user.type(within(dialog).getByLabelText('Find student'), 'amira');
    await waitFor(() => {
      expect(listStudents).toHaveBeenLastCalledWith({ search: 'amira', limit: 20 });
    });
    await user.selectOptions(within(dialog).getByLabelText(/^Student/), 'CS2026001 — Amira Costa');
    await user.click(within(dialog).getByRole('button', { name: 'Create account' }));

    expect(createUser).toHaveBeenCalledWith({
      username: 'grace.h',
      password: 'temp-pass-123',
      role: 'student',
      teacher_id: null,
      student_id: 1,
    });
  });

  it('an admin account has no link', async () => {
    vi.mocked(createUser).mockResolvedValue(account(22, 'grace.h'));
    const { user, dialog } = await openForm();

    await user.selectOptions(within(dialog).getByLabelText(/^Role/), 'Administrator');
    await user.click(within(dialog).getByRole('button', { name: 'Create account' }));

    expect(createUser).toHaveBeenCalledWith(
      expect.objectContaining({ role: 'admin', teacher_id: null, student_id: null }),
    );
  });

  it('checks the form before sending', async () => {
    const user = await open();
    await user.click(screen.getByRole('button', { name: 'New account' }));
    const dialog = screen.getByRole('dialog', { name: 'New account' });
    await user.type(within(dialog).getByLabelText(/Username/), 'x');
    await user.type(within(dialog).getByLabelText(/Temporary password/), 'short');

    await user.click(within(dialog).getByRole('button', { name: 'Create account' }));

    expect(within(dialog).getByText(/3–50 letters/)).toBeInTheDocument();
    expect(within(dialog).getByText('At least 8 characters')).toBeInTheDocument();
    expect(within(dialog).getByText('Choose the teacher')).toBeInTheDocument();
    expect(createUser).not.toHaveBeenCalled();
  });

  it.each([
    [409, "Username 'grace.h' is already taken", /Username/],
    [409, "Teacher 2 already has an account ('alan.kay')", /^Teacher/],
    [
      422,
      "Alan Kay doesn't head a department, so the account can't be hod. Make them head first.",
      /^Role/,
    ],
  ])('a %i "%s" is shown under its field', async (status, detail, field) => {
    vi.mocked(createUser).mockRejectedValue(apiError(status, detail));
    const { user, dialog } = await openForm();
    await user.selectOptions(await within(dialog).findByLabelText(/^Teacher/), 'Kay, Alan');

    await user.click(within(dialog).getByRole('button', { name: 'Create account' }));

    expect(await within(dialog).findByText(detail)).toBeInTheDocument();
    expect(within(dialog).getByLabelText(field)).toHaveAttribute('aria-invalid', 'true');
  });
});
