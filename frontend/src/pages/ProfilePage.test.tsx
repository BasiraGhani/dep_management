import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { changePassword, getMe } from '../api/auth';
import { getDepartment, listDepartments } from '../api/departments';
import { getStudent, updateStudent } from '../api/students';
import { getTeacher, updateTeacher } from '../api/teachers';
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
import type { CurrentUserOut } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/departments');
vi.mock('../api/teachers');
vi.mock('../api/students');

beforeEach(() => {
  clearToken();
  vi.mocked(getTeacher).mockResolvedValue(kayDetail);
  vi.mocked(getStudent).mockResolvedValue(amiraDetail);
  vi.mocked(getDepartment).mockResolvedValue(csDepartmentDetail);
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
});
afterEach(() => {
  vi.clearAllMocks();
});

async function open(me: CurrentUserOut) {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(me);
  const user = userEvent.setup();
  renderApp('/profile');
  await screen.findByRole('heading', { name: 'My profile' });
  return user;
}
const account = () => screen.getByRole('region', { name: 'Account' });

describe('your record', () => {
  it('a teacher sees their account and teacher record', async () => {
    await open(meFor('teacher'));

    expect(within(account()).getByText('demo.teacher')).toBeInTheDocument();
    expect(within(account()).getByText('Teacher')).toBeInTheDocument();
    const record = await screen.findByRole('region', { name: 'My teacher record' });
    expect(record).toHaveTextContent('Alan Kay');
    expect(record).toHaveTextContent('Associate Professor');
    expect(record).toHaveTextContent(kayDetail.email);
    expect(await within(record).findByRole('link', { name: 'Computer Science' })).toHaveAttribute(
      'href',
      '/departments/3',
    );
    expect(getTeacher).toHaveBeenCalledWith(2);
  });

  it('a teacher can edit only their phone and email', async () => {
    vi.mocked(updateTeacher).mockResolvedValue(kayDetail);
    const user = await open(meFor('teacher'));
    await user.click(await screen.findByRole('button', { name: 'Edit my contact details' }));

    const dialog = screen.getByRole('dialog', { name: 'Edit my contact details' });
    expect(within(dialog).queryByLabelText(/First name/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/Department/)).not.toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText(/Phone/));
    await user.type(within(dialog).getByLabelText(/Phone/), '+1 555 0199');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    await waitFor(() => {
      expect(updateTeacher).toHaveBeenCalledWith(2, {
        email: kayDetail.email,
        phone: '+1 555 0199',
      });
    });
  });

  it('a student sees their record and can edit only their phone and email', async () => {
    vi.mocked(updateStudent).mockResolvedValue(amiraDetail);
    const user = await open(meFor('student'));

    const record = await screen.findByRole('region', { name: 'My student record' });
    expect(record).toHaveTextContent('CS2026001');
    expect(record).toHaveTextContent('Year 1');
    await user.click(within(record).getByRole('button', { name: 'Edit my contact details' }));

    const dialog = screen.getByRole('dialog', { name: 'Edit my contact details' });
    expect(within(dialog).queryByLabelText(/Student number/)).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText(/Status/)).not.toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText(/Email/));
    await user.type(within(dialog).getByLabelText(/Email/), 'amira.c@student.uni.example');
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }));

    await waitFor(() => {
      expect(updateStudent).toHaveBeenCalledWith(1, {
        email: 'amira.c@student.uni.example',
        phone: amiraDetail.phone,
      });
    });
  });

  it('an admin without a linked record is told so', async () => {
    await open(meFor('admin'));

    expect(
      screen.getByText("This account isn't linked to a teacher or student record."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: 'Edit my contact details' }),
    ).not.toBeInTheDocument();
  });
});

describe('change password (FR-1.6)', () => {
  const fill = async (
    user: ReturnType<typeof userEvent.setup>,
    current: string,
    next: string,
    confirm = next,
  ) => {
    if (current) await user.type(screen.getByLabelText(/^Current password/), current);
    if (next) await user.type(screen.getByLabelText(/^New password/), next);
    if (confirm) await user.type(screen.getByLabelText(/^Confirm new password/), confirm);
    await user.click(screen.getByRole('button', { name: 'Change password' }));
  };

  it('sends the current and new password, then clears the form', async () => {
    vi.mocked(changePassword).mockResolvedValue(undefined);
    const user = await open(meFor('admin'));

    await fill(user, 'old-password', 'brand-new-pass');

    expect(changePassword).toHaveBeenCalledWith({
      current_password: 'old-password',
      new_password: 'brand-new-pass',
    });
    expect(await screen.findByRole('status')).toHaveTextContent('Password changed');
    expect(screen.getByLabelText(/^Current password/)).toHaveValue('');
    expect(screen.getByLabelText(/^New password/)).toHaveValue('');
  });

  it.each([
    ['too short', 'old-password', 'short', 'short', /^New password/, 'At least 8 characters'],
    [
      'not confirmed',
      'old-password',
      'brand-new-pass',
      'brand-new-paZZ',
      /^Confirm new password/,
      "Passwords don't match",
    ],
    [
      'same as now',
      'same-password',
      'same-password',
      'same-password',
      /^New password/,
      'different from the current one',
    ],
    [
      'no current password',
      '',
      'brand-new-pass',
      'brand-new-pass',
      /^Current password/,
      'Enter your current password',
    ],
  ])('checks the form first: %s', async (_case, current, next, confirm, field, message) => {
    const user = await open(meFor('admin'));

    await fill(user, current, next, confirm);

    expect(screen.getByLabelText(field)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText(new RegExp(message))).toBeInTheDocument();
    expect(changePassword).not.toHaveBeenCalled();
  });

  it('a wrong current password is shown under that field', async () => {
    vi.mocked(changePassword).mockRejectedValue(apiError(400, 'Current password is incorrect'));
    const user = await open(meFor('student'));

    await fill(user, 'wrong-password', 'brand-new-pass');

    expect(await screen.findByText('Current password is incorrect')).toBeInTheDocument();
    expect(screen.getByLabelText(/^Current password/)).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText(/^New password/)).toHaveValue('brand-new-pass'); // nothing lost
  });
});
