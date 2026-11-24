import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { useRole } from '../auth/useRole';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { DepartmentFormModal } from '../components/departments/DepartmentFormModal';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useToast } from '../components/useToast';
import { useDeleteDepartment, useDepartmentQuery } from '../hooks/useDepartments';
import { useTeachersQuery } from '../hooks/useTeachers';
import { TITLE_LABEL } from '../lib/labels';

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="text-2xl font-semibold text-slate-800">{value}</div>
      <div className="text-sm text-slate-500">{label}</div>
    </div>
  );
}

export function DepartmentDetailPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const toast = useToast();
  const { isAdmin, headsDepartment } = useRole();
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const query = useDepartmentQuery(id);
  const teachers = useTeachersQuery({ department_id: id, limit: 100 });
  const remove = useDeleteDepartment();

  if (query.isPending) return <LoadingSpinner label="Loading department…" />;
  if (query.isError) {
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  }
  const department = query.data;
  const canEdit = isAdmin || headsDepartment(department.head_id);

  const onDelete = async () => {
    try {
      await remove.mutateAsync(department.id);
      toast.success(`Department ${department.code} deleted`);
      await navigate('/departments', { replace: true });
    } catch (error) {
      // e.g. 409: "Department CS can't be deleted while it has 4 teachers, ..."
      toast.error(errorMessage(error, 'Could not delete the department.'));
    } finally {
      setConfirmingDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/departments" className="text-sm text-blue-700 hover:underline">
            ← Departments
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-800">
            {department.name} ({department.code})
          </h1>
          {department.description && (
            <p className="mt-1 text-slate-600">{department.description}</p>
          )}
          <p className="mt-1 text-sm text-slate-500">
            {department.building ?? 'No building'} · {department.phone ?? 'No phone'}
          </p>
        </div>
        <div className="flex gap-2">
          {canEdit && (
            <button
              type="button"
              onClick={() => {
                setEditing(true);
              }}
              className="rounded border border-slate-300 bg-white px-4 py-2 hover:bg-slate-50"
            >
              Edit
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

      <section aria-labelledby="head-heading" className="rounded-lg border bg-white p-4">
        <h2 id="head-heading" className="text-sm font-medium text-slate-500">
          Head of department
        </h2>
        <p className="mt-1 text-slate-800">
          {department.head ? (
            <Link to={`/teachers/${department.head.id}`} className="text-blue-700 hover:underline">
              {department.head.first_name} {department.head.last_name},{' '}
              {TITLE_LABEL[department.head.title]}
            </Link>
          ) : (
            'No head appointed'
          )}
        </p>
      </section>

      <section aria-label="Summary" className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat label="Teachers" value={department.teacher_count} />
        <Stat label="Students" value={department.student_count} />
        <Stat label="Courses" value={department.course_count} />
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <section aria-labelledby="courses-heading">
          <h2 id="courses-heading" className="mb-2 text-lg font-semibold text-slate-800">
            Courses
          </h2>
          {department.courses.length === 0 ? (
            <p className="text-slate-500">No courses yet.</p>
          ) : (
            <ul className="divide-y rounded-lg border bg-white">
              {department.courses.map((c) => (
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

        <section aria-labelledby="teachers-heading">
          <h2 id="teachers-heading" className="mb-2 text-lg font-semibold text-slate-800">
            Teachers
          </h2>
          {teachers.isPending ? (
            <LoadingSpinner label="Loading teachers…" />
          ) : teachers.isError ? (
            <ErrorMessage error={teachers.error} onRetry={() => void teachers.refetch()} />
          ) : teachers.data.items.length === 0 ? (
            <p className="text-slate-500">No teachers yet.</p>
          ) : (
            <ul className="divide-y rounded-lg border bg-white">
              {teachers.data.items.map((t) => (
                <li key={t.id} className="flex justify-between px-4 py-2">
                  <Link to={`/teachers/${t.id}`} className="text-blue-700 hover:underline">
                    {t.first_name} {t.last_name}
                  </Link>
                  <span className="text-sm text-slate-500">{TITLE_LABEL[t.title]}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {canEdit && (
        <DepartmentFormModal
          open={editing}
          department={department}
          canEditAll={isAdmin}
          onClose={() => {
            setEditing(false);
          }}
        />
      )}
      <ConfirmDialog
        open={confirmingDelete}
        title={`Delete ${department.code}?`}
        message={`${department.name} will be deleted. This can't be undone.`}
        pending={remove.isPending}
        onConfirm={() => void onDelete()}
        onCancel={() => {
          setConfirmingDelete(false);
        }}
      />
    </div>
  );
}
