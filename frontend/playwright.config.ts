import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end smoke test (T8.3): `npm run e2e`.
 *
 * * E2E_BASE_URL: the app (default http://localhost, the Docker stack)
 * * E2E_API_URL: the API, for clean-up (default <E2E_BASE_URL>/api/v1)
 * * E2E_CHANNEL: e.g. "chrome" to use an installed Google Chrome instead of
 *   Playwright's own Chromium (`npx playwright install chromium`)
 *
 * The app must have the demo data (`SEED_DEMO=true`, or `python -m app.cli seed-demo`).
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  // In CI, the github reporter turns failures into annotations on the PR.
  reporter: process.env.CI ? [['list'], ['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        ...(process.env.E2E_CHANNEL ? { channel: process.env.E2E_CHANNEL } : {}),
      },
    },
  ],
});
