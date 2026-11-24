import { Link } from 'react-router';

import type { TeacherDashboard } from '../../types';
import { StatCard, StatGrid } from './StatCard';
import { EmptyState } from '../EmptyState';

/** FR-7.3: the teacher's courses with enrolled and ungraded counts (all semesters). */
export function TeacherDashboardView({ data }: { data: TeacherDashboard }) {
  const enrolled = data.courses.reduce((sum, c) => sum + c.enrolled, 0);
  const ungraded = data.courses.reduce((sum, c) => sum + c.ungraded, 0);
  return (
    <div className="space-y-6">
      <StatGrid>
        <StatCard label="My courses" value={data.courses.length} />
        <StatCard label="Enrollments" value={enrolled} />
        <StatCard label="Still to grade" value={ungraded} />
      </StatGrid>
      <section aria-labelledby="my-courses-heading" className="rounded-lg border bg-white p-4">
        <h2 id="my-courses-heading" className="mb-3 text-lg font-semibold text-slate-800">
          My courses
        </h2>
        {data.courses.length === 0 ? (
          <EmptyState>You aren't teaching any courses yet.</EmptyState>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y text-sm">
              <caption className="sr-only">My courses</caption>
              <thead className="text-left text-slate-500">
                <tr>
                  <th scope="col" className="py-2 pr-4">
                    Course
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Credits
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Enrolled
                  </th>
                  <th scope="col" className="py-2 pr-4">
                    Ungraded
                  </th>
                  <th scope="col" className="py-2">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.courses.map(({ course, capacity, enrolled: n, ungraded: todo }) => (
                  <tr key={course.id}>
                    <td className="py-2 pr-4">
                      <Link to={`/courses/${course.id}`} className="text-blue-700 hover:underline">
                        {course.code} {course.title}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">{course.credits}</td>
                    <td className="py-2 pr-4">
                      {n} / {capacity}
                    </td>
                    <td className="py-2 pr-4">
                      {todo === 0 ? (
                        <span className="text-green-700">All graded</span>
                      ) : (
                        <span className="font-medium text-amber-700">{todo}</span>
                      )}
                    </td>
                    <td className="py-2">
                      {n > 0 && (
                        <Link
                          to={`/courses/${course.id}/grades`}
                          className="text-blue-700 hover:underline"
                          aria-label={`Enter grades for ${course.code}`}
                        >
                          Enter grades
                        </Link>
                      )}
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
