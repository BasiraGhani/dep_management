import { Navigate, useLocation, useNavigate } from 'react-router';

import { useAuth } from '../auth/useAuth';

/**
 * Temporary landing page at `/` so login has somewhere to go. T5.3 adds the real
 * route guards and layout, and T7.1 replaces this with the role dashboards.
 */
export function HomePage() {
  const { status, user, logout, retry } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (status === 'loading') {
    return <p className="p-8 text-slate-500">Loading…</p>;
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
  if (user === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  const linked = user.teacher ?? user.student;
  const onLogout = () => {
    logout();
    void navigate('/login', { replace: true });
  };

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-semibold text-slate-800">
        Welcome, {linked ? `${linked.first_name} ${linked.last_name}` : user.username}
      </h1>
      <p className="mt-1 text-slate-500">
        Signed in as <strong>{user.username}</strong> ({user.role})
      </p>
      <button
        type="button"
        onClick={onLogout}
        className="mt-6 rounded bg-slate-800 px-4 py-2 text-white hover:bg-slate-700"
      >
        Log out
      </button>
    </main>
  );
}
