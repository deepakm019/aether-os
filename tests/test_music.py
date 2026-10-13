"""Music: local player, listening history, auto playlists, analytics, privacy of
stored data, layout at phone and desktop widths, and search/More discovery."""
import math
import os
import struct
import sys
import tempfile
import wave

from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)


def make_wav(path, seconds, freq):
    rate = 8000
    frames = b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / rate)))
                      for i in range(int(rate * seconds)))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(frames)
    return path


def open_app(browser, width, height=844):
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


def go_music(page, tab=None):
    page.evaluate("() => setNav('music')")
    page.wait_for_timeout(200)
    if tab:
        page.locator(".tab", has_text=tab).first.click()
        page.wait_for_timeout(150)


def overflow(page):
    return page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")


def run():
    tmp = tempfile.mkdtemp()
    long_wav = make_wav(os.path.join(tmp, "long-track.wav"), 35, 440)
    short_wav = make_wav(os.path.join(tmp, "short-track.wav"), 3, 660)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])

        # 1. Layout at phone and desktop widths, empty state.
        for width in (320, 390, 1280):
            ctx, page, errors = open_app(browser, width)
            go_music(page)
            check(f"{width}px: music screen renders empty state", page.get_by_text("No music yet.").count() == 1)
            check(f"{width}px: no horizontal overflow", overflow(page) <= 0, f"overflow={overflow(page)}")
            check(f"{width}px: no page errors", not errors, str(errors[:2]))
            ctx.close()

        # 2. Discovery: More grid and search shortcut.
        ctx, page, errors = open_app(browser, 390)
        page.evaluate("() => setNav('more')"); page.wait_for_timeout(150)
        check("More grid lists Music", page.locator("button", has_text="Local player, playlists").count() == 1)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(100)
        page.evaluate("() => globalSearch()"); page.wait_for_timeout(250)
        page.locator("#search-input").fill("music"); page.wait_for_timeout(150)
        shortcut = page.locator("[data-action=search-shortcut][data-id=music]")
        check("search finds Music shortcut", shortcut.count() == 1)
        shortcut.first.click(); page.wait_for_timeout(250)
        check("search shortcut opens music route", page.evaluate("() => location.hash") == "#/music")
        ctx.close()

        # 3. Add files, library, playing, history, mini player.
        ctx, page, errors = open_app(browser, 390)
        go_music(page)
        page.locator("input[type=file][multiple]").first.set_input_files([long_wav, short_wav])
        page.wait_for_timeout(800)
        check("adding files lists both tracks", page.get_by_text("long-track").count() >= 1 and page.get_by_text("short-track").count() >= 1)
        tracks = page.evaluate("() => musicState().tracks")
        check("two tracks stored with ids", len(tracks) == 2, str(len(tracks)))
        check("stored track has no object URL or file data",
              all("url" not in t and "blob" not in str(t).lower() for t in tracks.values()))
        ids = sorted(tracks.keys())
        check("track ids are generated and valid", all(k.startswith("trk_") for k in ids))

        # Play the 35s track (library order is newest first, so pick by name).
        long_id = [k for k in ids if tracks[k]["name"] == "long-track.wav"][0]
        page.evaluate("(id) => musicPlayTrack(id, 'library')", long_id)
        page.wait_for_timeout(2500)
        plays = page.evaluate("(id) => musicState().tracks[id].plays", long_id)
        check("playing a track counts one play", plays == 1, f"plays={plays}")
        secs = page.evaluate("(id) => musicState().tracks[id].seconds", long_id)
        check("listening seconds accrue", secs >= 1, f"seconds={secs}")
        page.wait_for_timeout(300)
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(200)
        check("mini player visible on Today", page.locator("[data-music-mini]:not([hidden])").count() == 1)
        go_music(page)
        check("mini player hidden on Music screen", page.locator("[data-music-mini]:not([hidden])").count() == 0)
        check("now playing title shows track", page.locator("[data-music-title]").first.inner_text() == "long-track.wav")

        # Skip: next track within 30 seconds on a long track counts as a skip.
        page.evaluate("() => musicAdvance(1,true)"); page.wait_for_timeout(400)
        skips = page.evaluate("(id) => musicState().tracks[id].skips", long_id)
        check("early skip on a long track is counted", skips == 1, f"skips={skips}")
        page.evaluate("() => musicAdvance(-1,true)"); page.wait_for_timeout(300)

        # Favourite, playlists rule text, auto lists.
        page.evaluate("(id) => musicToggleFav(id)", long_id); page.wait_for_timeout(200)
        go_music(page, "Playlists")
        rules = page.locator(".music-playlist > .split .row-meta").all_inner_texts()
        check("six auto playlist cards with rule text", len(rules) == 6 and all(rules), str(len(rules)))
        check("Favourites card lists the starred track",
              page.locator(".music-playlist", has_text="Favourites").locator(".row-title", has_text="long-track").count() == 1)
        check("Most played lists the played track",
              page.locator(".music-playlist", has_text="Most played").locator(".row-title", has_text="long-track").count() == 1)
        check("Never played excludes played tracks",
              page.locator(".music-playlist", has_text="Never played").locator(".row-title", has_text="long-track").count() == 0)
        check("playlists: no overflow at 390px", overflow(page) <= 0, f"overflow={overflow(page)}")

        # Stats and hide toggle.
        go_music(page, "Stats")
        check("stats tiles render", page.get_by_text("Last 7 days").count() == 1 and page.get_by_text("Skip rate").count() == 1)
        check("stats show top tracks", page.get_by_text("Top tracks · all time").count() == 1)
        check("analytics charts render as svg", page.locator("svg.music-bars").count() == 2)
        page.get_by_role("button", name="Hide listening stats").click(); page.wait_for_timeout(150)
        check("hide stats hides tiles", page.get_by_text("Last 7 days").count() == 0 and page.get_by_text("Listening stats are hidden").count() == 1)
        page.get_by_role("button", name="Show stats").click(); page.wait_for_timeout(150)
        check("show stats restores tiles", page.get_by_text("Last 7 days").count() == 1)
        ctx320, page320, errors320 = open_app(browser, 320)
        page320.evaluate("() => setNav('music')"); page320.wait_for_timeout(200)
        page320.locator(".tab", has_text="Stats").first.click(); page320.wait_for_timeout(150)
        check("stats: no overflow at 320px", overflow(page320) <= 0, f"overflow={overflow(page320)}")
        ctx320.close()
        page.evaluate("() => setNav('today')"); page.wait_for_timeout(200)
        page.evaluate("() => musicToggle(false)"); page.wait_for_timeout(300)
        before = page.evaluate("() => Object.fromEntries(Object.entries(musicState().tracks).map(([k,v])=>[k,[v.plays,v.seconds,v.favourite]]))")
        check("no page errors during playback and browsing", not errors, str(errors[:3]))
        page.wait_for_timeout(4500)

        # 4. Persistence: history survives reload; files do not, and say so.
        page.reload(wait_until="load")
        page.wait_for_selector("#app")
        page.wait_for_timeout(1500)
        stored = page.evaluate("() => musicState().tracks")
        check("reload keeps track rows", len(stored) == 2, str(len(stored)))
        after = {k: [v["plays"], v["seconds"], v["favourite"]] for k, v in stored.items()}
        check("history survives reload", after == before, f"before={before} after={after}")
        go_music(page)
        page.wait_for_timeout(300)
        check("no audio is restored after reload", page.evaluate("() => !!(musicSession().files && Object.keys(musicSession().files).length)") is False)
        ctx.close()

        # 5. Sanitisation of stored music data.
        ctx, page, errors = open_app(browser, 390)
        clean = page.evaluate("""() => normalizeMusic({
          tracks:{trk_ok1:{name:'<img src=x onerror=alert(1)>'.repeat(40),size:-5,duration:9e9,plays:'7',skips:-1,seconds:'12',lastPlayed:'x',favourite:1},
                  'bad id!':{name:'nope'}, trk_bad2:null},
          log:[{t:1,k:'trk_ok1',s:99999},{k:'bogus',s:1},null],
          days:{'2026-10-01':{sec:-3,plays:2,skips:0,h:[1,2,'x']},'../etc':{sec:1}},
          hideStats:'yes'})""")
        check("bad track id dropped", "bad id!" not in clean["tracks"] and "trk_bad2" not in clean["tracks"])
        ok = clean["tracks"]["trk_ok1"]
        check("track name clamped to 160 chars", len(ok["name"]) <= 160, str(len(ok["name"])))
        check("numbers clamped", ok["size"] == 0 and ok["duration"] <= 86400 and ok["plays"] == 7 and ok["skips"] == 0 and ok["seconds"] == 12)
        check("log drops unknown keys and clamps seconds", len(clean["log"]) == 1 and clean["log"][0]["s"] == 86400)
        check("day keys validated and hours normalised", list(clean["days"].keys()) == ["2026-10-01"] and len(clean["days"]["2026-10-01"]["h"]) == 24 and clean["days"]["2026-10-01"]["sec"] == 0)
        check("hideStats coerced to boolean", clean["hideStats"] is True)
        empty = page.evaluate("() => normalizeMusic(undefined)")
        check("missing music data gives empty defaults", empty == {"tracks": {}, "log": [], "days": {}, "hideStats": False}, str(empty))
        check("no page errors in sanitisation", not errors, str(errors[:2]))
        ctx.close()
        browser.close()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\nMUSIC RESULT: {passed}/{len(results)} passed")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
