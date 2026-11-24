import { useContext } from 'react';

import { ToastContext, type ToastApi } from './toastContext';

/** Show success and error toasts (NFR-5). Must be used inside `<ToastProvider>`. */
export function useToast(): ToastApi {
  const api = useContext(ToastContext);
  if (api === null) throw new Error('useToast() must be used inside <ToastProvider>');
  return api;
}
