"""Loans phase 3: comparison with other uses of the cash, suggested next steps and the new settings."""
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


def open_settings(page, values):
    details = page.locator("#app details", has=page.locator("summary", has_text="Loan settings"))
    if not details.evaluate("d => d.open"):
        details.locator("summary").click()
        page.wait_for_timeout(100)
    for field, value in values.items():
        page.fill(f"#{field}", str(value))
    page.locator("form button:has-text('Save settings')").click()
    page.wait_for_timeout(300)


def open_prepay_amount(page, amount):
    page.locator(".row", has_text="Home loan").locator("button:has-text('Prepay or close')").click()
    page.wait_for_timeout(300)
    page.fill("#pp-amount", str(amount))
    page.wait_for_timeout(150)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = open_app(browser)

        card = page.locator(".row", has_text="Home loan").inner_text()
        check("loan card gives a suggested next step", "Add your returns" in card, card[-200:])

        open_prepay_amount(page, 500000)
        text = page.locator("#drawer-content").inner_text()
        check("drawer shows the comparison heading", "Compare with other uses of this cash" in text)
        check("drawer asks for returns when none are set", "Set a savings rate or stock estimates" in text)
        check("drawer shows the suggested next step", "suggested next step" in text.lower())
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Emergency fund below the target comes first.
        open_settings(page, {"ls-em": 6, "ls-ls": 100000, "ls-me": 50000})
        card = page.locator(".row", has_text="Home loan").inner_text()
        check("emergency fund gate shows months covered", "Build your emergency fund first (2.0 of 6 months covered)" in card, card[-220:])

        # Enough cash: prepaying is not gated, and savings and stocks are compared.
        open_settings(page, {"ls-ls": 400000, "ls-sr": 6, "ls-sb": 10})
        card = page.locator(".row", has_text="Home loan").inner_text()
        check("with enough cash, the gate lifts", "emergency fund first" not in card)
        check("stock base beats prepay, so the advice says keep the loan", "Keep the loan and put the cash to work" in card, card[-220:])

        open_prepay_amount(page, 500000)
        text = page.locator("#drawer-content").inner_text()
        check("drawer lists savings and stock options", "Savings or FD" in text and "Stocks or index, base" in text)
        check("stock options say they are not guaranteed", "Stock returns are not guaranteed" in text)
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Lower the stock and savings estimates: prepaying now comes out ahead.
        open_settings(page, {"ls-sr": 3, "ls-sb": 5})
        card = page.locator(".row", has_text="Home loan").inner_text()
        check("prepaying beats lower alternatives", "Prepaying beats the alternatives" in card, card[-220:])

        # The threshold moves a loan into the pay-down-first group.
        open_settings(page, {"ls-hr": 8})
        card = page.locator(".row", has_text="Home loan").inner_text()
        check("rate above the threshold says pay down first", "Pay this down first" in card, card[-220:])

        check("no script errors", errors == [], str(errors))
        page.close()

        for width in (320, 390):
            page, errors = open_app(browser, width=width)
            open_prepay_amount(page, 500000)
            scroll_w, inner_w = page.evaluate(PAGE_SCROLL)
            check(f"{width}px: comparison fits the screen", scroll_w <= inner_w, f"{scroll_w}>{inner_w}")
            check(f"{width}px: no script errors", errors == [], str(errors))
            page.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nLOAN COMPARE RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
