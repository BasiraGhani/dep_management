import { useMutation } from '@tanstack/react-query';

import { browser } from '../api/browser';
import { exportCsv, type ExportFilters } from '../api/export';
import type { ExportResource } from '../types';

/** FR-9.1: download a list as CSV with its current filters. */
export function useExportCsv(resource: ExportResource) {
  return useMutation({
    mutationFn: async (filters: ExportFilters) => {
      const file = await exportCsv(resource, filters);
      browser.download(file.blob, file.filename);
      return file;
    },
  });
}
