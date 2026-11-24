import { QueryClient } from '@tanstack/react-query';

/** The app's TanStack Query client. Tests create their own with `createQueryClient()`. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: false,
        // A 4xx won't fix itself by retrying; network blips get one more try.
        retry: (failureCount, error) =>
          failureCount < 1 && !(error as { response?: unknown }).response,
      },
    },
  });
}
