import { useEffect, useMemo, useState } from 'react';
import { Link, useBlocker, useParams } from 'react-router';

import { errorMessage } from '../api/client';
import { useRole } from '../auth/useRole';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ErrorMessage } from '../components/ErrorMessage';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { useToast } from '../components/useToast';
import { useCourseQuery } from '../hooks/useCourses';
import { useSetCourseGrades } from '../hooks/useEnrollments';
import { GRADES } from '../lib/labels';
import { compareSemesters } from '../lib/semesters';
import type { CourseDetailOut, Grade, RosterEntry } from '../types';

const ALL = '';
const NOT_GRADED = '';

/** Unsaved grade changes, keyed by enrollment id (null = clear the grade). */
type Edits = Record<number, Grade | null>;

const plural = (n: number, word: string) => `${String(n)} ${word}${n === 1 ? '' : 's'}`;

/** `/courses/:id/grades`: bulk grade entry (FR-6.7). */
export function GradeEntryPage() {
  const id = Number(useParams().id);
  const query = useCourseQuery(id);

  if (query.isPending) return <LoadingSpinner label="Loading course…" />;
  if (query.isError) {
    return <ErrorMessage error={query.error} onRetry={() => void query.refetch()} />;
  }
  return <GradeEntry course={query.data} />;
}

function GradeEntry({ course }: { course: CourseDetailOut }) {
  const { isAdmin, role, teacherId, hodDepartmentId } = useRole();
  // Admin, the HOD of the course's department, or its teacher (REQUIREMENTS §3).
  const canGrade =
    course.roster !== null &&
    (isAdmin ||
      (role === 'hod' && course.department_id === hodDepartmentId) ||
      (teacherId !== null && course.teacher_id === teacherId));
  const title = `${course.code} ${course.title}`;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/courses/${String(course.id)}`}
          className="text-sm text-blue-700 hover:underline"
        >
          ← {title}
        </Link>
        <h1 className="mt-1 text-2xl font-semibold text-slate-800">Grades: {title}</h1>
      </div>
      {canGrade && course.roster ? (
        <GradeTable course={course} roster={course.roster} />
      ) : (
        <p className="rounded-lg border bg-white p-4 text-slate-600">
          You can only enter grades for courses you teach or courses of the department you head.
        </p>
      )}
    </div>
  );
}

function GradeTable({ course, roster }: { course: CourseDetailOut; roster: RosterEntry[] }) {
  const toast = useToast();
  const save = useSetCourseGrades(course.id);
  const semesters = useMemo(
    () => Array.from(new Set(roster.map((r) => r.semester))).sort((a, b) => compareSemesters(b, a)),
    [roster],
  );
  // Newest semester first: that's usually the one being graded.
  const [semester, setSemester] = useState<string>(semesters[0] ?? ALL);
  const [edits, setEdits] = useState<Edits>({});
  const [saveError, setSaveError] = useState<string | null>(null);

  const saved = useMemo(() => new Map(roster.map((r) => [r.enrollment_id, r.grade])), [roster]);
  // Only changes to students still on the roster count (and are sent).
  const changes = Object.entries(edits)
    .map(([enrollmentId, grade]) => ({ enrollment_id: Number(enrollmentId), grade }))
    .filter((c) => saved.has(c.enrollment_id) && saved.get(c.enrollment_id) !== c.grade);
  const dirty = changes.length > 0;

  const rows = semester === ALL ? roster : roster.filter((r) => r.semester === semester);
  const gradeOf = (r: RosterEntry) => (r.enrollment_id in edits ? edits[r.enrollment_id] : r.grade);
  const ungradedShown = rows.filter((r) => gradeOf(r) === null).length;

  // Warn before leaving with unsaved changes: in-app navigation…
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      dirty && currentLocation.pathname !== nextLocation.pathname,
  );
  // …and reloading or closing the tab.
  useEffect(() => {
    if (!dirty) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
    };
  }, [dirty]);

  const setGrade = (entry: RosterEntry, value: string) => {
    const grade = value === NOT_GRADED ? null : (value as Grade);
    setSaveError(null);
    setEdits((current) => {
      // Back to the saved grade: no longer a change.
      const others = Object.entries(current).filter(([key]) => Number(key) !== entry.enrollment_id);
      return Object.fromEntries<Grade | null>(
        grade === entry.grade ? others : [...others, [entry.enrollment_id, grade]],
      );
    });
  };

  const onSave = async () => {
    setSaveError(null);
    try {
      await save.mutateAsync(changes);
      setEdits({});
      toast.success(`Saved ${plural(changes.length, 'grade')} for ${course.code}`);
    } catch (error) {
      // All-or-nothing on the server: nothing was saved, and the edits stay here.
      setSaveError(
        `${errorMessage(error, 'Could not save the grades.')} Your changes have not been saved; they are still here.`,
      );
    }
  };

  if (roster.length === 0) {
    return (
      <p className="rounded-lg border bg-white p-4 text-slate-600">
        No students are enrolled in {course.code} yet, so there is nothing to grade.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <label htmlFor="grade-semester" className="block text-sm font-medium text-slate-700">
            Semester
          </label>
          <select
            id="grade-semester"
            value={semester}
            onChange={(e) => {
              setSemester(e.target.value);
            }}
            className="mt-1 rounded border border-slate-300 px-3 py-2"
          >
            {semesters.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
            <option value={ALL}>All semesters</option>
          </select>
        </div>
        <p className="text-sm text-slate-600">
          {plural(rows.length, 'student')} · {ungradedShown} not graded
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="min-w-full divide-y text-sm">
          <caption className="sr-only">Grades for {course.code}</caption>
          <thead className="bg-slate-50 text-left">
            <tr>
              <th scope="col" className="px-4 py-2">
                Student no.
              </th>
              <th scope="col" className="px-4 py-2">
                Name
              </th>
              <th scope="col" className="px-4 py-2">
                Semester
              </th>
              <th scope="col" className="px-4 py-2">
                Grade
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((r) => {
              const name = `${r.first_name} ${r.last_name}`;
              const changed = r.enrollment_id in edits;
              return (
                <tr key={r.enrollment_id} className={changed ? 'bg-amber-50' : undefined}>
                  <td className="px-4 py-2">{r.student_no}</td>
                  <td className="px-4 py-2">{name}</td>
                  <td className="px-4 py-2">{r.semester}</td>
                  <td className="px-4 py-2">
                    <select
                      aria-label={`Grade for ${name} (${r.semester})`}
                      value={gradeOf(r) ?? NOT_GRADED}
                      onChange={(e) => {
                        setGrade(r, e.target.value);
                      }}
                      className="rounded border border-slate-300 px-2 py-1"
                    >
                      <option value={NOT_GRADED}>Not graded</option>
                      {GRADES.map((g) => (
                        <option key={g} value={g}>
                          {g}
                        </option>
                      ))}
                    </select>
                    {changed && <span className="ml-2 text-xs text-amber-700">Unsaved</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {saveError && (
        <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-red-700">
          {saveError}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-end gap-3">
        <p className="text-sm text-slate-600" aria-live="polite">
          {dirty ? plural(changes.length, 'unsaved change') : 'No unsaved changes'}
        </p>
        <button
          type="button"
          disabled={!dirty || save.isPending}
          onClick={() => {
            setEdits({});
            setSaveError(null);
          }}
          className="rounded border border-slate-300 bg-white px-4 py-2 hover:bg-slate-50 disabled:opacity-50"
        >
          Discard changes
        </button>
        <button
          type="button"
          disabled={!dirty || save.isPending}
          onClick={() => void onSave()}
          className="rounded bg-blue-700 px-4 py-2 text-white hover:bg-blue-800 disabled:opacity-50"
        >
          {save.isPending ? 'Saving…' : 'Save all'}
        </button>
      </div>

      <ConfirmDialog
        open={blocker.state === 'blocked'}
        title="Leave without saving?"
        message={`You have ${plural(changes.length, 'unsaved grade change')}. If you leave now, they will be lost.`}
        confirmLabel="Leave without saving"
        onConfirm={() => {
          blocker.proceed?.();
        }}
        onCancel={() => {
          blocker.reset?.();
        }}
      />
    </div>
  );
}
