---
name: run-playwright-tests
description: Install the development test dependencies and run the Playwright browser tests for Aether OS.
---

# Run Aether OS browser tests

Use this skill when asked to execute, diagnose, or extend the app's Playwright end-to-end tests.

## Setup

1. Configure a Python environment for the workspace.
2. Install the development dependencies from `requirements-dev.txt`.
3. Install the Playwright Chromium browser with `python -m playwright install chromium`.

## Execute

Run the complete suite from the repository root:

```powershell
python -m pytest
```

Run one test module or case when iterating:

```powershell
python -m pytest tests/test_screens.py
python -m pytest tests/test_workflows.py
python -m pytest -k "encrypted_v3"
```

The tests start a temporary local static HTTP server and launch headless Chromium. They cover desktop and mobile navigation, all app screens, data-entry workflows, local encrypted storage, external-request absence, and app-shell service-worker caching.
