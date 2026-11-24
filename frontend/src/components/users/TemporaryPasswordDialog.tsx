import { Modal } from '../Modal';
import { useToast } from '../useToast';

interface TemporaryPasswordDialogProps {
  /** Null closes the dialog (and forgets the password). */
  result: { username: string; password: string } | null;
  onClose: () => void;
}

/** Shows a reset password once (FR-8.1); it can't be fetched again. */
export function TemporaryPasswordDialog({ result, onClose }: TemporaryPasswordDialogProps) {
  const toast = useToast();
  const copy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.password);
      toast.success('Copied to the clipboard');
    } catch {
      toast.error("Couldn't copy: select the password and copy it yourself.");
    }
  };
  return (
    <Modal
      open={result !== null}
      title={`Temporary password for ${result?.username ?? ''}`}
      onClose={onClose}
      footer={
        <button
          type="button"
          onClick={onClose}
          className="rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700"
        >
          Done
        </button>
      }
    >
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <code
            aria-label="Temporary password"
            className="flex-1 select-all rounded bg-slate-100 px-3 py-2 font-mono text-lg"
          >
            {result?.password}
          </code>
          <button
            type="button"
            onClick={() => void copy()}
            className="rounded border border-slate-300 bg-white px-3 py-2 hover:bg-slate-50"
          >
            Copy
          </button>
        </div>
        <p className="text-sm text-slate-600">
          Give this to {result?.username}. It is shown only now; they can change it on their profile
          after signing in.
        </p>
      </div>
    </Modal>
  );
}
