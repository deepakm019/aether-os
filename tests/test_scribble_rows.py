"""Scribble rows: sticky header, rows and subrows, grouping, urgency, due dates, per-row focus timers, done, edit, persistence."""
import os

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def verify(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def open_minimal(browser, width=390, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => switchMinimalMode('minimal')")
    page.wait_for_selector(".minimal-app")
    return ctx, page


def row_for(page, title):
    return page.locator(f'article.minimal-item:has(> .minimal-row .minimal-item-text:text-is("{title}"))')


def post(page, text, crit=None, due=None, as_group=False):
    if crit:
        page.select_option("#minimal-crit", crit)
    if due:
        page.fill("#minimal-due", due)
    page.fill("#minimal-note", text)
    if as_group:
        page.click("button:has-text('as group')")
    else:
        page.press("#minimal-note", "Enter")
    page.wait_for_timeout(350)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx, page = open_minimal(browser, 390, 844)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        import datetime
        today = datetime.date.today().isoformat()
        post(page, "Pay electricity bill", crit="high", due=today)
        bill = row_for(page, "Pay electricity bill")
        verify("urgency chip shows on the row", bill.locator(".minimal-chip.c-high").count() == 1)
        verify("due-today chip shows on the row", bill.locator(".minimal-chip.today").count() == 1)

        post(page, "Launch plan", as_group=True)
        group = row_for(page, "Launch plan")
        verify("group row is marked as a group", group.locator(".minimal-chip", has_text="group").count() == 1)

        group.locator("button:has-text('+ subrow')").click()
        page.wait_for_timeout(300)
        verify("subrow composer shows the parent", page.locator(".minimal-parent-chip").count() == 1)
        post(page, "Write spec")
        spec = row_for(page, "Write spec")
        verify("subrow appears under its group", spec.count() == 1)
        verify("group shows progress 0/1", "0/1 done" in row_for(page, "Launch plan").locator(".minimal-chip").first.inner_text())

        toggle = row_for(page, "Launch plan").locator(".minimal-toggle").first
        toggle.click()
        page.wait_for_timeout(250)
        verify("clicking the group collapses its subrows", row_for(page, "Write spec").count() == 0)
        row_for(page, "Launch plan").locator(".minimal-toggle").first.click()
        page.wait_for_timeout(250)
        verify("clicking again expands the subrows", row_for(page, "Write spec").count() == 1)

        bill = row_for(page, "Pay electricity bill")
        bill.locator("button:has-text('focus')").first.click()
        page.wait_for_timeout(2600)
        live = bill.locator(".minimal-focus-live").first.inner_text() if bill.locator(".minimal-focus-live").count() else ""
        verify("row focus timer is running and counting", "●" in live and live != "● 00:00", live)
        spec.locator("button:has-text('focus')").first.click()
        page.wait_for_timeout(300)
        verify("only one row can run focus at a time", page.locator(".minimal-focus-live").count() == 1)
        page.wait_for_timeout(200)
        spec.locator("button:has-text('stop focus')").click()
        page.wait_for_timeout(300)
        verify("stopping focus keeps the total time", row_for(page, "Write spec").locator(".minimal-chip", has_text="focus ").count() == 1)

        row_for(page, "Pay electricity bill").locator(".minimal-check").check()
        page.wait_for_timeout(300)
        verify("marking done strikes the row through", "is-done" in (row_for(page, "Pay electricity bill").get_attribute("class") or ""))

        row_for(page, "Pay electricity bill").locator("button:has-text('edit')").click()
        page.wait_for_timeout(250)
        page.select_option("#minimal-edit-crit", "low")
        page.select_option("#minimal-edit-parent", label="Launch plan")
        page.fill("#minimal-edit-due", "2030-01-15")
        page.click("form.minimal-edit button[type=submit]")
        page.wait_for_timeout(350)
        moved = page.locator('article.minimal-item:has(> .minimal-row .minimal-item-text:text-is("Pay electricity bill"))')
        verify("edit moves a row under a group", moved.count() == 1 and (moved.get_attribute("data-parent") or "") != "")
        verify("edit saves urgency and due date", moved.locator(".minimal-chip.c-low").count() == 1 and moved.locator(".minimal-chip", has_text="due 2030-01-15").count() == 1)

        spec.locator("button:has-text('+ subrow')").click()
        page.wait_for_timeout(300)
        post(page, "Draft v1")
        draft = row_for(page, "Draft v1")
        verify("subrows can nest a third level", draft.count() == 1)
        verify("third-level rows cannot get more subrows", draft.locator("button:has-text('+ subrow')").count() == 0)

        page.set_viewport_size({"width": 390, "height": 844})
        for i in range(10):
            post(page, f"filler row {i}")
        page.evaluate("() => window.scrollTo(0, 700)")
        page.wait_for_timeout(300)
        top = page.evaluate("() => Math.round(document.querySelector('.minimal-sticky').getBoundingClientRect().top)")
        verify("header stays pinned while scrolling the list", top <= 8, f"top={top}")
        verify("no horizontal page scroll on phone", page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth"))

        page.evaluate("() => window.scrollTo(0, 0)")
        page.reload(wait_until="load")
        page.wait_for_selector(".minimal-app")
        page.wait_for_timeout(400)
        verify("rows and subrows survive a reload", row_for(page, "Launch plan").count() == 1 and row_for(page, "Pay electricity bill").count() == 1 and page.locator(".minimal-item").count() == 13)

        page.once("dialog", lambda d: d.accept())
        row_for(page, "Launch plan").locator("button:has-text('delete')").first.click()
        page.wait_for_timeout(400)
        verify("deleting a group deletes its subrows", row_for(page, "Launch plan").count() == 0 and row_for(page, "Write spec").count() == 0 and row_for(page, "Draft v1").count() == 0)

        verify("no script errors", errors == [], str(errors[:3]))
        ctx.close()

        desk_ctx, desk = open_minimal(browser, 1280, 800)
        desk.wait_for_timeout(200)
        verify("desktop list is a readable width", desk.evaluate("() => document.querySelector('.minimal-wrap').getBoundingClientRect().width") <= 790)
        desk_ctx.close()
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nSCRIBBLE ROWS RESULT: {len(results)-len(failed)}/{len(results)} passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
