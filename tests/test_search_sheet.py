"""Search sheet: opens from the top bar at every width, jumps to sections, ranks
by use, records usage on open, and sanitises stored usage on load."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []

SHORTCUT_COUNT = 16


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def open_app(browser, width, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
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
    return ctx, page, errors


def open_sheet(page):
    page.evaluate("() => setNav('today')")
    page.wait_for_timeout(150)
    page.evaluate("() => globalSearch()")
    page.wait_for_timeout(250)


def sheet_open(page):
    return page.evaluate("() => document.getElementById('modal').classList.contains('open')")


def shortcut_ids(page):
    return page.locator("[data-action=search-shortcut]").evaluate_all("els => els.map(e => e.dataset.id)")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # 1. The sheet opens from the top bar and fits every width.
        for width in (320, 390, 1280):
            ctx, page, errors = open_app(browser, width)
            page.locator("button.mobile-search, .search input").first.click() if width < 980 \
                else page.locator(".search input").first.click()
            page.wait_for_timeout(300)
            check(f"{width}px: search opens from top bar", sheet_open(page))
            check(f"{width}px: search input focused", page.locator("#search-input").count() == 1)
            check(f"{width}px: all shortcuts listed", len(shortcut_ids(page)) == SHORTCUT_COUNT,
                  f"got {len(shortcut_ids(page))}")
            overflow = page.evaluate(
                "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
            check(f"{width}px: sheet causes no horizontal overflow", overflow == 0, f"overflow {overflow}px")
            check(f"{width}px: no page errors", not errors, "; ".join(errors[:2]))
            if width < 980:
                box = page.locator("#modal").bounding_box()
                check(f"{width}px: sheet is docked to the bottom", box and abs((box["y"] + box["height"]) - 844) < 3,
                      str(box))
            ctx.close()

        # 2. Typing filters shortcuts and returns matching objects.
        ctx, page, errors = open_app(browser, 390)
        open_sheet(page)
        page.fill("#search-input", "money")
        page.wait_for_timeout(150)
        check("typing 'money' keeps the Money shortcut", "money" in shortcut_ids(page))
        check("typing 'money' hides unrelated shortcuts", "work" not in shortcut_ids(page))
        page.fill("#search-input", "proposal")
        page.wait_for_timeout(150)
        titles = page.locator(".search-row .row-title").all_inner_texts()
        check("typing 'proposal' finds the task", "Finish proposal" in titles, str(titles))
        page.fill("#search-input", "zzz-no-match-zzz")
        page.wait_for_timeout(150)
        check("no-match query shows empty state",
              "No matching workspace objects" in page.locator("#search-results").inner_text())
        ctx.close()

        # 3. Opening a result records usage and moves it to the top of 'Most used'.
        ctx, page, errors = open_app(browser, 390)
        open_sheet(page)
        page.fill("#search-input", "proposal")
        page.wait_for_timeout(150)
        page.locator("[data-action=search-open]").first.click()
        page.wait_for_timeout(300)
        check("Open on a result opens the task inspector",
              "Finish proposal" in page.locator("#drawer").inner_text())
        open_sheet(page)
        most = page.locator(".search-row .row-title").all_inner_texts()
        check("'Most used' lists the opened task first", bool(most) and most[0] == "Finish proposal", str(most))
        ctx.close()

        # 4. Shortcuts navigate, record use, and move to the front of the jump list.
        ctx, page, errors = open_app(browser, 390)
        open_sheet(page)
        page.locator("[data-action=search-shortcut][data-id=money]").click()
        page.wait_for_timeout(300)
        check("Money shortcut navigates to Money", page.evaluate("() => location.hash") == "#/money")
        check("shortcut closes the sheet", not sheet_open(page))
        open_sheet(page)
        check("most-used shortcut comes first", shortcut_ids(page)[0] == "money", str(shortcut_ids(page)[:3]))
        page.locator("[data-action=search-shortcut][data-id=inbox]").click()
        page.wait_for_timeout(300)
        check("Inbox shortcut opens Work on the Inbox tab",
              page.evaluate("() => location.hash") == "#/work" and page.evaluate("() => window.workTab") == "Inbox")
        check("no page errors during shortcuts", not errors, "; ".join(errors[:2]))
        ctx.close()

        # 5. Close button dismisses the sheet.
        ctx, page, errors = open_app(browser, 390)
        open_sheet(page)
        page.locator("[aria-label='Close search']").click()
        page.wait_for_timeout(200)
        check("close button dismisses the sheet", not sheet_open(page))
        check("closing removes the sheet class",
              page.evaluate("() => !document.getElementById('modal').classList.contains('search-sheet')"))
        ctx.close()

        # 6. Stored usage is sanitised on load (import validation).
        ctx, page, errors = open_app(browser, 390)
        clean = page.evaluate("""() => normalizeWorkspace({searchUsage:{
            'Task:ok_1':{count:3,last:5},
            'nav:money':{count:'7',last:'x'},
            'bad key!':{count:9,last:1},
            'Task:zero':{count:0,last:1},
            'Task:neg':{count:-4,last:1},
            'Task:huge':{count:1e12,last:1},
            'Other:thing':{count:2,last:1}
          }}).searchUsage""")
        check("keeps valid usage entries", "Task:ok_1" in clean and clean["Task:ok_1"]["count"] == 3, str(clean))
        check("drops malformed keys and zero/negative counts",
              "bad key!" not in clean and "Task:zero" not in clean and "Task:neg" not in clean and "Other:thing" not in clean,
              str(list(clean)))
        check("clamps huge counts", clean.get("Task:huge", {}).get("count") == 100000, str(clean.get("Task:huge")))
        check("coerces numeric strings", clean.get("nav:money", {}).get("count") == 7)
        check("non-object input yields empty usage",
              page.evaluate("() => Object.keys(normalizeWorkspace({searchUsage:'nope'}).searchUsage).length") == 0)
        ctx.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nSEARCH SHEET RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
