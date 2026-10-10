"""P1 batch: Today summary (copy and WhatsApp share) and the tomorrow-9am reminder snooze."""
import os
import sys
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 390, "height": 844})
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=URL.split("/index.html")[0])
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(URL, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)
        page.evaluate("() => setNav('today')")
        page.wait_for_timeout(250)

        # #12 Copy summary writes the Top 3 text to the clipboard.
        page.get_by_role("button", name="Copy summary", exact=True).click()
        page.wait_for_timeout(300)
        clip = page.evaluate("() => navigator.clipboard.readText()")
        check("copy summary puts the AstralSurge summary on the clipboard",
              clip.startswith("AstralSurge OS") and "Open tasks:" in clip, clip[:60].replace("\n", " | "))
        check("summary lists numbered top tasks", "1. " in clip, "")

        # #13 WhatsApp share is a plain wa.me link carrying the same text.
        href = page.get_by_role("link", name="Share to WhatsApp", exact=True).get_attribute("href")
        check("WhatsApp link uses wa.me with the text",
              href.startswith("https://wa.me/?text=") and "Open tasks" in unquote(href), href[:40])
        check("WhatsApp link opens in a new tab safely",
              page.get_by_role("link", name="Share to WhatsApp", exact=True).get_attribute("rel") == "noopener noreferrer")

        # #10 Snooze: Tomorrow 9am on a reminder, if the workspace has one.
        page.evaluate("() => setNav('reminders')")
        page.wait_for_timeout(250)
        page.on("dialog", lambda d: d.accept("Call the dentist") if d.type == "prompt" else d.accept())
        page.get_by_role("button", name="In 30m", exact=True).click()
        page.wait_for_timeout(300)
        snooze = page.get_by_role("button", name="Tomorrow 9am", exact=True)
        if snooze.count():
            snooze.first.click()
            page.wait_for_timeout(300)
            check("tomorrow 9am snooze confirms", page.get_by_text("Snoozed until tomorrow 9:00").count() >= 1)
        else:
            check("reminders screen offers Tomorrow 9am", False, "no snooze button found")

        check("no page errors during the batch", not errors, "; ".join(errors)[:200])
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nP1 BATCH RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
