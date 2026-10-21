"""Dog training companion: it is a normal app. It is always in More, opens without a setup step,
Settings has no workspace switch, the 55 skills render, and logging an event updates the saved dog data."""
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


def test_dog_training_is_always_available_like_any_app(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser, app_server)

        # No workspace switch in Settings and no "turn on" gate.
        page.evaluate("() => setNav('settings')")
        page.wait_for_timeout(200)
        assert page.locator("button:has-text('Dog training companion')").count() == 0
        assert page.locator("button:has-text('Existing setup')").count() == 0

        # The More tile is there straight away and the page opens with its skills.
        page.evaluate("() => setNav('more')")
        page.wait_for_timeout(200)
        assert page.locator("text=Dog training").count() >= 1
        page.evaluate("() => setNav('dog')")
        page.wait_for_timeout(300)
        assert page.locator("text=Dog training is off.").count() == 0
        assert page.locator(".dog-card").count() == 55
        assert errors == [], errors
        browser.close()


def test_dog_page_shows_all_skills_and_logs_events(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser, app_server)
        page.evaluate("() => setNav('dog')")
        page.wait_for_timeout(300)
        assert errors == [], errors
        assert page.locator(".dog-card").count() == 55
        # Outdoor filter shows outdoor and both-environment skills only.
        page.click("button[data-dog-val='outdoor']")
        page.wait_for_timeout(200)
        count = page.locator(".dog-card").count()
        assert 0 < count < 55

        # Logging a potty break updates the saved dog data (potty buttons live on the Care tab).
        page.click("button[data-dog-act='tab'][data-dog-val='care']")
        page.wait_for_timeout(200)
        page.click("button[data-dog-act='potty'][data-dog-val='pee']")
        page.wait_for_timeout(200)
        assert page.locator(".row-title", has_text="pee").count() >= 1

        # Marking a skill mastered adds XP (skill cards live on the Train tab).
        page.click("button[data-dog-act='tab'][data-dog-val='train']")
        page.wait_for_timeout(200)
        page.click("button[data-dog-act='env'][data-dog-val='all']")
        page.click(".dog-card >> nth=0")
        page.click("button[data-dog-act='toggleDone']")
        page.wait_for_timeout(200)
        xp = page.locator(".metric", has_text="XP").locator(".value").inner_text()
        assert int(xp.strip()) > 0

        assert errors == [], errors
        browser.close()


def test_skill_opens_in_a_modal_and_closes(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx, page, errors = open_app(browser, app_server)
        page.evaluate("() => setNav('dog')")
        page.wait_for_timeout(300)
        page.click("button[data-dog-act='tab'][data-dog-val='train']")
        page.wait_for_timeout(200)

        # The 20th card opens a dialog in the modal layer, not a section below the grid.
        page.locator(".dog-card").nth(20).click()
        page.wait_for_timeout(300)
        assert page.locator("#modal[data-dog-skill] [role='dialog']").count() == 1
        assert page.locator("#modal").is_visible()
        assert page.locator("#app section.panel .dog-steps").count() == 0

        # Marking mastered updates the open modal in place.
        page.click("#modal button[data-dog-act='toggleDone']")
        page.wait_for_timeout(200)
        assert page.locator("#modal button[data-dog-act='toggleDone']").inner_text().startswith("Undo")

        # Escape closes it.
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        assert not page.locator("#modal").is_visible()

        # Reopen and close with the close button.
        page.locator(".dog-card").nth(3).click()
        page.wait_for_timeout(200)
        page.click("#modal button[aria-label='Close']")
        page.wait_for_timeout(200)
        assert not page.locator("#modal").is_visible()

        assert errors == [], errors
        browser.close()
