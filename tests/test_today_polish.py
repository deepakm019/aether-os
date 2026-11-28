"""Today polish: Subtasks button beside Focus, contained task popup with copy list, time-of-day
greeting emoji, phone quick-capture layout, and check-in header spacing."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail and not ok else ""))


def open_app(browser, width=390, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_init_script("window.__asosTestHooks = true;")
    ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=URL.split("/index")[0])
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


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page, errors = open_app(browser)
        page.evaluate("() => setNav('today')")
        page.wait_for_timeout(300)

        # Greeting emoji matches the hour and is no longer the waving hand.
        h1 = page.locator(".page .h1").first.inner_text()
        check("greeting has no waving-hand emoji", "👋" not in h1, h1)
        expected = page.evaluate("""() => { const h=new Date().getHours();
            return h<5?'🌙':h<12?'🌅':h<17?'☀️':h<22?'🌇':'🌙' }""")
        emoji = page.locator(".page .greet-emoji").first.inner_text().strip()
        check("greeting emoji matches time of day", emoji == expected, f"{emoji!r} vs {expected!r}")
        check("greeting emoji sits outside the gradient heading", expected not in h1, h1)

        # Quick capture on phone: input and button stack full width at the same height.
        cap = page.evaluate("""() => { const i=document.querySelector('.quick-capture input').getBoundingClientRect();
            const b=document.querySelector('.quick-capture-btn').getBoundingClientRect();
            return {iw:i.width,bw:b.width,ih:i.height,bh:b.height,below:b.top>i.bottom-1} }""")
        check("capture input and button share a height", abs(cap["ih"] - cap["bh"]) <= 1, str(cap))
        check("capture button sits below the input on phone", cap["below"] and abs(cap["iw"] - cap["bw"]) <= 2, str(cap))

        # Check-in header: its divider sits above the buttons, with no overlap.
        page.evaluate("() => setCheckinForTest('meal', 60*60*1000)")
        page.wait_for_timeout(200)
        gap = page.evaluate("""() => { const h=document.querySelector('.checkin-card .panel-header').getBoundingClientRect();
            const g=document.querySelector('.checkin-card .ck-buttons').getBoundingClientRect(); return g.top - h.bottom }""")
        check("check-in buttons start below the header divider", gap >= 12, f"gap={gap}")

        # Morning priorities: each row has Subtasks beside Focus.
        page.click("button[onclick*='morningWizard']")
        page.wait_for_selector("#modal form")
        page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
        page.wait_for_selector(".plan-priority")
        rows = page.locator(".plan-priority")
        check("each priority has a Subtasks button",
              all(rows.nth(i).locator(".plan-open").count() == 1 for i in range(rows.count())))
        check("Subtasks and Focus are both at least 44px tall on phone",
              page.evaluate("""() => [...document.querySelectorAll('.plan-priority .plan-open,.plan-priority .plan-focus')]
                  .every(b => b.getBoundingClientRect().height >= 43)"""))

        # Opening Subtasks shows the task popup with the subtask list.
        page.locator(".plan-open").first.click()
        page.wait_for_selector("#modal .task-popup")
        check("Subtasks opens the task popup", page.locator("#modal .task-popup").count() == 1)

        for i in range(9):
            page.fill("#modal .subtask-add input[name=t]", f"Subtask {i + 1} with a longer name that wraps on a phone")
            page.click("#modal .subtask-add button[type=submit]")
            page.wait_for_timeout(40)

        # The popup is contained: the modal does not scroll, the list does, and the page is not wider.
        contained = page.evaluate("""() => { const m=document.getElementById('modal'); const l=document.querySelector('#modal .subtask-list');
            return { modalFits: m.scrollHeight <= m.clientHeight + 1, listScrolls: l.scrollHeight > l.clientHeight,
                     overflowY: getComputedStyle(l).overflowY, overflowX: getComputedStyle(l).overflowX,
                     pageW: document.documentElement.scrollWidth <= innerWidth } }""")
        check("popup frame does not scroll", contained["modalFits"], str(contained))
        check("only the subtask list scrolls, vertically", contained["listScrolls"] and contained["overflowY"] == "auto"
              and contained["overflowX"] == "hidden", str(contained))
        check("no sideways scroll with the popup open", contained["pageW"])

        # Up/down buttons are hidden on phones; the drag handle carries the reorder.
        visible_arrows = page.evaluate("""() => [...document.querySelectorAll('#modal .subtask-actions .btn')]
            .filter(b => b.getAttribute('aria-label')?.startsWith('Move') && getComputedStyle(b).display !== 'none').length""")
        check("up/down buttons hidden on phone", visible_arrows == 0, f"visible={visible_arrows}")
        grips = page.evaluate("() => [...document.querySelectorAll('#modal .sub-grip')].every(g => g.getBoundingClientRect().height >= 43)")
        check("drag handles are at least 44px", grips)

        # Copy list puts the checklist on the clipboard.
        page.click("#modal button[onclick*='copySubtasks']")
        page.wait_for_timeout(300)
        clip = page.evaluate("() => navigator.clipboard.readText().catch(() => '')")
        check("copy list writes the checklist", clip.startswith("Finish proposal") or "Subtask 1" in clip, clip[:120])
        check("copy list includes XP and checkbox", "(+2 XP)" in clip and ("[ ] " in clip or "[x] " in clip), clip[:120])

        check("no page errors", errors == [], str(errors)[:200])
        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
