"""Diet notes under More: reachable from More, keyword search finds foods by name,
alias or tag, category filters narrow the list, and the page fits a phone without sideways scrolling."""
from playwright.sync_api import sync_playwright


def _open_diet(page, app_server):
    page.goto(app_server, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => setNav('more')")
    page.wait_for_timeout(200)
    page.get_by_role("button", name="Diet Food notes, keyword search, portions").click()
    page.wait_for_selector("#diet-q")


def _titles(page):
    return page.locator("#diet-results .diet-card b").all_text_contents()


def test_diet_is_reachable_from_more_and_searchable(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        _open_diet(page, app_server)

        all_count = page.locator("#diet-results .diet-card").count()
        assert all_count >= 40, all_count

        page.fill("#diet-q", "clove")
        page.wait_for_timeout(150)
        assert "Laung (Clove)" in _titles(page), _titles(page)

        page.fill("#diet-q", "jira")
        page.wait_for_timeout(150)
        assert "Jeera (Cumin)" in _titles(page), _titles(page)

        page.fill("#diet-q", "stamina")
        page.wait_for_timeout(150)
        titles = _titles(page)
        assert "Ashwagandha (Winter Cherry)" in titles and "Almonds & Walnuts" in titles, titles

        page.fill("#diet-q", "zzzz-no-such-food")
        page.wait_for_timeout(150)
        assert page.locator("#diet-results .diet-card").count() == 0
        assert "No foods match" in page.locator("#diet-results").text_content()

        page.fill("#diet-q", "")
        page.get_by_role("button", name="Occasional Treats").click()
        page.wait_for_timeout(200)
        assert page.locator("#diet-results .diet-card").count() < all_count
        assert "Samosa (fried, 1 medium)" in _titles(page)

        overflow = page.evaluate(
            "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
        assert overflow == 0, f"overflow {overflow}px"
        assert not errors, errors
        browser.close()
