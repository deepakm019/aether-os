"""Bundled open-source fonts: every font setting renders with a font file shipped in fonts/,
the choice is kept across reloads, and the app makes no requests outside its own origin."""
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

NEW_FONTS = {
    "inter": "AS Inter",
    "atkinson": "AS Atkinson",
    "jetbrains": "AS JetBrains Mono",
    "lora": "AS Lora",
    "nunito": "AS Nunito",
}


def _origin(url):
    parts = urlparse(url)
    return f"{parts.scheme}://{parts.netloc}"


def test_font_options_load_bundled_files_without_external_requests(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        requests = []
        page.on("request", lambda r: requests.append(r.url))
        page.goto(app_server, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)

        page.evaluate("() => setNav('settings')")
        page.wait_for_timeout(300)
        options = page.evaluate("() => [...document.querySelectorAll('select[aria-label=\"Font style\"] option')].map(o => o.value)")
        for key in NEW_FONTS:
            assert key in options, f"font option missing from Settings: {key}"

        for key, family in NEW_FONTS.items():
            page.evaluate(f"() => setSetting('font', '{key}')")
            page.wait_for_timeout(250)
            loaded = page.evaluate(
                f"async () => {{ await document.fonts.load('16px \"{family}\"'); return document.fonts.check('16px \"{family}\"'); }}")
            assert loaded, f"{key}: {family} did not load from fonts/"
            body_font = page.evaluate("() => getComputedStyle(document.body).fontFamily")
            assert family in body_font, f"{key}: body font is {body_font}"

        external = [u for u in requests if not u.startswith(_origin(app_server))]
        assert external == [], f"requests left the app origin: {external[:5]}"
        browser.close()


def test_chosen_font_survives_a_reload(app_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(app_server, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)
        page.evaluate("() => setSetting('font', 'jetbrains')")
        page.wait_for_timeout(600)
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(400)
        assert page.evaluate("() => document.documentElement.dataset.font") == "jetbrains"
        assert "AS JetBrains Mono" in page.evaluate("() => getComputedStyle(document.body).fontFamily")
        browser.close()


def test_bundled_fonts_are_precached_for_offline_use(app_server):
    """The service worker must cache every bundled font so the Settings choices work offline."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(app_server, wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(300)
        if page.locator("#beta-ack").count():
            page.check("#beta-ack")
            page.click("#beta-demo")
            page.wait_for_timeout(300)
        cached = page.evaluate("""async () => {
          await navigator.serviceWorker.ready;
          for (let i = 0; i < 50; i++) {
            const keys = await caches.keys();
            for (const k of keys) {
              if (!k.startsWith('astralsurge-os-')) continue;
              const urls = (await (await caches.open(k)).keys()).map(r => r.url);
              if (urls.some(u => u.includes('/fonts/'))) return urls.filter(u => u.includes('/fonts/'));
            }
            await new Promise(r => setTimeout(r, 200));
          }
          return [];
        }""")
        names = {u.rsplit("/", 1)[-1] for u in cached}
        for expected in ("inter-latin-var.woff", "atkinson-hyperlegible-regular.woff2", "jetbrains-mono-regular.woff",
                         "lora-latin-var.woff", "nunito-latin-var.woff"):
            assert expected in names, f"{expected} is not precached; cached: {sorted(names)}"
        browser.close()
