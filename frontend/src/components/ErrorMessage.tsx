import { errorMessage } from '../api/client';

interface ErrorMessageProps {
  /** An error from the API client (its message is shown) or any other error. */
  error: unknown;
  /** Text used when the error carries no API message. */
  fallback?: string;
  /** Shows a "Try again" button when given. */
  onRetry?: () => void;
}

/** An error box with the API's message and an optional retry button. */
export function ErrorMessage({ error, fallback, onRetry }: ErrorMessageProps) {
  return (
    <div role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-red-800">
      <p>{errorMessage(error, fallback)}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded border border-red-300 bg-white px-3 py-1 text-sm hover:bg-red-100"
        >
          Try again
        </button>
      )}
    </div>
  );
}
