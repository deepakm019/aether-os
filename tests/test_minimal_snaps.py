"""Minimal mode snaps: edit text/color/time, +1 h snooze, drag-to-pin, countdown, phone layout, no leak into Normal mode."""
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def open_minimal(browser, width=390, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.evaluate("() => switchMinimalMode('minimal')")
    page.wait_for_selector(".minimal-app")
    return ctx, page


def post(page, text, duration=None):
    page.fill("#minimal-note", text)
    if duration:
        page.select_option("#minimal-duration", duration)
    page.click("button:has-text('post')")
    page.wait_for_selector(f".minimal-item:has-text('{text}')")


def items(page):
    """Read the persisted Minimal record straight from IndexedDB (the app's helpers are not global)."""
    return page.evaluate("""async () => {
        const db = await new Promise((res, rej) => {
            const r = indexedDB.open('astralsurge.minimal.v1', 1);
            r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
        });
        const value = await new Promise((res, rej) => {
            const q = db.transaction('kv', 'readonly').objectStore('kv').get('scribbles');
            q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error);
        });
        db.close();
        return (value && value.items) || [];
    }""")


def card(page, text):
    return page.locator(".minimal-item", has_text=text).first


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # 1. Phone layout: fits width and top padding is compact (no 15vh dead space).
        ctx, page = open_minimal(browser, 390, 844)
        post(page, "layout check note")
        overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("minimal fits 390px width", overflow <= 0, f"overflow {overflow}px")
        pad_top = page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.minimal-app')).paddingTop)")
        check("minimal phone top padding is compact", pad_top <= 40, f"{pad_top}px")
        ctx.close()

        # 2. Duration dropdown offers stays, 1h, 3h, 6h, 12h, 24h; default 24h.
        ctx, page = open_minimal(browser)
        opts = page.locator("#minimal-duration option").evaluate_all("els => els.map(e => e.value)")
        check("dropdown has stays,1h,3h,6h,12h,24h", opts == ["stays", "1h", "3h", "6h", "12h", "24h"], str(opts))
        check("dropdown defaults to 24h", page.locator("#minimal-duration").input_value() == "24h")

        # 3. Posting with 3h sets a ~3 hour expiry and shows a live countdown.
        post(page, "three hour snap", "3h")
        it = [i for i in items(page) if i.get("text") == "three hour snap"][0]
        span = it["expiresAt"] - it["createdAt"]
        check("3h snap expires in ~3 hours", abs(span - 10800000) < 3000, f"{span}ms")
        label = card(page, "three hour snap").locator(".minimal-countdown").text_content()
        check("countdown shows h:mm:ss left", "left" in label and label[:1].isdigit(), label)
        page.wait_for_timeout(2200)
        label2 = card(page, "three hour snap").locator(".minimal-countdown").text_content()
        check("countdown ticks down live", label2 != label, f"{label} -> {label2}")

        # 4. Edit text, then cancel keeps old text, empty save is rejected.
        card(page, "three hour snap").locator("button:has-text('edit')").click()
        page.fill("#minimal-edit-text", "edited snap text")
        page.click("button:has-text('cancel')")
        check("cancel keeps original text", card(page, "three hour snap").count() == 1)
        card(page, "three hour snap").locator("button:has-text('edit')").click()
        page.fill("#minimal-edit-text", "   ")
        page.click("form.minimal-edit button[type=submit]")
        page.wait_for_timeout(200)
        check("empty edit is rejected", page.locator("form.minimal-edit").count() == 1)
        page.fill("#minimal-edit-text", "edited snap text")
        page.click("form.minimal-edit button[type=submit]")
        page.wait_for_selector(".minimal-item:has-text('edited snap text')")
        check("edit saves new text", card(page, "edited snap text").count() == 1)

        # 5. Color change persists and is applied to the card.
        card(page, "edited snap text").locator("button:has-text('edit')").click()
        page.locator("input[name='minimal-edit-color'][value='pink']").check(force=True)
        page.click("form.minimal-edit button[type=submit]")
        page.wait_for_selector(".minimal-item[data-color='pink']")
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        page.evaluate("() => switchMinimalMode('minimal')")
        page.wait_for_selector(".minimal-item[data-color='pink']", timeout=5000)
        check("pink color persists across reload", page.locator(".minimal-item[data-color='pink']").count() == 1)
        post(page, "fresh default snap")
        check("default color is yellow for new snaps", card(page, "fresh default snap").get_attribute("data-color") == "yellow")

        # 6. Edit time: choose 12h from edit form.
        card(page, "edited snap text").locator("button:has-text('edit')").click()
        page.select_option("#minimal-edit-expiry", "12h")
        page.click("form.minimal-edit button[type=submit]")
        page.wait_for_timeout(300)
        it = [i for i in items(page) if i.get("text") == "edited snap text"][0]
        remaining = it["expiresAt"] - page.evaluate("() => Date.now()")
        check("edit time change to 12h", abs(remaining - 43200000) < 5000, f"{remaining}ms")

        # 7. +1 h snooze adds exactly one hour to the expiry.
        before = it["expiresAt"]
        card(page, "edited snap text").locator("button:has-text('+1 h')").click()
        page.wait_for_timeout(300)
        it = [i for i in items(page) if i.get("text") == "edited snap text"][0]
        check("+1 h snooze adds one hour", abs((it["expiresAt"] - before) - 3600000) < 2000, f"{it['expiresAt'] - before}ms")

        # 8. Edit + snooze combined from the edit form.
        card(page, "edited snap text").locator("button:has-text('edit')").click()
        page.fill("#minimal-edit-text", "snoozed in edit")
        page.click("button:has-text('save + 1 h')")
        page.wait_for_selector(".minimal-item:has-text('snoozed in edit')")
        it = [i for i in items(page) if i.get("text") == "snoozed in edit"][0]
        check("save + 1 h snooze stores text and extends time", it["expiresAt"] - page.evaluate("() => Date.now()") > 3600000 * 1.5)

        # 9. Stays snaps have no snooze button.
        post(page, "forever snap", "stays")
        check("stays snap has no +1 h button", card(page, "forever snap").locator("button:has-text('+1 h')").count() == 0)

        # 10. Drag the grip to reorder; pinned snaps keep their own group on top.
        def drag_card(text, target_text, offset=-4):
            src = card(page, text).locator(".minimal-grip")
            box = src.bounding_box()
            tgt = card(page, target_text).bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            ty = tgt["y"] + tgt["height"] / 2 + offset
            page.mouse.move(cx, cy)
            page.mouse.down()
            for step in range(1, 16):
                page.mouse.move(cx, cy + (ty - cy) * step / 15)
            page.mouse.up()
            page.wait_for_timeout(400)

        def feed_texts():
            return page.locator(".minimal-item .minimal-item-text").all_text_contents()

        for t in ["reorder A", "reorder B", "reorder C"]:
            post(page, t)
        check("new snaps start newest-first", feed_texts()[:3] == ["reorder C", "reorder B", "reorder A"], str(feed_texts()[:3]))
        drag_card("reorder A", "reorder C")
        check("drag A up above C reorders the feed", feed_texts()[0] == "reorder A", str(feed_texts()[:3]))
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        page.evaluate("() => switchMinimalMode('minimal')")
        page.wait_for_selector(".minimal-item:has-text('reorder A')")
        check("reorder persists across reload", feed_texts()[0] == "reorder A", str(feed_texts()[:3]))

        card(page, "reorder B").locator("button:has-text('pin')").click()
        page.wait_for_timeout(300)
        check("pinned snap moves to top group", feed_texts()[0] == "reorder B", str(feed_texts()[:3]))
        drag_card("reorder A", "reorder B", offset=-30)
        check("unpinned snap cannot be dragged above a pinned snap", feed_texts()[0] == "reorder B", str(feed_texts()[:3]))
        check("dragging keeps the pinned flag unchanged", card(page, "reorder A").get_attribute("data-pinned") == "0")

        # 11. Composer draft survives a re-render (edit start).
        page.fill("#minimal-note", "draft kept")
        card(page, "forever snap").locator("button:has-text('edit')").click()
        check("composer draft kept while editing", page.locator("#minimal-note").input_value() == "draft kept")

        # 12. No visual leak: Normal mode has no minimal chrome or classes.
        page.click("button:has-text('switch to normal')")
        page.wait_for_timeout(600)
        check("normal mode has no .minimal-app", page.locator(".minimal-app").count() == 0)
        check("normal mode drops minimal-mode-active", page.evaluate("() => !document.documentElement.classList.contains('minimal-mode-active')"))
        ctx.close()

        # 13. Mobile: edit form fits the phone width.
        ctx, page = open_minimal(browser, 320, 568)
        post(page, "small screen snap")
        card(page, "small screen snap").locator("button:has-text('edit')").click()
        overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
        check("edit form fits 320px width", overflow <= 0, f"overflow {overflow}px")
        ctx.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nMINIMAL SNAPS RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
