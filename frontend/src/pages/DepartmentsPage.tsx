import { useState } from 'react';
import { Link } from 'react-router';

import { useRole } from '../auth/useRole';
import { DataTable, type Column } from '../components/DataTable';
import { DepartmentFormModal } from '../components/departments/DepartmentFormModal';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { SearchInput } from '../components/SearchInput';
import { useDepartmentsQuery } from '../hooks/useDepartments';
import type { DepartmentOut } from '../types';

const PAGE_SIZE = 20;

const columns: Column<DepartmentOut>[] = [
  {
    key: 'code',
    header: 'Code',
    render: (d) => (
      <Link to={`/departments/${d.id}`} className="font-medium text-blue-700 hover:underline">
        {d.code}
      </Link>
    ),
  },
  { key: 'name', header: 'Name', render: (d) => d.name },
  { key: 'building', header: 'Building', render: (d) => d.building ?? '—' },
  { key: 'phone', header: 'Phone', render: (d) => d.phone ?? '—' },
];

export function DepartmentsPage() {
  const { isAdmin } = useRole();
  const [search, setSearch] = useState('');
  const [skip, setSkip] = useState(0);
  const [creating, setCreating] = useState(false);
  const query = useDepartmentsQuery({ search: search || undefined, skip, limit: PAGE_SIZE });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Departments</h1>
        {isAdmin && (
          <button
            type="button"
            onClick={() => {
              setCreating(true);
            }}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            New department
          </button>
        )}
      </div>

      <SearchInput
        label="Search departments"
        placeholder="Search by name or code…"
        onSearch={(value) => {
          setSearch(value);
          setSkip(0);
        }}
      />

      {query.isPending ? (
        <LoadingSpinner label="Loading departments…" />
      ) : query.isError ? (
        <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          caption="Departments"
          columns={columns}
          rows={query.data.items}
          rowKey={(d) => d.id}
          emptyMessage={search ? `No departments match "${search}".` : 'No departments yet.'}
          page={{ skip, limit: PAGE_SIZE, total: query.data.total, onChange: setSkip }}
        />
      )}

      {isAdmin && (
        <DepartmentFormModal
          open={creating}
          canEditAll
          onClose={() => {
            setCreating(false);
          }}
        />
      )}
    </div>
  );
}
