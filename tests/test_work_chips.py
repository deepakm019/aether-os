"""Work cards and Plan table stay inside their containers, even with long unbroken tags and titles."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
LONG_TITLE = "Averyveryveryverylongsingleword-without-spaces-to-test-wrapping-behaviour"
LONG_TAGS = ("supercalifragilisticexpialidociousantidisestablishmentarianismpneumonoultramicroscopic,"
             "design,health,finance,family,learning")
CARD_OVERFLOW = """() => { const out=[]; document.querySelectorAll('.task-card').forEach(c=>{
  const cr=c.getBoundingClientRect();
  c.querySelectorAll('.chip,.btn,.task-card-title,.row-meta').forEach(e=>{
    const r=e.getBoundingClientRect();
    if(r.width && (r.right>cr.right+0.5 || r.left<cr.left-0.5)) out.push(e.textContent.trim().slice(0,20)+' +'+Math.round(r.right-cr.right));
  });}); return out; }"""
PAGE_SCROLL = "() => [document.documentElement.scrollWidth, window.innerWidth]"
TABLES = "() => [...document.querySelectorAll('table.table')].map(t => [t.scrollWidth, t.clientWidth])"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail and not ok else ""))


def open_app(browser, width, height=900):
    page = browser.new_page(viewport={"width": width, "height": height})
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


def add_long_task(page):
    page.evaluate("() => setNav('work')")
    page.wait_for_timeout(200)
    page.evaluate("() => openModal(taskModal)")
    page.wait_for_timeout(200)
    page.fill("#modal input[name=title]", LONG_TITLE)
    page.fill("#modal input[name=tags]", LONG_TAGS)
    page.locator("#modal button:has-text('Save')").first.click()
    page.wait_for_timeout(400)


def open_inbox(page):
    page.locator(".tabs button.tab", has_text="Inbox").click()
    page.wait_for_timeout(200)


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        for width in (280, 320, 390, 1280):
            page, errors = open_app(browser, width)
            add_long_task(page)
            open_inbox(page)
            overflow = page.evaluate(CARD_OVERFLOW)
            check(f"{width}px: work card chips and buttons inside card", overflow == [], str(overflow))
            scroll_w, inner_w = page.evaluate(PAGE_SCROLL)
            check(f"{width}px: work page has no sideways scroll", scroll_w <= inner_w, f"{scroll_w}>{inner_w}")
            check(f"{width}px: work page has no script errors", errors == [], str(errors))
            page.close()

        for width in (320, 390):
            page, errors = open_app(browser, width)
            add_long_task(page)
            open_inbox(page)
            page.add_style_tag(content=".task-card-actions .btn,.chip{font-size:20px!important}")
            page.wait_for_timeout(100)
            overflow = page.evaluate(CARD_OVERFLOW)
            check(f"{width}px: work card survives larger text", overflow == [], str(overflow))
            page.close()

        for width in (320, 390):
            page, errors = open_app(browser, width)
            page.evaluate("() => setNav('plan')")
            page.wait_for_timeout(300)
            tables = page.evaluate(TABLES)
            hidden = [t for t in tables if t[0] > t[1] + 1]
            check(f"{width}px: plan upcoming table shows every column", hidden == [], str(tables))
            page.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nWORK CHIPS RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
