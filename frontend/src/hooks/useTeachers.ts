import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createTeacher,
  deleteTeacher,
  getTeacher,
  listTeachers,
  updateTeacher,
  type TeacherFilters,
} from '../api/teachers';
import type { TeacherCreate, TeacherUpdate } from '../types';
import { departmentKeys } from './useDepartments';

export const teacherKeys = {
  all: ['teachers'] as const,
  list: (params: TeacherFilters) => ['teachers', 'list', params] as const,
  detail: (id: number) => ['teachers', 'detail', id] as const,
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

export function useTeacherQuery(id: number) {
  return useQuery({ queryKey: teacherKeys.detail(id), queryFn: () => getTeacher(id) });
}

/** Teacher changes also change department counts and head lists. */
function useInvalidateTeachers() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: teacherKeys.all }),
      queryClient.invalidateQueries({ queryKey: departmentKeys.all }),
    ]);
  };
}

export function useCreateTeacher() {
  const invalidate = useInvalidateTeachers();
  return useMutation({
    mutationFn: (body: TeacherCreate) => createTeacher(body),
    onSuccess: invalidate,
  });
}

export function useUpdateTeacher(id: number) {
  const invalidate = useInvalidateTeachers();
  return useMutation({
    mutationFn: (body: TeacherUpdate) => updateTeacher(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteTeacher() {
  const invalidate = useInvalidateTeachers();
  return useMutation({ mutationFn: (id: number) => deleteTeacher(id), onSuccess: invalidate });
}
