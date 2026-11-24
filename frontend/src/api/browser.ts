/** Browser APIs used by the app, kept separate so tests can spy on them. */
export const browser = {
  currentPath: (): string => window.location.pathname,
  goTo: (path: string): void => {
    window.location.assign(path);
  },
  /** Save `blob` as a download named `filename`. */
  download: (blob: Blob, filename: string): void => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};
