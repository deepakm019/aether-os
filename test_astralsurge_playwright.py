import argparse, asyncio, json, tempfile, inspect
from pathlib import Path
from playwright.async_api import async_playwright, expect

DEFAULT_FILE = Path(__file__).with_name('index_fixed.html')

async def load_app(page, target):
    path = Path(target)
    if path.exists():
        await page.set_content(path.read_text(encoding='utf-8'), wait_until='load')
    else:
        await page.goto(target, wait_until='load')
    await expect(page.locator('#app')).to_contain_text('AstralSurge')

async def click(page, locator):
    await locator.first.click(force=True)

async def click_nav(page, route):
    loc = page.locator(f"button[onclick=\"setNav('{route}')\"]")
    if await loc.count():
        await click(page, loc)
    else:
        await page.evaluate('(r) => setNav(r)', route)
    await page.wait_for_timeout(30)

async def open_direct_modal(page, handler):
    await click(page, page.locator(f'button[onclick="{handler}"]'))
    await expect(page.locator('#modal')).to_be_visible()

async def save_form(page):
    await click(page, page.locator('#modal form button.primary'))
    await expect(page.locator('#modal')).to_be_hidden()

async def main():
    ap = argparse.ArgumentParser(description='AstralSurge OS browser E2E suite')
    ap.add_argument('--target', default=str(DEFAULT_FILE), help='HTML file path or hosted URL')
    args = ap.parse_args()

    checks=[]; failures=[]; page_errors=[]; console_errors=[]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        page.set_default_timeout(4000)
        page.set_default_navigation_timeout(6000)
        page.on('pageerror', lambda e: page_errors.append(str(e)))
        page.on('console', lambda m: console_errors.append(m.text) if m.type == 'error' else None)

        async def check(name, fn):
            try:
                result = fn()
                if inspect.isawaitable(result):
                    result = await result
                if result is False:
                    raise AssertionError('condition returned false')
                checks.append((name,'PASS'))
            except Exception as e:
                checks.append((name,'FAIL')); failures.append(f'{name}: {e}')

        print('1. Initial render / global handler bridge', flush=True)
        await load_app(page, args.target)
        await check('Initial render', lambda: expect(page.locator('#app')).to_contain_text('Today'))
        await check('Inline handler bridge', lambda: page.evaluate("() => ['setNav','globalCreate','openModal','closeModal','inspect','startFocus','stopFocus','pauseFocus','resumeFocus','toggleHabit','logWorkout','reconcile','backupWorkspace','createCheckpoint','compareCheckpoint','fileRestore','downloadState','startStandaloneTimer','resetStandaloneTimer'].every(k => typeof window[k] === 'function')"))
        await check('Dynamic state bridge', lambda: page.evaluate("() => !!window.state && state.tasks.length === 5"))
        
        print('2. Primary navigation', flush=True)
        for route in ['work','focus','plan','more','today']:
            await click_nav(page, route)
            await check(f'Primary route #{route}', lambda route=route: page.evaluate('(r) => location.hash === "#/" + r', route))

        print('3. Secondary navigation', flush=True)
        secondary = ['goals','life','money','memory','progress','rules','vault','calendar','reminders','timer','settings','legal']
        for route in secondary:
            await click_nav(page, 'more')
            await click(page, page.locator(f"button[onclick=\"setNav('{route}')\"]"))
            await page.wait_for_timeout(30)
            await check(f'Secondary route #{route}', lambda route=route: page.evaluate('(r) => location.hash === "#/" + r', route))

        print('4. Task CRUD + inspect + scheduling', flush=True)
        await click_nav(page,'today')
        await open_direct_modal(page,'openModal(taskModal)')
        await page.locator('#modal input[name="title"]').fill('E2E Task')
        await page.locator('#modal textarea[name="desc"]').fill('Created by browser E2E')
        await save_form(page)
        await check('Task created in state', lambda: page.evaluate("() => state.tasks.some(t => t.title === 'E2E Task')"))
        await open_direct_modal(page,'globalCreate()')
        await click(page, page.locator('#modal button').filter(has_text='+ Note'))
        await check('Global create note route', lambda: expect(page.locator('#modal')).to_contain_text('Capture context'))
        await click(page, page.locator('#modal button').filter(has_text='Cancel'))

        await click_nav(page,'work')
        # Find the newly created task in whichever status the form defaulted to (Inbox/To Do). 
        await page.evaluate("window.workTab = state.tasks.find(t => t.title==='E2E Task').status; render()")
        task_row = page.locator('.row').filter(has_text='E2E Task').first
        await check('Task visible in work list', lambda: expect(task_row).to_be_visible())
        await click(page, task_row.locator('button').filter(has_text='Inspect'))
        await check('Task inspect drawer', lambda: expect(page.locator('#drawer')).to_contain_text('E2E Task'))
        await page.locator('#drawer button').filter(has_text='Schedule 45m').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(50)
        await check('Task scheduling action', lambda: page.evaluate("() => state.tasks.find(t=>t.title==='E2E Task').scheduled === true && state.planner.some(p=>p.taskId===state.tasks.find(t=>t.title==='E2E Task').id)"))
        await click(page, page.locator('#drawer-backdrop'))
        await task_row.locator('button[onclick^="startFocus("]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(50)
        await check('Task focus starts', lambda: page.evaluate("() => state.focus.active && location.hash === '#/focus'"))
        await page.locator('button[onclick="pauseFocus()"]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(30)
        await check('Task focus pauses', lambda: page.evaluate("() => !state.focus.active && state.focus.paused === true"))
        await page.locator('button[onclick="resumeFocus()"]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(30)
        await check('Task focus resumes', lambda: page.evaluate("() => state.focus.active"))
        await page.locator('button[onclick="stopFocus()"]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(30)
        await check('Task focus ends', lambda: page.evaluate("() => !state.focus.active && state.tasks.find(t=>t.title==='E2E Task').timeSpent >= 0"))
        await click_nav(page,'work')
        await page.evaluate("window.workTab='To Do'; render()")
        if await page.locator('.row').filter(has_text='E2E Task').count() == 0:
            await page.evaluate("window.workTab='Inbox'; render()")
        task_row = page.locator('.row').filter(has_text='E2E Task').first
        await click(page, task_row.locator('button').filter(has_text='Complete'))
        await check('Task completes', lambda: page.evaluate("() => state.tasks.find(t=>t.title==='E2E Task').status === 'Completed'"))

        print('5. Goal create + step execution', flush=True)
        await click_nav(page,'goals')
        await click(page, page.locator('button').filter(has_text='+ Goal'))
        await page.locator('#modal input[name="title"]').fill('E2E Goal')
        await page.locator('#modal input[name="step"]').fill('E2E Milestone')
        await save_form(page)
        await check('Goal created', lambda: page.evaluate("() => state.goals.some(g=>g.title==='E2E Goal')"))
        await click(page, page.locator('button').filter(has_text='Prepare task'))
        await check('Goal step opens task preparation', lambda: expect(page.locator('#modal')).to_contain_text('E2E Milestone'))
        await save_form(page)

        print('6. Notes + search', flush=True)
        await click_nav(page,'memory')
        await open_direct_modal(page,'openModal(noteModal)')
        await page.locator('#modal input[name="title"]').fill('E2E Note')
        await page.locator('#modal textarea[name="content"]').fill('E2E note content')
        await page.locator('#modal input[name="tags"]').fill('e2e, test')
        await save_form(page)
        await check('Note created', lambda: page.evaluate("() => state.notes.some(n=>n.title==='E2E Note')"))
        await click_nav(page,'today')
        await click(page, page.locator('button[onclick="globalSearch()"]'))
        await page.locator('#search-input').fill('proposal')
        await check('Search finds task', lambda: expect(page.locator('#search-results')).to_contain_text('Finish proposal'))
        await click(page, page.locator('#search-results button').filter(has_text='Open'))
        await check('Search opens task inspector', lambda: expect(page.locator('#drawer')).to_contain_text('Finish proposal'))
        await click(page, page.locator('#drawer-backdrop'))

        print('7. Money expense + reconciliation + privacy toggle', flush=True)
        await open_direct_modal(page,'openModal(expenseModal)')
        await page.locator('#modal input[name="amount"]').fill('321')
        await page.locator('#modal input[name="title"]').fill('E2E Expense')
        await save_form(page)
        await click_nav(page,'money')
        await check('Expense recorded', lambda: page.evaluate("() => state.transactions.some(t=>t.title==='E2E Expense' && t.amount===321)"))
        decision_row = page.locator('.row').filter(has_text='New monitor').first
        await click(page, decision_row.locator('button').filter(has_text='Reconcile'))
        await check('Reconciliation modal', lambda: expect(page.locator('#modal')).to_contain_text('Financial decision'))
        await click(page, page.locator('#modal button').filter(has_text='Reconcile'))
        await check('Decision reconciled', lambda: page.evaluate("() => state.decisions.find(d=>d.id==='d1').status === 'Reconciled'"))
        await click_nav(page,'settings')
        hide_row = page.locator('.row').filter(has_text='Hide amounts').first
        await click(page, hide_row.locator('button'))
        await check('Hide amounts enabled', lambda: page.evaluate('() => state.settings.hideAmounts === true'))
        await click(page, hide_row.locator('button'))
        await check('Hide amounts disabled', lambda: page.evaluate('() => state.settings.hideAmounts === false'))

        print('8. Life habits + workout', flush=True)
        await click_nav(page,'life')
        mark = page.locator('button').filter(has_text='Mark done').first
        if await mark.count():
            await click(page, mark)
        await check('Habit action works', lambda: page.evaluate('() => state.habits.some(h=>h.done)'))
        await click(page, page.locator('button').filter(has_text='+ Log'))
        await check('Workout log action works', lambda: page.evaluate("() => state.workouts[0].title === \"Today's session\""))

        print('9. Vault backup / checkpoint / lock / restore', flush=True)
        await click_nav(page,'vault')
        async with page.expect_download() as di:
            await click(page, page.locator('button[onclick="backupWorkspace()"]'))
        dl = await di.value
        await check('Vault backup download', lambda: dl.suggested_filename == 'astralsurge-workspace-backup.json')
        await click(page, page.locator('button[onclick="createCheckpoint()"]'))
        await check('Checkpoint created', lambda: page.evaluate("() => state.vault.lastCheckpoint === state.vault.lastCheckpoint && state.events.some(e=>e.type==='CHECKPOINT_CREATED')"))
        await click(page, page.locator('button[onclick="compareCheckpoint()"]'))
        await check('Checkpoint compare drawer', lambda: expect(page.locator('#drawer')).to_contain_text('Checkpoint diff'))
        await click(page, page.locator('#drawer-backdrop'))
        await click(page, page.locator('button[onclick="toggleLock()"]'))
        await check('Vault locks', lambda: page.evaluate('() => state.vault.locked === true'))
        await click(page, page.locator('button[onclick="toggleLock()"]'))
        await check('Vault unlocks', lambda: page.evaluate('() => state.vault.locked === false'))
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as tf:
            json.dump({'mode':'demo'}, tf)
            restore_path=tf.name
        async with page.expect_file_chooser() as fc_info:
            await click(page, page.locator('button[onclick="fileRestore()"]'))
        await (await fc_info.value).set_files(restore_path)
        await check('Restore preview', lambda: expect(page.locator('#drawer')).to_contain_text('Restore preview'))
        await click(page, page.locator('#drawer-backdrop'))

        print('10. Calendar controls', flush=True)
        await click_nav(page,'calendar')
        initial=await page.locator('.panel-header h2').inner_text()
        await page.locator('button[onclick="shiftCalendar(1)"]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(50)
        next_label=await page.locator('.panel-header h2').inner_text()
        print('CALENDAR', repr(initial), '->', repr(next_label), flush=True)
        await check('Calendar next month', lambda: next_label != initial)
        await page.locator('button[onclick="shiftCalendar(-1)"]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(50)
        async def calendar_back_is_initial():
            return await page.locator('.panel-header h2').inner_text() == initial
        await check('Calendar returns', calendar_back_is_initial)
        await page.locator('button[onclick="resetCalendar()"]').evaluate('(e)=>e.click()')
        await page.wait_for_timeout(50)
        async def calendar_today_is_initial():
            return await page.locator('.panel-header h2').inner_text() == initial
        await check('Calendar today', calendar_today_is_initial)

        print('11. Standalone timer', flush=True)
        await click_nav(page,'timer')
        await click(page,page.locator('button[onclick="startStandaloneTimer()"]'))
        before=await page.locator('#tool-timer').inner_text()
        await page.wait_for_timeout(1200)
        after=await page.locator('#tool-timer').inner_text()
        await check('Standalone timer decrements', lambda: before != after)
        await click(page,page.locator('button[onclick="resetStandaloneTimer()"]'))
        async def standalone_reset():
            return await page.locator('#tool-timer').inner_text() == '25:00'
        await check('Standalone timer reset', standalone_reset)

        print('12. Settings export + reset + suggestions', flush=True)
        await click_nav(page,'settings')
        await page.locator('.row').filter(has_text='Suggestions').locator('select').select_option('Off')
        await check('Suggestions setting', lambda: page.evaluate("() => state.settings.suggestions === 'Off'"))
        async with page.expect_download() as di:
            await click(page,page.locator('button[onclick="downloadState()"]'))
        export=await di.value
        await check('Workspace export download', lambda: export.suggested_filename == 'astralsurge-workspace-demo.json')
        await click(page,page.locator('button[onclick="resetDemo()"]'))
        await check('Reset demo restores baseline', lambda: page.evaluate("() => state.tasks.length===5 && state.notes.length===1 && state.transactions.length===3 && state.mode==='demo'"))

        print('13. Rules inspector + legal/reminders/settings routes', flush=True)
        await click_nav(page,'rules')
        await click(page,page.locator('button').filter(has_text='Inspect rule').first)
        await check('Rule inspector opens', lambda: expect(page.locator('#drawer')).to_contain_text('Rule inspector'))
        await click(page,page.locator('#drawer-backdrop'))
        await click_nav(page,'reminders')
        await check('Reminders page', lambda: expect(page.locator('.h1')).to_contain_text('Reminder tools'))
        await click_nav(page,'legal')
        await check('Legal page', lambda: expect(page.locator('.h1')).to_contain_text('Read the source text unchanged'))

        print('14. Dead-button audit on rendered page', flush=True)
        await click_nav(page,'today')
        dead = await page.evaluate("""() => Array.from(document.querySelectorAll('button')).filter(b => !b.disabled && b.type !== 'submit' && !b.getAttribute('onclick') && b.innerText.trim()).map(b=>b.innerText.trim())""")
        # The active Plan tab is intentionally a current-state tab with no action.
        unexpected=[d for d in dead if d != 'Plan']
        await check('No unexpected inert buttons', lambda: not unexpected)

        await browser.close()

    print('\n=== E2E TEST RESULT ===')
    for name,status in checks:
        print(f'[{status}] {name}')
    if page_errors:
        print('\nPAGE ERRORS:')
        for e in page_errors: print(' -',e)
    if console_errors:
        print('\nCONSOLE ERRORS:')
        for e in console_errors: print(' -',e)
    if failures:
        print('\nFAILURES:')
        for e in failures: print(' -',e)
        raise SystemExit(1)
    if page_errors or console_errors:
        raise SystemExit(1)
    print(f'\nAll {len(checks)} checks passed. No page errors or console errors.')

if __name__ == '__main__':
    asyncio.run(main())
