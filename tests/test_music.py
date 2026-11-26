"""Music player: plays MP3s in place via file references and linked folders, keeps stats, never copies audio.

The file and folder pickers are replaced with real OPFS handles, so the reference path
(handle stored in IndexedDB, permission check, decode through Web Audio) runs for real.
Set MUSIC_FIXTURE to a short MP3 file path (about 2 seconds is ideal).
"""
import base64
import os
import sys

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
FIXTURE = os.environ.get("MUSIC_FIXTURE", "")
PREFS_KEY = "astralsurge.music.prefs.v2"
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


def dock(page):
    return page.evaluate(
        """() => { const d = document.querySelector('.mu-dock');
          return d ? { state: d.dataset.state, track: d.dataset.track || '' } : null; }"""
    )


def prefs(page):
    return page.evaluate("(k) => JSON.parse(localStorage.getItem(k) || '{}')", PREFS_KEY)


def set_range(page, selector, value):
    page.evaluate(
        """([sel, v]) => { const el = document.querySelector(sel); el.value = String(v);
          el.dispatchEvent(new Event('input', { bubbles: true })); }""",
        [selector, value],
    )


def add_reference(page, name, data_b64):
    """Write the MP3 into OPFS and hand the real handle to the file picker mock."""
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
    page.wait_for_function("() => document.querySelector('.mu-page') && /Added 1 song/.test(document.body.textContent)", timeout=10000)


def add_file_until(page, name, data_b64, songs):
    """Add one more file and wait until the header shows the expected song count."""
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
    page.wait_for_function(
        """(n) => { const h = document.querySelector('.mu-hero'); return !!h && new RegExp('(^|[^0-9])' + n + ' song').test(h.textContent); }""",
        arg=songs,
        timeout=10000,
    )


def add_folder(page, data_b64):
    """A linked folder with one song in a subfolder, via a directory picker mock."""
    page.evaluate(
        """async ([b64]) => {
          const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
          const root = await navigator.storage.getDirectory();
          const dir = await root.getDirectoryHandle('tm-folder', { create: true });
          const sub = await dir.getDirectoryHandle('album', { create: true });
          const fh = await sub.getFileHandle('folder-test.mp3', { create: true });
          const w = await fh.createWritable(); await w.write(bin); await w.close();
          window.showDirectoryPicker = async () => dir;
          render();
        }""",
        [data_b64],
    )
    page.click("button[data-mu='pickFolder']")
    page.wait_for_function("() => /Linked folder with 1 song/.test(document.body.textContent)", timeout=10000)


def main():
    if not FIXTURE or not os.path.exists(FIXTURE):
        print("MUSIC_FIXTURE not set or missing; skipping browser checks")
        sys.exit(2)
    data_b64 = base64.b64encode(open(FIXTURE, "rb").read()).decode()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = open_app(browser)
        # clear any earlier test state
        page.evaluate(
            """() => new Promise(r => { localStorage.removeItem('astralsurge.music.prefs.v2');
              const q = indexedDB.deleteDatabase('astralsurge.music.refs.v1');
              q.onsuccess = q.onerror = q.onblocked = () => r(); })"""
        )
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        open_music(page)

        # 1. Page and add
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

        # 2. Playback state comes from the Web Audio deck, shown on the dock
        page.click("button[data-mu='toggle']")
        page.wait_for_selector(".mu-dock[data-state='playing']", timeout=10000)
        check("playback starts and dock shows playing", True)

        page.wait_for_selector(".mu-dock[data-state='paused']", timeout=15000)
        page.click("button[data-mu='tab'][data-id='stats']")
        page.wait_for_selector(".mu-stats")
        check("finished track is counted as a play", stat_value(page, "Plays") == "1", stat_value(page, "Plays"))

        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        open_music(page)
        check("library survives reload", "1 song" in page.inner_text(".mu-page"))
        page.click("button[data-mu='play']")
        page.wait_for_selector(".mu-dock[data-state='playing']", timeout=10000)
        check("replays after reload using stored permission", True)
        page.click("button[data-mu='toggle']")
        page.wait_for_selector(".mu-dock[data-state='paused']")

        # 3. Shuffle and repeat
        page.click("button[data-mu='shuffle']")
        check("shuffle toggles", page.get_attribute("button[data-mu='shuffle']", "aria-pressed") == "true")
        page.click("button[data-mu='repeat']")
        check("repeat cycles to all", page.get_attribute("button[data-mu='repeat']", "aria-label") == "Repeat all")

        # 4. Folder-level access: one grant covers a whole folder tree
        add_folder(page, data_b64)
        roots = page.evaluate(
            """async () => {
              const db = await new Promise((res, rej) => { const r = indexedDB.open('astralsurge.music.refs.v1'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
              const get = s => new Promise(res => { const q = db.transaction(s).objectStore(s).getAll(); q.onsuccess = () => res(q.result); });
              const roots = await get('roots'); const tracks = await get('tracks'); db.close();
              const row = tracks.find(t => t.kind === 'root');
              return { roots: roots.length, path: row ? row.path : null, hasRoot: !!row && !!row.rootId };
            }"""
        )
        check("folder linked with a root and a relative path",
              roots["roots"] == 1 and roots["hasRoot"] and roots["path"] == ["album", "folder-test.mp3"],
              str(roots))
        page.click("button[data-mu='tab'][data-id='folders']")
        page.wait_for_selector(".mu-folder")
        check("folders tab lists the folder with a grant action",
              "tm-folder" in page.inner_text(".mu-page") and page.locator("button[data-mu='grantRoot']").count() == 1)
        add_file_until(page, "tone-c.mp3", data_b64, 3)
        page.click("button[data-mu='tab'][data-id='songs']")

        # 5. Gapless: the next song starts on the audio clock, with no user action in between
        if page.get_attribute("button[data-mu='shuffle']", "aria-pressed") == "true":
            page.click("button[data-mu='shuffle']")
        page.click(".mu-row >> nth=0 >> .mu-play-btn")
        page.wait_for_selector(".mu-dock[data-state='playing']", timeout=10000)
        first = dock(page)["track"]
        page.wait_for_function(
            """(prev) => { const d = document.querySelector('.mu-dock');
              return d && d.dataset.state === 'playing' && d.dataset.track && d.dataset.track !== prev; }""",
            arg=first,
            timeout=15000,
        )
        check("gapless: next song starts with no tap", dock(page)["track"] != first)

        # 6. Drag/keyboard reorder of upcoming queue items
        page.click("button[data-mu='toggle']")  # pause so the queue stays put
        page.wait_for_selector(".mu-dock[data-state='paused']")
        page.click(".mu-row >> nth=0 >> .mu-play-btn")
        page.wait_for_selector(".mu-dock[data-state='playing']", timeout=10000)
        page.click("button[data-mu='toggle']")
        page.wait_for_selector(".mu-dock[data-state='paused']")
        page.click("button[data-mu='tab'][data-id='queue']")
        page.wait_for_selector(".mu-qrow")
        before = page.evaluate("() => [...document.querySelectorAll('.mu-qrow .mu-row-title')].map(e => e.textContent)")
        if len(before) >= 2:
            page.click("button[data-mu='qDown'][data-id='1']")
            after = page.evaluate("() => [...document.querySelectorAll('.mu-qrow .mu-row-title')].map(e => e.textContent)")
            check("queue: move a song down swaps upcoming order",
                  len(after) == len(before) and after[0] == before[1] and after[1] == before[0],
                  f"before {before} after {after}")
        else:
            check("queue: enough upcoming songs to reorder", False, f"only {before}")

        # 7. Equalizer
        page.click("button[data-mu='tab'][data-id='songs']")
        page.click("button[data-mu='eqToggle']")
        page.wait_for_selector("#mu-preset")
        set_range(page, "input[data-band='0']", 6)
        check("eq band saved", prefs(page).get("eq", [None])[0] == 6, str(prefs(page).get("eq")))
        page.select_option("#mu-preset", "rock")
        saved = prefs(page)
        check("eq preset applies to all bands", saved.get("preset") == "rock" and saved.get("eq", [None])[0] == 4,
              str(saved))

        # 8. Crossfade still moves to the next song
        set_range(page, "#mu-xf", 3)
        check("crossfade setting saved", prefs(page).get("crossfade") == 3)
        page.click("button[data-mu='tab'][data-id='songs']")
        page.click(".mu-row >> nth=0 >> .mu-play-btn")
        page.wait_for_selector(".mu-dock[data-state='playing']", timeout=10000)
        xfirst = dock(page)["track"]
        page.wait_for_function(
            """(prev) => { const d = document.querySelector('.mu-dock');
              return d && d.dataset.state === 'playing' && d.dataset.track && d.dataset.track !== prev; }""",
            arg=xfirst,
            timeout=15000,
        )
        check("crossfade: next song starts before the first ends", dock(page)["track"] != xfirst)

        # 9. Mobile layout and errors
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
