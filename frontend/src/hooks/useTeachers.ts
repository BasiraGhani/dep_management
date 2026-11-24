import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { listTeachers, type TeacherFilters } from '../api/teachers';

export const teacherKeys = {
  all: ['teachers'] as const,
  list: (params: TeacherFilters) => ['teachers', 'list', params] as const,
};

/** Teachers matching `params` (students get the public shape). */
export function useTeachersQuery(params: TeacherFilters, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: teacherKeys.list(params),
    queryFn: () => listTeachers(params),
    placeholderData: keepPreviousData,
    enabled: options.enabled ?? true,
  });
}
