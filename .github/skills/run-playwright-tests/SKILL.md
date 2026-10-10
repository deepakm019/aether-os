---
name: run-playwright-tests
description: Install the development test dependencies and run the Playwright browser tests for AstralSurge OS.
---

# Run AstralSurge OS browser tests

Use this skill when asked to execute, diagnose, or extend the app's Playwright end-to-end tests.

## Setup

1. Configure a Python environment for the workspace.
2. Install the development dependencies from `requirements-dev.txt`.
3. Install the Playwright Chromium browser with `python -m playwright install chromium`.

## Execute

Run the complete suite from the repository root:

```bash
npm run test
```

Run one suite when iterating:

```bash
python -m pytest tests/test_browser_suites.py -k persistence
python -m pytest tests/test_browser_suites.py -k sweep
```

Suites can also run directly, for example `python tests/sweep_tests.py`. They read the app URL from `ASOS_URL`, which defaults to `http://127.0.0.1:8765/index.html`. The pytest fixture in `tests/conftest.py` starts that server for you.

The suites cover backup and restore round trips, legacy migration, bad-file rejection, encrypted vault restore, and the main workflows. Each suite fails if any check fails or a page error is raised.
