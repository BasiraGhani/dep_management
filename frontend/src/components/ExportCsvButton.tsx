import { errorMessage } from '../api/client';
import type { ExportFilters } from '../api/export';
import { useRole } from '../auth/useRole';
import { useExportCsv } from '../hooks/useExport';
import type { ExportResource } from '../types';
import { useToast } from './useToast';

interface ExportCsvButtonProps {
  resource: ExportResource;
  /** The list's current filters (without paging): the export uses the same ones. */
  filters: ExportFilters;
}

/**
 * "Export CSV" for admins and HODs (FR-9.1). A HOD's export holds only their
 * own department's rows (the backend enforces it); the button says so.
 */
export function ExportCsvButton({ resource, filters }: ExportCsvButtonProps) {
  const { isAdmin, role } = useRole();
  const toast = useToast();
  const exporter = useExportCsv(resource);
  if (!isAdmin && role !== 'hod') return null;

  const onClick = async () => {
    try {
      await exporter.mutateAsync(filters);
    } catch (error) {
      toast.error(errorMessage(error, 'Could not export the list.'));
    }
  };
  const hint =
    role === 'hod'
      ? "Only your department's rows, with the current filters"
      : 'With the current filters';
  return (
    <button
      type="button"
      onClick={() => void onClick()}
      disabled={exporter.isPending}
      title={hint}
      aria-describedby={`${resource}-export-hint`}
      className="rounded border border-slate-300 bg-white px-4 py-2 font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
    >
      {exporter.isPending ? 'Exporting…' : 'Export CSV'}
      <span id={`${resource}-export-hint`} className="sr-only">
        {hint}
      </span>
    </button>
  );
}
