"""Loans screen: calculator, saved loans, schedule, validation, persistence and phone-width layout."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
PAGE_SCROLL = "() => [document.documentElement.scrollWidth, window.innerWidth]"
ROW_OVERFLOW = """() => { const out=[]; document.querySelectorAll('.panel .row, .panel .metric').forEach(r=>{
  const pr=r.closest('.panel').getBoundingClientRect(); const rr=r.getBoundingClientRect();
  if(rr.right>pr.right+0.5) out.push(r.textContent.trim().slice(0,30)+' +'+Math.round(rr.right-pr.right));}); return out; }"""

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail and not ok else ""))


def open_app(browser, width=1280, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
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
    return page, errors


def open_loans(page):
    page.evaluate("() => setNav('loans')")
    page.wait_for_timeout(300)


def fill_loan(page, name, principal, rate, months, emi=None, loan_type="Car"):
    page.fill("#modal input[name=name]", name)
    page.select_option("#modal select[name=type]", loan_type)
    page.fill("#modal input[name=principal]", str(principal))
    page.fill("#modal input[name=rate]", str(rate))
    page.fill("#modal input[name=remainingMonths]", str(months))
    if emi is not None:
        page.fill("#modal input[name=emi]", str(emi))
    page.locator("#modal button[type=submit]").click()
    page.wait_for_timeout(300)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # Entry point from Money, and the calculator's default result.
        page, errors = open_app(browser)
        page.evaluate("() => setNav('money')")
        page.wait_for_timeout(300)
        check("money screen links to loans", page.locator("button:has-text('Loans calculator')").count() == 1)
        page.locator("button:has-text('Loans calculator')").click()
        page.wait_for_timeout(300)
        check("loans screen opens", page.locator(".h1", has_text="Loans").count() == 1)
        out = page.locator("#loan-calc-out").inner_text()
        check("default calculator shows the EMI for 20 lakh at 9% over 180 months", "20,285" in out, out[:120])

        page.fill("#lc-p", "1000000")
        page.wait_for_timeout(100)
        out = page.locator("#loan-calc-out").inner_text()
        check("changing the amount updates the EMI live", "10,142" in out, out[:120])

        page.select_option("#lc-mode", "tenure")
        page.wait_for_timeout(200)
        page.fill("#lc-x", "10142.67")
        page.wait_for_timeout(100)
        out = page.locator("#loan-calc-out").inner_text()
        check("time-to-repay mode returns about 15 years", "15 yr" in out, out[:160])

        page.fill("#lc-x", "100")
        page.wait_for_timeout(100)
        out = page.locator("#loan-calc-out").inner_text()
        check("an EMI below the monthly interest is flagged", "never clears" in out, out[:160])

        # Saved loans: the demo loan and its schedule.
        page.select_option("#lc-mode", "emi")
        page.wait_for_timeout(200)
        check("demo loan appears in the list", page.locator(".row", has_text="Home loan").count() == 1)
        page.locator(".row", has_text="Home loan").locator("button:has-text('Schedule')").click()
        page.wait_for_timeout(300)
        rows = page.locator("#drawer-content table tbody tr").count()
        check("schedule drawer shows one row per loan year", rows == 15, f"rows={rows}")
        check("schedule drawer has an interactive balance chart", page.locator("#drawer-content .lchart").count() >= 1)
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Add a loan, then check the calculated EMI.
        page.locator("button:has-text('+ Add loan')").click()
        page.wait_for_timeout(300)
        fill_loan(page, "Test car loan", 500000, 9, 60)
        card = page.locator(".row", has_text="Test car loan")
        check("added loan appears with its EMI", card.count() == 1 and "10,37" in card.inner_text(), card.inner_text()[:200] if card.count() else "missing")

        # A loan whose entered EMI never clears it is refused and the form stays open.
        page.locator("button:has-text('+ Add loan')").click()
        page.wait_for_timeout(300)
        fill_loan(page, "Trap loan", 1000000, 12, 120, emi=100)
        check("an EMI that never clears the loan is refused", page.locator("#modal form").count() == 1 and page.locator(".row", has_text="Trap loan").count() == 0)
        page.locator("#modal button:has-text('×')").click() if page.locator("#modal button:has-text('×')").count() else page.evaluate("() => closeModal()")
        page.wait_for_timeout(200)

        # Edit the saved loan's tenure.
        page.locator(".row", has_text="Test car loan").locator("button:has-text('Edit')").click()
        page.wait_for_timeout(300)
        page.fill("#modal input[name=remainingMonths]", "36")
        page.locator("#modal button[type=submit]").click()
        page.wait_for_timeout(300)
        check("editing tenure updates the loan", "3 yr" in page.locator(".row", has_text="Test car loan").inner_text())

        # Persistence across reloads.
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        open_loans(page)
        check("loan survives a reload", page.locator(".row", has_text="Test car loan").count() == 1)

        # Remove it.
        page.locator(".row", has_text="Test car loan").locator("button:has-text('Edit')").click()
        page.wait_for_timeout(300)
        page.locator("#modal button:has-text('Remove loan')").click()
        page.wait_for_timeout(300)
        check("removing a loan deletes it", page.locator(".row", has_text="Test car loan").count() == 0)
        check("no script errors in the main flow", errors == [], str(errors))
        page.close()

        # Layout at phone and desktop widths.
        for width in (280, 320, 390, 1280):
            page, errors = open_app(browser, width=width)
            open_loans(page)
            scroll_w, inner_w = page.evaluate(PAGE_SCROLL)
            check(f"{width}px: loans page has no sideways scroll", scroll_w <= inner_w, f"{scroll_w}>{inner_w}")
            overflow = page.evaluate(ROW_OVERFLOW)
            check(f"{width}px: loan rows stay inside their panel", overflow == [], str(overflow))
            check(f"{width}px: no script errors", errors == [], str(errors))
            page.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nLOANS RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
