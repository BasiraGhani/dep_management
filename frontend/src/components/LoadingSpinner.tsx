/** An accessible loading indicator. */
export function LoadingSpinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 p-4 text-slate-500">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600"
      />
      <span>{label}</span>
    </div>
  );
}
