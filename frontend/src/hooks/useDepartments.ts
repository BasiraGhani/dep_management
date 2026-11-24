import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createDepartment,
  deleteDepartment,
  getDepartment,
  listDepartments,
  updateDepartment,
} from '../api/departments';
import type { DepartmentCreate, DepartmentUpdate, ListParams } from '../types';

export const departmentKeys = {
  all: ['departments'] as const,
  list: (params: ListParams) => ['departments', 'list', params] as const,
  detail: (id: number) => ['departments', 'detail', id] as const,
};

export function useDepartmentsQuery(params: ListParams) {
  return useQuery({
    queryKey: departmentKeys.list(params),
    queryFn: () => listDepartments(params),
    placeholderData: keepPreviousData, // keep the table while the next page loads
  });
}

export function useDepartmentQuery(id: number, options: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: departmentKeys.detail(id),
    queryFn: () => getDepartment(id),
    enabled: options.enabled ?? true,
  });
}

/** After any change, every departments query (lists and details) is refetched. */
function useInvalidateDepartments() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: departmentKeys.all });
}

export function useCreateDepartment() {
  const invalidate = useInvalidateDepartments();
  return useMutation({
    mutationFn: (body: DepartmentCreate) => createDepartment(body),
    onSuccess: invalidate,
  });
}

export function useUpdateDepartment(id: number) {
  const invalidate = useInvalidateDepartments();
  return useMutation({
    mutationFn: (body: DepartmentUpdate) => updateDepartment(id, body),
    onSuccess: invalidate,
  });
}

export function useDeleteDepartment() {
  const invalidate = useInvalidateDepartments();
  return useMutation({
    mutationFn: (id: number) => deleteDepartment(id),
    onSuccess: invalidate,
  });
}
