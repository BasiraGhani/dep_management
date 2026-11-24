import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createCourse,
  deleteCourse,
  getCourse,
  listCourses,
  updateCourse,
  type CourseFilters,
} from '../api/courses';
import type { CourseCreate, CourseUpdate } from '../types';
import { departmentKeys } from './useDepartments';
import { teacherKeys } from './useTeachers';

export const courseKeys = {
  all: ['courses'] as const,
  list: (params: CourseFilters) => ['courses', 'list', params] as const,
  detail: (id: number) => ['courses', 'detail', id] as const,
};

export function useCoursesQuery(params: CourseFilters) {
  return useQuery({
    queryKey: courseKeys.list(params),
    queryFn: () => listCourses(params),
    placeholderData: keepPreviousData,
  });
}

/** `roster` is null when the user may not see this course's enrollments. */
export function useCourseQuery(id: number) {
  return useQuery({ queryKey: courseKeys.detail(id), queryFn: () => getCourse(id) });
}

/** Course changes also change department course lists and teachers' courses. */
function useInvalidateCourses() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: courseKeys.all }),
      queryClient.invalidateQueries({ queryKey: departmentKeys.all }),
      queryClient.invalidateQueries({ queryKey: teacherKeys.all }),
    ]);
  };
}

export function useCreateCourse() {
  const invalidate = useInvalidateCourses();
  return useMutation({
    mutationFn: (body: CourseCreate) => createCourse(body),
    onSuccess: invalidate,
  });
}

export function useUpdateCourse(id: number) {
  const invalidate = useInvalidateCourses();
  return useMutation({
    mutationFn: (body: CourseUpdate) => updateCourse(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteCourse() {
  const invalidate = useInvalidateCourses();
  return useMutation({ mutationFn: (id: number) => deleteCourse(id), onSuccess: invalidate });
}
