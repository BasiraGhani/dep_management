import type { ExportResource } from '../types';
import { api } from './client';
import type { CourseFilters } from './courses';
import type { StudentFilters } from './students';
import type { TeacherFilters } from './teachers';

/** Filters accepted by the export; those that don't apply to the resource are ignored. */
export type ExportFilters = Omit<StudentFilters & TeacherFilters & CourseFilters, 'skip' | 'limit'>;

export interface CsvFile {
  filename: string;
  blob: Blob;
}

/** GET /export/{resource}.csv with the list's current filters (admin and HOD). */
export async function exportCsv(
  resource: ExportResource,
  filters: ExportFilters = {},
): Promise<CsvFile> {
  const { data } = await api.get<Blob>(`/export/${resource}.csv`, {
    params: filters,
    responseType: 'blob',
  });
  return { filename: `${resource}.csv`, blob: data };
}
