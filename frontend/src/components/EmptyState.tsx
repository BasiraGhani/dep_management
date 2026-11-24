import type { ReactNode } from 'react';

/**
 * The one look for "nothing here" messages, matching DataTable's empty row:
 * centered, muted text. `boxed` frames a message that stands alone on a page.
 */
export function EmptyState({ children, boxed = false }: { children: ReactNode; boxed?: boolean }) {
  return (
    <p
      className={`px-4 py-6 text-center text-slate-500 ${boxed ? 'rounded-lg border border-slate-200 bg-white' : ''}`}
    >
      {children}
    </p>
  );
}
