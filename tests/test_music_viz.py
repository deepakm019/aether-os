"""Music transport uses SVG icons (no emoji glyphs), and the visualiser cycles bars -> oscilloscope -> off,
persisting its choice. The canvas is painted by the render loop, so a painted pixel proves the loop runs."""
import datetime
import os
import re

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
PREFS_KEY = "astralsurge.music.prefs.v2"
EMOJI = re.compile("[⏮⏭▶❰❤⤺↻↺]")


def _open_music(browser, width=390, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.clock.set_fixed_time(datetime.datetime(2026, 11, 28, 19, 30))
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => setNav('music')")
    page.wait_for_selector(".mu-page")
    return page, errors


def test_transport_icons_are_svg_and_visualiser_cycles(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = _open_music(browser)
        page.wait_for_timeout(200)

        dock_text = page.evaluate("() => document.querySelector('.mu-dock')?.textContent || ''")
        assert not EMOJI.search(dock_text), f"emoji still in dock: {dock_text!r}"
        assert page.locator(".mu-dock svg.mu-ico").count() >= 5, "transport icons missing"
        for label in ["Previous", "Next", "Shuffle"]:
            assert page.locator(f'.mu-dock [aria-label="{label}"] svg').count() == 1, label

        # Default is bars: canvas exists and the render loop paints the dark background
        assert page.locator("#mu-viz").count() == 1
        page.wait_for_timeout(300)
        px = page.evaluate("""() => { const c = document.getElementById('mu-viz');
            const d = c.getContext('2d').getImageData(c.width >> 1, c.height - 2, 1, 1).data;
            return [d[0], d[1], d[2]]; }""")
        assert px != [0, 0, 0], f"canvas not painted: {px}"

        # Cycle: bars -> scope -> off -> bars, persisted
        page.click('[data-mu="viz"]')
        page.wait_for_timeout(150)
        assert page.evaluate(f"() => JSON.parse(localStorage.getItem('{PREFS_KEY}')).viz") == "scope"
        assert page.locator("#mu-viz").count() == 1
        page.click('[data-mu="viz"]')
        page.wait_for_timeout(150)
        assert page.evaluate(f"() => JSON.parse(localStorage.getItem('{PREFS_KEY}')).viz") == "off"
        assert page.locator("#mu-viz").count() == 0, "canvas should be hidden when off"
        page.click('[data-mu="viz"]')
        page.wait_for_timeout(150)
        assert page.evaluate(f"() => JSON.parse(localStorage.getItem('{PREFS_KEY}')).viz") == "bars"
        assert page.locator("#mu-viz").count() == 1

        assert not errors, errors
        browser.close()
