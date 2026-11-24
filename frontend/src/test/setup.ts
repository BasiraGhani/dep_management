import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import type { InternalAxiosRequestConfig } from 'axios';
import { afterEach } from 'vitest';

import { api } from '../api/client';

// findBy*/waitFor give up after this long. The 1 s default is too tight when the
// whole suite runs in parallel (or on a slower CI runner); passing tests aren't
// slowed down, because they resolve as soon as the element appears.
configure({ asyncUtilTimeout: 5000 });

// Tests must never reach a real server: an API module that a test forgot to mock
// fails at once with its URL, instead of hanging until a timeout.
// (stubApi() in test/apiStub.ts installs its own adapter and restores this one.)
api.defaults.adapter = (config: InternalAxiosRequestConfig) =>
  Promise.reject(
    new Error(
      `Unmocked API request in a test: ${(config.method ?? 'get').toUpperCase()} ${config.url ?? ''}. ` +
        "Mock its module with vi.mock('…/api/<resource>').",
    ),
  );

afterEach(() => {
  cleanup();
});
