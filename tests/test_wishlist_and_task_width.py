"""Things to buy (Money) adds, marks bought and removes items; task cards keep a readable measure."""
from playwright.sync_api import sync_playwright


def _open(page, url, width):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)


def test_task_cards_have_readable_measure(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for width in (320, 390, 768, 1280):
            page = browser.new_page()
            _open(page, app_server, width)
            page.evaluate("() => { window.workTab = 'Inbox'; setNav('work'); }")
            page.wait_for_timeout(250)
            lists = page.locator(".list:has(> .task-card)")
            if lists.count() == 0:
                page.close()
                continue
            box = lists.first.bounding_box()
            assert box and box["width"] <= 760, f"{width}px list too wide: {box}"
            assert page.evaluate("() => document.documentElement.scrollWidth") <= width, f"{width}px horizontal scroll"
            page.close()
        browser.close()


def test_wishlist_add_bought_remove(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.on("dialog", lambda d: d.accept())
        _open(page, app_server, 1280)
        page.evaluate("() => setNav('money')")
        page.wait_for_timeout(250)
        panel = page.locator("section", has=page.locator("#wishlist-title"))
        assert panel.count() == 1
        panel.locator("button", has_text="+ Item").click()
        page.fill("#modal input[name=title]", "Test <b>headphones</b>")
        page.fill("#modal input[name=price]", "8500")
        page.click("#modal button.primary")
        page.wait_for_timeout(250)
        panel = page.locator("section", has=page.locator("#wishlist-title"))
        assert "Test <b>headphones</b>" in panel.inner_text()
        assert page.locator("#app b", has_text="headphones").count() == 0, "title must be escaped"
        panel.locator("button", has_text="Bought").click()
        page.wait_for_timeout(200)
        assert panel.locator("button", has_text="Undo").count() == 1
        panel.locator("button", has_text="Remove").click()
        page.wait_for_timeout(200)
        assert "headphones" not in page.locator("section", has=page.locator("#wishlist-title")).inner_text()
        browser.close()
