import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

import type { DepartmentStudents } from '../../types';
import { EmptyState } from '../EmptyState';

/**
 * FR-7.1 bar chart. The chart is drawn for sighted users; the same figures are
 * in a visually hidden table for screen readers (and tests).
 */
export function StudentsPerDepartmentChart({ data }: { data: DepartmentStudents[] }) {
  return (
    <section aria-labelledby="per-dept-heading" className="rounded-lg border bg-white p-4">
      <h2 id="per-dept-heading" className="mb-3 text-lg font-semibold text-slate-800">
        Students per department
      </h2>
      {data.length === 0 ? (
        <EmptyState>No departments yet.</EmptyState>
      ) : (
        <>
          <div className="h-64" aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="code" />
                <YAxis allowDecimals={false} />
                <Tooltip
                  labelFormatter={(code: unknown) =>
                    data.find((d) => d.code === code)?.name ??
                    (typeof code === 'string' ? code : '')
                  }
                />
                <Bar dataKey="students" name="Students" fill="#1d4ed8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="sr-only">
            <caption>Students per department</caption>
            <thead>
              <tr>
                <th scope="col">Department</th>
                <th scope="col">Students</th>
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.department_id}>
                  <td>
                    {d.name} ({d.code})
                  </td>
                  <td>{d.students}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
