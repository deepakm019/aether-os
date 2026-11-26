"""Music player: plays MP3s in place via file references, keeps stats, never copies audio.

The file picker is replaced with a real OPFS file handle, so the reference path
(handle stored in IndexedDB, permission check, streaming through an object URL)
runs for real. Set MUSIC_FIXTURE to a short MP3 file path.
"""
import base64
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
FIXTURE = os.environ.get("MUSIC_FIXTURE", "")
results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail and not ok else ""))


MOCK_PICKER = "window.showOpenFilePicker = async () => window.__pick || [];"


def open_app(browser, width=1280, height=900):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    ctx.add_init_script(MOCK_PICKER)
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


def open_music(page):
    page.evaluate("() => setNav('music')")
    page.wait_for_selector(".mu-page")


def stat_value(page, label):
    return page.evaluate(
        """(label) => {
          const card = [...document.querySelectorAll('.mu-stat')].find(c => c.querySelector('.quiet')?.textContent === label);
          return card ? card.querySelector('.mu-big').textContent : null; }""",
        label,
    )


def add_reference(page, name, data_b64):
    """Write the MP3 into OPFS and hand the real handle to the picker mock."""
    page.evaluate(
        """async ([name, b64]) => {
          const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
          const root = await navigator.storage.getDirectory();
          const fh = await root.getFileHandle(name, { create: true });
          const w = await fh.createWritable(); await w.write(bin); await w.close();
          window.__pick = [fh];
        }""",
        [name, data_b64],
    )
    page.click("button[data-mu='pickFiles']")
    page.wait_for_function("() => document.querySelector('.mu-page') && /Added 1 track/.test(document.body.textContent)", timeout=10000)


def main():
    if not FIXTURE or not os.path.exists(FIXTURE):
        print("MUSIC_FIXTURE not set or missing; skipping browser checks")
        sys.exit(2)
    data_b64 = base64.b64encode(open(FIXTURE, "rb").read()).decode()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = open_app(browser)
        # clear any earlier test state
        page.evaluate("""() => new Promise(r => { const q = indexedDB.deleteDatabase('astralsurge.music.refs.v1'); q.onsuccess = q.onerror = q.onblocked = () => r(); })""")
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        open_music(page)

        check("music page renders with add button", page.locator("button[data-mu='pickFiles']").count() == 1)

        add_reference(page, "tone-test.mp3", data_b64)
        check("reference added without copying audio", page.evaluate(
            """async () => {
              const db = await new Promise((res, rej) => { const r = indexedDB.open('astralsurge.music.refs.v1'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
              const names = [...db.objectStoreNames]; const ok = !names.includes('files');
              const rows = await new Promise(res => { const q = db.transaction('tracks').objectStore('tracks').getAll(); q.onsuccess = () => res(q.result); });
              db.close();
              return ok && rows.length === 1 && rows[0].kind === 'ref' && !!rows[0].handle && !('blob' in rows[0]);
            }"""), "expected one ref row with a handle and no file bytes")

        page.click("button[data-mu='toggle']")
        page.wait_for_function("() => { const a = document.getElementById('mu-audio'); return a && a.src.startsWith('blob:') && !a.paused; }", timeout=8000)
        check("playback streams from an object URL", True)

        page.wait_for_function("() => document.getElementById('mu-audio').ended === true", timeout=10000)
        page.click("button[data-mu='tab'][data-id='stats']")
        page.wait_for_selector(".mu-stats")
        check("finished track is counted as a play", stat_value(page, "Plays") == "1", stat_value(page, "Plays"))

        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        open_music(page)
        check("library survives reload", "1 track" in page.inner_text(".mu-page"))
        page.click("button[data-mu='play']")
        page.wait_for_function("() => { const a = document.getElementById('mu-audio'); return a && a.src.startsWith('blob:'); }", timeout=8000)
        check("replays after reload using stored permission", True)

        page.click("button[data-mu='shuffle']")
        check("shuffle toggles", "Shuffle on" in page.inner_text(".mu-player"))
        page.click("button[data-mu='repeat']")
        check("repeat cycles to all", "Repeat all" in page.inner_text(".mu-player"))

        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(200)
        overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
        check("no horizontal scroll at 390px", overflow <= 0, f"overflow {overflow}px")

        check("no page errors", not errors, "; ".join(errors[:3]))
        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
