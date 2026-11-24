import { Navigate, Outlet, useLocation } from 'react-router';

import { useAuth } from './useAuth';

/**
 * Renders its child routes only for a logged-in user. Visitors without a valid
 * token go to /login, which brings them back here after logging in.
 */
export function ProtectedRoute() {
  const { status, retry } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return (
      <p role="status" className="p-8 text-slate-500">
        Loading…
      </p>
    );
  }
  if (status === 'error') {
    return (
      <div className="p-8">
        <p role="alert" className="text-red-700">
          Cannot reach the server. Check your connection.
        </p>
        <button type="button" onClick={retry} className="mt-4 rounded border px-3 py-1">
          Try again
        </button>
      </div>
    );
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  }
  return <Outlet />;
}
