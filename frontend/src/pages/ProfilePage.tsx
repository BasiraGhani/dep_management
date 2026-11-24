import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';

import { useAuth } from '../auth/useAuth';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ChangePasswordForm } from '../components/profile/ChangePasswordForm';
import { StudentFormModal } from '../components/students/StudentFormModal';
import { TeacherFormModal } from '../components/teachers/TeacherFormModal';
import { useDepartmentQuery } from '../hooks/useDepartments';
import { useStudentQuery } from '../hooks/useStudents';
import { useTeacherQuery } from '../hooks/useTeachers';
import { ROLE_LABEL, STATUS_LABEL, TITLE_LABEL } from '../lib/labels';
import { isFullTeacher } from '../types';

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="text-slate-800 wrap-anywhere">{children}</dd>
    </div>
  );
}

function DepartmentName({ id }: { id: number }) {
  const department = useDepartmentQuery(id);
  return department.data ? (
    <Link to={`/departments/${String(id)}`} className="text-blue-700 hover:underline">
      {department.data.name}
    </Link>
  ) : (
    '—'
  );
}

function EditContactButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border border-slate-300 bg-white px-4 py-2 hover:bg-slate-50"
    >
      Edit my contact details
    </button>
  );
}

function RecordCard({
  title,
  action,
  children,
}: {
  title: string;
  action: ReactNode;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby="record-heading" className="rounded-lg border bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 id="record-heading" className="text-lg font-semibold text-slate-800">
          {title}
        </h2>
        {action}
      </div>
      <dl className="grid gap-4 sm:grid-cols-3">{children}</dl>
    </section>
  );
}

/** A teacher's or HOD's own record: phone and email are editable (REQUIREMENTS §3). */
function MyTeacherRecord({ id }: { id: number }) {
  const query = useTeacherQuery(id);
  const [editing, setEditing] = useState(false);
  if (query.isPending) return <LoadingSpinner label="Loading your record…" />;
  if (query.isError)
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  const t = query.data;
  // Your own record always comes back in the staff shape; this narrows the type.
  if (!isFullTeacher(t)) return null;
  return (
    <>
      <RecordCard
        title="My teacher record"
        action={
          <EditContactButton
            onClick={() => {
              setEditing(true);
            }}
          />
        }
      >
        <Field label="Name">
          {t.first_name} {t.last_name}
        </Field>
        <Field label="Title">{TITLE_LABEL[t.title]}</Field>
        <Field label="Department">
          <DepartmentName id={t.department_id} />
        </Field>
        <Field label="Email">{t.email}</Field>
        <Field label="Phone">{t.phone ?? '—'}</Field>
        <Field label="Hire date">{t.hire_date ?? '—'}</Field>
      </RecordCard>
      <TeacherFormModal
        open={editing}
        mode="self"
        teacher={t}
        onClose={() => {
          setEditing(false);
        }}
      />
    </>
  );
}

/** A student's own record: phone and email are editable (REQUIREMENTS §3). */
function MyStudentRecord({ id }: { id: number }) {
  const query = useStudentQuery(id);
  const [editing, setEditing] = useState(false);
  if (query.isPending) return <LoadingSpinner label="Loading your record…" />;
  if (query.isError)
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  const s = query.data;
  return (
    <>
      <RecordCard
        title="My student record"
        action={
          <EditContactButton
            onClick={() => {
              setEditing(true);
            }}
          />
        }
      >
        <Field label="Name">
          {s.first_name} {s.last_name}
        </Field>
        <Field label="Student number">{s.student_no}</Field>
        <Field label="Department">
          <DepartmentName id={s.department_id} />
        </Field>
        <Field label="Year of study">Year {s.year}</Field>
        <Field label="Status">{STATUS_LABEL[s.status]}</Field>
        <Field label="Enrolled since">{s.enrollment_date}</Field>
        <Field label="Email">{s.email}</Field>
        <Field label="Phone">{s.phone ?? '—'}</Field>
        <Field label="Date of birth">{s.date_of_birth ?? '—'}</Field>
      </RecordCard>
      <StudentFormModal
        open={editing}
        mode="self"
        student={s}
        onClose={() => {
          setEditing(false);
        }}
      />
    </>
  );
}

/** `/profile`: your account, your linked record (contact fields editable) and password (FR-1.6). */
export function ProfilePage() {
  const { user } = useAuth();
  if (user === null) return null; // ProtectedRoute only renders this when logged in

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold text-slate-800">My profile</h1>

      <section aria-labelledby="account-heading" className="rounded-lg border bg-white p-4">
        <h2 id="account-heading" className="mb-3 text-lg font-semibold text-slate-800">
          Account
        </h2>
        <dl className="grid gap-4 sm:grid-cols-3">
          <Field label="Username">{user.username}</Field>
          <Field label="Role">{ROLE_LABEL[user.role]}</Field>
          <Field label="Member since">{user.created_at.slice(0, 10)}</Field>
        </dl>
      </section>

      {user.teacher_id !== null ? (
        <MyTeacherRecord id={user.teacher_id} />
      ) : user.student_id !== null ? (
        <MyStudentRecord id={user.student_id} />
      ) : (
        <p className="text-sm text-slate-500">
          This account isn't linked to a teacher or student record.
        </p>
      )}

      <ChangePasswordForm />
    </div>
  );
}
