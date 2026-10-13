"""Problems: problem-kind goals, lifecycle (park, reopen, resolve), the four
problem rules (next step, stalled, registry overflow, stuck task), reschedule
counting, stored-data sanitising, and layout at phone and desktop widths."""
import re
import sys
from datetime import datetime, timedelta

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/index.html"
results = []
DAY_MS = 86400000
TASK_ID_JS = """() => {
  const el = [...document.querySelectorAll('[onclick]')].find(e => e.getAttribute('onclick').includes("inspect('task'"));
  const m = el && el.getAttribute('onclick').match(/tsk_[A-Za-z0-9_]+/);
  return m ? m[0] : null;
}"""


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def open_app(browser, width, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_init_script("window.__asosTestHooks = true;")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    return ctx, page, errors


def overflow(page):
    return page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")


def go_goals(page, filt=None):
    page.evaluate("() => setNav('goals')")
    page.wait_for_timeout(200)
    if filt:
        page.locator(".tab", has_text=filt).first.click()
        page.wait_for_timeout(150)


def add_problem(page, title, why, step):
    page.get_by_role("button", name="+ Problem").first.click()
    page.wait_for_timeout(150)
    page.locator("#modal input[name=title]").fill(title)
    page.locator("#modal input[name=why]").fill(why)
    page.locator("#modal input[name=step]").fill(step)
    page.locator("#modal button[type=submit]").click()
    page.wait_for_timeout(250)


def candidates(page):
    return page.evaluate("() => problemRuleCandidates().map(c => ({ruleId: c.ruleId, priority: c.priority, action: c.action, entityId: c.entityId}))")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # 1. Layout and the Problems filter at three widths.
        for width in (320, 390, 1280):
            ctx, page, errors = open_app(browser, width)
            go_goals(page)
            check(f"{width}px: + Problem button present", page.get_by_role("button", name="+ Problem").count() >= 1)
            add_problem(page, "Bills keep slipping", "Late fees add up", "Set reminders for recurring bills")
            go_goals(page, "Problems")
            check(f"{width}px: problem card shows on Problems tab", page.locator(".goal-card", has_text="Bills keep slipping").count() == 1)
            check(f"{width}px: no horizontal overflow", overflow(page) <= 0, f"overflow={overflow(page)}")
            check(f"{width}px: no page errors", not errors, str(errors[:2]))
            ctx.close()

        # 2. Creation, filters, and lifecycle on a fresh app.
        ctx, page, errors = open_app(browser, 390)
        go_goals(page)
        add_problem(page, "Procrastinating on taxes", "Penalty risk in April", "Gather last year's statements")
        go_goals(page, "Outcomes")
        check("Outcomes filter hides problems", page.locator(".goal-card", has_text="Procrastinating on taxes").count() == 0)
        go_goals(page, "Problems")
        card = page.locator(".goal-card", has_text="Procrastinating on taxes").first
        check("problem shows its why line", card.get_by_text("Penalty risk in April").count() == 1)
        check("problem shows active status", card.get_by_text("active", exact=True).count() == 1)
        card.get_by_role("button", name="Park").click(); page.wait_for_timeout(200)
        go_goals(page, "Problems")
        card = page.locator(".goal-card", has_text="Procrastinating on taxes").first
        check("park sets status to parked", card.get_by_text("parked", exact=True).count() == 1)
        check("parked problem offers Reopen", card.get_by_role("button", name="Reopen").count() == 1)
        card.get_by_role("button", name="Reopen").click(); page.wait_for_timeout(200)
        go_goals(page, "Problems")
        card = page.locator(".goal-card", has_text="Procrastinating on taxes").first
        check("reopen restores active", card.get_by_text("active", exact=True).count() == 1)
        check("resolve needs every step done first", card.get_by_role("button", name="Mark resolved").count() == 0)
        card.get_by_role("button", name="Mark done").first.click(); page.wait_for_timeout(250)
        go_goals(page, "Problems")
        card = page.locator(".goal-card", has_text="Procrastinating on taxes").first
        check("Mark resolved appears once every step is done", card.get_by_role("button", name="Mark resolved").count() == 1)
        card.get_by_role("button", name="Mark resolved").click(); page.wait_for_timeout(250)
        go_goals(page, "Problems")
        card = page.locator(".goal-card", has_text="Procrastinating on taxes").first
        check("resolve sets status to resolved", card.get_by_text("resolved", exact=True).count() >= 1)
        check("no page errors during lifecycle", not errors, str(errors[:2]))
        ctx.close()

        # 3. Rules: next step, stalled, dismiss, and overflow.
        ctx, page, errors = open_app(browser, 390)
        go_goals(page)
        add_problem(page, "Gym habit fading", "Energy is lower", "Book two sessions")
        pid = page.evaluate("(title) => activeProblems().find(g => g.title === title).id", "Gym habit fading")
        cands = candidates(page)
        check("fresh problem yields a problem_next candidate", any(c["ruleId"].startswith("problem_next:") for c in cands), str(cands))
        check("problem_next priority is 58", any(c["ruleId"].startswith("problem_next:") and c["priority"] == 58 for c in cands))
        page.evaluate("(id) => setProblemMovedForTest(id, Date.now() - 20 * 86400000)", pid)
        page.wait_for_timeout(150)
        cands = candidates(page)
        check("20-day-old problem yields step_stalled first", cands and cands[0]["ruleId"] == f"step_stalled:{pid}" and cands[0]["priority"] == 62, str(cands[:1]))
        check("stalled problem no longer offers problem_next", not any(c["ruleId"].startswith("problem_next:" + pid) for c in cands))
        page.evaluate("(k) => dismissRecommendation(k)", f"step_stalled:{pid}"); page.wait_for_timeout(150)
        cands = candidates(page)
        check("dismissing a stalled problem silences only that problem", not any(c["ruleId"] == f"step_stalled:{pid}" for c in cands))
        # Overflow: create five more active problems (six total).
        go_goals(page)
        for i in range(5):
            add_problem(page, f"Extra problem {i}", "Why", f"Step {i}")
        cands = candidates(page)
        check("more than five active problems triggers registry_overflow", any(c["ruleId"] == "registry_overflow" and c["priority"] == 55 for c in cands), str([c["ruleId"] for c in cands]))
        check("no page errors during rules", not errors, str(errors[:2]))
        ctx.close()

        # 4. Stuck task: reschedule through the real task form three times, then promote.
        ctx, page, errors = open_app(browser, 390)
        page.evaluate("() => setNav('work')"); page.wait_for_timeout(200)
        tid = page.evaluate(TASK_ID_JS)
        check("found a task id in the demo workspace", bool(tid), str(tid))
        for i in range(3):
            page.evaluate("(id) => openModal(taskModal, taskById(id))", tid); page.wait_for_timeout(150)
            page.evaluate("() => { const i = document.querySelector('#modal input[name=due]'); const d = new Date(Date.now() + (%d + 2) * 86400000); i.value = d.toISOString().slice(0,10); }" % i)
            page.locator("#modal form button.primary").click(); page.wait_for_timeout(200)
        cands = candidates(page)
        stuck = [c for c in cands if c["ruleId"] == f"stuck_task:{tid}"]
        check("three reschedules raise a stuck_task candidate", len(stuck) == 1 and stuck[0]["priority"] == 57, str(cands))
        page.evaluate("(id) => actionForRec({action: 'promote_task', entityId: id})", tid); page.wait_for_timeout(250)
        go_goals(page, "Problems")
        check("promoting a stuck task creates a problem", page.locator(".goal-card").count() >= 1)
        cands = candidates(page)
        check("promoted task no longer triggers stuck_task", not any(c["ruleId"] == f"stuck_task:{tid}" for c in cands))
        check("no page errors during reschedule and promotion", not errors, str(errors[:2]))
        ctx.close()

        # 5. Sanitising stored problem and task data.
        ctx, page, errors = open_app(browser, 390)
        clean = page.evaluate("""() => normalizeWorkspace({goals:[{id:'goal_a',title:'x',kind:'bogus',status:'nope',why:'y'.repeat(300),lastMovedAt:-5,steps:[]},
          {id:'goal_b',title:'p',kind:'problem',status:'resolved',why:'ok',lastMovedAt:12,steps:[]},
          {id:'goal_c',title:'q',kind:'problem',status:'weird',steps:[]}],
          tasks:[{id:'tsk_z',title:'t',reschedules:'9999'},{id:'tsk_y',title:'u',reschedules:-4}]})""")
        ga, gb, gc = clean["goals"][0], clean["goals"][1], clean["goals"][2]
        check("unknown kind becomes outcome", ga["kind"] == "outcome" and ga.get("status") is None)
        check("why is clamped to 200 characters", len(ga["why"]) == 200, str(len(ga["why"])))
        check("negative lastMovedAt clamps to zero", ga["lastMovedAt"] == 0)
        check("valid problem status is kept", gb["kind"] == "problem" and gb["status"] == "resolved")
        check("unknown problem status falls back to active", gc["status"] == "active")
        tz = {t["id"]: t["reschedules"] for t in clean["tasks"]}
        check("reschedules clamp to 999 and to zero", tz.get("tsk_z") == 999 and tz.get("tsk_y") == 0, str(tz))
        check("no page errors in sanitisation", not errors, str(errors[:2]))
        ctx.close()
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nPROBLEMS RESULT: {passed}/{len(results)} passed")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
