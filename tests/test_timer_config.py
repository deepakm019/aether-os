"""Countdown timer: presets and custom minutes change the duration, and reset keeps it."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def clock(page):
    return page.locator("#tool-timer").text_content().strip()


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(URL, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)
        page.evaluate("() => setNav('timer')")
        page.wait_for_timeout(250)

        check("default countdown is 25:00", clock(page) == "25:00", clock(page))

        page.get_by_role("button", name="10 min", exact=True).click()
        page.wait_for_timeout(200)
        check("10 min preset sets 10:00", clock(page) == "10:00", clock(page))

        page.fill("#timer-minutes", "42")
        page.get_by_role("button", name="Set", exact=True).click()
        page.wait_for_timeout(200)
        check("custom 42 minutes sets 42:00", clock(page) == "42:00", clock(page))

        page.get_by_role("button", name="Start", exact=True).first.click()
        page.wait_for_timeout(1300)
        page.get_by_role("button", name="Pause", exact=True).first.click()
        page.get_by_role("button", name="Reset", exact=True).first.click()
        page.wait_for_timeout(200)
        check("reset returns to the configured 42:00, not 25:00", clock(page) == "42:00", clock(page))

        page.fill("#timer-minutes", "0")
        page.get_by_role("button", name="Set", exact=True).click()
        page.wait_for_timeout(200)
        check("0 minutes is rejected and keeps 42:00", clock(page) == "42:00", clock(page))

        page.fill("#timer-minutes", "500")
        page.get_by_role("button", name="Set", exact=True).click()
        page.wait_for_timeout(200)
        check("500 minutes is rejected and keeps 42:00", clock(page) == "42:00", clock(page))
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nTIMER CONFIG RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
