import { useNavigate } from 'react-router';

import { useAuth } from '../auth/useAuth';

/**
 * Temporary dashboard at `/`. T5.4 moves logout into the top bar and T7.1
 * replaces this with the role-specific dashboards.
 */
export function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (user === null) return null; // ProtectedRoute only renders this when logged in

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
