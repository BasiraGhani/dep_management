import { canOpen, type Page } from '../auth/access';
import type { UserRole } from '../types';

export interface NavItem {
  page: Page;
  label: string;
  to: string;
}

/** Sidebar entries in display order. Who sees each comes from PAGE_ACCESS (§4). */
export const NAV_ITEMS: readonly NavItem[] = [
  { page: 'dashboard', label: 'Dashboard', to: '/' },
  { page: 'departments', label: 'Departments', to: '/departments' },
  { page: 'teachers', label: 'Teachers', to: '/teachers' },
  { page: 'students', label: 'Students', to: '/students' },
  { page: 'courses', label: 'Courses', to: '/courses' },
  { page: 'users', label: 'Users', to: '/users' },
  { page: 'profile', label: 'My profile', to: '/profile' },
];

/** The sidebar entries `role` may open. */
export function navItemsFor(role: UserRole): NavItem[] {
  return NAV_ITEMS.filter((item) => canOpen(role, item.page));
}
