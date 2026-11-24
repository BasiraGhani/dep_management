import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { useRole } from '../auth/useRole';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { TeacherFormModal, type TeacherFormMode } from '../components/teachers/TeacherFormModal';
import { useToast } from '../components/useToast';
import { useDepartmentQuery } from '../hooks/useDepartments';
import { useDeleteTeacher, useTeacherQuery } from '../hooks/useTeachers';
import { TITLE_LABEL } from '../lib/labels';
import { isFullTeacher } from '../types';
import { EmptyState } from '../components/EmptyState';

export function TeacherDetailPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const toast = useToast();
  const { isAdmin, role, teacherId, hodDepartmentId } = useRole();
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const query = useTeacherQuery(id);
  const departmentId = query.data?.department_id;
  const department = useDepartmentQuery(departmentId ?? 0, { enabled: departmentId !== undefined });
  const remove = useDeleteTeacher();

  if (query.isPending) return <LoadingSpinner label="Loading teacher…" />;
  if (query.isError) {
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  }
  const teacher = query.data;
  const name = `${teacher.first_name} ${teacher.last_name}`;

  // Which edit form (if any) this user gets; the backend checks the same rules.
  let editMode: TeacherFormMode | null = null;
  if (isAdmin) editMode = 'admin';
  else if (role === 'hod' && teacher.department_id === hodDepartmentId) editMode = 'hod';
  else if (teacherId === teacher.id) editMode = 'self';

  const onDelete = async () => {
    try {
      await remove.mutateAsync(teacher.id);
      toast.success(`${name} deleted`);
      await navigate('/teachers', { replace: true });
    } catch (error) {
      // e.g. 409: "Teacher can't be deleted: they head department CS and teach 1 course"
      toast.error(errorMessage(error, 'Could not delete the teacher.'));
    } finally {
      setConfirmingDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/teachers" className="text-sm text-blue-700 hover:underline">
            ← Teachers
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-800">{name}</h1>
          <p className="text-slate-600">
            {TITLE_LABEL[teacher.title]}
            {department.data && (
              <>
                {' · '}
                <Link
                  to={`/departments/${department.data.id}`}
                  className="text-blue-700 hover:underline"
                >
                  {department.data.name}
                </Link>
              </>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {editMode && (
            <button
              type="button"
              onClick={() => {
                setEditing(true);
              }}
              className="rounded border border-slate-300 bg-white px-4 py-2 hover:bg-slate-50"
            >
              {editMode === 'self' ? 'Edit my contact details' : 'Edit'}
            </button>
          )}
          {isAdmin && (
            <button
              type="button"
              onClick={() => {
                setConfirmingDelete(true);
              }}
              className="rounded bg-red-600 px-4 py-2 text-white hover:bg-red-700"
            >
              Delete
            </button>
          )}
        </div>
      </div>

      <dl className="grid gap-4 rounded-lg border bg-white p-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-slate-500">Email</dt>
          <dd>
            <a href={`mailto:${teacher.email}`} className="text-blue-700 hover:underline">
              {teacher.email}
            </a>
          </dd>
        </div>
        {isFullTeacher(teacher) && (
          <>
            <div>
              <dt className="text-sm text-slate-500">Phone</dt>
              <dd>{teacher.phone ?? '—'}</dd>
            </div>
            <div>
              <dt className="text-sm text-slate-500">Hire date</dt>
              <dd>{teacher.hire_date ?? '—'}</dd>
            </div>
            {'user_id' in teacher && (
              <div>
                <dt className="text-sm text-slate-500">Login account</dt>
                <dd>{teacher.user_id === null ? 'No account' : 'Has a login account'}</dd>
              </div>
            )}
          </>
        )}
      </dl>

      <section aria-labelledby="taught-heading">
        <h2 id="taught-heading" className="mb-2 text-lg font-semibold text-slate-800">
          Courses taught
        </h2>
        {teacher.courses.length === 0 ? (
          <EmptyState>Not teaching any courses yet.</EmptyState>
        ) : (
          <ul className="divide-y rounded-lg border bg-white">
            {teacher.courses.map((c) => (
              <li key={c.id} className="flex justify-between px-4 py-2">
                <Link to={`/courses/${c.id}`} className="text-blue-700 hover:underline">
                  {c.code} {c.title}
                </Link>
                <span className="text-sm text-slate-500">{c.credits} credits</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {editMode && isFullTeacher(teacher) && (
        <TeacherFormModal
          open={editing}
          mode={editMode}
          teacher={teacher}
          hodDepartmentId={hodDepartmentId}
          onClose={() => {
            setEditing(false);
          }}
        />
      )}
      <ConfirmDialog
        open={confirmingDelete}
        title={`Delete ${name}?`}
        message={`${name} will be deleted. This can't be undone.`}
        pending={remove.isPending}
        onConfirm={() => void onDelete()}
        onCancel={() => {
          setConfirmingDelete(false);
        }}
      />
    </div>
  );
}
