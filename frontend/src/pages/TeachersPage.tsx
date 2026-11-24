import { useMemo, useState } from 'react';
import { Link } from 'react-router';

import { useRole } from '../auth/useRole';
import { DataTable, type Column } from '../components/DataTable';
import { ErrorMessage } from '../components/ErrorMessage';
import { ExportCsvButton } from '../components/ExportCsvButton';
import { filterClass } from '../components/FormField';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { SearchInput } from '../components/SearchInput';
import { TeacherFormModal } from '../components/teachers/TeacherFormModal';
import { useDepartmentsQuery } from '../hooks/useDepartments';
import { useTeachersQuery } from '../hooks/useTeachers';
import { TITLE_LABEL } from '../lib/labels';
import { isFullTeacher, type TeacherPublicOut, type TeacherTitle } from '../types';

const PAGE_SIZE = 20;
const TITLES = Object.keys(TITLE_LABEL) as TeacherTitle[];

export function TeachersPage() {
  const { isAdmin, role, hodDepartmentId } = useRole();
  const [search, setSearch] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [title, setTitle] = useState('');
  const [skip, setSkip] = useState(0);
  const [creating, setCreating] = useState(false);
  const departments = useDepartmentsQuery({ limit: 100 });
  const filters = {
    search: search || undefined,
    department_id: departmentId ? Number(departmentId) : undefined,
    title: (title || undefined) as TeacherTitle | undefined,
  };
  const query = useTeachersQuery({ ...filters, skip, limit: PAGE_SIZE });
  const canCreate = isAdmin || role === 'hod';

  const columns = useMemo(() => {
    const codeOf = new Map(departments.data?.items.map((d) => [d.id, d.code]));
    const base: Column<TeacherPublicOut>[] = [
      {
        key: 'name',
        header: 'Name',
        render: (t) => (
          <Link to={`/teachers/${t.id}`} className="font-medium text-blue-700 hover:underline">
            {t.first_name} {t.last_name}
          </Link>
        ),
      },
      { key: 'title', header: 'Title', render: (t) => TITLE_LABEL[t.title] },
      {
        key: 'department',
        header: 'Department',
        render: (t) => codeOf.get(t.department_id) ?? '—',
      },
      { key: 'email', header: 'Email', render: (t) => t.email },
    ];
    // Students get the public shape, without phone numbers.
    const staffView = query.data?.items.some(isFullTeacher) ?? false;
    if (staffView) {
      base.push({
        key: 'phone',
        header: 'Phone',
        render: (t) => (isFullTeacher(t) ? (t.phone ?? '—') : '—'),
      });
    }
    return base;
  }, [departments.data, query.data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Teachers</h1>
        <div className="flex flex-wrap gap-2">
          <ExportCsvButton resource="teachers" filters={filters} />
          {canCreate && (
            <button
              type="button"
              onClick={() => {
                setCreating(true);
              }}
              className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
            >
              New teacher
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          label="Search teachers"
          placeholder="Search by name or email…"
          onSearch={(value) => {
            setSearch(value);
            setSkip(0);
          }}
        />
        <label className="sr-only" htmlFor="teacher-department-filter">
          Department
        </label>
        <select
          id="teacher-department-filter"
          value={departmentId}
          onChange={(e) => {
            setDepartmentId(e.target.value);
            setSkip(0);
          }}
          className={filterClass}
        >
          <option value="">All departments</option>
          {departments.data?.items.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} — {d.name}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="teacher-title-filter">
          Title
        </label>
        <select
          id="teacher-title-filter"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
            setSkip(0);
          }}
          className={filterClass}
        >
          <option value="">All titles</option>
          {TITLES.map((t) => (
            <option key={t} value={t}>
              {TITLE_LABEL[t]}
            </option>
          ))}
        </select>
      </div>

      {query.isPending ? (
        <LoadingSpinner label="Loading teachers…" />
      ) : query.isError ? (
        <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          caption="Teachers"
          columns={columns}
          rows={query.data.items}
          rowKey={(t) => t.id}
          emptyMessage={
            search || departmentId || title
              ? 'No teachers match these filters.'
              : 'No teachers yet.'
          }
          page={{ skip, limit: PAGE_SIZE, total: query.data.total, onChange: setSkip }}
        />
      )}

      {canCreate && (
        <TeacherFormModal
          open={creating}
          mode={isAdmin ? 'admin' : 'hod'}
          hodDepartmentId={hodDepartmentId}
          onClose={() => {
            setCreating(false);
          }}
        />
      )}
    </div>
  );
}
