import { Link } from 'react-router';

import { compareSemesters } from '../../lib/semesters';
import type { StudentDashboard } from '../../types';
import { StatCard, StatGrid } from './StatCard';

/** FR-7.4: the student's enrollments with grades, and their GPA. */
export function StudentDashboardView({ data }: { data: StudentDashboard }) {
  // Newest semester first; the backend sends them in enrollment order.
  const enrollments = [...data.enrollments].sort((a, b) =>
    compareSemesters(b.semester, a.semester),
  );
  const ungraded = data.enrollments.filter((e) => e.grade === null).length;
  return (
    <div className="space-y-6">
      <StatGrid>
        <StatCard label="GPA" value={data.gpa === null ? '—' : data.gpa.toFixed(2)} />
        <StatCard label="Graded credits" value={data.graded_credits} />
        <StatCard label="Courses taken" value={data.enrollments.length} />
        <StatCard label="Awaiting a grade" value={ungraded} />
      </StatGrid>
      {data.gpa === null && data.enrollments.length > 0 && (
        <p className="text-sm text-slate-500">Your GPA appears once a course has been graded.</p>
      )}
      <section aria-labelledby="my-enrollments-heading" className="rounded-lg border bg-white p-4">
        <h2 id="my-enrollments-heading" className="mb-3 text-lg font-semibold text-slate-800">
          My enrollments and grades
        </h2>
        {enrollments.length === 0 ? (
          <p className="text-slate-500">You aren't enrolled in any course yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y text-sm">
              <caption className="sr-only">My enrollments and grades</caption>
              <thead className="text-left text-slate-500">
                <tr>
                  <th scope="col" className="py-2 pr-4">
                    Course
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Semester
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Credits
                  </th>
                  <th scope="col" className="py-2">
                    Grade
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {enrollments.map((e) => (
                  <tr key={e.id}>
                    <td className="py-2 pr-4">
                      <Link
                        to={`/courses/${e.course.id}`}
                        className="text-blue-700 hover:underline"
                      >
                        {e.course.code} {e.course.title}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">{e.semester}</td>
                    <td className="py-2 pr-4">{e.course.credits}</td>
                    <td className="py-2">
                      {e.grade ?? <span className="text-slate-500">Not graded</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
