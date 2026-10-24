"""Loans phase 2: penalties, lock-in, tax, the prepay/close simulator, recording and settings."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
PAGE_SCROLL = "() => [document.documentElement.scrollWidth, window.innerWidth]"

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
    page.evaluate("() => setNav('loans')")
    page.wait_for_timeout(300)
    return page, errors


def open_prepay(page, name):
    page.locator(".row", has_text=name).locator("button:has-text('Prepay or close')").click()
    page.wait_for_timeout(300)


def drawer_text(page):
    return page.locator("#drawer-content").inner_text()


def edit_loan(page, name):
    page.locator(".row", has_text=name).locator("button:has-text('Edit')").click()
    page.wait_for_timeout(300)


def open_terms(page):
    details = page.locator("#modal details")
    if not details.evaluate("d => d.open"):
        details.locator("summary").click()


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = open_app(browser)

        # Simulator opens on the demo loan with no penalty.
        open_prepay(page, "Home loan")
        check("prepay drawer opens for a loan", page.locator("#drawer-content h2", has_text="Home loan").count() == 1)
        page.fill("#pp-amount", "500000")
        page.wait_for_timeout(150)
        text = drawer_text(page).lower()
        check("no penalty on the demo loan", "pays now" in text and "5,00,000.00" in text and "no penalty applies" in text, text[:300])
        check("comparison shows both ways to record it", "shorten tenure" in text and "reduce emi" in text and "net saving" in text)
        check("verdict is shown", "saves about" in text or "not worth it" in text)
        check("recording now is offered", page.locator("button:has-text('Record prepayment now')").count() == 1)

        # Set a 2% penalty on the amount prepaid.
        page.keyboard.press("Escape")
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)
        edit_loan(page, "Home loan")
        open_terms(page)
        page.select_option("#modal select[name=penaltyType]", "Percent")
        page.fill("#modal input[name=penaltyValue]", "2")
        page.locator("#modal button[type=submit]").click()
        page.wait_for_timeout(300)
        open_prepay(page, "Home loan")
        page.fill("#pp-amount", "500000")
        page.wait_for_timeout(150)
        text = drawer_text(page).lower()
        check("2% penalty adds 10,000 to the cash needed", "5,10,000.00" in text, text[:300])
        check("penalty is shown in words", "penalty ₹10,000.00" in text.lower() or "penalty ₹10,000.00" in drawer_text(page).lower())

        # Tax on the penalty from settings.
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)
        page.locator("#app summary", has_text="Loan settings").click()
        page.fill("#ls-tax", "18")
        page.fill("#ls-sr", "7")
        page.locator("form button:has-text('Save settings')").click()
        page.wait_for_timeout(300)
        open_prepay(page, "Home loan")
        page.fill("#pp-amount", "500000")
        page.wait_for_timeout(150)
        text = drawer_text(page).lower()
        check("tax on penalty is added to cash needed", "5,11,800.00" in text, text[:300])
        check("growth given up uses the savings rate", "growth you give up at your savings rate" in text)
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Lock-in: no penalty once the lock-in date has passed.
        edit_loan(page, "Home loan")
        open_terms(page)
        page.fill("#modal input[name=lockInEnd]", "2020-01-01")
        page.locator("#modal button[type=submit]").click()
        page.wait_for_timeout(300)
        open_prepay(page, "Home loan")
        page.fill("#pp-amount", "500000")
        page.wait_for_timeout(150)
        text = drawer_text(page).lower()
        check("no penalty after the lock-in has ended", "5,00,000.00" in text and "no penalty applies" in text, text[:300])
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Projection: months ahead is a projection only, with no record button.
        open_prepay(page, "Home loan")
        page.fill("#pp-month", "12")
        page.fill("#pp-amount", "500000")
        page.wait_for_timeout(150)
        check("a future month only projects", "this is a projection" in drawer_text(page).lower())
        check("no record button for a projection", page.locator("button:has-text('now')").count() == 0)
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Record a prepayment now (shorten): the loan changes and a decision is logged.
        open_prepay(page, "Home loan")
        page.fill("#pp-month", "0")
        page.fill("#pp-amount", "500000")
        page.locator("input[name=pmode][value=Shorten]").check()
        page.wait_for_timeout(150)
        before = page.locator(".row", has_text="Home loan").inner_text()
        page.locator("button:has-text('Record prepayment now')").click()
        page.wait_for_timeout(400)
        after = page.locator(".row", has_text="Home loan").inner_text()
        check("recording a prepayment reduces the loan", before != after, after[:200])
        check("the loan now shows a balance date", "balance as of" in after)
        page.evaluate("() => setNav('money')")
        page.wait_for_timeout(300)
        check("a decision is logged for the prepayment", page.locator("text=Prepay ₹5,00,000.00 on Home loan").count() >= 1 or "prepay ₹5,00,000.00 on home loan" in page.locator("#app").inner_text().lower())
        page.evaluate("() => setNav('loans')")
        page.wait_for_timeout(300)

        # Closing a loan moves it to Closed.
        page.locator("button:has-text('+ Add loan')").click()
        page.wait_for_timeout(300)
        page.fill("#modal input[name=name]", "Small personal loan")
        page.select_option("#modal select[name=type]", "Personal")
        page.fill("#modal input[name=principal]", "100000")
        page.fill("#modal input[name=rate]", "14")
        page.fill("#modal input[name=remainingMonths]", "24")
        page.locator("#modal button[type=submit]").click()
        page.wait_for_timeout(300)
        open_prepay(page, "Small personal loan")
        page.wait_for_timeout(150)
        check("closing in full is offered with no amount", page.locator("button:has-text('Record closure now')").count() == 1)
        page.locator("button:has-text('Record closure now')").click()
        page.wait_for_timeout(400)
        check("closed loan leaves the open list", page.locator(".row", has_text="Small personal loan").count() == 0)
        check("closed loan is listed as closed", "Closed:" in page.locator("#app").inner_text() and "Small personal loan" in page.locator("#app").inner_text())
        check("no script errors in the prepay flow", errors == [], str(errors))
        page.close()

        # Phone width: the simulator drawer does not scroll the page sideways.
        for width in (320, 390):
            page, errors = open_app(browser, width=width)
            open_prepay(page, "Home loan")
            page.fill("#pp-amount", "500000")
            page.wait_for_timeout(150)
            scroll_w, inner_w = page.evaluate(PAGE_SCROLL)
            check(f"{width}px: simulator fits the screen", scroll_w <= inner_w, f"{scroll_w}>{inner_w}")
            check(f"{width}px: no script errors", errors == [], str(errors))
            page.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nLOAN PREPAY RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
