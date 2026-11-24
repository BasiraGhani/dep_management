import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from 'vitest';

import { getMe } from '../api/auth';
import { browser } from '../api/browser';
import { listCourses } from '../api/courses';
import { listDepartments } from '../api/departments';
import { exportCsv } from '../api/export';
import { listStudents } from '../api/students';
import { listTeachers } from '../api/teachers';
import { clearToken, setToken } from '../auth/token';
import {
  amiraDetail,
  apiError,
  cs101Detail,
  csDepartment,
  csTeachers,
  meFor,
} from '../test/fixtures';
import { renderApp } from '../test/render';
import type { UserRole } from '../types';

vi.mock('../api/auth', () => ({ login: vi.fn(), getMe: vi.fn(), changePassword: vi.fn() }));
vi.mock('../api/courses');
vi.mock('../api/departments');
vi.mock('../api/teachers');
vi.mock('../api/students');
vi.mock('../api/export');

const csv = new Blob(['id,code\r\n'], { type: 'text/csv' });

beforeEach(() => {
  clearToken();
  vi.mocked(listDepartments).mockResolvedValue({ items: [csDepartment], total: 1 });
  vi.mocked(listTeachers).mockResolvedValue(csTeachers);
  vi.mocked(listStudents).mockResolvedValue({ items: [amiraDetail], total: 1 });
  vi.mocked(listCourses).mockResolvedValue({ items: [cs101Detail], total: 1 });
  vi.mocked(exportCsv).mockImplementation((resource) =>
    Promise.resolve({ filename: `${resource}.csv`, blob: csv }),
  );
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

async function open(path: string, role: UserRole = 'admin') {
  setToken('valid.token');
  vi.mocked(getMe).mockResolvedValue(meFor(role));
  const user = userEvent.setup();
  renderApp(path);
  await screen.findByRole('table');
  return user;
}

describe('Export CSV uses the current filters (FR-9.1)', () => {
  it('students: search, department, year and status', async () => {
    const download = vi.spyOn(browser, 'download').mockImplementation(() => undefined);
    const user = await open('/students');

    await user.type(screen.getByLabelText('Search students'), 'costa');
    await user.selectOptions(screen.getByLabelText('Department'), 'CS — Computer Science');
    await user.selectOptions(screen.getByLabelText('Year'), 'Year 2');
    await user.selectOptions(screen.getByLabelText('Status'), 'Suspended');
    await waitFor(() => {
      expect(listStudents).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'costa' }));
    });
    await user.click(screen.getByRole('button', { name: /^Export CSV/ }));

    expect(exportCsv).toHaveBeenCalledWith('students', {
      search: 'costa',
      department_id: 3,
      year: 2,
      status: 'suspended',
    });
    expect(download).toHaveBeenCalledWith(csv, 'students.csv');
  });

  it('teachers: department and title', async () => {
    const download = vi.spyOn(browser, 'download').mockImplementation(() => undefined);
    const user = await open('/teachers');

    await user.selectOptions(screen.getByLabelText('Department'), 'CS — Computer Science');
    await user.selectOptions(screen.getByLabelText('Title'), 'Professor');
    await user.click(screen.getByRole('button', { name: /^Export CSV/ }));

    expect(exportCsv).toHaveBeenCalledWith('teachers', {
      search: undefined,
      department_id: 3,
      title: 'professor',
    });
    expect(download).toHaveBeenCalledWith(csv, 'teachers.csv');
  });

  it('courses: no filters exports everything', async () => {
    const download = vi.spyOn(browser, 'download').mockImplementation(() => undefined);
    const user = await open('/courses');

    await user.click(screen.getByRole('button', { name: /^Export CSV/ }));

    expect(exportCsv).toHaveBeenCalledWith('courses', {
      search: undefined,
      department_id: undefined,
      teacher_id: undefined,
    });
    expect(download).toHaveBeenCalledWith(csv, 'courses.csv');
  });

  it('a failed export shows the error', async () => {
    vi.spyOn(browser, 'download').mockImplementation(() => undefined);
    vi.mocked(exportCsv).mockRejectedValue(
      apiError(403, 'You can only export the department you head'),
    );
    const user = await open('/courses', 'hod');

    await user.click(screen.getByRole('button', { name: /^Export CSV/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You can only export the department you head',
    );
  });
});

describe('who sees Export CSV', () => {
  it.each([
    ['admin', '/students', 'With the current filters'],
    ['hod', '/teachers', "Only your department's rows"],
  ] as const)('%s on %s', async (role, path, hint) => {
    await open(path, role);
    expect(screen.getByRole('button', { name: /^Export CSV/ })).toHaveAccessibleDescription(
      new RegExp(hint),
    );
  });

  it.each([
    ['teacher', '/students'],
    ['teacher', '/courses'],
    ['student', '/teachers'],
    ['student', '/courses'],
  ] as const)('not %s on %s', async (role, path) => {
    await open(path, role);
    expect(screen.queryByRole('button', { name: /Export CSV/ })).not.toBeInTheDocument();
  });
});

describe('download helper', () => {
  it('saves the blob under the file name', () => {
    vi.spyOn(browser, 'download'); // keep the real implementation
    const created = vi.fn(() => 'blob:fake');
    const revoked = vi.fn();
    // jsdom has no object URLs: stand them in for this test only.
    const original: unknown = {
      createObjectURL: Reflect.get(URL, 'createObjectURL'),
      revokeObjectURL: Reflect.get(URL, 'revokeObjectURL'),
    };
    Object.assign(URL, { createObjectURL: created, revokeObjectURL: revoked });
    onTestFinished(() => {
      Object.assign(URL, original);
    });
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      expect(this.download).toBe('students.csv');
      expect(this.href).toBe('blob:fake');
    });

    browser.download(csv, 'students.csv');

    expect(created).toHaveBeenCalledWith(csv);
    expect(click).toHaveBeenCalledTimes(1);
    expect(revoked).toHaveBeenCalledWith('blob:fake');
    expect(document.querySelector('a[download]')).toBeNull(); // removed again
  });
});
