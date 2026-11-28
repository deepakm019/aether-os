"""Budgets on phones: a category opens a popup where line items are added, edited, paid and deleted
without browser prompt() dialogs. Spending can be reset per category or for all expenses. The Money
page fits 320 px and 390 px without sideways scrolling."""
import datetime

from playwright.sync_api import sync_playwright


def _open_money(browser, app_server, width=390):
    ctx = browser.new_context(viewport={"width": width, "height": 844})
    page = ctx.new_page()
    errors, dialogs = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))

    def on_dialog(d):
        dialogs.append(d.type)
        d.accept()

    page.on("dialog", on_dialog)
    page.clock.set_fixed_time(datetime.datetime(2026, 11, 28, 19, 30))
    page.goto(app_server, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => setNav('money')")
    page.wait_for_timeout(250)
    return page, errors, dialogs


def _overflow(page):
    return page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")


def test_budget_popup_manages_items_without_prompts(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors, dialogs = _open_money(browser, app_server)
        assert _overflow(page) == 0

        page.locator(".budget-row").first.click()
        page.wait_for_selector("#modal .budget-popup")
        box = page.locator("#modal").bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 390 + 1, box
        assert _overflow(page) == 0

        # Add a line item from the popup.
        page.fill("#modal input[name=title]", "Test internet bill")
        page.fill("#modal input[name=amount]", "499")
        page.get_by_role("button", name="Add item").click()
        page.wait_for_selector("#modal .bp-item:has-text('Test internet bill')")

        # Edit it in the popup (no prompt dialogs).
        item = page.locator("#modal .bp-item", has_text="Test internet bill")
        item.locator("button", has_text="Edit").click()
        page.wait_for_selector("#modal input[name=title]")
        assert page.input_value("#modal input[name=title]") == "Test internet bill"
        page.fill("#modal input[name=title]", "Internet (renamed)")
        page.fill("#modal input[name=amount]", "550")
        page.get_by_role("button", name="Save item").click()
        page.wait_for_selector("#modal .bp-item:has-text('Internet (renamed)')")

        # Pay it: the row shows Paid and the summary spent figure rises.
        spent_before = page.locator("#modal .bp-summary .value").first.inner_text()
        page.locator("#modal .bp-item", has_text="Internet (renamed)").locator("input[type=checkbox]").check()
        page.wait_for_selector("#modal .bp-item:has-text('Paid')")
        assert page.locator("#modal .bp-summary .value").first.inner_text() != spent_before

        # Reset this category's spending: paid one-time items become unpaid again.
        page.get_by_role("button", name="Reset spending").click()
        page.wait_for_timeout(250)
        assert "Paid" not in page.locator("#modal .bp-item", has_text="Internet (renamed)").inner_text()
        assert "₹0" in page.locator("#modal .bp-summary .value").first.inner_text()

        # Rename the category from the popup.
        page.get_by_role("button", name="Rename / limit").click()
        page.fill("#bp-cat-name", "Eating out")
        page.get_by_role("button", name="Save category").click()
        page.wait_for_selector("#modal h2:text-is('Eating out')")

        # Delete the test line item, then close.
        page.locator("#modal .bp-item", has_text="Internet (renamed)").locator("button", has_text="Delete").click()
        page.wait_for_timeout(250)
        assert page.locator("#modal .bp-item", has_text="Internet (renamed)").count() == 0
        page.click("#modal .icon-btn")
        page.wait_for_timeout(200)
        assert page.locator(".budget-row", has_text="Eating out").count() == 1

        assert "prompt" not in dialogs, dialogs
        assert not errors, errors[:3]
        browser.close()


def test_reset_all_expenses_and_new_category(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors, dialogs = _open_money(browser, app_server, width=320)
        assert _overflow(page) == 0

        page.get_by_role("button", name="+ Category").click()
        page.fill("#nb-name", "Groceries")
        page.fill("#nb-limit", "6000")
        page.get_by_role("button", name="Create category").click()
        page.wait_for_selector(".budget-row:has-text('Groceries')")

        page.get_by_role("button", name="Reset expenses").click()
        page.wait_for_timeout(250)
        assert page.locator(".table-wrap tbody tr").count() == 0
        assert "₹0 spent" in page.locator(".budget-row", has_text="Dining").inner_text()
        assert _overflow(page) == 0

        assert "prompt" not in dialogs, dialogs
        assert not errors, errors[:3]
        browser.close()
