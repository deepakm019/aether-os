import json, time, os, tempfile, sys
from playwright.sync_api import sync_playwright
URL="http://127.0.0.1:8765/astralsurge.html"
OUT=tempfile.mkdtemp(prefix="sweep_")
results=[]; errs=[]
PROMPTS=[]
def check(n,ok,d=""):
    results.append((n,bool(ok),d)); print(("PASS" if ok else "FAIL"),n,d,flush=True)
RAW="""async(k)=>{if(!(await indexedDB.databases()).some(d=>d.name==='astralsurge.os.v2'))return null;const db=await new Promise((res,rej)=>{const r=indexedDB.open('astralsurge.os.v2',1);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)});const rec=await new Promise(res=>{const g=db.transaction('kv').objectStore('kv').get(k);g.onsuccess=()=>res(g.result)});db.close();if(!rec)return null;return rec.encoding==='gzip'?await new Response(new Blob([rec.data]).stream().pipeThrough(new DecompressionStream('gzip'))).text():String(rec.data)}"""
def ws(page):
    page.wait_for_timeout(500)
    t=page.evaluate(RAW,'workspace')
    return json.loads(t) if t else None
def handle(d):
    if d.type=="prompt":
        d.accept(PROMPTS.pop(0) if PROMPTS else "")
    else:
        d.accept()
def new_app(b):
    ctx=b.new_context(accept_downloads=True,viewport={"width":1280,"height":860})
    pg=ctx.new_page(); pg.on("pageerror",lambda e: errs.append(str(e))); pg.on("dialog",handle)
    pg.goto(URL,wait_until="load"); pg.wait_for_selector("#app"); pg.wait_for_timeout(400)
    if pg.locator("#beta-ack").count():
        pg.check("#beta-ack"); pg.click("#beta-demo"); pg.wait_for_timeout(400)
    return ctx,pg
def nav(pg,r): pg.evaluate("(r)=>setNav(r)",r); pg.wait_for_timeout(250)

with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--no-sandbox"])
    ctx,pg=new_app(b)
    # Habits
    nav(pg,"life"); PROMPTS[:]=["Meditate","daily"]
    pg.get_by_role("button",name="+ Habit").click(); pg.wait_for_timeout(300)
    check("habit created", pg.get_by_text("Meditate").count()>=1)
    pg.locator(".row",has_text="Meditate").get_by_role("button",name="Mark done").click(); pg.wait_for_timeout(300)
    s=ws(pg); hid=[h for h in s["habits"] if h["title"]=="Meditate"]
    check("habit completion logged for today", hid and len(s["habitLog"].get(hid[0]["id"],{}))==1)
    # Notes
    nav(pg,"memory"); pg.get_by_role("button",name="+ Note").first.click()
    pg.fill("#modal input[name=title]","Sweep note"); pg.fill("#modal textarea[name=content]","body text"); pg.fill("#modal input[name=tags]","x, y")
    pg.get_by_role("button",name="Save note").click(); pg.wait_for_timeout(300)
    s=ws(pg); check("note saved with tags", any(n["title"]=="Sweep note" and n["tags"]==["x","y"] for n in s["notes"]))
    # Goals
    nav(pg,"goals"); pg.get_by_role("button",name="+ Goal").click()
    pg.fill("#modal input[name=title]","Sweep goal"); pg.fill("#modal input[name=step]","First step"); pg.get_by_role("button",name="Create goal").click(); pg.wait_for_timeout(300)
    s=ws(pg); check("goal created with milestone", any(g["title"]=="Sweep goal" and len(g["steps"])==1 for g in s["goals"]))
    # Workouts
    nav(pg,"life"); pg.get_by_role("button",name="+ Workout").click()
    pg.fill("#modal textarea[name=exercises]","Squat|3x5@60"); pg.get_by_role("button",name="Save workout").click(); pg.wait_for_timeout(300)
    s=ws(pg); w=[x for x in s["workouts"] if x["exercises"] and x["exercises"][0]["name"]=="Squat"]
    check("workout parsed into sets", w and w[0]["exercises"][0]["sets"]==[{"sets":3,"reps":5,"weight":60}])
    # Expense
    nav(pg,"money"); before=len(ws(pg)["transactions"])
    pg.get_by_role("button",name="+ Expense").first.click(); pg.fill("#modal input[name=amount]","250"); pg.fill("#modal input[name=title]","Sweep expense")
    pg.get_by_role("button",name="Save expense").click(); pg.wait_for_timeout(300)
    s=ws(pg); check("expense recorded", len(s["transactions"])==before+1 and s["transactions"][0]["title"]=="Sweep expense")
    # Decision reconcile
    pg.get_by_role("button",name="Reconcile",exact=True).first.click(); pg.wait_for_timeout(200)
    pg.get_by_role("button",name="Reconcile",exact=True).last.click(); pg.wait_for_timeout(300)
    s=ws(pg); check("decision reconciled", any(d["status"]=="Reconciled" for d in s["decisions"]))
    # Search
    pg.evaluate("globalSearch()"); pg.wait_for_timeout(250); pg.fill("#search-input","proposal"); pg.wait_for_timeout(250)
    check("search finds task", pg.get_by_text("Finish proposal").count()>=1)
    pg.locator("[data-action=search-open]").first.click(); pg.wait_for_timeout(300)
    check("search result opens inspector", "Finish proposal" in pg.locator("#drawer").inner_text())
    pg.evaluate("closeDrawer()")
    # Calendar
    nav(pg,"calendar"); h1=pg.locator(".panel-header h2").first.inner_text()
    pg.get_by_role("button",name="Next month").click(); pg.wait_for_timeout(200)
    check("calendar advances a month", pg.locator(".panel-header h2").first.inner_text()!=h1)
    # Weekly review
    nav(pg,"progress"); pg.get_by_role("button",name="Write review").first.click() if pg.get_by_role("button",name="Write review").count() else pg.get_by_role("button",name="Edit review").first.click()
    pg.fill("#modal textarea[name=win]","Sweep win"); pg.fill("#modal textarea[name=improve]","Sweep improve"); pg.get_by_role("button",name="Save review").click(); pg.wait_for_timeout(300)
    s=ws(pg); check("weekly review saved", any(v.get("win")=="Sweep win" for v in s["weeklyReviews"].values()))
    # Reminders
    nav(pg,"reminders"); PROMPTS[:]=["Sweep reminder"]
    pg.get_by_role("button",name="In 1h").click(); pg.wait_for_timeout(300)
    pg.locator(".row",has_text="Sweep reminder").get_by_role("button",name="+1h").click(); pg.wait_for_timeout(300)
    s=ws(pg); r=[x for x in s["reminders"] if x["title"]=="Sweep reminder"]
    check("reminder created and snoozed", r and r[0]["status"]=="scheduled" and r[0].get("snoozedUntil"))
    # Task completion
    nav(pg,"work"); pg.evaluate("inspect('task','tsk_docs')"); pg.wait_for_timeout(250)
    xp0=ws(pg)["xp"]; pg.locator("#drawer").get_by_role("button",name="Complete",exact=True).click(); pg.wait_for_timeout(300)
    s=ws(pg); t=[x for x in s["tasks"] if x["id"]=="tsk_docs"][0]
    check("task completed with XP", t["status"]=="Completed" and s["xp"]>xp0, f"xp {xp0}->{s['xp']}")
    # Settings: hide amounts, theme, accent
    nav(pg,"settings")
    pg.locator(".row",has_text="Hide amounts").locator("button").first.click(); pg.wait_for_timeout(300)
    check("hide amounts persisted", ws(pg)["settings"]["hideAmounts"] is True)
    pg.locator(".row",has_text="Hide amounts").locator("button").first.click(); pg.wait_for_timeout(300)
    pg.get_by_label("Theme").select_option("Light")
    pg.wait_for_timeout(300)
    check("light theme applies", pg.evaluate("document.documentElement.dataset.theme")=="light")
    pg.locator("button[aria-label='Accent #ff7eb6']").click(); pg.wait_for_timeout(300)
    check("accent persisted", ws(pg)["settings"].get("accent")=="#ff7eb6")
    ctx.close()

    # Restore a plain backup into an already-encrypted vault: encryption must stay on.
    ctx,pg=new_app(b)
    nav(pg,"settings")
    with pg.expect_download() as dl:
        pg.get_by_role("button",name="Export",exact=True).first.click()
    plain=os.path.join(OUT,"plain.json"); open(plain,"w").write(open(dl.value.path()).read())
    ctx.close()
    ctx,pg=new_app(b)
    nav(pg,"vault"); PROMPTS[:]=["correct horse 1"]
    pg.get_by_role("button",name="Enable encrypted vault").click(); pg.wait_for_timeout(3000)
    nav(pg,"vault")
    with pg.expect_file_chooser() as fc:
        pg.get_by_role("button",name="Restore",exact=True).first.click()
    fc.value.set_files(plain); pg.wait_for_timeout(500)
    pg.get_by_role("button",name="Replace workspace").click(); pg.wait_for_timeout(800)
    s=None
    pg.reload(wait_until="load"); pg.wait_for_selector("#app"); pg.wait_for_timeout(500)
    check("plain restore into encrypted vault stays encrypted", pg.get_by_text("Welcome back.").count()==1)
    pg.fill("#unlock-input","correct horse 1"); pg.get_by_role("button",name="Unlock",exact=True).click(); pg.wait_for_timeout(2500)
    nav(pg,"work")
    check("encrypted workspace opens after restore", pg.get_by_text("Finish proposal").count()>=1)
    ctx.close()
    check("no page errors in sweep", not errs, "; ".join(errs[:3]))
    b.close()

failed=[r for r in results if not r[1]]
print(f"\nSWEEP RESULT: {len(results)-len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
