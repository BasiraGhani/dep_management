import { QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';

import { appRoutes } from '../AppRoutes';
import { AuthProvider } from '../auth/AuthProvider';
import { ToastProvider } from '../components/ToastProvider';
import { createQueryClient } from '../lib/queryClient';

/** Render the real routes and providers at `route`, like App does in the browser. */
export function renderApp(route = '/'): RenderResult {
  const router = createMemoryRouter(appRoutes, { initialEntries: [route] });
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({
    queries: { ...queryClient.getDefaultOptions().queries, retry: false },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <RouterProvider router={router} />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}
