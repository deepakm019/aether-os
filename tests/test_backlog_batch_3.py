"""Backlog batch 3: timer input theme, converter speed/area/time/data, auto-sort on
completion, prompt builder, decision review loop, workout repeat and personal bests.
Also responsive checks for the new and changed views at 320 and 390 px."""
import json
import os
import re
import sys
import tempfile
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []
RAW = """async(k)=>{if(!(await indexedDB.databases()).some(d=>d.name==='astralsurge.os.v2'))return null;const db=await new Promise((res,rej)=>{const r=indexedDB.open('astralsurge.os.v2',1);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});const rec=await new Promise(res=>{const g=db.transaction('kv').objectStore('kv').get(k);g.onsuccess=()=>res(g.result)});db.close();if(!rec)return null;return rec.encoding==='gzip'?await new Response(new Blob([rec.data]).stream().pipeThrough(new DecompressionStream('gzip'))).text():String(rec.data)}"""


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def new_app(browser, width=390):
    ctx = browser.new_context(viewport={"width": width, "height": 844})
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
        page.wait_for_timeout(400)
    return ctx, page, errors


def nav(page, route):
    page.evaluate("(r)=>setNav(r)", route)
    page.wait_for_timeout(250)


def stored(page):
    page.wait_for_timeout(500)
    t = page.evaluate(RAW, "workspace")
    return json.loads(t) if t else None


def set_file_via(page, trigger_fn, path):
    with page.expect_file_chooser() as fc:
        trigger_fn()
    fc.value.set_files(path)
    page.wait_for_timeout(500)


def convert(page, cat, value, src, dst):
    page.select_option("#conv-cat", cat)
    page.wait_for_timeout(150)
    page.select_option("#conv-from", src)
    page.select_option("#conv-to", dst)
    page.fill("#conv-value", value)
    page.wait_for_timeout(120)
    return page.inner_text("#conv-result")


PRIO = {"High": 0, "Medium": 1, "Low": 2}


def expected_order(tasks, status):
    rows = [t for t in tasks if t.get("status") == status]
    rows.sort(key=lambda t: (
        0 if t.get("urgent") else 1,
        0 if t.get("important") else 1,
        PRIO.get(t.get("priority"), 1),
        t.get("due") or "9999-12-31",
    ))
    return [t["title"] for t in rows]


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # ---- Timer input uses themed styling (was browser-default white) ----
        ctx, page, errors = new_app(browser)
        nav(page, "timer")
        bg = page.eval_on_selector("#timer-minutes", "e => getComputedStyle(e).backgroundColor")
        fg = page.eval_on_selector("#timer-minutes", "e => getComputedStyle(e).color")
        check("timer minutes input is dark-themed in dark mode", bg == "rgb(15, 18, 22)", bg)
        check("timer minutes input text is light in dark mode", fg == "rgb(240, 238, 232)", fg)
        page.evaluate("() => setSetting('theme','Light')")
        page.wait_for_timeout(250)
        nav(page, "timer")
        bg_light = page.eval_on_selector("#timer-minutes", "e => getComputedStyle(e).backgroundColor")
        check("timer minutes input is light in light mode", bg_light == "rgb(255, 255, 255)", bg_light)
        page.evaluate("() => setSetting('theme','Dark')")
        page.wait_for_timeout(200)
        check("no page errors on timer", not errors, "; ".join(errors[:2]))
        ctx.close()

        # ---- Converter: speed, area, time, data ----
        ctx, page, errors = new_app(browser)
        nav(page, "convert")
        cats = page.eval_on_selector_all("#conv-cat option", "els => els.map(e => e.value)")
        for c in ["speed", "area", "time", "data"]:
            check(f"converter has category {c}", c in cats, str(cats))
        r = convert(page, "speed", "100", "km/h", "mph")
        check("100 km/h = 62.1371 mph", "62.1371" in r, r)
        r = convert(page, "area", "1", "ha", "m2")
        check("1 hectare = 10000 m2", "10000" in r, r)
        r = convert(page, "time", "2", "h", "min")
        check("2 h = 120 min", "120" in r, r)
        r = convert(page, "data", "1", "GiB", "MB")
        check("1 GiB = 1073.74 MB", "1073.74" in r, r)
        r = convert(page, "speed", "1", "kn", "km/h")
        check("1 knot = 1.852 km/h", "1.852" in r, r)
        page.select_option("#conv-cat", "data")
        page.wait_for_timeout(150)
        check("converter select uses themed background", page.eval_on_selector(
            "#conv-cat", "e => getComputedStyle(e).backgroundColor") == "rgb(15, 18, 22)")
        check("no page errors on converter", not errors, "; ".join(errors[:2]))
        ctx.close()

        # ---- Auto-sort on completion (Work) ----
        ctx, page, errors = new_app(browser)
        nav(page, "work")
        page.evaluate("() => { window.workTab = 'To Do'; render(); }")
        page.wait_for_timeout(200)
        ws_state = stored(page)
        titles = page.locator(".task-card .entity-link").all_inner_texts()
        want = expected_order(ws_state["tasks"], "To Do")
        check("To Do is sorted by urgency, importance, priority, due (auto-sort On)", titles == want,
              f"got={titles} want={want}")
        page.evaluate("() => setSetting('autoSort','Off')")
        page.wait_for_timeout(250)
        nav(page, "work")
        page.evaluate("() => { window.workTab = 'To Do'; render(); }")
        page.wait_for_timeout(200)
        raw_titles = page.locator(".task-card .entity-link").all_inner_texts()
        raw_want = [t["title"] for t in ws_state["tasks"] if t.get("status") == "To Do"]
        check("To Do keeps stored order when auto-sort is Off", raw_titles == raw_want,
              f"got={raw_titles} want={raw_want}")
        page.evaluate("() => setSetting('autoSort','On')")
        page.wait_for_timeout(250)
        nav(page, "work")
        page.evaluate("() => { window.workTab = 'To Do'; render(); }")
        page.wait_for_timeout(200)
        first = page.locator(".task-card .entity-link").first.inner_text()
        page.locator(".task-card").first.get_by_role("button", name="Complete").click()
        page.wait_for_timeout(500)
        after = stored(page)
        done = [t for t in after["tasks"] if t["title"] == first]
        check("completed task records completedAt", done and done[0]["status"] == "Completed"
              and isinstance(done[0].get("completedAt"), (int, float)), str(done[:1]))
        page.evaluate("() => { window.workTab = 'Completed'; render(); }")
        page.wait_for_timeout(200)
        completed_titles = page.locator(".task-card .entity-link").all_inner_texts()
        check("Completed tab lists the newest completion first", completed_titles[:1] == [first],
              str(completed_titles[:3]))
        check("no page errors on work", not errors, "; ".join(errors[:2]))
        ctx.close()

        # ---- Prompt builder ----
        ctx, page, errors = new_app(browser)
        nav(page, "prompts")
        check("prompt builder view renders", page.locator("#pb-task").count() == 1)
        page.fill("#pb-role", "a careful analyst")
        page.fill("#pb-task", "Summarise the quarterly report")
        page.fill("#pb-constraints", "Under 100 words\nNo jargon")
        page.select_option("#pb-format", "Bulleted list")
        page.evaluate("() => document.querySelector('#pb-task').form.requestSubmit()")
        page.wait_for_timeout(300)
        out = page.input_value("#prompt-output")
        check("prompt has role line", "You are a careful analyst." in out, out[:120])
        check("prompt has task section", "## Task\nSummarise the quarterly report" in out)
        check("prompt has constraints as bullets", "- Under 100 words\n- No jargon" in out)
        check("prompt has chosen format", "Format: Bulleted list" in out)
        check("prompt asks for a self-check", "check your answer against every constraint" in out)
        page.fill("#pb-task", "<img src=x onerror=alert(1)> test")
        page.evaluate("() => document.querySelector('#pb-task').form.requestSubmit()")
        page.wait_for_timeout(300)
        check("user text is not rendered as HTML", page.locator('img[src="x"]').count() == 0)
        check("user text appears literally in the prompt",
              "<img src=x onerror=alert(1)> test" in page.input_value("#prompt-output"))
        check("copy button is shown after generating", page.get_by_role("button", name="Copy prompt").count() == 1)
        check("no page errors on prompt builder", not errors, "; ".join(errors[:2]))
        ctx.close()

        # ---- Decision review loop ----
        ctx, page, errors = new_app(browser)
        state = stored(page)
        state["decisions"][0]["status"] = "Awaiting reconciliation"
        state["decisions"][0].pop("reviewOn", None)
        state["decisions"][0].pop("review", None)
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f)
        nav(page, "vault")
        set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), path)
        page.get_by_role("button", name="Replace workspace").click()
        page.wait_for_timeout(600)
        nav(page, "money")
        page.get_by_role("button", name="Reconcile", exact=True).first.click()
        page.wait_for_timeout(300)
        page.get_by_role("button", name="Reconcile", exact=True).last.click()
        page.wait_for_timeout(500)
        dec = stored(page)["decisions"][0]
        check("reconciling sets status to Reconciled", dec["status"] == "Reconciled", dec.get("status"))
        days = (date.fromisoformat(dec.get("reviewOn", "2000-01-01")) - date.today()).days
        check("reconciling schedules a review about 30 days ahead", 29 <= days <= 31, f"days={days}")

        # Make the review due and reload from a backup
        state = stored(page)
        state["decisions"][0]["reviewOn"] = (date.today() - timedelta(days=1)).isoformat()
        state["decisions"][0].pop("review", None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
        nav(page, "vault")
        set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), path)
        page.get_by_role("button", name="Replace workspace").click()
        page.wait_for_timeout(600)
        nav(page, "money")
        check("due decision shows review due", page.get_by_text("review due").count() >= 1)
        page.get_by_role("button", name="Review", exact=True).first.click()
        page.wait_for_timeout(300)
        page.select_option("#dr-outcome", "Worse than expected")
        page.fill("#dr-lesson", "Get two quotes before buying")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_timeout(500)
        saved = stored(page)["decisions"][0]
        check("review is saved with outcome and lesson",
              saved.get("review", {}).get("outcome") == "Worse than expected"
              and saved.get("review", {}).get("lesson") == "Get two quotes before buying", str(saved.get("review")))
        check("review text is shown on Money", page.get_by_text("Get two quotes before buying").count() >= 1)
        check("no page errors on decision review", not errors, "; ".join(errors[:2]))
        os.unlink(path)
        ctx.close()

        # ---- Workouts: repeat last session and personal bests ----
        ctx, page, errors = new_app(browser)
        nav(page, "life")
        page.get_by_role("button", name="+ Workout").first.click()
        page.wait_for_timeout(300)
        page.fill("#modal input[name=title]", "Push day")
        page.fill("#modal textarea[name=exercises]", "Bench Press|3x8@60")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_timeout(250)
        page.get_by_role("button", name="+ Workout").first.click()
        page.wait_for_timeout(300)
        page.fill("#modal input[name=title]", "Push day heavy")
        page.fill("#modal textarea[name=exercises]", "Bench Press|3x5@65")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_timeout(120)
        toast_text = page.inner_text("#toast")
        check("saving a heavier set announces a personal best", "New personal best" in toast_text
              and "Bench Press 65 kg" in toast_text, toast_text)
        page.get_by_role("button", name="Repeat last", exact=True).click()
        page.wait_for_timeout(300)
        ex = page.input_value("#modal textarea[name=exercises]")
        check("Repeat last prefills the most recent session", "Bench Press" in ex and "65" in ex, ex)
        check("Repeat last sets today's date", page.input_value("#modal input[name=date]") == date.today().isoformat())
        check("no page errors on workouts", not errors, "; ".join(errors[:2]))
        ctx.close()

        # ---- Settings row for auto-sort ----
        ctx, page, errors = new_app(browser)
        nav(page, "settings")
        check("settings has an auto-sort control",
              page.locator('select[aria-label="Auto-sort tasks"]').count() == 1)
        ctx.close()

        # ---- Responsive: new and changed views at 320 and 390 px ----
        for width in (320, 390):
            ctx, page, errors = new_app(browser, width)
            for route in ["prompts", "convert", "timer", "work", "money", "life", "settings"]:
                nav(page, route)
                overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
                check(f"{route} has no horizontal scroll at {width}px", overflow <= 0, f"overflow={overflow}")
            ctx.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nBACKLOG BATCH 3 RESULT: {len(results)-len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run()
