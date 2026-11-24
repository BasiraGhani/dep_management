import { useParams } from 'react-router';

/**
 * Placeholder for a page that a later task builds (named in `task`). It keeps
 * every route of ARCHITECTURE §4 reachable and guarded in the meantime.
 */
export function ComingSoon({ title, task }: { title: string; task: string }) {
  const { id } = useParams();
  return (
    <div className="mx-auto max-w-2xl p-8">
      <h1 className="text-2xl font-semibold text-slate-800">
        {id === undefined ? title : `${title} #${id}`}
      </h1>
      <p className="mt-2 text-slate-500">This page arrives in {task}.</p>
    </div>
  );
}
