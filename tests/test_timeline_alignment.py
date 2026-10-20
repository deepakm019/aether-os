"""Today's commitments timeline: the time label, the marker dot and the title share one centre line,
and every marker sits on the rail, at phone and desktop widths."""
from playwright.sync_api import sync_playwright

MEASURE = """() => {
  const t = document.querySelector('.timeline');
  const tr = t.getBoundingClientRect();
  const bc = getComputedStyle(t, '::before');
  const railX = tr.left + parseFloat(bc.left) + parseFloat(bc.width) / 2;
  return [...t.querySelectorAll('.time-row')].map(r => {
    const rr = r.getBoundingClientRect();
    const ac = getComputedStyle(r, '::after');
    const dotX = rr.left + parseFloat(ac.left) + parseFloat(ac.width) / 2;
    const dotY = rr.top + parseFloat(ac.top) + parseFloat(ac.height) / 2;
    const time = r.querySelector('.time').getBoundingClientRect();
    const title = r.querySelector('.event-title').getBoundingClientRect();
    return {
      dotX, railX, dotY,
      timeY: (time.top + time.bottom) / 2,
      titleY: (title.top + title.bottom) / 2,
    };
  });
}"""


def test_timeline_markers_share_the_text_centre_line(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for width in (320, 390, 1280):
            ctx = browser.new_context(viewport={"width": width, "height": 800})
            page = ctx.new_page()
            page.goto(app_server, wait_until="load")
            page.wait_for_selector("#app")
            page.wait_for_timeout(300)
            if page.locator("#beta-ack").count():
                page.check("#beta-ack")
                page.click("#beta-demo")
                page.wait_for_timeout(300)
            page.evaluate("() => setNav('today')")
            page.wait_for_timeout(300)
            rows = page.evaluate(MEASURE)
            assert len(rows) >= 2, f"{width}px: expected timeline rows in the demo plan"
            for r in rows:
                assert abs(r["dotY"] - r["titleY"]) <= 1, f"{width}px: dot is off the title line {r}"
                assert abs(r["timeY"] - r["titleY"]) <= 1, f"{width}px: time is off the title line {r}"
                assert abs(r["dotX"] - r["railX"]) <= 1, f"{width}px: dot is off the rail {r}"
            ctx.close()
        browser.close()
