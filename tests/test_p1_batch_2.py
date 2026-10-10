"""P1 batch 2: bills due in 7 days and quick expense on Today; .ics export of dated tasks."""
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def open_app(browser, width=390):
    ctx = browser.new_context(accept_downloads=True, viewport={"width": width, "height": 844})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    return ctx, page, errors


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser)

        # #15 Bills due in 7 days on Today
        page.evaluate("() => setNav('today')")
        page.wait_for_timeout(250)
        check("Today shows the bills due in 7 days section",
              page.locator("#bills-soon-title").count() == 1)
        empty_or_rows = page.get_by_text("Nothing due in the next 7 days.").count() + \
            page.locator("#bills-soon-title").locator("xpath=../..").locator(".row").count()
        check("bills section shows rows or the empty message", empty_or_rows >= 1)

        # #11 Quick expense from Today
        page.get_by_role("button", name="Add expense", exact=True).first.click()
        page.wait_for_timeout(300)
        check("Add expense opens the expense form", page.locator("#modal input[name=amount]").count() == 1)
        page.fill("#modal input[name=amount]", "12.5")
        page.fill("#modal input[name=title]", "Test lunch")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_timeout(400)
        page.evaluate("() => setNav('money')")
        page.wait_for_timeout(250)
        check("saved expense appears on Money", page.get_by_text("Test lunch").count() >= 1)

        # #6 .ics export from Calendar
        page.evaluate("() => setNav('calendar')")
        page.wait_for_timeout(250)
        with page.expect_download() as dl:
            page.get_by_role("button", name="Export dated tasks (.ics)", exact=True).click()
        download = dl.value
        check("calendar export downloads an .ics file", download.suggested_filename.endswith(".ics"),
              download.suggested_filename)
        body = open(download.path(), encoding="utf-8", newline="").read()
        check("file starts and ends as a calendar", body.startswith("BEGIN:VCALENDAR\r\n") and body.endswith("END:VCALENDAR\r\n"))
        check("file declares version 2.0", "VERSION:2.0" in body)
        begins = body.count("BEGIN:VEVENT")
        ends = body.count("END:VEVENT")
        check("every event is closed", begins == ends, f"{begins} begin / {ends} end")
        starts = re.findall(r"DTSTART;VALUE=DATE:(\d{8})", body)
        check("every event is an all-day date", len(starts) == begins, f"{len(starts)} dated starts")
        check("event UIDs are present", body.count("UID:") == begins)
        check("no page errors during the batch", not errors, "; ".join(errors)[:200])
        ctx.close()

        # Tiny-screen layout for the new Today section and the calendar button
        for width in (320, 390, 1280):
            ctx, page, errs = open_app(browser, width)
            for view in ("today", "calendar"):
                page.evaluate("(v) => setNav(v)", view)
                page.wait_for_timeout(200)
                overflow = page.evaluate(
                    "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
                check(f"{width}px: {view} with new P1 content fits", overflow == 0, f"overflow {overflow}px")
            check(f"{width}px: no page errors", not errs, "; ".join(errs)[:160])
            ctx.close()
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nP1 BATCH 2 RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
