import { useMutation, useQueryClient } from '@tanstack/react-query';

import { setCourseGrades } from '../api/courses';
import { enroll, unenroll } from '../api/enrollments';
import type { BulkGradeItem, EnrollmentCreate } from '../types';
import { courseKeys } from './useCourses';
import { dashboardKeys } from './useDashboard';
import { studentKeys } from './useStudents';

/** Enrolling and grading change the course roster, students' grades and GPA, and dashboards. */
function useInvalidateEnrollments() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: courseKeys.all }),
      queryClient.invalidateQueries({ queryKey: studentKeys.all }),
      queryClient.invalidateQueries({ queryKey: ['enrollments'] }),
      queryClient.invalidateQueries({ queryKey: dashboardKeys.all }),
    ]);
  };
}

export function useEnroll() {
  const invalidate = useInvalidateEnrollments();
  return useMutation({
    mutationFn: (body: EnrollmentCreate) => enroll(body),
    onSuccess: invalidate,
  });
}

export function useUnenroll() {
  const invalidate = useInvalidateEnrollments();
  return useMutation({ mutationFn: (id: number) => unenroll(id), onSuccess: invalidate });
}

/** PUT /courses/{id}/grades (FR-6.7). All-or-nothing on the server. */
export function useSetCourseGrades(courseId: number) {
  const invalidate = useInvalidateEnrollments();
  return useMutation({
    mutationFn: (rows: BulkGradeItem[]) => setCourseGrades(courseId, rows),
    onSuccess: invalidate,
  });
}
