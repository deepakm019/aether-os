from __future__ import annotations

from playwright.sync_api import Page, expect


def test_create_task_and_open_its_inspector(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="projects"]').click()
    app_page.get_by_role("button", name="Add Task").click()
    app_page.locator("#task-title").fill("Playwright-created task")
    app_page.locator("#task-desc").fill("Created by the browser test")
    app_page.get_by_role("button", name="Save Item (+25 XP)").click()

    card = app_page.locator(".task-card").filter(has_text="Playwright-created task")
    expect(card).to_be_visible()
    card.locator("div").filter(has_text="Playwright-created task").first.click()
    expect(app_page.locator("#drawer-task-title")).to_have_value("Playwright-created task")


def test_create_workout_and_render_canvas_chart(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="workout"]').click()
    app_page.get_by_role("button", name="Log Session").click()
    app_page.locator("#wo-title").fill("Playwright workout")
    app_page.locator("#wo-duration").fill("30")
    app_page.get_by_role("button", name="Commit (+100 XP)").click()

    expect(app_page.locator(".flex-col").filter(has_text="Playwright workout").first).to_be_visible()
    expect(app_page.locator("#workout-chart")).to_be_visible()
    expect(app_page.locator("#workout-chart-legend")).to_contain_text("Strength")


def test_create_story_finance_entry_note_and_checkpoint(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="stories"]').click()
    app_page.get_by_role("button", name="New Story").click()
    app_page.locator("#story-title").fill("Playwright story")
    app_page.get_by_role("button", name="Commit Story (+50 XP)").click()
    expect(app_page.locator("#content")).to_contain_text("Playwright story")

    app_page.locator('.nav-item[data-view="finance"]').click()
    app_page.get_by_role("button", name="Record Outflow").click()
    app_page.locator("#tx-desc").fill("Playwright transaction")
    app_page.locator("#tx-amount").fill("12")
    app_page.get_by_role("button", name="Log Entry").click()
    expect(app_page.locator("#content")).to_contain_text("Playwright transaction")

    app_page.locator('.nav-item[data-view="brain"]').click()
    app_page.get_by_role("button", name="Create Note").click()
    app_page.locator("#note-title").fill("Playwright note")
    app_page.locator("#note-content").fill("Local encrypted test note")
    app_page.get_by_role("button", name="Save Note (+35 XP)").click()
    expect(app_page.locator("#content")).to_contain_text("Playwright note")

    app_page.locator('.nav-item[data-view="snapshots"]').click()
    app_page.get_by_role("button", name="Take Checkpoint").click()
    expect(app_page.locator("#content")).to_contain_text("Checkpoint #")


def test_edit_note_category_and_create_editable_task_from_note(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="brain"]').click()
    app_page.get_by_role("button", name="Create Note").click()
    app_page.locator("#note-title").fill("Note to refine")
    app_page.locator("#note-category").fill("Engineering")
    app_page.locator("#note-content").fill("Implementation details from the note")
    app_page.get_by_role("button", name="Save Note (+35 XP)").click()

    note_card = app_page.locator('.card[data-action="note-open"]').filter(has_text="Note to refine")
    expect(note_card).to_contain_text("Engineering")
    note_card.click()
    expect(app_page.locator("#note-modal-title")).to_have_text("Note Details")
    expect(app_page.locator("#note-category")).to_have_value("Engineering")

    app_page.locator("#note-title").fill("Refined note")
    app_page.locator("#note-category").fill("Architecture")
    app_page.get_by_role("button", name="Save Changes").click()
    note_card = app_page.locator('.card[data-action="note-open"]').filter(has_text="Refined note")
    expect(note_card).to_contain_text("Architecture")

    note_card.click()
    app_page.get_by_role("button", name="Create Task").click()
    expect(app_page.locator("#task-title")).to_have_value("Refined note")
    expect(app_page.locator("#task-desc")).to_have_value("Implementation details from the note")
    app_page.locator("#task-title").fill("Task refined from note")
    app_page.get_by_role("button", name="Save Item (+25 XP)").click()

    app_page.locator('.nav-item[data-view="projects"]').click()
    task_card = app_page.locator(".task-card").filter(has_text="Task refined from note")
    expect(task_card).to_be_visible()
    task_card.click()
    expect(app_page.locator("#drawer-task-title")).to_have_value("Task refined from note")


def test_timer_and_theme_controls_work(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="timeview"]').click()
    app_page.get_by_role("button", name="Start Stopwatch").click()
    expect(app_page.locator("#global-timer-pill")).to_be_visible()
    expect(app_page.locator("#chrono-actions-row")).to_contain_text("Pause Timer")
    expect(app_page.locator("#chrono-view-clock")).to_have_text("00:01", timeout=3000)

    app_page.locator("#theme-btn").click()
    expect(app_page.locator("html")).to_have_attribute("data-theme", "light")


def test_standalone_mode_uses_encrypted_local_storage(app_page: Page, app_url: str) -> None:
    standalone_url = app_url.replace("index.html", "standalone.html")
    app_page.goto(standalone_url)
    standalone_app = app_page.frame_locator("iframe")
    expect(standalone_app.get_by_role("heading", name="Aether Vault Core")).to_be_visible()

    result = standalone_app.locator("body").evaluate(
        """async () => {
            const passphrase = 'standalone-storage-test-passphrase';
            const marker = 'private-roundtrip-marker';
            const envelope = await WebCrypto.encrypt({ marker }, passphrase);
            try {
                await StorageEngine.set(DB_KEY, envelope);
                const stored = localStorage.getItem(StorageEngine.localStorageKey(DB_KEY));
                const decrypted = await WebCrypto.decrypt(await StorageEngine.get(DB_KEY), passphrase);
                return {
                    localOnly: StorageEngine.localOnly,
                    indexedDbDisabled: await StorageEngine.init() === null,
                    separateKey: StorageEngine.localStorageKey(DB_KEY) !== DB_KEY,
                    encryptedAtRest: stored !== null && !stored.includes(marker),
                    roundTrip: decrypted.marker === marker
                };
            } finally {
                await StorageEngine.remove(DB_KEY);
            }
        }"""
    )

    assert result == {
        "localOnly": True,
        "indexedDbDisabled": True,
        "separateKey": True,
        "encryptedAtRest": True,
        "roundTrip": True,
    }
