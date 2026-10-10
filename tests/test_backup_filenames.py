"""Backup files must carry a date and time in their filename, so repeated backups never overwrite each other."""
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
STAMP = r"astralsurge-backup-\d{4}-\d{2}-\d{2}_\d{6}\.json"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 800})
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.goto(URL, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)
        page.evaluate("() => setNav('vault')")
        page.wait_for_timeout(250)
        with page.expect_download() as dl:
            page.locator("button[onclick='backupWorkspace()']").first.click()
        name = dl.value.suggested_filename
        check("readable backup filename has date and time", re.fullmatch(STAMP, name) is not None, name)
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nBACKUP FILENAME RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
