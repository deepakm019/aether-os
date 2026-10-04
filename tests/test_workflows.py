from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def navigate_to_view(page: Page, view: str) -> None:
    item = page.locator(f'.nav-item[data-view="{view}"]')
    if not item.is_visible():
        item.locator("xpath=ancestor::details[1]").locator("summary").click()
    item.click()


def test_create_task_and_open_its_inspector(app_page: Page) -> None:
    navigate_to_view(app_page, "projects")
    app_page.get_by_role("button", name="Add Task").click()
    app_page.locator("#task-title").fill("Playwright-created task")
    app_page.locator("#task-desc").fill("Created by the browser test")
    app_page.locator("#task-energy").select_option("reactive")
    app_page.get_by_role("button", name="Save Task").click()

    card = app_page.locator(".task-card").filter(has_text="Playwright-created task")
    expect(card).to_be_visible()
    expect(card.locator(".energy-reactive")).to_contain_text("Reactive")
    card.locator("div").filter(has_text="Playwright-created task").first.click()
    expect(app_page.locator("#drawer-task-title")).to_have_value("Playwright-created task")
    expect(app_page.locator("#drawer-task-energy")).to_have_value("reactive")
    app_page.locator("#drawer-task-energy").select_option("shallow")
    assert app_page.evaluate(
        "() => State.tasks.find(task => task.title === 'Playwright-created task').energy"
    ) == "shallow"


def test_day_planner_builds_non_overlapping_schedule_and_tracks_habits(app_page: Page) -> None:
    navigate_to_view(app_page, "planner")
    app_page.locator('#planner-builder-form [name="meetingTitle"]').fill("Planning meeting")
    app_page.locator('#planner-builder-form [name="meetingTime"]').fill("10:00")
    app_page.get_by_role("button", name="Build this day").click()

    schedule = app_page.locator(".planner-entry")
    expect(schedule).to_have_count(8)
    expect(app_page.locator("#content")).to_contain_text("Travel to Planning meeting")
    expect(app_page.locator("#content")).to_contain_text("Travel from Planning meeting")
    expect(app_page.locator("#content")).to_contain_text("Priority focus block")
    expect(app_page.locator("#content")).to_contain_text("Lunch / reset")
    assert app_page.evaluate(
        """() => {
            const entries = State.planner.entries.filter(item => item.date === PlannerEngine.displayDate)
                .sort((a, b) => a.time.localeCompare(b.time));
            return entries.every((item, index) => index === 0 ||
                entries[index - 1].time.slice(0, 2) * 60 + Number(entries[index - 1].time.slice(3)) +
                    entries[index - 1].duration <= item.time.slice(0, 2) * 60 + Number(item.time.slice(3)));
        }"""
    )
    navigate_to_view(app_page, "calendar")
    expect(app_page.locator("#content")).to_contain_text("Planning meeting")
    navigate_to_view(app_page, "planner")

    habit = app_page.locator('#planner-habit-form [name="title"]')
    habit.fill("Stretch for two minutes")
    app_page.get_by_role("button", name="Add habit").click()
    habit_checkbox = app_page.get_by_role("checkbox", name="Mark Stretch for two minutes complete today")
    habit_checkbox.check()
    expect(habit_checkbox).to_be_checked()
    assert app_page.evaluate(
        "() => State.planner.habits.find(item => item.title === 'Stretch for two minutes').completedDates.length"
    ) == 1


def test_planner_marks_blocks_done_and_starts_focus_blocks(app_page: Page) -> None:
    navigate_to_view(app_page, "planner")
    tomorrow = app_page.evaluate(
        """() => {
            const date = new Date();
            date.setDate(date.getDate() + 1);
            return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
                String(date.getDate()).padStart(2, '0')].join('-');
        }"""
    )
    app_page.locator("#planner-date-filter").fill(tomorrow)
    app_page.locator("#planner-date-filter").dispatch_event("change")
    app_page.get_by_role("button", name="Build this day").click()

    app_page.get_by_role("button", name="Complete Priority focus block").click()
    assert app_page.evaluate(
        "() => State.planner.entries.find(item => item.title === 'Priority focus block').completed"
    ) is True
    expect(app_page.locator('[aria-label="Day plan progress"]')).to_have_attribute("aria-valuenow", "20")

    app_page.get_by_role("button", name="Reopen Priority focus block").click()
    start_focus = app_page.get_by_role("button", name="Start focus session for Priority focus block")
    expect(start_focus).to_be_visible()
    start_focus.click()
    expect(app_page.locator("#content h2").first).to_have_text("Focus Timer")
    assert app_page.evaluate("ChronoEngine.activeCategory") == "Priority focus block"
    expect(app_page.locator("#global-timer-pill")).to_be_visible()


def test_planner_rejects_overlapping_day_builder_suggestions(app_page: Page) -> None:
    navigate_to_view(app_page, "planner")
    app_page.locator('#planner-builder-form [name="meetingTitle"]').fill("Early meeting")
    app_page.locator('#planner-builder-form [name="meetingTime"]').fill("08:00")
    app_page.get_by_role("button", name="Build this day").click()

    expect(app_page.locator("#toast-container")).to_contain_text("overlap")
    assert app_page.evaluate("() => State.planner.entries.length") == 0


def test_planner_clock_stopwatch_and_alarm_creation(app_page: Page) -> None:
    navigate_to_view(app_page, "planner")
    expect(app_page.locator("#planner-clock")).to_be_visible()
    expect(app_page.locator("#planner-timezone")).not_to_be_empty()

    app_page.locator("#planner-timer-minutes").fill("1")
    app_page.get_by_role("button", name="Start", exact=True).click()
    assert app_page.evaluate("() => PlannerEngine.countdownEndsAt > Date.now()")
    app_page.get_by_role("button", name="Stop", exact=True).click()
    expect(app_page.locator("#planner-countdown")).to_have_text("00:00:00")

    app_page.get_by_role("button", name="Start / Pause").click()
    assert app_page.evaluate("() => Boolean(PlannerEngine.stopwatchStartedAt)")
    app_page.get_by_role("button", name="Start / Pause").click()
    assert app_page.evaluate("() => PlannerEngine.stopwatchStartedAt === null")

    app_page.evaluate(
        """() => {
            const when = new Date(Date.now() + 3600000);
            const date = [when.getFullYear(), String(when.getMonth() + 1).padStart(2, '0'),
                String(when.getDate()).padStart(2, '0')].join('-');
            document.querySelector('#planner-alarm-form [name="date"]').value = date;
            document.querySelector('#planner-alarm-form [name="time"]').value =
                `${String(when.getHours()).padStart(2, '0')}:${String(when.getMinutes()).padStart(2, '0')}`;
        }"""
    )
    app_page.locator('#planner-alarm-form [name="title"]').fill("Leave for the train")
    app_page.get_by_role("button", name="Set alarm").click()
    expect(app_page.locator("#content")).to_contain_text("Leave for the train")
    assert app_page.evaluate("() => State.planner.alarms[0].enabled") is True


def test_clear_offline_cache_action_explains_data_is_preserved(app_page: Page) -> None:
    navigate_to_view(app_page, "legal")
    app_page.get_by_role("button", name="Clear offline cache & refresh").click()
    dialog = app_page.locator("#confirm-modal")
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text("encrypted vault and checkpoints are not changed")
    expect(dialog).to_contain_text("network connection")
    dialog.get_by_role("button", name="Cancel").click()


def test_dashboard_orders_five_tasks_and_supports_focus_and_completion(app_page: Page) -> None:
    app_page.evaluate(
        """() => {
            State.tasks = [
                { id: 'first-high', title: 'First high', status: 'todo', priority: 'high', urgent: true, dueDate: '2026-10-07', energy: 'deep' },
                { id: 'second-high', title: 'Second high', status: 'todo', priority: 'high', urgent: true, dueDate: '2026-10-08', energy: 'shallow' },
                { id: 'third-high', title: 'Third high', status: 'todo', priority: 'high', urgent: false, dueDate: '2026-10-01', energy: 'reactive' },
                { id: 'fourth-med', title: 'Fourth medium', status: 'in_progress', priority: 'med', urgent: true, dueDate: '2026-10-05', energy: 'deep' },
                { id: 'fifth-low', title: 'Fifth low', status: 'inbox', priority: 'low', urgent: true, dueDate: '2026-10-02', energy: 'shallow' },
                { id: 'completed', title: 'Completed task', status: 'done', priority: 'high', urgent: true, energy: 'reactive' }
            ];
            App.router('dashboard');
        }"""
    )
    rows = app_page.locator(".dashboard-task-row")
    expect(rows).to_have_count(5)
    for index, title in enumerate(("First high", "Second high", "Third high", "Fourth medium", "Fifth low")):
        expect(rows.nth(index)).to_contain_text(f"#{index + 1}")
        expect(rows.nth(index)).to_contain_text(title)

    rows.first.get_by_role("button", name="Focus on First high").click()
    assert app_page.evaluate(
        "() => ({ view: document.querySelector('#sidebar .nav-item.active')?.dataset.view, category: ChronoEngine.activeCategory, taskId: ChronoEngine.boundTaskId })"
    ) == {"view": "timeview", "category": "Deep Work", "taskId": "first-high"}
    app_page.evaluate("ChronoEngine.reset()")

    navigate_to_view(app_page, "dashboard")
    before_xp = app_page.evaluate("State.user.xp")
    app_page.locator('.dashboard-task-row[data-task-index="0"] [data-task-action="complete"]').check()
    app_page.wait_for_function("State.tasks.find(task => task.id === 'first-high').status === 'done'")
    assert app_page.evaluate("State.user.xp") == before_xp + 80


def test_reactive_task_completion_unlocks_badge_and_rewards_xp(app_page: Page) -> None:
    app_page.evaluate(
        """() => {
            State.user = { level: 1, xp: 0, title: 'Novice Strategist', badges: [] };
            State.tasks = Array.from({ length: 9 }, (_, index) => ({
                id: `reactive-${index}`,
                title: `Reactive completed ${index + 1}`,
                status: 'done',
                priority: 'med',
                energy: 'reactive'
            }));
            State.tasks.push({
                id: 'reactive-final',
                title: 'Reactive final task',
                status: 'todo',
                priority: 'high',
                energy: 'reactive'
            });
            App.router('dashboard');
        }"""
    )
    app_page.locator('.dashboard-task-row [data-task-action="complete"]').check()
    app_page.wait_for_function(
        "State.user.badges.some(badge => badge.id === 'badge_reactive_sentinel')"
    )
    assert app_page.evaluate("State.user.badges.find(badge => badge.id === 'badge_reactive_sentinel')?.unlockedAt")
    assert app_page.evaluate("State.user.xp") == 230
    expect(app_page.locator("#toast-container")).to_contain_text("Achievement Unlocked: Firefighter!")
    navigate_to_view(app_page, "dashboard")
    expect(app_page.locator("#content .badge-tile.unlocked")).to_contain_text("Firefighter")


def test_deep_task_focus_session_awards_completion_bonus(app_page: Page) -> None:
    result = app_page.evaluate(
        """() => {
            State.user.xp = 0;
            State.user.badges = [];
            State.tasks = [{
                id: 'deep-focus',
                title: 'Deep focus task',
                status: 'todo',
                priority: 'high',
                energy: 'deep'
            }];
            ChronoEngine.startForTask('deep-focus');
            const category = ChronoEngine.activeCategory;
            ChronoEngine.isRunning = false;
            ChronoEngine.startTime = null;
            ChronoEngine.seconds = 60;
            ChronoEngine.stopAndLog();
            return { category, xp: State.user.xp };
        }"""
    )
    assert result == {"category": "Deep Work", "xp": 52}


def test_drag_task_between_kanban_columns(app_page: Page) -> None:
    navigate_to_view(app_page, "projects")
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


def test_finance_view_remains_available_without_calculator_screen(app_page: Page) -> None:
    navigate_to_view(app_page, "finance")
    expect(app_page.locator("#content h2")).to_have_text("Wealth & Capital Ledger")
    expect(app_page.locator("#content [id^='finance-loan-']")).to_have_count(0)


def test_budget_categories_can_be_renamed_added_and_deleted_safely(app_page: Page) -> None:
    navigate_to_view(app_page, "finance")
    app_page.evaluate(
        """async () => {
            State.finances.budgetItems.push({
                id: "category-linked-item",
                title: "Monthly groceries",
                amount: 250,
                category: "Food",
                recurrence: "monthly",
                dueDate: "",
                paidPeriod: null
            });
            State.finances.transactions.push({
                id: "category-history",
                desc: "Previous grocery purchase",
                amount: 75,
                category: "Food",
                date: new Date().toLocaleDateString([], { month: "short", day: "numeric" }),
                isoDate: new Date().toISOString()
            });
            await Data.save();
            App.refreshCurrentView();
        }"""
    )

    food_card = app_page.locator('section[aria-label="Budget category"]').filter(has_text="Food")
    food_card.get_by_role("button", name="Rename").click()
    app_page.locator("#finance-category-name").fill("Groceries")
    app_page.get_by_role("button", name="Save Changes").click()
    groceries_card = app_page.locator('section[aria-label="Budget category"]').filter(has_text="Groceries")
    expect(groceries_card).to_contain_text("Monthly groceries")
    expect(app_page.locator("#content")).to_contain_text("Previous grocery purchase")
    assert app_page.evaluate(
        "() => State.finances.transactions.find(item => item.id === 'category-history').category"
    ) == "Groceries"

    groceries_card.locator('[data-action="finance-delete-category"]').click()
    app_page.get_by_role("button", name="Proceed").click()
    uncategorized_card = app_page.locator('section[aria-label="Budget category"]').filter(has_text="Uncategorized")
    expect(uncategorized_card).to_contain_text("Monthly groceries")
    assert app_page.evaluate(
        """() => ({
            itemCategory: State.finances.budgetItems.find(item => item.id === "category-linked-item").category,
            historicalCategory: State.finances.transactions.find(item => item.id === "category-history").category
        })"""
    ) == {"itemCategory": "Uncategorized", "historicalCategory": "Groceries"}

    app_page.get_by_role("button", name="Add Category").click()
    app_page.locator("#finance-category-name").fill("Travel")
    app_page.locator("#finance-category-budget").fill("500")
    app_page.locator("#finance-category-submit").click()
    travel_card = app_page.locator('section[aria-label="Budget category"]').filter(has_text="Travel")
    expect(travel_card).to_be_visible()
    travel_card.locator('[data-action="finance-delete-category"]').click()
    app_page.get_by_role("button", name="Proceed").click()
    expect(app_page.locator('section[aria-label="Budget category"]').filter(has_text="Travel")).to_have_count(0)


def test_eisenhower_matrix_and_calendar_aggregate_workspace_events(app_page: Page) -> None:
    today = app_page.evaluate("CalendarView.dateKey(new Date())")
    navigate_to_view(app_page, "projects")
    app_page.get_by_role("button", name="Add Task").click()
    app_page.locator("#task-title").fill("Urgent calendar task")
    app_page.locator("#task-due-date").fill(today)
    app_page.locator("#task-important").check()
    app_page.locator("#task-urgent").check()
    app_page.get_by_role("button", name="Save Task").click()

    navigate_to_view(app_page, "eisenhower")
    expect(app_page.locator('section[aria-label="Do First"]')).to_contain_text("Urgent calendar task")

    navigate_to_view(app_page, "workout")
    app_page.get_by_role("button", name="Log Session").click()
    app_page.locator("#wo-title").fill("Calendar workout")
    app_page.get_by_role("button", name="Save Workout").click()

    navigate_to_view(app_page, "finance")
    app_page.get_by_role("button", name="Record Outflow").click()
    app_page.locator("#tx-desc").fill("Calendar transaction")
    app_page.locator("#tx-amount").fill("75")
    app_page.get_by_role("button", name="Log Entry").click()
    app_page.get_by_role("button", name="Add Budget Item").click()
    app_page.locator("#finance-expense-title").fill("Calendar bill")
    app_page.locator("#finance-expense-amount").fill("200")
    app_page.locator("#finance-expense-due-date").fill(today)
    app_page.get_by_role("button", name="Save Item").click()

    navigate_to_view(app_page, "calendar")
    for title in ("Urgent calendar task", "Calendar workout", "Calendar transaction", "Calendar bill"):
        expect(app_page.locator(".calendar-grid")).to_contain_text(title)


def test_goal_roadmap_templates_are_editable_and_reusable(app_page: Page) -> None:
    navigate_to_view(app_page, "pathways")
    template_cards = app_page.locator(".pathway-template-card")
    expect(template_cards).to_have_count(4)
    expect(app_page.locator("#content")).to_contain_text("Ship a portfolio project in 4 weeks")
    expect(app_page.locator("#content")).to_contain_text("Learn a practical skill in 30 days")
    expect(app_page.locator("#content")).to_contain_text("Build a consistent fitness routine")
    expect(app_page.locator("#content")).to_contain_text("Build a 3-month emergency fund")

    template_cards.nth(0).get_by_role("button", name="Use and edit").click()
    expect(app_page.locator("#pathway-title")).to_have_value("Ship a portfolio project in 4 weeks")
    expect(app_page.locator(".pathway-step-title")).to_have_count(4)
    app_page.locator("#pathway-title").fill("My portfolio launch")
    app_page.locator(".pathway-step-title").nth(0).fill("Choose my target audience and project outcome")
    app_page.get_by_role("button", name="Save Path").click()

    roadmap = app_page.locator("#content .card").filter(has_text="My portfolio launch")
    expect(roadmap).to_contain_text("Choose my target audience and project outcome")
    expect(roadmap.locator(".pathway-step-item")).to_have_count(4)


def test_create_and_edit_custom_guided_path(app_page: Page) -> None:
    navigate_to_view(app_page, "pathways")
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
    navigate_to_view(app_page, "workout")
    app_page.get_by_role("button", name="Log Session").click()
    app_page.locator("#wo-title").fill("Playwright workout")
    app_page.locator("#wo-type").fill("Trail running")
    app_page.locator("#wo-duration").fill("30")
    app_page.get_by_role("button", name="Save Workout").click()

    expect(app_page.locator(".flex-col").filter(has_text="Playwright workout").first).to_be_visible()
    expect(app_page.locator("#workout-chart")).to_be_visible()
    expect(app_page.locator("#workout-chart-legend")).to_contain_text("Trail running")
    expect(app_page.locator('#workout-category-options option[value="Trail running"]')).to_have_count(1)
    assert app_page.evaluate("State.workouts[0].type") == "Trail running"


def test_create_story_finance_entry_note_and_checkpoint(app_page: Page) -> None:
    navigate_to_view(app_page, "stories")
    app_page.get_by_role("button", name="New Story").click()
    app_page.locator("#story-title").fill("Playwright story")
    app_page.get_by_role("button", name="Save Project (+50 XP)").click()
    expect(app_page.locator("#content")).to_contain_text("Playwright story")

    navigate_to_view(app_page, "finance")
    app_page.get_by_role("button", name="Record Outflow").click()
    app_page.locator("#tx-desc").fill("Playwright transaction")
    app_page.locator("#tx-amount").fill("12")
    app_page.get_by_role("button", name="Log Entry").click()
    expect(app_page.locator("#content")).to_contain_text("Playwright transaction")

    navigate_to_view(app_page, "brain")
    app_page.get_by_role("button", name="Create Note").click()
    app_page.locator("#note-title").fill("Playwright note")
    app_page.locator("#note-content").fill("Local encrypted test note")
    app_page.get_by_role("button", name="Save Note (+35 XP)").click()
    expect(app_page.locator("#content")).to_contain_text("Playwright note")

    navigate_to_view(app_page, "snapshots")
    app_page.get_by_role("button", name="Take Checkpoint").click()
    expect(app_page.locator("#content")).to_contain_text("Checkpoint #")


def test_edit_note_category_and_create_editable_task_from_note(app_page: Page) -> None:
    navigate_to_view(app_page, "brain")
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
    app_page.get_by_role("button", name="Create Task", exact=True).click()
    expect(app_page.locator("#task-title")).to_have_value("Refined note")
    expect(app_page.locator("#task-desc")).to_have_value("Implementation details from the note")
    app_page.locator("#task-title").fill("Task refined from note")
    app_page.get_by_role("button", name="Save Task").click()

    navigate_to_view(app_page, "projects")
    task_card = app_page.locator(".task-card").filter(has_text="Task refined from note")
    expect(task_card).to_be_visible()
    task_card.click()
    expect(app_page.locator("#drawer-task-title")).to_have_value("Task refined from note")


def test_finance_categories_recurring_paid_items_and_amount_visibility(app_page: Page) -> None:
    navigate_to_view(app_page, "finance")
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


def test_monthly_budget_projections_lock_actuals_and_roll_forward(app_page: Page) -> None:
    navigate_to_view(app_page, "finance")
    app_page.get_by_role("button", name="Add projection").click()
    app_page.locator("#finance-decision-title").fill("Weekend trip")
    app_page.locator("#finance-decision-category").select_option("Discretionary")
    app_page.locator("#finance-decision-projected").fill("1000")
    app_page.get_by_role("button", name="Save projection").click()

    expect(app_page.locator(".finance-decision-row").filter(has_text="Weekend trip")).to_contain_text("Provisional")
    expect(app_page.locator(".finance-decision-summary")).to_contain_text("₹1,000")
    app_page.get_by_role("button", name="Mark done").click()
    expect(app_page.locator("#finance-decision-projected-label")).to_contain_text("₹1,000")
    app_page.locator("#finance-decision-actual").fill("850")
    app_page.get_by_role("button", name="Lock actual").click()

    decision_row = app_page.locator(".finance-decision-row").filter(has_text="Weekend trip")
    expect(decision_row).to_contain_text("Locked actual ₹850")
    expect(decision_row).to_contain_text("Saved ₹150")
    expect(app_page.locator(".finance-decision-summary")).to_contain_text("₹850")
    expect(app_page.locator(".finance-decision-summary")).to_contain_text("₹150")
    app_page.get_by_role("button", name="Hide amounts").click()
    expect(decision_row).to_contain_text("••••••")
    expect(decision_row).not_to_contain_text("850")
    app_page.get_by_role("button", name="Show amounts").click()
    assert app_page.evaluate(
        "() => State.finances.transactions.filter(tx => tx.budgetDecisionId).map(tx => tx.amount)"
    ) == [850]
    assert app_page.evaluate("FinanceEngine.categorySpent('Discretionary')") == 850

    app_page.evaluate(
        """async () => {
            const previousMonth = new Date();
            previousMonth.setDate(1);
            previousMonth.setMonth(previousMonth.getMonth() - 1);
            State.finances.budgetDecisions[0].monthKey = FinanceEngine.monthKey(previousMonth);
            await Data.save();
            App.refreshCurrentView();
        }"""
    )
    expect(app_page.locator(".finance-decision-summary")).to_contain_text("₹0")
    app_page.get_by_text("Previous months (1)").click()
    expect(app_page.locator(".finance-history-month")).to_contain_text("Weekend trip")
    expect(app_page.locator(".finance-history-month")).to_contain_text("Locked actual ₹850")

    app_page.set_viewport_size({"width": 393, "height": 852})
    app_page.evaluate("App.refreshCurrentView()")
    housing = app_page.locator("#content section.stat-card").filter(has_text="Housing").first
    assert not housing.locator("details.finance-category-expander").evaluate("(details) => details.open")
    housing.locator("summary.finance-category-summary").click()
    expect(housing.locator("#finance-budget-0")).to_be_visible()
    assert app_page.locator("#content").evaluate("(content) => content.scrollWidth <= content.clientWidth")


def test_timer_and_theme_controls_work(app_page: Page) -> None:
    navigate_to_view(app_page, "timeview")
    app_page.locator("#chrono-custom-tag").fill("Interview prep")
    app_page.get_by_role("button", name="Use tag").click()
    expect(app_page.locator('.chrono-category[data-chrono-category="Interview prep"]')).to_have_class("chip chrono-category active")
    app_page.get_by_role("button", name="Start Stopwatch").click()
    expect(app_page.locator("#global-timer-pill")).to_be_visible()
    expect(app_page.locator("#chrono-actions-row")).to_contain_text("Pause Timer")
    expect(app_page.locator("#chrono-view-clock")).to_have_text("00:01", timeout=3000)
    app_page.get_by_role("button", name="Save Focus Session").click()
    assert app_page.evaluate("State.timeLogs[0].category") == "Interview prep"

    app_page.locator("#theme-btn").click()
    expect(app_page.locator("html")).to_have_attribute("data-theme", "light")
    expect(app_page.locator("#system-clock")).to_have_text(re.compile(r"\d{1,2}:\d{2}"))


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
