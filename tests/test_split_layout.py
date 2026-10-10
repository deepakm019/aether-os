"""Regression test: long names in the split expense form must not run into the amount inputs.

Reproduces the phone-width overlap where an unbroken name (no spaces) overflowed
its label column onto the input beside it.
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
LONG_NAME = "Maximiliandersteinhausenbergwitzelhaus"
WIDTHS = [320, 390, 430, 768, 1280]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def create_group_with_long_name(page):
    page.evaluate("() => setNav('split')")
    page.wait_for_timeout(250)
    page.locator("button[onclick='splitGroupModal()']").first.click()
    page.wait_for_timeout(250)
    page.fill("#modal input[name=name]", "Layout check")
    page.fill("#modal textarea[name=people]", f"Ann\n{LONG_NAME}\nBo")
    page.evaluate("() => document.querySelector('#modal form').requestSubmit()")
    page.wait_for_timeout(300)


def open_expense_form(page):
    page.locator("a.row").filter(
        has=page.locator(".row-title", has_text=re.compile(r"^Layout check$"))
    ).first.click()
    page.wait_for_timeout(250)
    page.locator("button[onclick^='splitExpenseModal']").first.click()
    page.wait_for_timeout(250)


MEASURE = """() => [...document.querySelectorAll('#modal .split-line')].map(line => {
  const label = line.querySelector('label.check');
  const input = line.querySelector('input[data-pid]');
  const range = document.createRange();
  range.selectNodeContents(label.querySelector('.split-name') || label);
  return {
    textRight: range.getBoundingClientRect().right,
    inputLeft: input.getBoundingClientRect().left,
  };
})"""


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        for width in WIDTHS:
            ctx = browser.new_context(viewport={"width": width, "height": 800})
            page = ctx.new_page()
            page.goto(URL, wait_until="load")
            page.wait_for_selector("#app")
            page.wait_for_timeout(300)
            if page.locator("#beta-ack").count():
                page.check("#beta-ack")
                page.click("#beta-demo")
                page.wait_for_timeout(300)
            create_group_with_long_name(page)
            open_expense_form(page)
            lines = page.evaluate(MEASURE)
            check(f"{width}px: three split lines rendered", len(lines) == 3, f"found {len(lines)}")
            for line in lines:
                ok = line["textRight"] < line["inputLeft"]
                check(f"{width}px: name stays left of its input",
                      ok, f"text ends {line['textRight']:.0f}px, input starts {line['inputLeft']:.0f}px")
            ctx.close()
        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nSPLIT LAYOUT RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
