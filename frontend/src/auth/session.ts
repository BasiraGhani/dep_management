/**
 * "The session has expired" signal. The API client raises it on a 401; the
 * AuthProvider listens and logs out, and the route guard then sends the user to
 * the login page through the router (no full page reload).
 */

type Listener = () => void;
const listeners = new Set<Listener>();

/** Subscribe; returns the unsubscribe function. */
export function onSessionExpired(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Tell every listener. Returns false when nobody is listening. */
export function notifySessionExpired(): boolean {
  listeners.forEach((listener) => {
    listener();
  });
  return listeners.size > 0;
}
