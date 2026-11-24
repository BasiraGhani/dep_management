import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach } from 'vitest';

// findBy*/waitFor give up after this long. The 1 s default is too tight when the
// whole suite runs in parallel (or on a slower CI runner); passing tests aren't
// slowed down, because they resolve as soon as the element appears.
configure({ asyncUtilTimeout: 5000 });

afterEach(() => {
  cleanup();
});
