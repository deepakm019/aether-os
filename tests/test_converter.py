"""Unit converter: known conversions, invalid input, and a phone-width layout check."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def result(page):
    return page.locator("#conv-result").text_content().strip()


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(URL, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)
        page.evaluate("() => setNav('convert')")
        page.wait_for_timeout(250)

        check("default is 1 ft = 0.3048 m", "0.3048 m" in result(page), result(page))

        page.select_option("#conv-cat", "weight")
        page.wait_for_timeout(150)
        page.select_option("#conv-from", "lb")
        page.select_option("#conv-to", "kg")
        page.fill("#conv-value", "1")
        page.wait_for_timeout(150)
        check("1 lb = 0.453592 kg", "0.453592 kg" in result(page), result(page))

        page.select_option("#conv-cat", "temperature")
        page.wait_for_timeout(150)
        page.select_option("#conv-from", "C")
        page.select_option("#conv-to", "F")
        page.fill("#conv-value", "100")
        page.wait_for_timeout(150)
        check("100 C = 212 F", "212 F" in result(page), result(page))

        page.select_option("#conv-to", "K")
        page.fill("#conv-value", "0")
        page.wait_for_timeout(150)
        check("0 C = 273.15 K", "273.15 K" in result(page), result(page))

        page.select_option("#conv-cat", "length")
        page.wait_for_timeout(150)
        page.select_option("#conv-from", "mi")
        page.select_option("#conv-to", "km")
        page.fill("#conv-value", "10")
        page.wait_for_timeout(150)
        check("10 mi = 16.0934 km", "16.0934 km" in result(page), result(page))

        page.fill("#conv-value", "abc")
        page.wait_for_timeout(150)
        check("non-number shows an error", "Enter a valid number." in result(page), result(page))

        page.fill("#conv-value", "")
        page.wait_for_timeout(150)
        check("empty input asks for a number", "Enter a number" in result(page), result(page))

        page.fill("#conv-value", "5")
        page.get_by_role("button", name="Swap units").click()
        page.wait_for_timeout(200)
        check("swap reverses the units: 5 km = 3.10686 mi", "5 km = 3.10686 mi" in result(page), result(page))

        overflow = page.evaluate(
            "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
        check("converter fits a 390 px phone without sideways scrolling", overflow == 0, f"overflow {overflow}px")
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nCONVERTER RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
