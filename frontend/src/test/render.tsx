import { QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router';

import { AppRoutes } from '../AppRoutes';
import { AuthProvider } from '../auth/AuthProvider';
import { ToastProvider } from '../components/ToastProvider';
import { createQueryClient } from '../lib/queryClient';

/** Render the real routes and providers at `route`, like App does in the browser. */
export function renderApp(route = '/', children: ReactNode = <AppRoutes />): RenderResult {
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({
    queries: { ...queryClient.getDefaultOptions().queries, retry: false },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}
