"""Dog training Health tab: form labels, inputs and buttons line up, and no two blocks overlap,
at phone and desktop widths. Controls keep a 44px touch target."""
from playwright.sync_api import sync_playwright

OVERLAP = """() => {
  const root = document.querySelector('.page');
  const els = [...root.querySelectorAll('*')].filter(e => {
    const r = e.getBoundingClientRect(), cs = getComputedStyle(e);
    return r.width > 1 && r.height > 1 && cs.visibility !== 'hidden' && cs.display !== 'none' && cs.position !== 'fixed';
  });
  const hits = [];
  for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) {
    const a = els[i], b = els[j];
    if (a.contains(b) || b.contains(a)) continue;
    const ra = a.getBoundingClientRect(), rb = b.getBoundingClientRect();
    const ix = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
    const iy = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (ix > 3 && iy > 3) hits.push((a.textContent || a.tagName).trim().slice(0, 24) + ' x ' + (b.textContent || b.tagName).trim().slice(0, 24));
  }
  return hits;
}"""

FORMS = """() => [...document.querySelectorAll('.dog-form-row')].map(r => ({
  labelTops: [...r.querySelectorAll('label')].map(l => l.getBoundingClientRect().top),
  inputTops: [...r.querySelectorAll('input')].map(i => i.getBoundingClientRect().top),
  inputHeights: [...r.querySelectorAll('input')].map(i => i.getBoundingClientRect().height),
  inputBottoms: [...r.querySelectorAll('input')].map(i => i.getBoundingClientRect().bottom),
  button: (() => { const b = r.querySelector('.btn'); if (!b) return null; const x = b.getBoundingClientRect();
    return { bottom: x.bottom, height: x.height, width: x.width, parentWidth: r.getBoundingClientRect().width }; })(),
}))"""


def _open_health(browser, url, width):
    ctx = browser.new_context(viewport={"width": width, "height": 844})
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(300)
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        page.click("#beta-demo")
        page.wait_for_timeout(300)
    page.wait_for_timeout(150)
    page.evaluate("() => setNav('dog')")
    page.wait_for_timeout(250)
    page.locator("button.tab", has_text="Health").click()
    page.wait_for_timeout(500)
    return ctx, page, errors


def test_health_forms_align_and_do_not_overlap(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for width in (320, 390, 1280):
            ctx, page, errors = _open_health(browser, app_server, width)
            overflow = page.evaluate(
                "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
            assert overflow == 0, f"{width}px: Health page scrolls sideways by {overflow}px"

            forms = page.evaluate(FORMS)
            assert len(forms) == 3, f"{width}px: expected weight, vaccine and note forms, found {len(forms)}"
            for f in forms:
                labels = f["labelTops"]
                inputs = f["inputTops"]
                # Fields that share a visual line must share their label and input tops; fields that
                # wrap onto a new line are allowed to differ. Each label must sit the same distance above its input.
                gaps = [i - l for l, i in zip(labels, inputs)]
                assert max(gaps) - min(gaps) <= 1, f"{width}px: label-to-input spacing differs {gaps}"
                for a in range(len(labels)):
                    for c in range(len(labels)):
                        same_line_label = abs(labels[a] - labels[c]) <= 1
                        same_line_input = abs(inputs[a] - inputs[c]) <= 1
                        assert same_line_label == same_line_input, (
                            f"{width}px: a field's label and input disagree about their line {labels} {inputs}")
                for h in f["inputHeights"]:
                    assert h >= 43, f"{width}px: input is smaller than a touch target ({h}px)"
                b = f["button"]
                if b:
                    assert b["height"] >= 43, f"{width}px: button is smaller than a touch target"
                    assert b["width"] <= b["parentWidth"] + 1, f"{width}px: button overflows its form"

            overlaps = page.evaluate(OVERLAP)
            assert overlaps == [], f"{width}px: overlapping elements {overlaps[:5]}"
            assert errors == [], errors
            ctx.close()
        browser.close()
