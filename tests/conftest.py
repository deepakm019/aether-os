"""Shared fixtures: serve the app from the repository root for browser tests."""
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 8765
APP_URL = f"http://127.0.0.1:{PORT}/index.html"


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def app_server():
    """Serve the repository root over HTTP (service workers need http://localhost or https)."""
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 15
        while not _port_open(PORT):
            if time.time() > deadline:
                raise RuntimeError("static server did not start on port %d" % PORT)
            time.sleep(0.1)
        yield APP_URL
    finally:
        process.terminate()
        process.wait(timeout=5)
