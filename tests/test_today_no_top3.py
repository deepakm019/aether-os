"""Today: the separate Top 3 panel is gone. The morning card keeps the priorities, with Focus buttons."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for width in (320, 390, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 800})
            page = ctx.new_page()
            page.goto(URL, wait_until="load")
            page.wait_for_selector("#app")
            page.wait_for_timeout(300)
            if page.locator("#beta-ack").count():
                page.check("#beta-ack")
                page.click("#beta-demo")
                page.wait_for_timeout(300)
            page.evaluate("() => setNav('today')")
            page.wait_for_timeout(250)

            check(f"{width}px: no Top 3 panel on Today", page.locator("#top-today-title").count() == 0)
            check(f"{width}px: morning card is on Today",
                  page.locator("h2:has-text('Morning check-in'), h2:has-text(\"Today's plan is shaped\")").count() == 1)
            overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            check(f"{width}px: no sideways scroll", overflow <= 0, f"overflow {overflow}px")
            ctx.close()
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nTODAY NO TOP 3 RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
