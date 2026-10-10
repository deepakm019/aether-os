"""Responsive smoke test: every main view must fit the viewport width at common device sizes.

A view fails if the document scrolls horizontally, which is the most common
phone layout bug. Runs in headless Chromium against the app served by conftest.
"""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")

# Common devices: (label, width, height)
DEVICES = [
    ("small phone", 320, 568),
    ("phone", 390, 844),
    ("large phone", 430, 932),
    ("tablet portrait", 768, 1024),
    ("desktop", 1280, 800),
]

# Main navigation routes, from the render() route table in index.html
VIEWS = [
    "today", "work", "focus", "plan", "more", "goals", "life", "money",
    "memory", "progress", "rules", "vault", "calendar", "reminders",
    "timer", "settings", "legal",
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def open_app(browser, width, height):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(400)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(400)
    return ctx, page


def overflow_px(page):
    """How many pixels the document is wider than the viewport (0 = fits)."""
    return page.evaluate(
        "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)"
    )


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for label, width, height in DEVICES:
            ctx, page = open_app(browser, width, height)
            for view in VIEWS:
                page.evaluate("(v) => setNav(v)", view)
                page.wait_for_timeout(200)
                extra = overflow_px(page)
                check(f"{label} {width}px: {view} fits width", extra == 0,
                      f"overflow {extra}px" if extra else "")
            ctx.close()
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nRESPONSIVE RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
