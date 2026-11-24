import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { useRole } from '../auth/useRole';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { CourseFormModal, type CourseFormMode } from '../components/courses/CourseFormModal';
import { EnrollmentPanel } from '../components/courses/EnrollmentPanel';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useToast } from '../components/useToast';
import { useCourseQuery, useDeleteCourse } from '../hooks/useCourses';
import { useDepartmentQuery } from '../hooks/useDepartments';
import { useUnenroll } from '../hooks/useEnrollments';
import { TITLE_LABEL } from '../lib/labels';
import { currentSemester, semesterOptions } from '../lib/semesters';
import type { RosterEntry } from '../types';

export function CourseDetailPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const toast = useToast();
  const { isAdmin, isStudent, role, teacherId, hodDepartmentId } = useRole();
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [semester, setSemester] = useState(currentSemester);
  const [unenrolling, setUnenrolling] = useState<RosterEntry | null>(null);
  const query = useCourseQuery(id);
  const unenroll = useUnenroll();
  const departmentId = query.data?.department_id;
  const department = useDepartmentQuery(departmentId ?? 0, { enabled: departmentId !== undefined });
  const remove = useDeleteCourse();

  if (query.isPending) return <LoadingSpinner label="Loading course…" />;
  if (query.isError) {
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  }
  const course = query.data;

  // Who may change this course (the backend checks the same rules).
  let editMode: CourseFormMode | null = null;
  if (isAdmin) editMode = 'admin';
  else if (role === 'hod' && course.department_id === hodDepartmentId) editMode = 'hod';
  else if (teacherId !== null && course.teacher_id === teacherId) editMode = 'teacher';
  const canDelete = editMode === 'admin' || editMode === 'hod';
  // Enrollments: admins and the HOD of the course's department (§3).
  const canManageEnrollments = canDelete && course.roster !== null;
  const semesters = Array.from(
    new Set([...semesterOptions(), ...(course.roster ?? []).map((r) => r.semester)]),
  ).sort((a, b) => a.localeCompare(b));

  const onUnenroll = async (entry: RosterEntry) => {
    const name = `${entry.first_name} ${entry.last_name}`;
    try {
      await unenroll.mutateAsync(entry.enrollment_id);
      toast.success(`${name} unenrolled from ${course.code} (${entry.semester})`);
    } catch (error) {
      toast.error(errorMessage(error, 'Could not unenroll the student.'));
    } finally {
      setUnenrolling(null);
    }
  };

  const onDelete = async () => {
    try {
      await remove.mutateAsync(course.id);
      toast.success(`Course ${course.code} deleted`);
      await navigate('/courses', { replace: true });
    } catch (error) {
      // e.g. 409: "Course CS101 can't be deleted while it has 18 enrollments."
      toast.error(errorMessage(error, 'Could not delete the course.'));
    } finally {
      setConfirmingDelete(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/courses" className="text-sm text-blue-700 hover:underline">
            ← Courses
          </Link>
          <h1 className="mt-1 text-2xl font-semibold text-slate-800">
            {course.code} {course.title}
          </h1>
          <p className="text-slate-600">
            {course.credits} credits · capacity {course.capacity}
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
              {editMode === 'teacher' ? 'Edit description' : 'Edit'}
            </button>
          )}
          {canDelete && (
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
          <dt className="text-sm text-slate-500">Teacher</dt>
          <dd>
            {course.teacher ? (
              <Link to={`/teachers/${course.teacher.id}`} className="text-blue-700 hover:underline">
                {course.teacher.first_name} {course.teacher.last_name},{' '}
                {TITLE_LABEL[course.teacher.title]}
              </Link>
            ) : (
              'No teacher assigned'
            )}
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-500">Description</dt>
          <dd className="whitespace-pre-line">{course.description ?? 'No description.'}</dd>
        </div>
      </dl>

      {canManageEnrollments && (
        <EnrollmentPanel
          course={course}
          semester={semester}
          semesters={semesters}
          onSemesterChange={setSemester}
        />
      )}

      {course.roster !== null ? (
        <section aria-labelledby="roster-heading" className="space-y-2">
          <h2 id="roster-heading" className="text-lg font-semibold text-slate-800">
            Enrolled students ({course.roster.length})
          </h2>
          {course.roster.length === 0 ? (
            <p className="text-slate-500">No students enrolled yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border bg-white">
              <table className="min-w-full divide-y text-sm">
                <caption className="sr-only">Enrolled students and grades</caption>
                <thead className="bg-slate-50 text-left">
                  <tr>
                    <th scope="col" className="px-4 py-2">
                      Student
                    </th>
                    <th scope="col" className="px-4 py-2">
                      Student no.
                    </th>
                    <th scope="col" className="px-4 py-2">
                      Semester
                    </th>
                    <th scope="col" className="px-4 py-2">
                      Grade
                    </th>
                    {canManageEnrollments && (
                      <th scope="col" className="px-4 py-2">
                        <span className="sr-only">Actions</span>
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {course.roster.map((r) => (
                    <tr key={r.enrollment_id}>
                      <td className="px-4 py-2">
                        <Link
                          to={`/students/${r.student_id}`}
                          className="text-blue-700 hover:underline"
                        >
                          {r.first_name} {r.last_name}
                        </Link>
                      </td>
                      <td className="px-4 py-2">{r.student_no}</td>
                      <td className="px-4 py-2">{r.semester}</td>
                      <td className="px-4 py-2">{r.grade ?? 'Not graded'}</td>
                      {canManageEnrollments && (
                        <td className="px-4 py-2 text-right">
                          <button
                            type="button"
                            aria-label={`Unenroll ${r.first_name} ${r.last_name} (${r.semester})`}
                            onClick={() => {
                              setUnenrolling(r);
                            }}
                            className="text-sm text-red-700 hover:underline"
                          >
                            Unenroll
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        !isStudent && (
          <p className="text-sm text-slate-500">
            The class list is visible to the course&apos;s teacher, the head of department and
            admins.
          </p>
        )
      )}

      {editMode && (
        <CourseFormModal
          open={editing}
          mode={editMode}
          course={course}
          hodDepartmentId={hodDepartmentId}
          onClose={() => {
            setEditing(false);
          }}
        />
      )}
      <ConfirmDialog
        open={unenrolling !== null}
        title="Unenroll student?"
        confirmLabel="Unenroll"
        message={
          unenrolling &&
          `${unenrolling.first_name} ${unenrolling.last_name} will be removed from ${course.code} for ${unenrolling.semester}${unenrolling.grade ? `, including their grade (${unenrolling.grade})` : ''}.`
        }
        pending={unenroll.isPending}
        onConfirm={() => {
          if (unenrolling) void onUnenroll(unenrolling);
        }}
        onCancel={() => {
          setUnenrolling(null);
        }}
      />
      <ConfirmDialog
        open={confirmingDelete}
        title={`Delete ${course.code}?`}
        message={`${course.code} ${course.title} will be deleted. This can't be undone.`}
        pending={remove.isPending}
        onConfirm={() => void onDelete()}
        onCancel={() => {
          setConfirmingDelete(false);
        }}
      />
    </div>
  );
}
