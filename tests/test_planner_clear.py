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


def _open_plan(page, app_server, dialogs=None):
    page.on("dialog", lambda d: (dialogs.append(d.message) if dialogs is not None else None, d.dismiss()))
    _open(page, app_server)
    page.evaluate("() => setNav('plan')")
    page.wait_for_timeout(250)


def test_plan_block_removal_needs_no_dialog_and_undo_restores_it(app_server):
    """Removal is immediate (no native confirm that can be suppressed) and an Undo action brings the block back."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        dialogs = []
        _open_plan(page, app_server, dialogs)
        page.locator(".plan-row", has_text="Lunch").locator("button", has_text="Remove").click()
        page.wait_for_timeout(200)
        assert dialogs == [], f"removal should not open a dialog: {dialogs}"
        assert page.locator(".plan-row", has_text="Lunch").count() == 0
        page.locator("#toast .toast-action", has_text="Undo").click()
        page.wait_for_timeout(200)
        titles = [page.locator(".plan-row").nth(i).locator(".row-title").text_content()
                  for i in range(page.locator(".plan-row").count())]
        assert titles == ["Client meeting", "Lunch", "Deep work"], f"undo should restore the original order: {titles}"
        browser.close()


def test_clear_plan_empties_the_list_and_undo_restores_every_block(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        _open_plan(page, app_server)
        page.locator("button", has_text="Clear plan").click()
        page.wait_for_timeout(200)
        assert page.locator(".plan-row").count() == 0
        assert page.locator("text=Nothing planned").count() == 1, "empty plan should show an empty state"
        page.locator("#toast .toast-action", has_text="Undo").click()
        page.wait_for_timeout(200)
        assert page.locator(".plan-row").count() == 3, "undo should restore all three blocks"
        browser.close()


def test_removed_plan_block_stays_removed_after_reload(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        _open_plan(page, app_server)
        page.locator(".plan-row", has_text="Client meeting").locator("button", has_text="Remove").click()
        page.wait_for_timeout(600)  # allow the save to finish
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(400)
        page.evaluate("() => setNav('plan')")
        page.wait_for_timeout(250)
        assert page.locator(".plan-row", has_text="Client meeting").count() == 0, "removal must persist"
        assert page.locator(".plan-row").count() == 2
        browser.close()


def test_upcoming_shows_real_due_tasks_not_sample_commitments(app_server):
    """Upcoming lists tasks due in the next 7 days. It has no sample rows, and clearing the plan does not change it."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.on("dialog", lambda d: d.accept())
        _open(page, app_server)
        page.evaluate("() => setNav('plan')")
        page.wait_for_timeout(250)
        table = page.locator("section", has_text="Upcoming").locator("tbody")
        text = table.text_content()
        for sample in ("Demo rehearsal", "Client follow-up", "Workout"):
            assert sample not in text, f"sample commitment still listed: {sample}"
        assert "Finish proposal" in text, "a task due today should appear under Upcoming"
        before = table.locator("tr").count()
        page.locator("button", has_text="Clear plan").click()
        page.wait_for_timeout(250)
        assert table.locator("tr").count() == before, "clearing the plan must not change Upcoming"
        browser.close()
