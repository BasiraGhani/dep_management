import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createStudent,
  deleteStudent,
  getStudent,
  listStudents,
  updateStudent,
  type StudentFilters,
} from '../api/students';
import type { StudentCreate, StudentUpdate } from '../types';
import { departmentKeys } from './useDepartments';

export const studentKeys = {
  all: ['students'] as const,
  list: (params: StudentFilters) => ['students', 'list', params] as const,
  detail: (id: number) => ['students', 'detail', id] as const,
};

/** Students the user may see (the backend scopes the list by role). */
export function useStudentsQuery(params: StudentFilters) {
  return useQuery({
    queryKey: studentKeys.list(params),
    queryFn: () => listStudents(params),
    placeholderData: keepPreviousData,
  });
}

export function useStudentQuery(id: number) {
  return useQuery({ queryKey: studentKeys.detail(id), queryFn: () => getStudent(id) });
}

/** Student changes also change department counts and enrollment lists. */
function useInvalidateStudents() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: studentKeys.all }),
      queryClient.invalidateQueries({ queryKey: departmentKeys.all }),
      queryClient.invalidateQueries({ queryKey: ['enrollments'] }),
    ]);
  };
}

export function useCreateStudent() {
  const invalidate = useInvalidateStudents();
  return useMutation({
    mutationFn: (body: StudentCreate) => createStudent(body),
    onSuccess: invalidate,
  });
}

export function useUpdateStudent(id: number) {
  const invalidate = useInvalidateStudents();
  return useMutation({
    mutationFn: (body: StudentUpdate) => updateStudent(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteStudent() {
  const invalidate = useInvalidateStudents();
  return useMutation({ mutationFn: (id: number) => deleteStudent(id), onSuccess: invalidate });
}
