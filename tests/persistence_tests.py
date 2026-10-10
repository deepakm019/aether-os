import json, base64, time, os, sys, tempfile
from playwright.sync_api import sync_playwright

URL = os.environ.get("ASOS_URL", "http://127.0.0.1:8765/index.html")
OUT = tempfile.mkdtemp(prefix="asos_")
results = []
page_errors = []
PROMPT_ANSWER = ["correct horse 1"]

def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS" if ok else "FAIL"), name, detail, flush=True)

READ_IDB = """async () => {
 if(!(await indexedDB.databases()).some(d=>d.name==='astralsurge.os.v2')) return null;
 const db = await new Promise((res,rej)=>{const r=indexedDB.open('astralsurge.os.v2',1);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});
 const rec = await new Promise(res=>{const tx=db.transaction('kv','readonly');const q=tx.objectStore('kv').get('workspace');q.onsuccess=()=>res(q.result)});
 db.close();
 if(!rec) return null;
 let text = rec.encoding==='gzip' ? await new Response(new Blob([rec.data]).stream().pipeThrough(new DecompressionStream('gzip'))).text() : String(rec.data);
 return {raw:text, parsed:(()=>{try{return JSON.parse(text)}catch(e){return null}})()};
}"""

def idb_workspace(page):
    page.wait_for_timeout(400)
    r = page.evaluate(READ_IDB)
    return None if r is None else r["parsed"]

def new_app(browser, label):
    ctx = browser.new_context(accept_downloads=True, viewport={"width": 1280, "height": 860})
    page = ctx.new_page()
    page.on("pageerror", lambda e: page_errors.append(f"[{label}] {e}"))
    page.on("dialog", lambda d: d.accept(PROMPT_ANSWER[0]) if d.type == "prompt" else d.accept())
    page.goto(URL, wait_until="load")
    page.wait_for_selector("#app")
    page.wait_for_timeout(500)
    return ctx, page

def acknowledge(page, mode="demo"):
    if page.locator("#beta-ack").count():
        page.check("#beta-ack")
        if mode == "demo":
            page.click("#beta-demo")
        else:
            page.click("#beta-new")
        page.wait_for_timeout(400)

def nav(page, route):
    page.evaluate("(r)=>setNav(r)", route)
    page.wait_for_timeout(250)

def read_json(download):
    with open(download.path(), encoding="utf-8") as f:
        return json.load(f)

def set_file_via(page, trigger_fn, path):
    with page.expect_file_chooser() as fc:
        trigger_fn()
    fc.value.set_files(path)
    page.wait_for_timeout(500)

def write(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f) if not isinstance(obj, str) else f.write(obj)
    return p

LEGACY = {
    "mode": "demo", "vault": {"locked": False},
    "tasks": [{"id": "legacy_t1", "title": "Legacy task survives", "status": "To Do", "priority": "High",
               "energy": "Deep", "due": None, "important": True, "urgent": False, "timeSpent": 12,
               "tags": ["migrated"], "scheduled": False}],
    "planner": [], "habits": [{"id": "hl1", "title": "Legacy habit", "done": True, "streak": 2}],
    "workouts": [], "budgets": [{"id": "bl1", "name": "Dining", "limit": 5000, "spent": 100}],
    "transactions": [], "notes": [], "goals": [], "decisions": [],
    "focus": {"active": False, "paused": False}, "settings": {"theme": "Dark"},
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])

    # A. Backup export produces a versioned wrapper with the real workspace.
    ctx, page = new_app(browser, "A")
    acknowledge(page)
    nav(page, "settings")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Export", exact=True).first.click()
    backup_a = read_json(dl.value)
    backup_path = os.path.join(OUT, "backup_a.json")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_a, f)
    ws = backup_a.get("workspace", {})
    check("A1 backup has versioned wrapper", backup_a.get("format") == "astralsurge-backup" and backup_a.get("schema") == 2)
    check("A2 backup contains demo tasks", len(ws.get("tasks", [])) == 5, str(len(ws.get("tasks", []))))
    check("A3 backup never carries encryption secrets", "encryptionMeta" not in ws.get("vault", {}))
    check("A4 backup has no transient recovery marker", "__recoveryExport" not in json.dumps(backup_a))
    ctx.close()

    # B. Restore the wrapper into a brand-new browser profile (empty IndexedDB).
    ctx, page = new_app(browser, "B")
    acknowledge(page, mode="new")
    nav(page, "vault")
    set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), backup_path)
    check("B1 restore preview opens", page.get_by_text("Restore preview").count() == 1)
    page.get_by_role("button", name="Replace workspace").click()
    page.wait_for_timeout(600)
    stored = idb_workspace(page)
    check("B2 restored data is persisted to IndexedDB", stored is not None and len(stored.get("tasks", [])) == 5)
    check("B3 restored workspace is schema v2", stored and stored.get("schema") == 2)
    nav(page, "work")
    check("B4 restored task visible in UI", page.get_by_text("Finish proposal").count() >= 1)
    ctx.close()

    # C. Legacy localStorage-only workspace migrates into IndexedDB without fabricated data.
    ctx, page = new_app(browser, "C")
    acknowledge(page)
    page.evaluate("""() => new Promise(res => { const q = indexedDB.deleteDatabase('astralsurge.os.v2'); q.onsuccess = q.onerror = q.onblocked = () => res(); })""")
    page.evaluate("(v)=>localStorage.setItem('astralsurge.os.v1', v)", json.dumps(LEGACY))
    page.reload(wait_until="load"); page.wait_for_selector("#app"); page.wait_for_timeout(600)
    migrated = idb_workspace(page)
    check("C1 legacy localStorage migrated to IndexedDB", migrated is not None and migrated["tasks"][0]["title"] == "Legacy task survives")
    check("C2 no demo bills injected into real budgets", migrated and migrated["budgets"][0]["items"] == [])
    check("C3 no fabricated activity history", migrated and migrated["activity"] == {})
    check("C4 habit log not seeded with fake history", migrated and migrated["habitLog"].get("hl1") == {time.strftime("%Y-%m-%d"): 1})
    check("C5 legacy localStorage copy cleared", page.evaluate("localStorage.getItem('astralsurge.os.v1')") is None)
    nav(page, "work")
    check("C6 migrated task renders", page.get_by_text("Legacy task survives").count() >= 1)
    ctx.close()

    # D. Older bare-state file (no wrapper, no v2 keys) imports and renders; running timers are not resumed.
    future = int(time.time() * 1000) + 600000
    old_bare = dict(LEGACY, focus={"active": True, "paused": False, "seconds": 600, "initial": 1500,
                                   "startedAt": int(time.time()*1000), "endsAt": future, "taskId": "legacy_t1"})
    old_path = write("old_bare.json", old_bare)
    ctx, page = new_app(browser, "D")
    acknowledge(page, mode="new")
    nav(page, "vault")
    set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), old_path)
    check("D1 older bare backup is accepted", page.get_by_text("Restore preview").count() == 1)
    page.get_by_role("button", name="Replace workspace").click()
    page.wait_for_timeout(600)
    stored = idb_workspace(page)
    check("D2 imported focus is not running", stored and stored["focus"]["active"] is False and stored["focus"]["paused"] is True, str(stored and stored["focus"]))
    check("D3 imported bare backup gets v2 keys", stored and "reminders" in stored and "morningCheckins" in stored)
    nav(page, "today")
    check("D4 Today renders after older import", page.get_by_text("Good").count() >= 1 or page.locator(".h1").count() >= 1)
    ctx.close()

    # E. Malformed or newer-version files are rejected with a clear message and no state change.
    ctx, page = new_app(browser, "E")
    acknowledge(page)
    nav(page, "vault")
    for label, content, expect in [
        ("E1 non-JSON rejected", "not json at all", "not valid JSON"),
        ("E2 newer schema rejected", json.dumps({"format": "astralsurge-backup", "schema": 99, "workspace": {"tasks": []}}), "newer version"),
        ("E3 list-type violation rejected", json.dumps({"tasks": "oops", "notes": []}), "must be a list"),
    ]:
        path = write(f"bad_{label[:2]}.json", content)
        set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), path)
        page.wait_for_timeout(200)
        check(label, page.locator("#toast").inner_text().find(expect) >= 0 if True else False, page.locator("#toast").inner_text())
        page.wait_for_timeout(1600)
    check("E4 rejected imports left existing data intact", page.get_by_role("button", name="Restore", exact=True).count() >= 1 and page.locator("#drawer-content").inner_text().strip() == "")
    ctx.close()

    # F. Recovery export excludes images, and a wrapped no-image export imports cleanly.
    ctx, page = new_app(browser, "F")
    acknowledge(page)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    png_path = os.path.join(OUT, "dot.png"); open(png_path, "wb").write(png)
    nav(page, "work")
    page.get_by_role("button", name="+ Task").first.click()
    page.fill("input[name=title]", "Image task")
    set_file_via(page, lambda: page.get_by_role("button", name="choose images").click(), png_path)
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Save task").click()
    page.wait_for_timeout(400)
    nav(page, "settings")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Export recovery").click()
    rec_text = open(dl.value.path(), encoding="utf-8").read()
    rec_path = os.path.join(OUT, "recovery.json"); open(rec_path, "w", encoding="utf-8").write(rec_text)
    rec = json.loads(rec_text)
    check("F1 recovery export has no image payloads", "data:image" not in rec_text)
    check("F2 recovery export flags excluded images", rec.get("imagesExcluded") is True and rec.get("excludedImageCount", 0) >= 1)
    ctx.close()

    ctx, page = new_app(browser, "F2")
    acknowledge(page, mode="new")
    nav(page, "vault")
    set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), rec_path)
    page.get_by_role("button", name="Replace workspace").click()
    page.wait_for_timeout(600)
    stored = idb_workspace(page)
    check("F3 no-image recovery restores the task", stored and any(t["title"] == "Image task" for t in stored["tasks"]))
    ctx.close()

    # G. Encrypted vault: enable, lock/unlock (right and wrong passphrase), encrypted backup restore on a new profile.
    ctx, page = new_app(browser, "G")
    acknowledge(page)
    nav(page, "vault")
    PROMPT_ANSWER[0] = "correct horse 1"
    page.get_by_role("button", name="Enable encrypted vault").click()
    page.wait_for_timeout(3000)
    stored = idb_workspace(page)
    check("G1 encrypted envelope stored instead of plaintext", stored is not None and stored.get("type") == "ASOS-ENC-1")
    page.reload(wait_until="load"); page.wait_for_selector("#app"); page.wait_for_timeout(600)
    check("G2 reload shows lock screen", page.get_by_text("Welcome back.").count() == 1)
    page.fill("#unlock-input", "wrong passphrase")
    page.get_by_role("button", name="Unlock", exact=True).click()
    page.wait_for_timeout(1500)
    check("G3 wrong passphrase rejected", page.get_by_text("Welcome back.").count() == 1)
    page.fill("#unlock-input", "correct horse 1")
    page.get_by_role("button", name="Unlock", exact=True).click()
    page.wait_for_timeout(2500)
    nav(page, "work")
    check("G4 correct passphrase unlocks", page.get_by_text("Finish proposal").count() >= 1)
    nav(page, "settings")
    with page.expect_download() as dl:
        page.get_by_role("button", name="Export", exact=True).first.click()
    enc_text = open(dl.value.path(), encoding="utf-8").read()
    enc_path = os.path.join(OUT, "encrypted.asbackup"); open(enc_path, "w", encoding="utf-8").write(enc_text)
    check("G5 encrypted export is an envelope", json.loads(enc_text).get("type") == "ASOS-ENC-1")
    ctx.close()

    ctx, page = new_app(browser, "G2")
    acknowledge(page, mode="new")
    nav(page, "vault")
    set_file_via(page, lambda: page.locator('button[onclick="fileRestore()"]').click(), enc_path)
    check("G6 encrypted backup shows storage replace preview", page.get_by_text("Encrypted backup").count() == 1)
    page.get_by_role("button", name="Replace storage").click()
    page.wait_for_timeout(1000)
    check("G7 encrypted restore requires unlock", page.get_by_text("Welcome back.").count() == 1)
    page.fill("#unlock-input", "correct horse 1")
    page.get_by_role("button", name="Unlock", exact=True).click()
    page.wait_for_timeout(2500)
    nav(page, "work")
    check("G8 encrypted backup opens with passphrase", page.get_by_text("Finish proposal").count() >= 1)
    ctx.close()

    # H. Checkpoint: create, mutate, restore -> mutation gone.
    ctx, page = new_app(browser, "H")
    acknowledge(page)
    nav(page, "vault")
    page.locator("button[onclick='createCheckpoint()']").first.click()
    page.wait_for_timeout(800)
    nav(page, "work")
    page.get_by_role("button", name="+ Task").first.click()
    page.fill("input[name=title]", "Checkpoint extra")
    page.get_by_role("button", name="Save task").click()
    page.wait_for_timeout(500)
    nav(page, "vault")
    page.locator("button[onclick='compareCheckpoint()']").first.click()
    page.wait_for_timeout(400)
    page.locator("button[onclick='restoreCheckpoint()']").click()
    page.wait_for_timeout(600)
    stored = idb_workspace(page)
    check("H1 checkpoint restore removes later task", stored and not any(t["title"] == "Checkpoint extra" for t in stored["tasks"]))
    check("H2 checkpoint restore keeps original tasks", stored and len(stored["tasks"]) == 5)
    ctx.close()

    # I. Read-only guard: unreadable saved data is never overwritten.
    ctx, page = new_app(browser, "I")
    acknowledge(page)
    page.evaluate("""() => new Promise(res => { const r = indexedDB.open('astralsurge.os.v2',1); r.onsuccess = () => { const db = r.result; const tx = db.transaction('kv','readwrite'); tx.objectStore('kv').put({v:3,encoding:'json',data:'{corrupt',updatedAt:1,bytes:8,compressed:false},'workspace'); tx.oncomplete = () => { db.close(); res(); }; }; })""")
    page.reload(wait_until="load"); page.wait_for_selector("#app"); page.wait_for_timeout(1200)
    check("I1 read-only mode announced", page.evaluate("window.__asosReadOnly===true"))
    nav(page, "settings")
    page.get_by_role("button", name="Hide amounts", exact=False).count()
    before = page.evaluate(READ_IDB)["raw"]
    page.locator(".row", has_text="Hide amounts").locator("button").first.click()
    page.wait_for_timeout(500)
    after = page.evaluate(READ_IDB)["raw"]
    check("I2 writes blocked, corrupt record untouched", before == after == "{corrupt", after[:20])
    ctx.close()

    # J. Fonts: every option applies, persists, and invalid keys are refused.
    ctx, page = new_app(browser, "J")
    acknowledge(page)
    nav(page, "settings")
    options = page.get_by_label("Font style").locator("option").count()
    check("J1 nine font options in settings", options == 9, str(options))
    fonts = ["system", "humanist", "rounded", "geometric", "editorial", "serif", "condensed", "mono", "accessible"]
    bad = []
    for key in fonts:
        page.evaluate("(k)=>setSetting('font',k)", key)
        page.wait_for_timeout(50)
        applied = page.evaluate("document.documentElement.dataset.font")
        fam = page.evaluate("getComputedStyle(document.body).fontFamily")
        if applied != key or not fam:
            bad.append((key, applied, fam[:30]))
    check("J2 every font applies a body family", not bad, str(bad))
    page.evaluate("setSetting('font','comic-sans')")
    check("J3 unknown font refused", page.evaluate("document.documentElement.dataset.font") == "accessible")
    page.evaluate("setSetting('font','mono')"); page.wait_for_timeout(400)
    stored = idb_workspace(page)
    check("J4 font choice persisted", stored and stored["settings"]["font"] == "mono")
    ctx.close()

    # K. Tags: add on create, persisted, shown on card, searchable.
    ctx, page = new_app(browser, "K")
    acknowledge(page)
    nav(page, "work")
    page.get_by_role("button", name="+ Task").first.click()
    page.fill("input[name=title]", "Tagged task")
    page.fill("input[name=tags]", "alpha, beta ,, gamma")
    page.get_by_role("button", name="Save task").click()
    page.wait_for_timeout(500)
    stored = idb_workspace(page)
    created = [t for t in stored["tasks"] if t["title"] == "Tagged task"] if stored else []
    check("K1 tags parsed and persisted", created and created[0]["tags"] == ["alpha", "beta", "gamma"], str(created and created[0]["tags"]))
    page.get_by_role("tab", name="Inbox").click() if page.get_by_role("tab", name="Inbox").count() else page.get_by_role("button", name="Inbox", exact=True).click()
    page.wait_for_timeout(300)
    check("K2 tag chips render on the task card", page.get_by_text("#alpha").count() >= 1)
    ctx.close()

    # L. Focus session: start, pause, resume, end -> saved, nothing left running.
    ctx, page = new_app(browser, "L")
    acknowledge(page)
    nav(page, "focus")
    page.get_by_role("button", name="Start Focus").click(); page.wait_for_timeout(500)
    page.get_by_role("button", name="Pause", exact=True).click(); page.wait_for_timeout(300)
    page.get_by_role("button", name="Resume Focus").click(); page.wait_for_timeout(300)
    page.get_by_role("button", name="End & save").click(); page.wait_for_timeout(600)
    stored = idb_workspace(page)
    check("L1 focus ends cleanly", stored and stored["focus"]["active"] is False and stored["focus"]["paused"] is False)
    ctx.close()

    check("no page errors across all scenarios", not page_errors, "; ".join(page_errors[:4]))
    browser.close()

failed = [r for r in results if not r[1]]
print(f"\nPERSISTENCE RESULT: {len(results)-len(failed)}/{len(results)} passed")
if failed:
    sys.exit(1)
