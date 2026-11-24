import { useAuth } from '../auth/useAuth';

/** Temporary dashboard at `/`; T7.1 replaces it with the role-specific dashboards. */
export function DashboardPage() {
  const { user } = useAuth();
  if (user === null) return null; // ProtectedRoute only renders this when logged in

  const linked = user.teacher ?? user.student;
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-800">
        Welcome, {linked ? `${linked.first_name} ${linked.last_name}` : user.username}
      </h1>
      <p className="mt-1 text-slate-500">
        Signed in as <strong>{user.username}</strong> ({user.role})
      </p>
    </div>
  );
}
