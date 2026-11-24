import { Link } from 'react-router';

export function NotAuthorizedPage() {
  return (
    <main className="mx-auto max-w-xl p-8 text-center">
      <h1 className="text-2xl font-semibold text-slate-800">Not authorized</h1>
      <p className="mt-2 text-slate-600">Your account doesn&apos;t have access to this page.</p>
      <Link to="/" className="mt-6 inline-block text-blue-600 hover:underline">
        Go to the dashboard
      </Link>
    </main>
  );
}
