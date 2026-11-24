import { lazy, Suspense } from 'react';
import { Link } from 'react-router';

import type { AdminDashboard, HodDashboard } from '../../types';
import { LoadingSpinner } from '../LoadingSpinner';
import { RecentEnrollments } from './RecentEnrollments';
import { StatCard, StatGrid } from './StatCard';

// Recharts is large and only admins and HODs see a chart: load it on demand.
const StudentsPerDepartmentChart = lazy(() =>
  import('./StudentsPerDepartmentChart').then((m) => ({ default: m.StudentsPerDepartmentChart })),
);

/** FR-7.1 (admin, everything) and FR-7.2 (HOD, their own department). */
export function AdminDashboardView({ data }: { data: AdminDashboard | HodDashboard }) {
  if (data.role === 'hod' && data.department === null) {
    return (
      <p className="rounded-lg border bg-white p-4 text-slate-600">
        You don't head a department at the moment, so there are no department figures to show.
      </p>
    );
  }
  const { totals } = data;
  return (
    <div className="space-y-6">
      {data.role === 'hod' && data.department && (
        <p className="text-slate-600">
          Figures for{' '}
          <Link to={`/departments/${data.department.id}`} className="text-blue-700 hover:underline">
            {data.department.name} ({data.department.code})
          </Link>
        </p>
      )}
      <StatGrid>
        {data.role === 'admin' && (
          <StatCard label="Departments" value={totals.departments} to="/departments" />
        )}
        <StatCard label="Teachers" value={totals.teachers} to="/teachers" />
        <StatCard label="Students" value={totals.students} to="/students" />
        <StatCard label="Courses" value={totals.courses} to="/courses" />
      </StatGrid>
      <div className="grid gap-6 lg:grid-cols-2">
        <Suspense fallback={<LoadingSpinner label="Loading chart…" />}>
          <StudentsPerDepartmentChart data={data.students_per_department} />
        </Suspense>
        <RecentEnrollments enrollments={data.recent_enrollments} />
      </div>
    </div>
  );
}
