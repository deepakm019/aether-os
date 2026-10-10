"""Run the Playwright browser suites against the app served by conftest.app_server."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
SUITES = ["persistence_tests.py", "sweep_tests.py", "test_split_layout.py"]


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
