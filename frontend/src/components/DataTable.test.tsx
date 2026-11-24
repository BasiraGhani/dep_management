import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { DataTable, type Column } from './DataTable';

interface Row {
  id: number;
  code: string;
  title: string;
}

const columns: Column<Row>[] = [
  { key: 'code', header: 'Code', render: (r) => r.code, sortable: true },
  { key: 'title', header: 'Title', render: (r) => r.title },
];
const rows: Row[] = [
  { id: 1, code: 'CS101', title: 'Programming' },
  { id: 2, code: 'CS201', title: 'Data Structures' },
];

describe('DataTable', () => {
  it('renders the headers and one row per item', () => {
    render(<DataTable caption="Courses" columns={columns} rows={rows} rowKey={(r) => r.id} />);

    const table = screen.getByRole('table', { name: 'Courses' });
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((h) => h.textContent),
    ).toEqual(['Code', 'Title']); // no onSortChange: plain headers, no dead sort arrows
    expect(within(table).queryByRole('button')).not.toBeInTheDocument();
    expect(within(table).getAllByRole('row')).toHaveLength(3);
    expect(screen.getByRole('cell', { name: 'Data Structures' })).toBeInTheDocument();
  });

  it('shows the empty message when there are no rows', () => {
    render(
      <DataTable
        caption="Courses"
        columns={columns}
        rows={[]}
        rowKey={(r) => r.id}
        emptyMessage="No courses yet."
      />,
    );

    expect(screen.getByRole('cell', { name: 'No courses yet.' })).toBeInTheDocument();
  });

  it('pages through results', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <DataTable
        caption="Courses"
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        page={{ skip: 0, limit: 2, total: 5, onChange }}
      />,
    );

    expect(screen.getByText('Showing 1–2 of 5')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    expect(onChange).toHaveBeenLastCalledWith(2);

    rerender(
      <DataTable
        caption="Courses"
        columns={columns}
        rows={rows.slice(0, 1)}
        rowKey={(r) => r.id}
        page={{ skip: 4, limit: 2, total: 5, onChange }}
      />,
    );
    expect(screen.getByText('Showing 5–5 of 5')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Previous' }));
    expect(onChange).toHaveBeenLastCalledWith(2);
  });

  it('hides paging when there are no results', () => {
    render(
      <DataTable
        caption="Courses"
        columns={columns}
        rows={[]}
        rowKey={(r) => r.id}
        page={{ skip: 0, limit: 20, total: 0, onChange: vi.fn() }}
      />,
    );
    expect(screen.queryByRole('navigation', { name: 'Pagination' })).not.toBeInTheDocument();
  });

  it('sortable headers report sorting and show it with aria-sort', async () => {
    const onSortChange = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <DataTable
        caption="Courses"
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        onSortChange={onSortChange}
      />,
    );
    const codeHeader = screen.getByRole('columnheader', { name: /Code/ });
    expect(codeHeader).toHaveAttribute('aria-sort', 'none');
    expect(screen.getByRole('columnheader', { name: 'Title' })).not.toHaveAttribute('aria-sort');

    await user.click(screen.getByRole('button', { name: /Code/ }));
    expect(onSortChange).toHaveBeenLastCalledWith({ key: 'code', direction: 'asc' });

    rerender(
      <DataTable
        caption="Courses"
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        sort={{ key: 'code', direction: 'asc' }}
        onSortChange={onSortChange}
      />,
    );
    expect(screen.getByRole('columnheader', { name: /Code/ })).toHaveAttribute(
      'aria-sort',
      'ascending',
    );
    await user.click(screen.getByRole('button', { name: /Code/ }));
    expect(onSortChange).toHaveBeenLastCalledWith({ key: 'code', direction: 'desc' });
  });
});
