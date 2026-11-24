import type { UserRole } from '../types';

/**
 * Who may open each page (ARCHITECTURE §4). The route guards use this table; the
 * sidebar (T5.4) should use it too, so menus and guards can't disagree. The
 * backend is still the real security check for every request.
 */
export const ALL_ROLES: readonly UserRole[] = ['admin', 'hod', 'teacher', 'student'];
export const STAFF_ROLES: readonly UserRole[] = ['admin', 'hod', 'teacher'];
export const ADMIN_ONLY: readonly UserRole[] = ['admin'];

export const PAGE_ACCESS = {
  dashboard: ALL_ROLES,
  departments: ALL_ROLES,
  teachers: ALL_ROLES,
  students: STAFF_ROLES,
  courses: ALL_ROLES,
  /** "teacher (own)": whether it's their course is checked by the backend. */
  gradeEntry: STAFF_ROLES,
  users: ADMIN_ONLY,
  profile: ALL_ROLES,
} as const satisfies Record<string, readonly UserRole[]>;

export type Page = keyof typeof PAGE_ACCESS;

export function canOpen(role: UserRole, page: Page): boolean {
  return PAGE_ACCESS[page].includes(role);
}
