import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react';

import { ToastContext, type Toast, type ToastApi, type ToastKind } from './toastContext';

const STYLE: Record<ToastKind, string> = {
  success: 'border-green-200 bg-green-50 text-green-800',
  error: 'border-red-200 bg-red-50 text-red-800',
};

/**
 * Shows toasts in the bottom-right corner. Success toasts disappear after
 * `duration` ms; error toasts stay until closed so they can't be missed.
 */
export function ToastProvider({
  children,
  duration = 4000,
}: {
  children: ReactNode;
  duration?: number;
}) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current++;
      setToasts((current) => [...current, { id, kind, message }]);
      if (kind === 'success') {
        window.setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss, duration],
  );

  const api = useMemo<ToastApi>(
    () => ({
      success: (message) => {
        show('success', message);
      },
      error: (message) => {
        show('error', message);
      },
    }),
    [show],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed right-4 bottom-4 z-50 flex w-80 flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.kind === 'error' ? 'alert' : 'status'}
            className={`flex items-start justify-between gap-3 rounded border p-3 shadow ${STYLE[toast.kind]}`}
          >
            <p className="text-sm">{toast.message}</p>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => {
                dismiss(toast.id);
              }}
              className="leading-none opacity-70 hover:opacity-100"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
