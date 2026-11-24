import { Link } from 'react-router';

export function NotFoundPage() {
  return (
    <main className="mx-auto max-w-xl p-8 text-center">
      <h1 className="text-2xl font-semibold text-slate-800">Page not found</h1>
      <p className="mt-2 text-slate-600">There is no page at this address.</p>
      <Link to="/" className="mt-6 inline-block text-blue-600 hover:underline">
        Go to the dashboard
      </Link>
    </main>
  );
}
