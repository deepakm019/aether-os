"""Themes: seven named themes plus Auto. Each applies its base mode, palette
attributes, accent and browser theme colour; text meets WCAG AA; stored theme
names are validated on load."""
import os
import re
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []

THEMES = ["Dark", "Light", "Reading", "Night", "Contrast", "Ocean", "Forest", "Auto"]
# name -> (base mode, palette attr or None, body background rgb, accent hex, theme-color)
EXPECT = {
    "Dark": ("dark", None, (12, 14, 17), "#9d88ff", None),
    "Light": ("light", None, (245, 246, 248), "#9d88ff", None),
    "Reading": ("light", "reading", (244, 236, 216), "#8a5a2b", "#f4ecd8"),
    "Night": ("dark", "night", (0, 0, 0), "#8fb4ff", "#000000"),
    "Contrast": ("dark", "contrast", (0, 0, 0), "#ffd60a", "#000000"),
    "Ocean": ("dark", "ocean", (11, 22, 32), "#5fc9f8", "#0b1620"),
    "Forest": ("dark", "forest", (13, 20, 15), "#8fdc9a", "#0d140f"),
}


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def luminance(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b):
    la, lb = sorted([luminance(a), luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def parse_rgb(text):
    nums = [int(float(x)) for x in re.findall(r"[\d.]+", text)[:3]]
    return tuple(nums)


def open_app(browser, width=390, height=844):
    ctx = browser.new_context(viewport={"width": width, "height": height})
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


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

        # 1. Settings offers every theme, in order.
        ctx, page, errors = open_app(browser)
        page.evaluate("() => setNav('settings')")
        page.wait_for_timeout(300)
        options = page.locator("select[onchange*=\"setSetting('theme'\"] option").all_inner_texts()
        check("theme picker lists all eight options in order", options == THEMES, str(options))
        ctx.close()

        # 2. Each theme applies its mode, palette, accent and colours, with AA text contrast.
        for name in THEMES:
            ctx, page, errors = open_app(browser)
            page.evaluate("(t) => { setSetting('theme', t); setNav('today'); }", name)
            page.wait_for_timeout(350)
            info = page.evaluate("""() => {
              const root = document.documentElement, body = getComputedStyle(document.body);
              const panel = document.querySelector('.panel');
              const meta = document.querySelector('.row-meta');
              return {
                mode: root.dataset.theme, palette: root.dataset.palette || null,
                accent: getComputedStyle(root).getPropertyValue('--accent').trim(),
                bg: body.backgroundColor, text: body.color,
                panelBg: panel ? getComputedStyle(panel).backgroundColor : null,
                muted: meta ? getComputedStyle(meta).color : null,
                themeColor: (document.querySelector('meta[name=theme-color]') || {}).content || null
              };
            }""")
            if name == "Auto":
                check("Auto follows system (no palette attribute)", info["palette"] is None, str(info))
                check("Auto sets a valid base mode", info["mode"] in ("dark", "light"), info["mode"])
                ctx.close()
                continue
            mode, palette, bg_rgb, accent, theme_color = EXPECT[name]
            check(f"{name}: base mode is {mode}", info["mode"] == mode, info["mode"])
            check(f"{name}: palette attribute is {palette}", info["palette"] == palette, str(info["palette"]))
            bg = parse_rgb(info["bg"])
            check(f"{name}: body background is {bg_rgb}", bg == bg_rgb, info["bg"])
            check(f"{name}: accent is {accent}", info["accent"].lower() == accent.lower(), info["accent"])
            if theme_color:
                check(f"{name}: browser theme colour is {theme_color}",
                      (info["themeColor"] or "").lower() == theme_color.lower(), str(info["themeColor"]))
            text_ratio = contrast(parse_rgb(info["text"]), bg)
            check(f"{name}: body text contrast >= 4.5", text_ratio >= 4.5, f"{text_ratio:.1f}")
            if info["panelBg"] and info["muted"]:
                muted_ratio = contrast(parse_rgb(info["muted"]), parse_rgb(info["panelBg"]))
                check(f"{name}: muted text on panels >= 4.5", muted_ratio >= 4.5, f"{muted_ratio:.1f}")
            check(f"{name}: no page errors", not errors, "; ".join(errors[:2]))
            ctx.close()

        # 3. A palette does not break narrow layouts.
        for name in ("Reading", "Contrast"):
            ctx, page, errors = open_app(browser, width=320, height=640)
            page.evaluate("(t) => { setSetting('theme', t); setNav('settings'); }", name)
            page.wait_for_timeout(300)
            overflow = page.evaluate(
                "() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth)")
            check(f"320px {name}: Settings fits width", overflow == 0, f"overflow {overflow}px")
            ctx.close()

        # 4. Stored theme names are validated on load (import safety).
        ctx, page, errors = open_app(browser)
        checks = page.evaluate("""() => ({
            reading: normalizeWorkspace({settings:{theme:'Reading'}}).settings.theme,
            night: normalizeWorkspace({settings:{theme:'Night'}}).settings.theme,
            forest: normalizeWorkspace({settings:{theme:'Forest'}}).settings.theme,
            bogus: normalizeWorkspace({settings:{theme:'Neon'}}).settings.theme,
            script: normalizeWorkspace({settings:{theme:'<img src=x onerror=alert(1)>'}}).settings.theme,
            missing: normalizeWorkspace({settings:{}}).settings.theme
        })""")
        check("stored 'Reading' is kept", checks["reading"] == "Reading", str(checks))
        check("stored 'Night' is kept", checks["night"] == "Night", str(checks))
        check("stored 'Forest' is kept", checks["forest"] == "Forest", str(checks))
        check("unknown theme falls back to Dark", checks["bogus"] == "Dark", str(checks))
        check("markup-like theme value falls back to Dark", checks["script"] == "Dark", str(checks))
        check("missing theme falls back to Dark", checks["missing"] == "Dark", str(checks))
        ctx.close()

        browser.close()

    failed = [r for r in results if not r[1]]
    print(f"\nTHEMES RESULT: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
