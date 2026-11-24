import { Link } from 'react-router';

import type { EnrollmentOut } from '../../types';

/** FR-7.1: the latest enrollments, newest first (the backend sends at most 10). */
export function RecentEnrollments({ enrollments }: { enrollments: EnrollmentOut[] }) {
  return (
    <section aria-labelledby="recent-heading" className="rounded-lg border bg-white p-4">
      <h2 id="recent-heading" className="mb-3 text-lg font-semibold text-slate-800">
        Recent enrollments
      </h2>
      {enrollments.length === 0 ? (
        <p className="text-slate-500">No enrollments yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y text-sm">
            <caption className="sr-only">Recent enrollments</caption>
            <thead className="text-left text-slate-500">
              <tr>
                <th scope="col" className="py-2 pr-4">
                  Student
                </th>
                <th scope="col" className="py-2 pr-4">
                  Course
                </th>
                <th scope="col" className="py-2 pr-4">
                  Semester
                </th>
                <th scope="col" className="py-2">
                  Enrolled on
                </th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {enrollments.map((e) => (
                <tr key={e.id}>
                  <td className="py-2 pr-4">
                    <Link
                      to={`/students/${e.student.id}`}
                      className="text-blue-700 hover:underline"
                    >
                      {e.student.first_name} {e.student.last_name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">
                    <Link to={`/courses/${e.course.id}`} className="text-blue-700 hover:underline">
                      {e.course.code} {e.course.title}
                    </Link>
                  </td>
                  <td className="py-2 pr-4">{e.semester}</td>
                  <td className="py-2">{e.created_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
