"""Today's Top 3 reads as one ranked list: numbered rows, one 'Next' task, priority colour and friendly due dates."""
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


def test_top3_is_numbered_marks_one_next_task_and_uses_friendly_due_labels(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = _open_today(browser, app_server)
        section = page.locator("section", has=page.locator("#top-today-title"))
        rows = section.locator(".top3-row")
        count = rows.count()
        assert 1 <= count <= 3, count

        ranks = [rows.nth(i).locator(".top3-rank").text_content().strip() for i in range(count)]
        assert ranks == [str(i + 1) for i in range(count)], ranks

        assert section.locator(".top3-next").count() == 1, "exactly one task should be marked Next"

        metas = [rows.nth(i).locator(".row-meta").text_content().strip() for i in range(count)]
        for meta in metas:
            assert meta.split(" · ")[0] in ("High", "Medium", "Low"), meta
        joined = " | ".join(metas)
        assert "Due today" in joined or "Overdue" in joined or "Due " in joined, joined
        assert "2026-" not in joined, f"raw ISO dates should not show: {joined}"

        for i in range(count):
            label = rows.nth(i).get_by_role("button", name="Start focus on")
            assert label.count() == 1, "each row should have a labelled Start focus action"
        assert errors == [], errors
        browser.close()
