"""Typed capture: the parser (fixtures with a fixed clock), the check-before-saving
card, switching kind, saving each kind, cancel, plain tasks staying one step,
escaping, and layout at phone width."""
import sys
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

from test_problems import open_app, overflow

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


TODAY = date.today()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
FRIDAY = (TODAY + timedelta(days=(4 - TODAY.weekday()) % 7 or 0)).isoformat()
# Fixtures use a fixed clock of 09:00 on the real current date.
FIX_NOW = "(() => new Date(%d, %d, %d, 9, 0))()" % (TODAY.year, TODAY.month - 1, TODAY.day)
FRI_FIXTURE = (TODAY + timedelta(days=(4 - TODAY.weekday()) % 7)).isoformat()
TODAY_ISO = TODAY.isoformat()
IN20 = "09:20"

# (text, expected fields). Only listed keys are compared.
FIXTURES = [
    ("buy milk", {"intent": "task", "title": "buy milk", "due": "", "alternatives": []}),
    ("Call the dentist", {"intent": "task", "title": "Call the dentist"}),
    ("buy milk tomorrow", {"intent": "task", "title": "Buy milk", "due": TOMORROW}),
    ("tax form on friday", {"intent": "task", "title": "Tax form", "due": FRI_FIXTURE}),
    ("spent a lot today", {"intent": "task", "due": TODAY_ISO}),
    ("tell mum thanks", {"intent": "task", "title": "tell mum thanks"}),
    ("<img src=x onerror=alert(1)>", {"intent": "task", "title": "<img src=x onerror=alert(1)>"}),
    ("", {"intent": "task", "title": ""}),
    ("remind me to call mum tomorrow at 3pm", {"intent": "reminder", "title": "Call mum", "due": TOMORROW, "time": "15:00", "confidence": "high"}),
    ("remind me to take tablets at 9", {"intent": "reminder", "title": "Take tablets", "time": "09:00"}),
    ("remind me to stretch in 20 minutes", {"intent": "reminder", "title": "Stretch", "due": TODAY_ISO, "time": IN20}),
    ("remind me at 7 to stretch", {"intent": "reminder", "title": "Stretch", "time": "19:00"}),
    ("remind me to pay rent on 2026-11-01 at 8am", {"intent": "reminder", "title": "Pay rent", "due": "2026-11-01", "time": "08:00"}),
    ("remember to renew passport", {"intent": "reminder", "title": "Renew passport", "confidence": "medium", "alternatives": ["task", "note"]}),
    ("I spent 40 on lunch", {"intent": "expense", "amount": "40", "category": "Food", "title": "Lunch"}),
    ("paid 12.50 for parking", {"intent": "expense", "amount": "12.5", "category": "Transport", "title": "Parking"}),
    ("spent 9 at 7pm on coffee", {"intent": "expense", "amount": "9", "category": "Food", "title": "Coffee"}),
    ("bought milk for 3", {"intent": "expense", "amount": "3", "category": "Other", "title": "Milk"}),
    ("block 20 minutes for reading", {"intent": "block", "duration": "20", "title": "Reading"}),
    ("block 2 hours for deep work at 2pm", {"intent": "block", "duration": "120", "time": "14:00", "title": "Deep work"}),
    ("note that the wifi password changed", {"intent": "note", "title": "The wifi password changed", "content": "the wifi password changed"}),
    ("note: bring charger", {"intent": "note", "title": "Bring charger"}),
    ("Remember that the gate code is 4411", {"intent": "note"}),
    ("I keep putting off the tax form", {"intent": "problem", "title": "The tax form", "confidence": "medium", "alternatives": ["task"]}),
    ("problem: bills keep slipping", {"intent": "problem", "title": "Bills keep slipping", "confidence": "high"}),
    ("I'm stuck on the login bug", {"intent": "problem", "title": "The login bug", "confidence": "high"}),
    ("I can't start the report", {"intent": "problem", "title": "The report", "confidence": "medium"}),
    ("I can't stop putting off calling the bank", {"intent": "problem", "title": "Calling the bank"}),
]


def parse_js(text):
    return "(t) => parseCapture(t, %s)" % FIX_NOW


def fixtures(page):
    for text, want in FIXTURES:
        got = page.evaluate(parse_js(text), text)
        bad = []
        for key, value in want.items():
            if key == "values":
                continue
            actual = got.get("values", {}).get(key, got.get(key)) if key in ("title", "due", "time", "amount", "category", "duration", "content") else got.get(key)
            if key == "alternatives":
                actual = got.get("alternatives")
            if actual != value:
                bad.append(f"{key}: got {actual!r} want {value!r}")
        check(f"parse: {text!r} -> {want.get('intent')}", not bad, "; ".join(bad))


def modal_open(page):
    return page.evaluate("() => document.getElementById('modal').classList.contains('open')")


def type_capture(page, text):
    page.fill("input[name=qc]", text)
    page.press("input[name=qc]", "Enter")
    page.wait_for_timeout(250)


def toast_text(page):
    return page.evaluate("() => document.getElementById('toast').textContent")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # 1. Parser fixtures (no UI).
        ctx, page, errors = open_app(browser, 390)
        fixtures(page)
        check("parser never throws on fixtures", not errors, str(errors[:2]))
        ctx.close()

        # 2. Plain tasks stay one step; structured text gets the card.
        ctx, page, errors = open_app(browser, 390)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(150)
        type_capture(page, "buy milk")
        check("plain task saves straight to Inbox", not modal_open(page) and "Captured to Inbox" in toast_text(page), toast_text(page))
        type_capture(page, "remind me to call mum tomorrow at 3pm")
        check("reminder text opens the check card", modal_open(page) and page.locator("#modal h2").inner_text() == "Save as Reminder?")
        check("card prefills title, date and time", page.input_value("#cap-title") == "Call mum" and page.input_value("#cap-due") == TOMORROW and page.input_value("#cap-time") == "15:00",
              f"{page.input_value('#cap-title')} {page.input_value('#cap-due')} {page.input_value('#cap-time')}")
        check("card explains why it chose reminder", page.locator("#modal").get_by_text("Why:").count() == 1)
        check("card title is focused on open", page.evaluate("() => document.activeElement && document.activeElement.id") == "cap-title")
        page.locator("#modal .tabs button", has_text="Task").click(); page.wait_for_timeout(150)
        check("switching kind keeps the title", page.locator("#modal h2").inner_text() == "Save as Task?" and page.input_value("#cap-title") == "Call mum")
        page.locator("#modal .tabs button", has_text="Reminder").click(); page.wait_for_timeout(150)
        page.locator("#modal form button.primary").click(); page.wait_for_timeout(250)
        check("saving a reminder closes the card", not modal_open(page) and "Saved as Reminder" in toast_text(page), toast_text(page))
        page.evaluate("() => setNav('reminders')"); page.wait_for_timeout(200)
        check("saved reminder appears in Reminders", page.get_by_text("Call mum").count() >= 1)
        check("no page errors in plain and reminder flows", not errors, str(errors[:2]))
        ctx.close()

        # 3. Expense, validation, cancel.
        ctx, page, errors = open_app(browser, 390)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(150)
        type_capture(page, "I spent 40 on lunch")
        check("expense card fills amount and category", page.input_value("#cap-amount") == "40" and page.input_value("#cap-cat") == "Food")
        page.locator("#modal form button.primary").click(); page.wait_for_timeout(250)
        page.evaluate("() => setNav('money')"); page.wait_for_timeout(200)
        check("saved expense appears in Money", page.get_by_text("Lunch").count() >= 1)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(150)
        type_capture(page, "buy milk tomorrow")
        page.locator("#modal .tabs button", has_text="Expense").click(); page.wait_for_timeout(150)
        page.locator("#modal form button.primary").click(); page.wait_for_timeout(250)
        check("empty amount keeps the card open", modal_open(page) and page.locator("#modal h2").inner_text() == "Save as Expense?")
        page.locator("#modal .btn", has_text="Cancel").click(); page.wait_for_timeout(150)
        check("cancel closes without saving", not modal_open(page))
        type_capture(page, "block 20 minutes for reading")
        page.locator("#modal .btn", has_text="Cancel").click(); page.wait_for_timeout(150)
        page.evaluate("() => setNav('plan')"); page.wait_for_timeout(200)
        check("cancelled planner block is not saved", page.get_by_text("Reading").count() == 0)
        check("no page errors in expense, validation and cancel", not errors, str(errors[:2]))
        ctx.close()

        # 4. Problem, alternative, note, and the card at phone width.
        ctx, page, errors = open_app(browser, 320)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(150)
        type_capture(page, "I keep putting off the tax form")
        check("problem card offers a task alternative", page.get_by_role("button", name="Save as task instead").count() == 1)
        check("card at 320px has no horizontal overflow", overflow(page) <= 0, f"overflow={overflow(page)}")
        page.get_by_role("button", name="Save as task instead").click(); page.wait_for_timeout(150)
        check("alternative switches to Task and keeps title", page.locator("#modal h2").inner_text() == "Save as Task?" and page.input_value("#cap-title") == "The tax form")
        page.locator("#modal .tabs button", has_text="Problem").click(); page.wait_for_timeout(150)
        page.fill("#cap-step", "Gather last year's statements")
        page.locator("#modal form button.primary").click(); page.wait_for_timeout(250)
        page.evaluate("() => { window.goalFilter = 'problems'; setNav('goals'); render(); }"); page.wait_for_timeout(200)
        check("saved problem appears under Problems", page.locator(".goal-card", has_text="The tax form").count() == 1)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(150)
        type_capture(page, "note that the wifi password changed")
        page.locator("#modal form button.primary").click(); page.wait_for_timeout(250)
        page.evaluate("() => setNav('memory')"); page.wait_for_timeout(200)
        check("saved note appears in Memory", page.get_by_text("The wifi password changed").count() >= 1)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(150)
        type_capture(page, "<img src=x onerror=alert(1)>")
        check("markup in capture is shown as text, not rendered", page.evaluate("() => document.querySelectorAll('img[src=\"x\"]').length") == 0)
        check("no page errors in problem, note and escaping", not errors, str(errors[:2]))
        ctx.close()
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nCAPTURE RESULT: {passed}/{len(results)} passed")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
