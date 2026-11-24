import type { ReactNode } from 'react';

export type SortDirection = 'asc' | 'desc';

export interface SortState {
  key: string;
  direction: SortDirection;
}

export interface Column<T> {
  /** Unique key; also the sort key for sortable columns. */
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  /** Accessible name of the table, e.g. "Students". */
  caption: string;
  /** Paging (the API's `skip`/`limit`/`total`). Omit for an unpaged table. */
  page?: { skip: number; limit: number; total: number; onChange: (skip: number) => void };
  /** Controlled sorting: the table shows and reports it; the page decides what it means. */
  sort?: SortState;
  onSortChange?: (sort: SortState) => void;
  emptyMessage?: string;
}

function nextSort(current: SortState | undefined, key: string): SortState {
  if (current?.key === key) {
    return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' };
  }
  return { key, direction: 'asc' };
}

/** A table with sortable headers, an empty state and Previous/Next paging. */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
  page,
  sort,
  onSortChange,
  emptyMessage = 'Nothing to show.',
}: DataTableProps<T>) {
  const first = page ? page.skip + 1 : 1;
  const last = page ? Math.min(page.skip + rows.length, page.total) : rows.length;

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="bg-slate-50">
          <tr>
            {columns.map((column) => {
              const active = sort?.key === column.key;
              const ariaSort = active
                ? sort.direction === 'asc'
                  ? 'ascending'
                  : 'descending'
                : undefined;
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={column.sortable ? (ariaSort ?? 'none') : undefined}
                  className={`px-4 py-2 text-left font-semibold text-slate-700 ${column.className ?? ''}`}
                >
                  {column.sortable && onSortChange ? (
                    <button
                      type="button"
                      onClick={() => {
                        onSortChange(nextSort(sort, column.key));
                      }}
                      className="inline-flex items-center gap-1 hover:text-blue-700"
                    >
                      {column.header}
                      <span aria-hidden="true" className="text-xs text-slate-400">
                        {active ? (sort.direction === 'asc' ? '▲' : '▼') : '↕'}
                      </span>
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-500">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={rowKey(row)} className="hover:bg-slate-50">
                {columns.map((column) => (
                  <td key={column.key} className={`px-4 py-2 ${column.className ?? ''}`}>
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {page && page.total > 0 && (
        <nav
          aria-label="Pagination"
          className="flex items-center justify-between border-t px-4 py-2 text-sm text-slate-600"
        >
          <span>
            Showing {first}–{last} of {page.total}
          </span>
          <span className="flex gap-2">
            <button
              type="button"
              disabled={page.skip === 0}
              onClick={() => {
                page.onChange(Math.max(0, page.skip - page.limit));
              }}
              className="rounded border px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page.skip + page.limit >= page.total}
              onClick={() => {
                page.onChange(page.skip + page.limit);
              }}
              className="rounded border px-3 py-1 hover:bg-slate-50 disabled:opacity-50"
            >
              Next
            </button>
          </span>
        </nav>
      )}
    </div>
  );
}
