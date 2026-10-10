"""Run every browser suite in tests/ against the app served by conftest.app_server.

Suites are discovered automatically: any tests/*_tests.py or tests/test_*.py
file (except this runner and conftest.py). Adding a suite never requires
editing this file.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
EXCLUDE = {"conftest.py", "test_browser_suites.py"}
SUITES = sorted(
    p.name
    for p in TESTS_DIR.glob("*.py")
    if p.name not in EXCLUDE and (p.name.endswith("_tests.py") or p.name.startswith("test_"))
)


@pytest.mark.parametrize("suite", SUITES)
def test_browser_suite(app_server, suite):
    env = {**os.environ, "ASOS_URL": app_server}
    result = subprocess.run(
        [sys.executable, str(TESTS_DIR / suite)],
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"{suite} failed:\n{output[-4000:]}"
