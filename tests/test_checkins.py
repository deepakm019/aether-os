"""Activity check-ins: quick logging on Today, next-window timers, configurable Life sliders,
workout check-in modal, undo, notification path and phone-width layout."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
PAGE_SCROLL = "() => [document.documentElement.scrollWidth, window.innerWidth]"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail and not ok else ""))


def open_app(browser, width=1280, height=900):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_init_script("window.__asosTestHooks = true;")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("dialog", lambda d: d.accept())
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    return page, errors


def card_text(page):
    return page.locator("#ck-card").inner_text()


def row_timer(page, title):
    return page.evaluate(
        """(t) => { const r=[...document.querySelectorAll('#ck-card .ck-row')].find(x=>x.innerText.includes(t));
        return r ? r.querySelector('.ck-timer').textContent : null; }""",
        title,
    )


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = open_app(browser)
        page.evaluate("() => setNav('today')")
        page.wait_for_timeout(300)

        # 1. Card and one-tap buttons exist on Today.
        check("Today shows the check-in card", page.locator("#ck-card").count() == 1)
        check("Meal, snack, water and workout buttons present",
              all(page.locator(f"#ck-card button[onclick*=\"logCheckin('{k}')\"], #ck-card button[onclick*='openWorkoutCheckin']").count() >= 1
                  for k in ["meal", "snack", "water"]) and page.locator("#ck-card button[onclick*='openWorkoutCheckin']").count() == 1)

        # 2. Logging a meal starts the meal timer, about 3 hours out.
        page.click("#ck-card button[onclick*=\"logCheckin('meal')\"]")
        page.wait_for_timeout(300)
        check("Logging a meal bumps the today count", "1 today" in card_text(page))
        timer = row_timer(page, "Next meal")
        check("Next meal timer shows about 3 hours", (timer or "").startswith("in 2h"), f"timer={timer}")

        # 3. Timer ticks every second without a full re-render.
        t1 = row_timer(page, "Next meal")
        page.wait_for_timeout(1500)
        t2 = row_timer(page, "Next meal")
        check("Countdown ticks live", t1 != t2, f"{t1} -> {t2}")

        # 4. Screen-free note appears after a meal.
        check("Screen-free note shown after a meal", "Screen-free until" in card_text(page))

        # 5. Water logged adds a water window.
        page.click("#ck-card button[onclick*=\"logCheckin('water')\"]")
        page.wait_for_timeout(300)
        check("Water window appears after logging water", row_timer(page, "Water") is not None)

        # 6. Workout modal logs a cardio session and starts its recovery window.
        page.click("#ck-card button[onclick*='openWorkoutCheckin']")
        page.wait_for_timeout(300)
        page.select_option("#modal select[name=type]", "Cardio")
        page.fill("#modal input[name=minutes]", "30")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_timeout(300)
        check("Workout check-in creates a cardio recovery window",
              row_timer(page, "Next cardio session") is not None)
        check("Workout count increments", "1 today" in card_text(page))

        # 7. A strength session 25 hours ago is past its 24-hour recovery: due now.
        page.evaluate("() => setCheckinForTest('workout', 25*3600*1000, 'Strength')")
        page.wait_for_timeout(200)
        check("Strength recovery reads Due now after 24 hours",
              (row_timer(page, "Next strength session") or "") == "Due now")

        # 8. Post-workout water and protein windows follow a fresh workout.
        page.evaluate("() => setCheckinForTest('workout', 10*60*1000, 'Strength')")
        page.wait_for_timeout(200)
        check("Post-workout water window shown", row_timer(page, "Water after your workout") is not None)
        check("Post-workout protein meal window shown", row_timer(page, "Protein meal after your workout") is not None)

        # 9. Undo removes the most recent check-in.
        # The cardio session was logged last, so undo removes it and its recovery row.
        page.click("#ck-card button[onclick='undoCheckin()']")
        page.wait_for_timeout(200)
        check("Undo removes the latest check-in (cardio recovery row gone)",
              row_timer(page, "Next cardio session") is None)

        # 10. Life sliders change the meal window.
        page.evaluate("() => setNav('life')")
        page.wait_for_timeout(300)
        check("Life page has check-in window sliders", page.locator(".ck-rule input").count() == 10)
        page.evaluate("""() => { const el=document.querySelector(".ck-rule input[oninput*='mealGap']");
            el.value='120'; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); }""")
        page.wait_for_timeout(200)
        page.evaluate("() => setNav('today')")
        page.wait_for_timeout(300)
        meal = row_timer(page, "Next meal") or ""
        check("Meal slider at 2 hours shortens the meal window", meal.startswith("in 1h"), f"timer={meal}")

        # 11. Notifications: a window that comes due fires a toast once while the app is open.
        page.evaluate("() => { setCheckinRule('quietStart',0); setCheckinRule('quietEnd',0); setCheckinForTest('snack', 9*3600*1000); }")
        try:
            page.wait_for_function("() => document.body.innerText.includes('Next snack · due now')", timeout=4000)
            check("Due window fires a toast", True)
        except Exception as e:
            check("Due window fires a toast", False, str(e)[:120])

        # 12. Phone width: no sideways scroll on Today or Life.
        phone, perrs = open_app(browser, width=390, height=844)
        for view in ["today", "life"]:
            phone.evaluate(f"() => setNav('{view}')")
            phone.wait_for_timeout(300)
            sw, iw = phone.evaluate(PAGE_SCROLL)
            check(f"No sideways scroll on {view} at 390px", sw <= iw + 1, f"{sw}>{iw}")
        check("No page errors", not errors and not perrs, f"{errors + perrs}"[:200])
        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
