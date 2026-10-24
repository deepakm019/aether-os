"""Loans charts: touch, mouse and keyboard readouts with amounts, plus the chart types for the loans screen."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
PAGE_SCROLL = "() => [document.documentElement.scrollWidth, window.innerWidth]"
TIP = "el => el.querySelector('.lchart-tip').innerText"
ON = "el => el.classList.contains('on')"
INDEX = "el => el.dataset.i"

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


def point_at(page, chart, fraction, mode="mouse"):
    chart.evaluate("el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
    page.wait_for_timeout(80)
    box = chart.bounding_box()
    x = box["x"] + box["width"] * fraction
    y = box["y"] + box["height"] * 0.5
    if mode == "touch":
        chart.evaluate(
            """(chartEl, point) => {
                const [x, y] = point;
                const el = document.elementFromPoint(x, y);
                el.dispatchEvent(new PointerEvent('pointerdown', {clientX: x, clientY: y, pointerType: 'touch', bubbles: true}));
                el.dispatchEvent(new PointerEvent('pointermove', {clientX: x, clientY: y, pointerType: 'touch', bubbles: true}));
            }""",
            [x, y],
        )
    else:
        page.mouse.move(x, y)
    page.wait_for_timeout(120)


def set_returns(page):
    details = page.locator("#app details", has=page.locator("summary", has_text="Loan settings"))
    if not details.evaluate("d => d.open"):
        details.locator("summary").click()
        page.wait_for_timeout(100)
    page.fill("#ls-sr", "6")
    page.fill("#ls-sb", "10")
    page.locator("form button:has-text('Save settings')").click()
    page.wait_for_timeout(300)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = open_app(browser)

        # Schedule drawer: hover shows amounts at that point in the loan.
        page.locator(".row", has_text="Home loan").locator("button:has-text('Schedule')").click()
        page.wait_for_timeout(300)
        chart = page.locator("#drawer-content .lchart").first
        point_at(page, chart, 0.5)
        tip = chart.evaluate(TIP)
        check("mouse hover shows the chart tooltip", chart.evaluate(ON))
        check("tooltip names the month and both balances", "Balance left" in tip and "Interest paid so far" in tip, tip)
        check("tooltip shows an amount in rupees", "₹" in tip, tip)
        check("tooltip shows the date", "Month " in tip and " 20" in tip, tip)

        # Touch and drag: the readout follows the finger.
        point_at(page, chart, 0.1, mode="touch")
        tip_early = chart.evaluate(TIP)
        point_at(page, chart, 0.9, mode="touch")
        tip_late = chart.evaluate(TIP)
        check("touch shows the readout", "₹" in tip_early)
        check("dragging moves the readout to a later month", tip_early != tip_late)

        # Keyboard: arrows step through the points.
        chart.focus()
        page.keyboard.press("Home")
        page.wait_for_timeout(60)
        first = chart.evaluate(INDEX)
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(60)
        check("arrow keys move the readout", chart.evaluate(INDEX) == str(int(first) + 2), f"{first}->{chart.evaluate(INDEX)}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(60)
        check("escape clears the readout", not chart.evaluate(ON))

        # Yearly split bars: each year shows principal, interest and the balance left.
        point_at(page, page.locator("#drawer-content .lchart").nth(1), 0.5)
        bars_tip = page.locator("#drawer-content .lchart").nth(1).evaluate(TIP)
        check("yearly bars show principal and interest", "Principal" in bars_tip and "Interest" in bars_tip and "Balance left" in bars_tip, bars_tip)
        page.evaluate("() => closeDrawer()")
        page.wait_for_timeout(200)

        # Where the money goes: a bar per loan with a readout on hover.
        overview = page.locator(".lchart-h").first
        check("loans page shows interest left per loan", overview.count() == 1)
        point_at(page, overview, 0.2)
        check("hovering a loan bar shows its EMI and end date", "EMI" in overview.evaluate(TIP) and "ends" in overview.evaluate(TIP), overview.evaluate(TIP))

        # The calculator chart reads out values too.
        calc = page.locator("#loan-calc-out .lchart").first
        point_at(page, calc, 0.4)
        check("calculator chart reads out values", "₹" in calc.evaluate(TIP), calc.evaluate(TIP))

        # Prepay drawer: balance paths, timing and options bars.
        set_returns(page)
        page.locator(".row", has_text="Home loan").locator("button:has-text('Prepay or close')").click()
        page.wait_for_timeout(300)
        page.fill("#pp-amount", "500000")
        page.wait_for_timeout(250)
        drawer_charts = page.locator("#drawer-content .lchart")
        check("prepay drawer has balance, timing and option charts", drawer_charts.count() >= 3, f"count={drawer_charts.count()}")
        paths = drawer_charts.nth(0)
        point_at(page, paths, 0.3)
        paths_tip = paths.evaluate(TIP)
        check("balance chart compares keep, shorten and reduce", "Keep as is" in paths_tip and "Shorten tenure" in paths_tip and "Reduce EMI" in paths_tip, paths_tip)
        options = page.locator("#drawer-content .lchart-h").first
        point_at(page, options, 0.3)
        check("option bars show a yearly return on hover", "% a year" in options.evaluate(TIP), options.evaluate(TIP))
        check("no script errors in the chart flows", errors == [], str(errors))
        page.close()

        for width in (320, 390):
            page, errors = open_app(browser, width=width)
            page.locator(".row", has_text="Home loan").locator("button:has-text('Prepay or close')").click()
            page.wait_for_timeout(300)
            page.fill("#pp-amount", "500000")
            page.wait_for_timeout(250)
            scroll_w, inner_w = page.evaluate(PAGE_SCROLL)
            check(f"{width}px: charts fit the screen", scroll_w <= inner_w, f"{scroll_w}>{inner_w}")
            check(f"{width}px: no script errors", errors == [], str(errors))
            page.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nLOAN CHARTS RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
