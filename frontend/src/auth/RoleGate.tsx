import { Outlet } from 'react-router';

import { NotAuthorizedPage } from '../pages/NotAuthorizedPage';
import type { UserRole } from '../types';
import { useAuth } from './useAuth';

/**
 * Renders its child routes only for the given roles; everyone else sees the
 * "Not authorized" page. Use inside ProtectedRoute. The backend still checks
 * every request; this only keeps users away from pages they can't use.
 */
export function RoleGate({ roles }: { roles: readonly UserRole[] }) {
  const { user } = useAuth();
  if (user === null || !roles.includes(user.role)) {
    return <NotAuthorizedPage />;
  }
  return <Outlet />;
}
