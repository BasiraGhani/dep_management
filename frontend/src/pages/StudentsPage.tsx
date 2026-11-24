import { useMemo, useState } from 'react';
import { Link } from 'react-router';

import { useRole } from '../auth/useRole';
import { DataTable, type Column } from '../components/DataTable';
import { ErrorMessage } from '../components/ErrorMessage';
import { inputClass } from '../components/FormField';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { SearchInput } from '../components/SearchInput';
import { StudentFormModal } from '../components/students/StudentFormModal';
import { useDepartmentsQuery } from '../hooks/useDepartments';
import { useStudentsQuery } from '../hooks/useStudents';
import { STATUS_LABEL } from '../lib/labels';
import type { StudentOut, StudentStatus } from '../types';

const PAGE_SIZE = 20;
const STATUSES = Object.keys(STATUS_LABEL) as StudentStatus[];

function Filter(props: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: [value: string, label: string][];
}) {
  return (
    <>
      <label className="sr-only" htmlFor={props.id}>
        {props.label}
      </label>
      <select
        id={props.id}
        value={props.value}
        onChange={(e) => {
          props.onChange(e.target.value);
        }}
        className={`${inputClass} w-auto`}
      >
        {props.options.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </>
  );
}

export function StudentsPage() {
  const { isAdmin, role, hodDepartmentId } = useRole();
  const [search, setSearch] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [year, setYear] = useState('');
  const [status, setStatus] = useState('');
  const [skip, setSkip] = useState(0);
  const [creating, setCreating] = useState(false);
  const departments = useDepartmentsQuery({ limit: 100 });
  const query = useStudentsQuery({
    search: search || undefined,
    department_id: departmentId ? Number(departmentId) : undefined,
    year: year ? Number(year) : undefined,
    status: (status || undefined) as StudentStatus | undefined,
    skip,
    limit: PAGE_SIZE,
  });
  const canCreate = isAdmin || role === 'hod';
  const filtering = Boolean(search || departmentId || year || status);

  const columns = useMemo<Column<StudentOut>[]>(() => {
    const codeOf = new Map(departments.data?.items.map((d) => [d.id, d.code]));
    return [
      {
        key: 'student_no',
        header: 'Student no.',
        render: (s) => (
          <Link to={`/students/${s.id}`} className="font-medium text-blue-700 hover:underline">
            {s.student_no}
          </Link>
        ),
      },
      { key: 'name', header: 'Name', render: (s) => `${s.first_name} ${s.last_name}` },
      {
        key: 'department',
        header: 'Department',
        render: (s) => codeOf.get(s.department_id) ?? '—',
      },
      { key: 'year', header: 'Year', render: (s) => s.year },
      { key: 'status', header: 'Status', render: (s) => STATUS_LABEL[s.status] },
      { key: 'email', header: 'Email', render: (s) => s.email },
    ];
  }, [departments.data]);

  const resetTo = (setter: (v: string) => void) => (value: string) => {
    setter(value);
    setSkip(0);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Students</h1>
        {canCreate && (
          <button
            type="button"
            onClick={() => {
              setCreating(true);
            }}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            New student
          </button>
        )}
      </div>
      {role === 'teacher' && (
        <p className="text-sm text-slate-500">Showing students enrolled in your courses.</p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          label="Search students"
          placeholder="Search by name, email or number…"
          onSearch={resetTo(setSearch)}
        />
        <Filter
          id="student-department-filter"
          label="Department"
          value={departmentId}
          onChange={resetTo(setDepartmentId)}
          options={[
            ['', 'All departments'],
            ...(departments.data?.items.map((d): [string, string] => [
              String(d.id),
              `${d.code} — ${d.name}`,
            ]) ?? []),
          ]}
        />
        <Filter
          id="student-year-filter"
          label="Year"
          value={year}
          onChange={resetTo(setYear)}
          options={[
            ['', 'All years'],
            ...[1, 2, 3, 4, 5, 6].map((y): [string, string] => [String(y), `Year ${y}`]),
          ]}
        />
        <Filter
          id="student-status-filter"
          label="Status"
          value={status}
          onChange={resetTo(setStatus)}
          options={[
            ['', 'All statuses'],
            ...STATUSES.map((s): [string, string] => [s, STATUS_LABEL[s]]),
          ]}
        />
      </div>

      {query.isPending ? (
        <LoadingSpinner label="Loading students…" />
      ) : query.isError ? (
        <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          caption="Students"
          columns={columns}
          rows={query.data.items}
          rowKey={(s) => s.id}
          emptyMessage={filtering ? 'No students match these filters.' : 'No students yet.'}
          page={{ skip, limit: PAGE_SIZE, total: query.data.total, onChange: setSkip }}
        />
      )}

      {canCreate && (
        <StudentFormModal
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
