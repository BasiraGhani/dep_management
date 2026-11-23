"""Shared test setup. T1.4 adds the test database, client and factories."""

import os

# Settings require SECRET_KEY. Set a test value before any `app` module is imported,
# so the suite runs without a .env file (e.g. in CI). A real env var still wins.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
