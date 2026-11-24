import { useMutation, useQueryClient } from '@tanstack/react-query';

import { enroll, unenroll } from '../api/enrollments';
import type { EnrollmentCreate } from '../types';
import { courseKeys } from './useCourses';
import { dashboardKeys } from './useDashboard';
import { studentKeys } from './useStudents';

/** Enrolling changes the course roster, the student's enrollments and dashboards. */
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
