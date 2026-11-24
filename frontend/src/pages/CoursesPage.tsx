import { useMemo, useState } from 'react';
import { Link } from 'react-router';

import { useRole } from '../auth/useRole';
import { CourseFormModal } from '../components/courses/CourseFormModal';
import { DataTable, type Column } from '../components/DataTable';
import { ErrorMessage } from '../components/ErrorMessage';
import { inputClass } from '../components/FormField';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { SearchInput } from '../components/SearchInput';
import { useCoursesQuery } from '../hooks/useCourses';
import { useDepartmentsQuery } from '../hooks/useDepartments';
import { useTeachersQuery } from '../hooks/useTeachers';
import type { CourseOut } from '../types';

const PAGE_SIZE = 20;

export function CoursesPage() {
  const { isAdmin, role, hodDepartmentId } = useRole();
  const [search, setSearch] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [teacherId, setTeacherId] = useState('');
  const [skip, setSkip] = useState(0);
  const [creating, setCreating] = useState(false);
  const departments = useDepartmentsQuery({ limit: 100 });
  // The teacher filter lists the teachers of the chosen department (all if none).
  const teachers = useTeachersQuery({
    department_id: departmentId ? Number(departmentId) : undefined,
    limit: 100,
  });
  const allTeachers = useTeachersQuery({ limit: 100 });
  const query = useCoursesQuery({
    search: search || undefined,
    department_id: departmentId ? Number(departmentId) : undefined,
    teacher_id: teacherId ? Number(teacherId) : undefined,
    skip,
    limit: PAGE_SIZE,
  });
  const canCreate = isAdmin || role === 'hod';

  const columns = useMemo<Column<CourseOut>[]>(() => {
    const codeOf = new Map(departments.data?.items.map((d) => [d.id, d.code]));
    const nameOf = new Map(
      allTeachers.data?.items.map((t) => [t.id, `${t.first_name} ${t.last_name}`]),
    );
    return [
      {
        key: 'code',
        header: 'Code',
        render: (c) => (
          <Link to={`/courses/${c.id}`} className="font-medium text-blue-700 hover:underline">
            {c.code}
          </Link>
        ),
      },
      { key: 'title', header: 'Title', render: (c) => c.title },
      {
        key: 'department',
        header: 'Department',
        render: (c) => codeOf.get(c.department_id) ?? '—',
      },
      {
        key: 'teacher',
        header: 'Teacher',
        render: (c) => (c.teacher_id === null ? 'Unassigned' : (nameOf.get(c.teacher_id) ?? '—')),
      },
      { key: 'credits', header: 'Credits', render: (c) => c.credits },
      { key: 'capacity', header: 'Capacity', render: (c) => c.capacity },
    ];
  }, [departments.data, allTeachers.data]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold text-slate-800">Courses</h1>
        {canCreate && (
          <button
            type="button"
            onClick={() => {
              setCreating(true);
            }}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
          >
            New course
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput
          label="Search courses"
          placeholder="Search by code or title…"
          onSearch={(value) => {
            setSearch(value);
            setSkip(0);
          }}
        />
        <label className="sr-only" htmlFor="course-department-filter">
          Department
        </label>
        <select
          id="course-department-filter"
          value={departmentId}
          onChange={(e) => {
            setDepartmentId(e.target.value);
            setTeacherId(''); // the chosen teacher may not be in the new department
            setSkip(0);
          }}
          className={`${inputClass} w-auto`}
        >
          <option value="">All departments</option>
          {departments.data?.items.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} — {d.name}
            </option>
          ))}
        </select>
        <label className="sr-only" htmlFor="course-teacher-filter">
          Teacher
        </label>
        <select
          id="course-teacher-filter"
          value={teacherId}
          onChange={(e) => {
            setTeacherId(e.target.value);
            setSkip(0);
          }}
          className={`${inputClass} w-auto`}
        >
          <option value="">All teachers</option>
          {teachers.data?.items.map((t) => (
            <option key={t.id} value={t.id}>
              {t.first_name} {t.last_name}
            </option>
          ))}
        </select>
      </div>

      {query.isPending ? (
        <LoadingSpinner label="Loading courses…" />
      ) : query.isError ? (
        <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />
      ) : (
        <DataTable
          caption="Courses"
          columns={columns}
          rows={query.data.items}
          rowKey={(c) => c.id}
          emptyMessage={
            search || departmentId || teacherId
              ? 'No courses match these filters.'
              : 'No courses yet.'
          }
          page={{ skip, limit: PAGE_SIZE, total: query.data.total, onChange: setSkip }}
        />
      )}

      {canCreate && (
        <CourseFormModal
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
