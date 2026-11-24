/**
 * Smoke test (T8.3): each role signs in, sees their dashboard and does one key
 * action through the UI. Anything a test creates or changes is undone through the
 * API afterwards, so the test can run again on the same database.
 */
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const BASE_URL = process.env.E2E_BASE_URL ?? 'http://localhost';
const API = process.env.E2E_API_URL ?? `${BASE_URL.replace(/\/$/, '')}/api/v1`;
const PASSWORD = process.env.E2E_DEMO_PASSWORD ?? 'demo-password';
/** Makes this run's codes unique (5 upper-case letters/digits). */
const RUN = Date.now().toString(36).slice(-5).toUpperCase();

interface Listing<T> {
  items: T[];
}
interface RosterEntry {
  enrollment_id: number;
  first_name: string;
  last_name: string;
  semester: string;
  grade: string | null;
}

async function signIn(page: Page, username: string, dashboard: string) {
  await page.goto('/login');
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { level: 1, name: /^Welcome, / })).toBeVisible();
  await expect(page.getByText(dashboard)).toBeVisible();
}

/** An API client signed in as `username` (for clean-up and cross-checks). */
async function apiAs(request: APIRequestContext, username: string) {
  const response = await request.post(`${API}/auth/login`, {
    form: { username, password: PASSWORD },
  });
  expect(response.ok()).toBe(true);
  const { access_token } = (await response.json()) as { access_token: string };
  const headers = { Authorization: `Bearer ${access_token}` };
  return {
    get: async <T>(path: string): Promise<T> => {
      const r = await request.get(`${API}${path}`, { headers });
      expect(r.ok()).toBe(true);
      return (await r.json()) as T;
    },
    put: (path: string, data: unknown) => request.put(`${API}${path}`, { headers, data }),
    delete: (path: string) => request.delete(`${API}${path}`, { headers }),
  };
}

test('admin creates a department', async ({ page, request }) => {
  const code = `E2E${RUN}`;
  await signIn(page, 'demo.admin', 'Administrator dashboard');
  await expect(page.getByLabel(/^Departments: \d+$/)).toBeVisible();

  try {
    await page.getByRole('link', { name: 'Departments', exact: true }).click();
    await page.getByRole('button', { name: 'New department' }).click();
    const dialog = page.getByRole('dialog', { name: 'New department' });
    await dialog.getByLabel('Code').fill(code);
    await dialog.getByLabel('Name').fill(`E2E department ${RUN}`);
    await dialog.getByRole('button', { name: 'Create department' }).click();

    await expect(page.getByRole('status')).toContainText(`Department ${code} created`);
    await page.getByLabel('Search departments').fill(code);
    await page.getByRole('link', { name: code, exact: true }).click();
    await expect(
      page.getByRole('heading', { level: 1, name: `E2E department ${RUN} (${code})` }),
    ).toBeVisible();
  } finally {
    const admin = await apiAs(request, 'demo.admin');
    const found = await admin.get<Listing<{ id: number; code: string }>>(
      `/departments?search=${code}`,
    );
    for (const d of found.items.filter((d) => d.code === code)) {
      expect((await admin.delete(`/departments/${String(d.id)}`)).ok()).toBe(true);
    }
  }
});

test('HOD creates a course in their department', async ({ page, request }) => {
  const code = `E2E-${RUN}`;
  await signIn(page, 'demo.hod', 'Head of department dashboard');

  try {
    await page.getByRole('link', { name: 'Courses', exact: true }).click();
    await page.getByRole('button', { name: 'New course' }).click();
    const dialog = page.getByRole('dialog', { name: 'New course' });
    await dialog.getByLabel('Code').fill(code);
    await dialog.getByLabel('Title').fill(`E2E course ${RUN}`);
    await dialog.getByRole('button', { name: 'Create course' }).click();

    await expect(page.getByRole('status')).toContainText(`Course ${code} created`);
  } finally {
    const hod = await apiAs(request, 'demo.hod');
    const found = await hod.get<Listing<{ id: number; code: string }>>(`/courses?search=${code}`);
    for (const c of found.items.filter((c) => c.code === code)) {
      expect((await hod.delete(`/courses/${String(c.id)}`)).ok()).toBe(true);
    }
  }
});

test('teacher saves a grade', async ({ page, request }) => {
  await signIn(page, 'demo.teacher', 'Teacher dashboard');
  await page
    .getByRole('link', { name: /^Enter grades for / })
    .first()
    .click();
  await expect(page.getByRole('heading', { level: 1, name: /^Grades: / })).toBeVisible();

  const courseId = Number(new URL(page.url()).pathname.split('/')[2]);
  const box = page.getByRole('combobox', { name: /^Grade for / }).first();
  const label = (await box.getAttribute('aria-label')) ?? '';
  const before = await box.inputValue();
  const next = before === 'A-' ? 'B+' : 'A-';

  try {
    await box.selectOption(next);
    await expect(page.getByText('1 unsaved change')).toBeVisible();
    await page.getByRole('button', { name: 'Save all' }).click();
    await expect(page.getByRole('status')).toContainText(/Saved 1 grade for /);

    await page.reload(); // the saved grade comes back from the server
    await expect(page.getByRole('combobox', { name: label })).toHaveValue(next);
  } finally {
    const teacher = await apiAs(request, 'demo.teacher');
    const course = await teacher.get<{ roster: RosterEntry[] }>(`/courses/${String(courseId)}`);
    const entry = course.roster.find(
      (r) => label === `Grade for ${r.first_name} ${r.last_name} (${r.semester})`,
    );
    expect(entry).toBeDefined();
    const restore = [{ enrollment_id: entry?.enrollment_id, grade: before || null }];
    expect((await teacher.put(`/courses/${String(courseId)}/grades`, restore)).ok()).toBe(true);
  }
});

test('student sees their GPA', async ({ page, request }) => {
  await signIn(page, 'demo.student', 'Student dashboard');

  const student = await apiAs(request, 'demo.student');
  const { gpa } = await student.get<{ gpa: number | null }>('/dashboard');
  await expect(page.getByLabel(`GPA: ${gpa === null ? '—' : gpa.toFixed(2)}`)).toBeVisible();
  const grades = page.getByRole('region', { name: 'My enrollments and grades' });
  await expect(grades.getByRole('row').nth(1)).toBeVisible();
});
