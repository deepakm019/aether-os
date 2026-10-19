"""Plan blocks, including fixed commitments, can be cleared; the Calendar's planned marker opens Plan."""
from playwright.sync_api import sync_playwright


def _open(page, url, width=1280):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)


def test_fixed_plan_block_can_be_cleared(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.on("dialog", lambda d: d.accept())
        _open(page, app_server)
        page.evaluate("() => setNav('plan')")
        page.wait_for_timeout(250)
        row = page.locator(".plan-row", has_text="Client meeting")
        assert row.count() == 1, "seeded fixed block should be listed in Plan"
        row.locator("button", has_text="Remove").click()
        page.wait_for_timeout(250)
        assert page.locator(".plan-row", has_text="Client meeting").count() == 0, "fixed block must be removable"
        browser.close()


def test_calendar_planned_marker_opens_plan(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        _open(page, app_server)
        page.evaluate("() => setNav('calendar')")
        page.wait_for_timeout(250)
        marker = page.locator("button", has_text="planned · manage")
        assert marker.count() == 1, "calendar should expose a manage link for today's plan"
        marker.click()
        page.wait_for_timeout(250)
        assert page.locator(".plan-row").count() > 0, "marker should open the Plan view"
        browser.close()
