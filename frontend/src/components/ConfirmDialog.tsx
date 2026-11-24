import type { ReactNode } from 'react';

import { Modal } from './Modal';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** What will happen, e.g. "Delete CS101? Its enrollments are deleted too." */
  message: ReactNode;
  confirmLabel?: string;
  /** Red confirm button for destructive actions (the default). */
  danger?: boolean;
  /** True while the confirmed action runs: buttons are disabled. */
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** "Are you sure?" before deleting or other destructive actions (NFR-5, FR-4.4). */
export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  danger = true,
  pending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      title={title}
      onClose={() => {
        if (!pending) onCancel();
      }}
      footer={
        <>
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="rounded border border-slate-300 px-4 py-2 hover:bg-slate-50 disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            className={`rounded px-4 py-2 font-medium text-white disabled:opacity-60 ${
              danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {pending ? 'Working…' : confirmLabel}
          </button>
        </>
      }
    >
      <div className="text-slate-700">{message}</div>
    </Modal>
  );
}
