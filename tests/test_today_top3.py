"""Today: the Top 3 section lists up to three open tasks by priority and starts focus in one tap."""
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
RANK = {"High": 0, "Medium": 1, "Low": 2}
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def section(page):
    return page.locator("section", has=page.locator("#top-today-title"))


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

            heading = page.locator("#top-today-title")
            check(f"{width}px: Top 3 section is on Today", heading.count() == 1)
            rows = section(page).locator(".row")
            count = rows.count()
            check(f"{width}px: lists between 1 and 3 tasks", 1 <= count <= 3, f"found {count}")

            priorities = []
            for i in range(count):
                meta = rows.nth(i).locator(".row-meta").text_content()
                priorities.append(meta.split(" · ")[0].strip())
            ranks = [RANK.get(x, 1) for x in priorities]
            check(f"{width}px: tasks ordered High, Medium, Low",
                  ranks == sorted(ranks), " > ".join(priorities))

            if width == 390 and count:
                section(page).locator("button", has_text="Start focus").first.click()
                page.wait_for_timeout(400)
                check("one tap starts focus", re.search(r"focus", page.evaluate("() => location.hash")) is not None,
                      page.evaluate("() => location.hash"))

            ctx.close()
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nTODAY TOP 3 RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
