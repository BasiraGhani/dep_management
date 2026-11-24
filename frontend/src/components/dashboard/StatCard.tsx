import type { ReactNode } from 'react';
import { Link } from 'react-router';

interface StatCardProps {
  label: string;
  value: number | string;
  /** Optional page the card links to (e.g. the matching list). */
  to?: string;
}

/** One headline figure. The label is the accessible name of the value. */
export function StatCard({ label, value, to }: StatCardProps) {
  const body = (
    <>
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold text-slate-800">{value}</dd>
    </>
  );
  return (
    <div className="rounded-lg border bg-white p-4">
      {to ? (
        <Link
          to={to}
          className="block hover:text-blue-700"
          aria-label={`${label}: ${String(value)}`}
        >
          <dl>{body}</dl>
        </Link>
      ) : (
        <dl aria-label={`${label}: ${String(value)}`}>{body}</dl>
      )}
    </div>
  );
}

/** A responsive row of stat cards. */
export function StatGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{children}</div>;
}
