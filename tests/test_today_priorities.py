"""Today's morning card lists the day's priorities: numbered rows, the first one highlighted, each with a Focus action."""
from playwright.sync_api import sync_playwright


def _open_today(browser, url):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => setNav('today')")
    page.wait_for_timeout(300)
    return page, errors


def test_priorities_are_numbered_first_is_marked_and_each_has_focus(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = _open_today(browser, app_server)
        assert page.locator("#top-today-title").count() == 0, "the Top 3 panel should be gone"

        # Save today's check-in with the wizard's default priorities.
        page.click("button[onclick*='morningWizard']")
        page.wait_for_selector("#modal form")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_selector(".plan-priority")

        rows = page.locator(".plan-priority")
        count = rows.count()
        assert 1 <= count <= 3, count

        ranks = [rows.nth(i).locator(".plan-rank").text_content().strip() for i in range(count)]
        assert ranks == [str(i + 1) for i in range(count)], ranks

        assert page.locator(".plan-priority.is-first").count() == 1, "exactly one priority should be marked first"

        for i in range(count):
            assert rows.nth(i).locator("button", has_text="Focus").count() == 1, "each priority needs a Focus action"
        assert errors == [], errors
        browser.close()
