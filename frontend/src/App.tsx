import { QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { BrowserRouter } from 'react-router';

import { AppRoutes } from './AppRoutes';
import { AuthProvider } from './auth/AuthProvider';
import { createQueryClient } from './lib/queryClient';

function App() {
  const [queryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
