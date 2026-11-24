import { useAuth } from '../auth/useAuth';
import { AdminDashboardView } from '../components/dashboard/AdminDashboardView';
import { StudentDashboardView } from '../components/dashboard/StudentDashboardView';
import { TeacherDashboardView } from '../components/dashboard/TeacherDashboardView';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useDashboardQuery } from '../hooks/useDashboard';
import { ROLE_LABEL } from '../lib/labels';
import type { Dashboard } from '../types';

function DashboardBody({ data }: { data: Dashboard }) {
  switch (data.role) {
    case 'admin':
    case 'hod':
      return <AdminDashboardView data={data} />;
    case 'teacher':
      return <TeacherDashboardView data={data} />;
    case 'student':
      return <StudentDashboardView data={data} />;
  }
}

/** `/`: the role-specific dashboard (FR-7.1–FR-7.4). */
export function DashboardPage() {
  const { user } = useAuth();
  const query = useDashboardQuery();
  if (user === null) return null; // ProtectedRoute only renders this when logged in

  const linked = user.teacher ?? user.student;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">
          Welcome, {linked ? `${linked.first_name} ${linked.last_name}` : user.username}
        </h1>
        <p className="mt-1 text-slate-500">{ROLE_LABEL[user.role]} dashboard</p>
      </div>
      {query.isPending ? (
        <LoadingSpinner label="Loading dashboard…" />
      ) : query.isError ? (
        <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DashboardBody data={query.data} />
      )}
    </div>
  );
}
