"""Dog training: mastered skills move to Archived, water and treat logs, and a focus timer that can be dragged up or down."""
from playwright.sync_api import sync_playwright


def _open_dog(page, url, width=1280):
    page.set_viewport_size({"width": width, "height": 900})
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => { setWorkspace('dog'); }")
    page.wait_for_timeout(300)


def test_mastered_skills_move_to_archive(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        _open_dog(page, app_server)
        page.evaluate("() => { DogCompanion._act('toggleDone', 'name'); setNav('dog'); }")
        page.wait_for_timeout(300)
        archive = page.locator("aside.dog-archive")
        assert archive.count() == 1
        assert "Name recognition" in archive.inner_text()
        main = page.locator(".dog-train-layout > .grid")
        assert "Name recognition" not in main.inner_text(), "mastered skill still in main grid"
        archive.locator("button", has_text="Restore").click()
        page.wait_for_timeout(300)
        assert "Name recognition" in page.locator(".dog-train-layout > .grid").inner_text()
        browser.close()


def test_water_and_treat_logs(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        _open_dog(page, app_server)
        page.evaluate("() => setNav('dog')")
        page.wait_for_timeout(200)
        page.evaluate("() => { DogCompanion._act('tab', 'care'); }")
        page.wait_for_timeout(200)
        page.click("button[data-dog-act='drink']")
        page.wait_for_timeout(200)
        page.click("button[data-dog-act='treat']")
        page.wait_for_timeout(200)
        text = page.locator("body").inner_text()
        assert "Water" in text and "Treat" in text
        browser.close()


def test_focus_timer_drags_up_and_down(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        _open_dog(page, app_server, 1280)
        page.evaluate("() => { startFreeFocus(); setNav('today'); }")
        page.wait_for_timeout(400)
        overlay = page.locator("#focus-overlay")
        assert overlay.is_visible()
        grip = page.locator(".focus-overlay-grip")
        box = grip.bounding_box()
        start_top = overlay.bounding_box()["y"]
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2 - 120, steps=8)
        page.mouse.up()
        page.wait_for_timeout(100)
        up_top = overlay.bounding_box()["y"]
        assert up_top < start_top - 60, f"did not move up: {start_top} -> {up_top}"
        assert page.evaluate("() => localStorage.getItem('asos.focusOverlayY')") is not None
        grip.focus()
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(50)
        assert overlay.bounding_box()["y"] > up_top
        browser.close()
