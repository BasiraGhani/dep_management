/** Browser navigation used by the API client, kept separate so tests can spy on it. */
export const browser = {
  currentPath: (): string => window.location.pathname,
  goTo: (path: string): void => {
    window.location.assign(path);
  },
};
