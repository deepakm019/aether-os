from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Iterator

import pytest
from playwright.sync_api import Browser, Page, sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@pytest.fixture(scope="session")
def app_url() -> Iterator[str]:
    handler = partial(QuietStaticHandler, directory=str(PROJECT_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://localhost:{server.server_port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Iterator[Browser]:
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(headless=True)
        yield instance
        instance.close()


@pytest.fixture
def app_page(browser: Browser, app_url: str) -> Iterator[Page]:
    context = browser.new_context(viewport={"width": 1365, "height": 900})
    page = context.new_page()
    page.goto(app_url, wait_until="domcontentloaded")
    page.get_by_role("button", name="I accept — continue").click()
    page.get_by_role("button", name="Load Demo").click()
    page.locator("#content h2").wait_for(state="visible")
    yield page
    context.close()
