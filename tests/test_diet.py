"""Diet notes under More: responsive card grid, category sections, tag filtering, detail modal,
and Diet foods in global search. Checks phone and desktop widths and fails on JavaScript errors."""
from playwright.sync_api import sync_playwright


def _start(page, app_server, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(app_server, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)


def _columns(page):
    return page.evaluate(
        "() => { const g = document.querySelector('#diet-results .diet-grid');"
        " return g ? getComputedStyle(g).gridTemplateColumns.split(' ').length : 0; }")


def _overflow(page):
    return page.evaluate(
        "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")


def test_diet_layout_search_tags_and_details(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        errors = []

        # Phone: one column, no sideways scroll.
        phone = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        phone.on("pageerror", lambda e: errors.append(str(e)))
        _start(phone, app_server, 390)
        phone.evaluate("() => setNav('diet')")
        phone.wait_for_selector("#diet-q")
        assert _columns(phone) == 1, _columns(phone)
        assert _overflow(phone) == 0, _overflow(phone)

        # Desktop: three columns, no sideways scroll.
        desktop = browser.new_context(viewport={"width": 1280, "height": 900}).new_page()
        desktop.on("pageerror", lambda e: errors.append(str(e)))
        _start(desktop, app_server, 1280)
        desktop.evaluate("() => setNav('diet')")
        desktop.wait_for_selector("#diet-q")
        assert _columns(desktop) == 3, _columns(desktop)
        assert _overflow(desktop) == 0, _overflow(desktop)
        headings = desktop.locator("#diet-results .diet-section h3").all_text_contents()
        assert any("Spices & Herbs" in h for h in headings), headings

        # Search by alias.
        desktop.fill("#diet-q", "jira")
        desktop.wait_for_timeout(150)
        assert desktop.locator("#diet-results .diet-card .diet-name", has_text="Jeera (Cumin)").count() == 1

        # Tag chip sets the search.
        desktop.fill("#diet-q", "")
        desktop.wait_for_timeout(100)
        desktop.locator("#diet-results .diet-tag", has_text="#stamina").first.click()
        desktop.wait_for_timeout(150)
        assert desktop.input_value("#diet-q") == "stamina"
        names = desktop.locator("#diet-results .diet-name").all_text_contents()
        assert "Almonds & Walnuts" in names and "Ashwagandha (Winter Cherry)" in names, names

        # No match message.
        desktop.fill("#diet-q", "zzzz-no-such-food")
        desktop.wait_for_timeout(150)
        assert "No foods match" in desktop.locator("#diet-results").text_content()

        # Card opens the detail modal with benefits and do / don't lists.
        desktop.fill("#diet-q", "clove")
        desktop.wait_for_timeout(150)
        desktop.locator(".diet-card", has_text="Laung (Clove)").click()
        desktop.wait_for_selector("#modal .diet-detail")
        modal = desktop.locator("#modal .diet-detail").text_content()
        assert "Laung (Clove)" in modal and "Benefits" in modal and "Don't" in modal, modal[:200]
        desktop.get_by_role("button", name="Close details").click()
        desktop.wait_for_timeout(150)

        # Global search returns Diet foods and opens the same detail view.
        desktop.keyboard.press("Control+k")
        desktop.wait_for_selector("#search-input")
        desktop.fill("#search-input", "clove")
        desktop.wait_for_timeout(200)
        row = desktop.locator(".search-row", has_text="Laung (Clove)")
        assert row.count() >= 1, desktop.locator("#search-results").text_content()
        row.get_by_role("button", name="Open").click()
        desktop.wait_for_selector("#modal .diet-detail")
        assert "Laung (Clove)" in desktop.locator("#modal .diet-detail").text_content()

        assert not errors, errors
        browser.close()
