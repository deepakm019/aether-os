"""Minimal mode uses the main app's theme, background and font, and returning to normal keeps your data.

Covers: normal -> minimal -> normal, a reload while in minimal, and the Today list after returning.
"""
from playwright.sync_api import sync_playwright

LOOK = """() => {
  const b = getComputedStyle(document.body);
  return { bg: b.backgroundColor, font: b.fontFamily, dataFont: document.documentElement.dataset.font,
           minimal: document.documentElement.classList.contains('minimal-mode-active') };
}"""


def _open(browser, url):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    return page, errors


def test_minimal_matches_main_theme_and_font_and_returns_cleanly(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = _open(browser, app_server)
        page.evaluate("() => { setSetting('theme', 'Reading'); setSetting('font', 'nunito'); }")
        page.wait_for_timeout(1200)  # let the normal workspace save
        normal = page.evaluate(LOOK)
        assert normal["bg"] == "rgb(244, 236, 216)", normal

        page.evaluate("() => switchMinimalMode('minimal')")
        page.wait_for_timeout(900)
        assert page.locator(".minimal-app").count() == 1
        minimal = page.evaluate(LOOK)
        assert minimal["minimal"] is True
        assert minimal["bg"] == normal["bg"], f"minimal background differs: {minimal} vs {normal}"
        assert minimal["font"] == normal["font"] and minimal["dataFont"] == "nunito", minimal

        # A reload while in minimal mode must still show the same look.
        page.reload(wait_until="load")
        page.wait_for_selector(".minimal-app")
        page.wait_for_timeout(600)
        reloaded = page.evaluate(LOOK)
        assert reloaded["bg"] == normal["bg"] and reloaded["font"] == normal["font"], reloaded

        # Returning to normal restores the same look and the saved tasks.
        page.evaluate("() => switchMinimalMode('normal')")
        page.wait_for_timeout(1500)
        back = page.evaluate(LOOK)
        assert back["minimal"] is False
        assert back["bg"] == normal["bg"] and back["font"] == normal["font"], back
        page.evaluate("() => setNav('today')")
        page.wait_for_timeout(300)
        assert page.locator(".top3-row").count() == 3, "saved tasks should be back after returning"
        assert errors == [], errors
        browser.close()
