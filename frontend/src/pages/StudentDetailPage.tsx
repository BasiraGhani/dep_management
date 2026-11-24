import { useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { useRole } from '../auth/useRole';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { StudentFormModal, type StudentFormMode } from '../components/students/StudentFormModal';
import { useToast } from '../components/useToast';
import { useDepartmentQuery } from '../hooks/useDepartments';
import { useDeleteStudent, useStudentQuery } from '../hooks/useStudents';
import { STATUS_LABEL } from '../lib/labels';
import { EmptyState } from '../components/EmptyState';

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-slate-800 wrap-anywhere">{children}</dd>
    </div>
  );
}

export function StudentDetailPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const toast = useToast();
  const { isAdmin, role, hodDepartmentId } = useRole();
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const query = useStudentQuery(id);
  const departmentId = query.data?.department_id;
  const department = useDepartmentQuery(departmentId ?? 0, { enabled: departmentId !== undefined });
  const remove = useDeleteStudent();

  if (query.isPending) return <LoadingSpinner label="Loading student…" />;
  if (query.isError) {
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  }
  const student = query.data;
  const name = `${student.first_name} ${student.last_name}`;

  // Admins manage every student, a HOD those of their own department (FR-4.1).
  let manageMode: StudentFormMode | null = null;
  if (isAdmin) manageMode = 'admin';
  else if (role === 'hod' && student.department_id === hodDepartmentId) manageMode = 'hod';

  const enrollmentCount = student.enrollments.length;
  const onDelete = async () => {
    try {
      await remove.mutateAsync(student.id);
      toast.success(`${name} deleted`);
      await navigate('/students', { replace: true });
    } catch (error) {
      // e.g. 409: "Student can't be deleted: they have a login account (...)"
      toast.error(errorMessage(error, 'Could not delete the student.'));
    } finally {
      setConfirmingDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/students" className="text-sm text-blue-700 hover:underline">
            ← Students
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-800">{name}</h1>
          <p className="text-slate-600">
            {student.student_no} · Year {student.year} · {STATUS_LABEL[student.status]}
          </p>
        </div>
        {manageMode && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setEditing(true);
              }}
              className="rounded border border-slate-300 bg-white px-4 py-2 hover:bg-slate-50"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => {
                setConfirmingDelete(true);
              }}
              className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        )}
      </div>

      <dl className="grid gap-4 rounded-lg border bg-white p-4 sm:grid-cols-3">
        <Field label="Department">
          {department.data ? (
            <Link
              to={`/departments/${department.data.id}`}
              className="text-blue-700 hover:underline"
            >
              {department.data.name}
            </Link>
          ) : (
            '—'
          )}
        </Field>
        <Field label="Email">
          <a href={`mailto:${student.email}`} className="text-blue-700 hover:underline">
            {student.email}
          </a>
        </Field>
        <Field label="Phone">{student.phone ?? '—'}</Field>
        <Field label="Date of birth">{student.date_of_birth ?? '—'}</Field>
        <Field label="Enrolled since">{student.enrollment_date}</Field>
        <Field label="Login account">
          {student.user_id === null ? 'No account' : 'Has a login account'}
        </Field>
      </dl>

      <section aria-labelledby="enrollments-heading" className="space-y-2">
        <div className="flex items-baseline justify-between">
          <h2 id="enrollments-heading" className="text-lg font-semibold text-slate-800">
            Enrollments and grades
          </h2>
          <p className="text-slate-700">
            GPA: <strong>{student.gpa === null ? 'not graded yet' : student.gpa.toFixed(2)}</strong>
          </p>
        </div>
        {enrollmentCount === 0 ? (
          <EmptyState>Not enrolled in any courses yet.</EmptyState>
        ) : (
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="min-w-full divide-y text-sm">
              <caption className="sr-only">Enrollments and grades</caption>
              <thead className="bg-slate-50 text-left">
                <tr>
                  <th scope="col" className="px-4 py-2">
                    Course
                  </th>
                  <th scope="col" className="px-4 py-2">
                    Semester
                  </th>
                  <th scope="col" className="px-4 py-2">
                    Credits
                  </th>
                  <th scope="col" className="px-4 py-2">
                    Grade
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {student.enrollments.map((e) => (
                  <tr key={e.id}>
                    <td className="px-4 py-2">
                      <Link
                        to={`/courses/${e.course.id}`}
                        className="text-blue-700 hover:underline"
                      >
                        {e.course.code} {e.course.title}
                      </Link>
                    </td>
                    <td className="px-4 py-2">{e.semester}</td>
                    <td className="px-4 py-2">{e.course.credits}</td>
                    <td className="px-4 py-2">{e.grade ?? 'Not graded'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {manageMode && (
        <StudentFormModal
          open={editing}
          mode={manageMode}
          student={student}
          hodDepartmentId={hodDepartmentId}
          onClose={() => {
            setEditing(false);
          }}
        />
      )}
      <ConfirmDialog
        open={confirmingDelete}
        title={`Delete ${name}?`}
        message={
          enrollmentCount === 0
            ? `${name} will be deleted. This can't be undone.`
            : `${name} and their ${enrollmentCount} enrollment${enrollmentCount === 1 ? '' : 's'} (with grades) will be deleted. This can't be undone.`
        }
        pending={remove.isPending}
        onConfirm={() => void onDelete()}
        onCancel={() => {
          setConfirmingDelete(false);
        }}
      />
    </div>
  );
}
