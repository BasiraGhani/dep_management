import { useState } from 'react';

import { useEnroll } from '../../hooks/useEnrollments';
import { useStudentsQuery } from '../../hooks/useStudents';
import { errorMessage } from '../../api/client';
import type { CourseDetailOut } from '../../types';
import { filterClass } from '../FormField';
import { LoadingSpinner } from '../LoadingSpinner';
import { SearchInput } from '../SearchInput';
import { useToast } from '../useToast';
import { EmptyState } from '../EmptyState';

interface EnrollmentPanelProps {
  course: CourseDetailOut;
  semester: string;
  semesters: string[];
  onSemesterChange: (semester: string) => void;
}

/**
 * "Enroll student" for admins and the department's HOD: pick a semester, see the
 * capacity for it, search active students (BR-4) and enroll them. Refusals from
 * the server (full, duplicate, inactive) are shown in the panel as they are.
 */
export function EnrollmentPanel({
  course,
  semester,
  semesters,
  onSemesterChange,
}: EnrollmentPanelProps) {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const enroll = useEnroll();
  const students = useStudentsQuery({ search: search || undefined, status: 'active', limit: 10 });

  const roster = course.roster ?? [];
  const inSemester = roster.filter((r) => r.semester === semester);
  const enrolledIds = new Set(inSemester.map((r) => r.student_id));
  const full = inSemester.length >= course.capacity;

  const onEnroll = async (studentId: number, name: string) => {
    setProblem(null);
    try {
      await enroll.mutateAsync({ student_id: studentId, course_id: course.id, semester });
      toast.success(`${name} enrolled in ${course.code} for ${semester}`);
    } catch (error) {
      // e.g. "CS101 is full for 2026-Fall (40 / 40)", "… is already enrolled …",
      // "… is suspended; only active students can be enrolled"
      setProblem(errorMessage(error, 'Could not enroll the student.'));
    }
  };

  return (
    <section aria-labelledby="enroll-heading" className="space-y-3 rounded-lg border bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="enroll-heading" className="text-lg font-semibold text-slate-800">
          Enroll student
        </h2>
        <div className="flex items-center gap-3">
          <label htmlFor="enroll-semester" className="text-sm text-slate-600">
            Semester
          </label>
          <select
            id="enroll-semester"
            value={semester}
            onChange={(e) => {
              setProblem(null);
              onSemesterChange(e.target.value);
            }}
            className={filterClass}
          >
            {semesters.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <p
            aria-live="polite"
            className={`text-sm font-medium whitespace-nowrap ${full ? 'text-red-700' : 'text-slate-700'}`}
          >
            <span className="sr-only">Enrolled for {semester}: </span>
            {inSemester.length} / {course.capacity}
          </p>
        </div>
      </div>

      {full && (
        <p className="rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {course.code} is full for {semester}. Unenroll someone or raise the capacity to add more.
        </p>
      )}
      {problem && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">
          {problem}
        </p>
      )}

      <SearchInput
        label="Search active students"
        placeholder="Search by name, email or number…"
        onSearch={setSearch}
      />

      {students.isPending ? (
        <LoadingSpinner label="Searching students…" />
      ) : students.isError ? (
        <p role="alert" className="text-sm text-red-700">
          {errorMessage(students.error)}
        </p>
      ) : students.data.items.length === 0 ? (
        <EmptyState>No active students match this search.</EmptyState>
      ) : (
        <ul aria-label="Matching students" className="divide-y rounded border">
          {students.data.items.map((s) => {
            const name = `${s.first_name} ${s.last_name}`;
            const already = enrolledIds.has(s.id);
            return (
              <li key={s.id} className="flex items-center justify-between px-3 py-2">
                <span>
                  {name} <span className="text-sm text-slate-500">{s.student_no}</span>
                </span>
                {already ? (
                  <span className="text-sm text-slate-500">Already enrolled</span>
                ) : (
                  <button
                    type="button"
                    disabled={full || enroll.isPending}
                    aria-label={`Enroll ${name}`}
                    onClick={() => void onEnroll(s.id, name)}
                    className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Enroll
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
