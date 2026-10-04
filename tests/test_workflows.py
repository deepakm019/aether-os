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


def test_drag_task_between_kanban_columns(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="projects"]').click()
    source = app_page.locator("#board-inbox .task-card").first
    task_id = source.get_attribute("data-task-id")
    assert task_id
    source_handle = source.locator(".drag-handle")
    source_box = source_handle.bounding_box()
    target_box = app_page.locator("#board-todo").bounding_box()
    assert source_box and target_box
    app_page.mouse.move(source_box["x"] + source_box["width"] / 2, source_box["y"] + source_box["height"] / 2)
    app_page.mouse.down()
    app_page.mouse.move(target_box["x"] + 20, target_box["y"] + 40, steps=12)
    app_page.mouse.up()

    moved_task = app_page.locator(f'#board-todo .task-card[data-task-id="{task_id}"]')
    expect(moved_task).to_be_visible()
    assert app_page.evaluate(
        "(taskId) => State.tasks.find(task => task.id === taskId)?.status", task_id
    ) == "todo"


def test_finance_calculators_and_projection_are_live(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="finance"]').click()

    app_page.locator("#finance-loan-principal").fill("120000")
    app_page.locator("#finance-loan-rate").fill("0")
    app_page.locator("#finance-loan-months").fill("12")
    expect(app_page.locator("#finance-loan-emi")).to_have_text("₹10,000")
    expect(app_page.locator("#finance-loan-interest")).to_have_text("₹0")

    app_page.locator("#finance-fd-principal").fill("10000")
    app_page.locator("#finance-fd-rate").fill("0")
    app_page.locator("#finance-fd-years").fill("2")
    expect(app_page.locator("#finance-fd-maturity")).to_have_text("₹10,000")

    app_page.locator("#finance-sip-monthly").fill("500")
    app_page.locator("#finance-sip-rate").fill("0")
    app_page.locator("#finance-sip-years").fill("1")
    expect(app_page.locator("#finance-sip-value")).to_have_text("₹6,000")
    expect(app_page.locator("#finance-projection-note")).to_contain_text("Straight-line estimate")
    app_page.evaluate(
        """() => {
            State.finances.transactions.push({
                id: 'projection-check',
                amount: 1000,
                category: 'Food',
                isoDate: new Date().toISOString()
            });
            FinanceEngine.updateTools();
        }"""
    )
    expect(app_page.locator("#finance-projection-spent")).to_have_text("₹1,000")


def test_eisenhower_matrix_and_calendar_aggregate_workspace_events(app_page: Page) -> None:
    today = app_page.evaluate("CalendarView.dateKey(new Date())")
    app_page.locator('.nav-item[data-view="projects"]').click()
    app_page.get_by_role("button", name="Add Task").click()
    app_page.locator("#task-title").fill("Urgent calendar task")
    app_page.locator("#task-due-date").fill(today)
    app_page.locator("#task-important").check()
    app_page.locator("#task-urgent").check()
    app_page.get_by_role("button", name="Save Item (+25 XP)").click()

    app_page.locator('.nav-item[data-view="eisenhower"]').click()
    expect(app_page.locator('section[aria-label="Do First"]')).to_contain_text("Urgent calendar task")

    app_page.locator('.nav-item[data-view="workout"]').click()
    app_page.get_by_role("button", name="Log Session").click()
    app_page.locator("#wo-title").fill("Calendar workout")
    app_page.get_by_role("button", name="Commit (+100 XP)").click()

    app_page.locator('.nav-item[data-view="finance"]').click()
    app_page.get_by_role("button", name="Record Outflow").click()
    app_page.locator("#tx-desc").fill("Calendar transaction")
    app_page.locator("#tx-amount").fill("75")
    app_page.get_by_role("button", name="Log Entry").click()
    app_page.get_by_role("button", name="Add Budget Item").click()
    app_page.locator("#finance-expense-title").fill("Calendar bill")
    app_page.locator("#finance-expense-amount").fill("200")
    app_page.locator("#finance-expense-due-date").fill(today)
    app_page.get_by_role("button", name="Save Item").click()

    app_page.locator('.nav-item[data-view="calendar"]').click()
    for title in ("Urgent calendar task", "Calendar workout", "Calendar transaction", "Calendar bill"):
        expect(app_page.locator(".calendar-grid")).to_contain_text(title)


def test_create_and_edit_custom_guided_path(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="pathways"]').click()
    expect(app_page.locator("#content")).to_contain_text("No guided paths yet")
    expect(app_page.locator("#content")).not_to_contain_text("Peak Physical Architecture")

    app_page.get_by_role("button", name="Create Path").click()
    app_page.locator("#pathway-title").fill("Quarterly learning plan")
    app_page.locator("#pathway-desc").fill("Build a steady learning habit.")
    app_page.locator(".pathway-step-title").nth(0).fill("Read one chapter")
    app_page.locator(".pathway-step-activity").nth(0).select_option("time")
    app_page.locator(".pathway-step-action-label").nth(0).fill("Start reading timer")
    app_page.get_by_role("button", name="Add Milestone").click()
    app_page.locator(".pathway-step-title").nth(1).fill("Write a short summary")
    app_page.locator(".pathway-step-activity").nth(1).select_option("note")
    app_page.get_by_role("button", name="Save Path").click()

    path_card = app_page.locator("#content .card").filter(has_text="Quarterly learning plan")
    expect(path_card).to_contain_text("Build a steady learning habit.")
    expect(path_card.locator(".pathway-step-item")).to_have_count(2)
    expect(path_card.locator(".pathway-step-actions button").first).to_have_text("Start reading timer")

    path_card.locator('input[type="checkbox"]').first.check()
    path_card.get_by_role("button", name="Edit").click()
    expect(app_page.locator("#pathway-modal-title")).to_have_text("Edit Guided Path")
    expect(app_page.locator(".pathway-step-title").nth(0)).to_have_value("Read one chapter")
    expect(app_page.locator(".pathway-step-activity").nth(0)).to_have_value("time")

    app_page.locator("#pathway-title").fill("Updated learning plan")
    app_page.locator(".pathway-step-title").nth(0).fill("Read two chapters")
    app_page.locator('[data-action="pathway-remove-step"]').nth(1).click()
    app_page.get_by_role("button", name="Save Path").click()

    path_card = app_page.locator("#content .card").filter(has_text="Updated learning plan")
    expect(path_card.locator(".pathway-step-item")).to_have_count(1)
    expect(path_card.locator(".pathway-step-item")).to_contain_text("Read two chapters")
    expect(path_card.locator('input[type="checkbox"]')).to_be_checked()

    path_card.get_by_role("button", name="Delete guided path").click()
    app_page.get_by_role("button", name="Proceed").click()
    expect(app_page.locator("#content")).to_contain_text("No guided paths yet")


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


def test_finance_categories_recurring_paid_items_and_amount_visibility(app_page: Page) -> None:
    app_page.locator('.nav-item[data-view="finance"]').click()
    housing = app_page.locator("#content section.stat-card").filter(has_text="Housing").first
    expect(housing).to_be_visible()

    housing.get_by_role("button", name="Add item").click()
    app_page.locator("#finance-expense-title").fill("Internet service")
    app_page.locator("#finance-expense-amount").fill("350")
    app_page.locator("#finance-expense-recurrence").select_option("weekly")
    expect(app_page.locator("#finance-expense-category")).to_have_value("Housing")
    app_page.get_by_role("button", name="Save Item").click()

    housing = app_page.locator("#content section.stat-card").filter(has_text="Housing").first
    paid_checkbox = housing.locator('[data-action="finance-item-paid"]')
    expect(paid_checkbox).not_to_be_checked()
    paid_checkbox.check()
    expect(app_page.locator("#toast-container")).to_contain_text("Marked paid and added to transactions.")
    expect(app_page.locator("#content")).to_contain_text("Internet service")
    assert app_page.evaluate("State.finances.transactions.filter(tx => tx.budgetItemId).length") == 1
    assert app_page.evaluate("FinanceEngine.categorySpent('Housing')") == 350

    app_page.evaluate(
        """async () => {
            const item = State.finances.budgetItems[0];
            const previousWeek = new Date();
            previousWeek.setDate(previousWeek.getDate() - 7);
            item.paidPeriod = FinanceEngine.cycleKey('weekly', previousWeek);
            await Data.save();
            App.refreshCurrentView();
        }"""
    )
    housing = app_page.locator("#content section.stat-card").filter(has_text="Housing").first
    expect(housing.locator('[data-action="finance-item-paid"]')).not_to_be_checked()

    app_page.get_by_role("button", name="Hide amounts").click()
    housing = app_page.locator("#content section.stat-card").filter(has_text="Housing").first
    expect(app_page.get_by_role("button", name="Show amounts")).to_be_visible()
    expect(housing.locator("#finance-budget-0")).to_be_disabled()
    expect(housing).not_to_contain_text("30,000")
    expect(housing).not_to_contain_text("350")

    app_page.get_by_role("button", name="Show amounts").click()
    housing = app_page.locator("#content section.stat-card").filter(has_text="Housing").first
    expect(housing.locator("#finance-budget-0")).to_have_value("30000")
    expect(housing).to_contain_text("29,650")

    app_page.get_by_role("button", name="Add Category").click()
    app_page.locator("#finance-category-name").fill("Travel")
    app_page.locator("#finance-category-budget").fill("5000")
    app_page.get_by_role("button", name="Add Category").last.click()
    expect(app_page.locator("#content section.stat-card").filter(has_text="Travel").first).to_be_visible()
    app_page.get_by_role("button", name="Add Budget Item").click()
    expect(app_page.locator("#finance-expense-category")).to_contain_text("Travel")
    app_page.get_by_role("button", name="Cancel").last.click()

    app_page.set_viewport_size({"width": 393, "height": 852})
    layout = app_page.locator("#content").evaluate(
        "(content) => content.scrollWidth <= content.clientWidth"
    )
    assert layout


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
    expect(standalone_app.get_by_role("heading", name="AstralSurge Vault Core")).to_be_visible()

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
