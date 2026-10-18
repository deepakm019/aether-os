"""Dog training companion: the workspace setting is mutually exclusive with the
existing setup, the dog menu item only appears when it is active, the 55 skills
render, and logging an event updates the saved dog data."""
from playwright.sync_api import sync_playwright


def open_app(browser, url):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(400)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(400)
    return ctx, page, errors


def pressed(page, label):
    return page.get_attribute(f"button:has-text('{label}')", "aria-pressed")


def test_workspace_choice_is_mutually_exclusive(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser, app_server)

        page.evaluate("() => setNav('settings')")
        page.wait_for_timeout(200)
        assert pressed(page, "Existing setup") == "true"
        assert pressed(page, "Dog training companion") == "false"

        # Dog training is off, so its menu tile is hidden.
        page.evaluate("() => setNav('more')")
        page.wait_for_timeout(200)
        assert page.locator("text=Dog training").count() == 0

        # Turning dog training on turns existing setup off.
        page.evaluate("() => setNav('settings')")
        page.click("button:has-text('Dog training companion')")
        page.wait_for_timeout(300)
        assert errors == [], errors
        assert pressed(page, "Dog training companion") == "true"
        assert pressed(page, "Existing setup") == "false"

        # The menu tile now appears.
        page.evaluate("() => setNav('more')")
        page.wait_for_timeout(200)
        assert page.locator("text=Dog training").count() >= 1

        # Switching back restores existing setup and hides the tile again.
        page.evaluate("() => setNav('settings')")
        page.click("button:has-text('Existing setup')")
        page.wait_for_timeout(300)
        assert pressed(page, "Existing setup") == "true"
        page.evaluate("() => setNav('more')")
        page.wait_for_timeout(200)
        assert page.locator("text=Dog training").count() == 0

        assert errors == [], errors
        browser.close()


def test_dog_page_is_blocked_while_existing_setup_is_active(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser, app_server)
        page.evaluate("() => setNav('dog')")
        page.wait_for_timeout(200)
        assert page.locator("text=Dog training is off.").count() == 1
        assert page.locator(".dog-card").count() == 0
        assert errors == [], errors
        browser.close()


def test_dog_page_shows_all_skills_and_logs_events(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser, app_server)
        page.evaluate("() => setNav('settings')")
        page.wait_for_timeout(200)
        page.click("button:has-text('Dog training companion')")
        page.wait_for_timeout(200)
        page.evaluate("() => setNav('dog')")
        page.wait_for_timeout(300)
        assert errors == [], errors
        assert page.locator(".dog-card").count() == 55
        # Outdoor filter shows outdoor and both-environment skills only.
        page.click("button[data-dog-val='outdoor']")
        page.wait_for_timeout(200)
        count = page.locator(".dog-card").count()
        assert 0 < count < 55

        # Logging a potty break updates the saved dog data.
        page.click("button[data-dog-act='potty'][data-dog-val='pee']")
        page.wait_for_timeout(200)
        assert page.locator(".row-title", has_text="pee").count() >= 1

        # Marking a skill mastered adds XP.
        page.click("button[data-dog-act='env'][data-dog-val='all']")
        page.click(".dog-card >> nth=0")
        page.click("button[data-dog-act='toggleDone']")
        page.wait_for_timeout(200)
        xp = page.locator(".metric", has_text="XP").locator(".value").inner_text()
        assert int(xp.strip()) > 0

        assert errors == [], errors
        browser.close()
