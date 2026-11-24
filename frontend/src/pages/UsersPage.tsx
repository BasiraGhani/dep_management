import { useState } from 'react';
import { Link } from 'react-router';

import type { UserFilters } from '../api/users';
import { errorMessage } from '../api/client';
import { useAuth } from '../auth/useAuth';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { DataTable, type Column } from '../components/DataTable';
import { ErrorMessage } from '../components/ErrorMessage';
import { filterClass } from '../components/FormField';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { SearchInput } from '../components/SearchInput';
import { TemporaryPasswordDialog } from '../components/users/TemporaryPasswordDialog';
import { UserFormModal } from '../components/users/UserFormModal';
import { useToast } from '../components/useToast';
import { useStudentQuery } from '../hooks/useStudents';
import { useTeacherQuery } from '../hooks/useTeachers';
import { useResetPassword, useUpdateUser, useUsersQuery } from '../hooks/useUsers';
import { ROLE_LABEL } from '../lib/labels';
import type { UserOut, UserRole } from '../types';

const PAGE_SIZE = 20;
const ROLES = Object.keys(ROLE_LABEL) as UserRole[];

function TeacherName({ id }: { id: number }) {
  const q = useTeacherQuery(id);
  return (
    <Link to={`/teachers/${String(id)}`} className="text-blue-700 hover:underline">
      {q.data ? `${q.data.first_name} ${q.data.last_name}` : `Teacher #${String(id)}`}
    </Link>
  );
}

function StudentName({ id }: { id: number }) {
  const q = useStudentQuery(id);
  return (
    <Link to={`/students/${String(id)}`} className="text-blue-700 hover:underline">
      {q.data ? `${q.data.first_name} ${q.data.last_name}` : `Student #${String(id)}`}
    </Link>
  );
}

type Pending = { kind: 'deactivate' | 'reset'; user: UserOut } | null;

/** `/users`: account management for admins (FR-8). */
export function UsersPage() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [role, setRole] = useState('');
  const [active, setActive] = useState('');
  const [skip, setSkip] = useState(0);
  const [creating, setCreating] = useState(false);
  const [pending, setPending] = useState<Pending>(null);
  const [revealed, setRevealed] = useState<{ username: string; password: string } | null>(null);
  const update = useUpdateUser();
  const reset = useResetPassword();

  const filters: UserFilters = {
    search: search || undefined,
    role: (role || undefined) as UserRole | undefined,
    is_active: active === '' ? undefined : active === 'active',
    skip,
    limit: PAGE_SIZE,
  };
  const query = useUsersQuery(filters);
  const filtering = Boolean(search || role || active);

  const setActiveState = async (user: UserOut, isActive: boolean) => {
    try {
      await update.mutateAsync({ id: user.id, body: { is_active: isActive } });
      toast.success(`${user.username} ${isActive ? 'reactivated' : 'deactivated'}`);
    } catch (error) {
      toast.error(errorMessage(error, 'Could not update the account.'));
    }
  };

  const onConfirm = async () => {
    if (!pending) return;
    const { kind, user } = pending;
    if (kind === 'deactivate') {
      await setActiveState(user, false);
    } else {
      try {
        const { temporary_password } = await reset.mutateAsync(user.id);
        setRevealed({ username: user.username, password: temporary_password });
      } catch (error) {
        toast.error(errorMessage(error, 'Could not reset the password.'));
      }
    }
    setPending(null);
  };

  const columns: Column<UserOut>[] = [
    {
      key: 'username',
      header: 'Username',
      render: (u) => (
        <span className="font-medium">
          {u.username}
          {u.id === me?.id && <span className="ml-1 text-slate-500">(you)</span>}
        </span>
      ),
    },
    { key: 'role', header: 'Role', render: (u) => ROLE_LABEL[u.role] },
    {
      key: 'linked',
      header: 'Linked record',
      render: (u) =>
        u.teacher_id !== null ? (
          <TeacherName id={u.teacher_id} />
        ) : u.student_id !== null ? (
          <StudentName id={u.student_id} />
        ) : (
          '—'
        ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (u) =>
        u.is_active ? (
          <span className="text-green-700">Active</span>
        ) : (
          <span className="text-red-700">Deactivated</span>
        ),
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (u) => (
        <div className="flex flex-wrap gap-2">
          {u.id !== me?.id &&
            (u.is_active ? (
              <button
                type="button"
                aria-label={`Deactivate ${u.username}`}
                onClick={() => {
                  setPending({ kind: 'deactivate', user: u });
                }}
                className="rounded border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50"
              >
                Deactivate
              </button>
            ) : (
              <button
                type="button"
                aria-label={`Reactivate ${u.username}`}
                disabled={update.isPending}
                onClick={() => void setActiveState(u, true)}
                className="rounded border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50"
              >
                Reactivate
              </button>
            ))}
          <button
            type="button"
            aria-label={`Reset password of ${u.username}`}
            onClick={() => {
              setPending({ kind: 'reset', user: u });
            }}
            className="rounded border border-slate-300 px-2 py-1 text-sm hover:bg-slate-50"
          >
            Reset password
          </button>
        </div>
      ),
    },
  ];

  const resetTo = (setter: (v: string) => void) => (value: string) => {
    setter(value);
    setSkip(0);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">User management</h1>
        <button
          type="button"
          onClick={() => {
            setCreating(true);
          }}
          className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
        >
          New account
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          label="Search users"
          placeholder="Search by username…"
          onSearch={resetTo(setSearch)}
        />
        <label className="sr-only" htmlFor="user-role-filter">
          Role
        </label>
        <select
          id="user-role-filter"
          value={role}
          onChange={(e) => {
            resetTo(setRole)(e.target.value);
          }}
          className={filterClass}
        >
          <option value="">All roles</option>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABEL[r]}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="user-status-filter">
          Status
        </label>
        <select
          id="user-status-filter"
          value={active}
          onChange={(e) => {
            resetTo(setActive)(e.target.value);
          }}
          className={filterClass}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Deactivated</option>
        </select>
      </div>

      {query.isPending ? (
        <LoadingSpinner label="Loading users…" />
      ) : query.isError ? (
        <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          caption="Users"
          columns={columns}
          rows={query.data.items}
          rowKey={(u) => u.id}
          emptyMessage={filtering ? 'No accounts match these filters.' : 'No accounts yet.'}
          page={{ skip, limit: PAGE_SIZE, total: query.data.total, onChange: setSkip }}
        />
      )}

      <UserFormModal
        open={creating}
        onClose={() => {
          setCreating(false);
        }}
      />
      <ConfirmDialog
        open={pending !== null}
        title={
          pending?.kind === 'reset'
            ? `Reset the password of ${pending.user.username}?`
            : `Deactivate ${pending?.user.username ?? ''}?`
        }
        message={
          pending?.kind === 'reset'
            ? 'Their current password stops working. You will see a temporary password once, to give to them.'
            : "They won't be able to sign in until the account is reactivated."
        }
        confirmLabel={pending?.kind === 'reset' ? 'Reset password' : 'Deactivate'}
        pending={update.isPending || reset.isPending}
        onConfirm={() => void onConfirm()}
        onCancel={() => {
          setPending(null);
        }}
      />
      <TemporaryPasswordDialog
        result={revealed}
        onClose={() => {
          setRevealed(null);
        }}
      />
    </div>
  );
}
