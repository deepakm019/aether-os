// Unit tests for dog-companion.js. Run with: npm run test:unit
const { test } = require('node:test');
const assert = require('node:assert/strict');
const D = require('../../dog-companion.js');

const at = (y, m, d, h = 12, min = 0) => new Date(y, m - 1, d, h, min, 0, 0);
const key = (y, m, d) => D.dateKey(new Date(y, m - 1, d));

/* ---------- content ---------- */

test('exactly 55 skills, unique ids, ordered from most to least important', () => {
  assert.equal(D.ITEMS.length, 55);
  assert.equal(new Set(D.ITEMS.map(i => i.id)).size, 55);
  assert.deepEqual(D.ITEMS.map(i => i.i), D.ITEMS.map((_, k) => k + 1));
  assert.equal(D.ITEMS[0].id, 'name', 'first skill is name recognition');
  assert.equal(D.ITEMS[1].id, 'look', 'second skill is eye contact');
});

test('every skill has a valid environment, minutes, items needed and at least two steps', () => {
  for (const it of D.ITEMS) {
    assert.ok(['indoor', 'outdoor', 'both'].includes(it.env), it.id);
    assert.ok(it.min >= 5 && it.min <= 60, `${it.id} minutes`);
    assert.ok(it.req.length > 0, `${it.id} needs items`);
    assert.ok(it.steps.length >= 2, `${it.id} steps`);
    assert.ok(it.xp >= 10, `${it.id} xp`);
  }
});

test('indoor and outdoor pools are each large enough for a daily set of three', () => {
  for (const f of ['indoor', 'outdoor', 'both']) {
    const n = D.ITEMS.filter(it => it.env === f || it.env === 'both').length;
    assert.ok(n >= 3, f);
  }
});

/* ---------- validation of stored or imported data ---------- */

test('normalizeDog returns a blank record for missing or non-object input', () => {
  for (const bad of [null, undefined, 'x', 42, [], true]) {
    const d = D.normalizeDog(bad);
    assert.equal(d.xp, 0);
    assert.deepEqual(d.done, {});
    assert.equal(d.pref, 'both');
  }
});

test('normalizeDog drops unknown skills, bad dates and malformed records', () => {
  const d = D.normalizeDog({
    done: { sit: '2026-10-01', nope: '2026-10-01', look: 'not-a-date' },
    potty: [{ t: 1, type: 'pee' }, { t: 2, type: 'hack' }, { t: 'x', type: 'pee' }, null],
    weights: [{ d: '2026-10-01', kg: 12.34 }, { d: 'bad', kg: 5 }, { d: '2026-10-01', kg: -1 }],
    vax: [{ d: '2026-10-01', name: '   ' }, { d: '2026-10-01', name: 'DHPP' }],
    pref: 'space',
  });
  assert.deepEqual(Object.keys(d.done), ['sit']);
  assert.equal(d.potty.length, 1);
  assert.equal(d.potty[0].type, 'pee');
  assert.equal(d.weights.length, 1);
  assert.equal(d.weights[0].kg, 12.3);
  assert.equal(d.vax.length, 1);
  assert.equal(d.vax[0].name, 'DHPP');
  assert.equal(d.pref, 'both', 'unknown preference falls back');
});

test('normalizeDog caps list sizes and text lengths', () => {
  const potty = Array.from({ length: 2500 }, (_, i) => ({ t: 1e12 + i, type: 'pee' }));
  const d = D.normalizeDog({ potty, notes: [{ d: '2026-10-01', text: 'x'.repeat(900) }], name: 'n'.repeat(200) });
  assert.equal(d.potty.length, D.LIMITS.potty);
  assert.equal(d.notes[0].text.length, D.LIMITS.noteLen);
  assert.equal(d.name.length, D.LIMITS.nameLen);
});

test('normalizeDog strips control characters from text', () => {
  const d = D.normalizeDog({ name: 'Bo\u0000b\u0007y' });
  assert.equal(d.name, 'Bo b y');
});

test('normalizeDog keeps potty events sorted by time', () => {
  const d = D.normalizeDog({ potty: [{ t: 300, type: 'pee' }, { t: 100, type: 'poop' }, { t: 200, type: 'pee' }] });
  assert.deepEqual(d.potty.map(p => p.t), [100, 200, 300]);
});

test('esc escapes markup so stored text cannot inject HTML', () => {
  assert.equal(D.esc('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
  assert.equal(D.esc(`'&`), '&#39;&amp;');
  assert.equal(D.esc(null), '');
});

test('art escapes its label', () => {
  const svg = D.art('treat', '"><script>x</script>');
  assert.ok(!svg.includes('<script>'));
  assert.ok(svg.includes('&quot;&gt;&lt;script&gt;'));
});

/* ---------- XP and skills ---------- */

test('marking a skill mastered adds its XP; undoing removes it and never goes below zero', () => {
  const dog = D.blank();
  const now = at(2026, 10, 18);
  const it = D.IDX.sit;
  assert.equal(D.toggleDone(dog, 'sit', now), true);
  assert.equal(dog.xp, it.xp);
  assert.equal(dog.done.sit, key(2026, 10, 18));
  D.toggleDone(dog, 'sit', now);
  assert.equal(dog.xp, 0);
  assert.equal(dog.done.sit, undefined);
  D.toggleDone(dog, 'sit', now);
  D.toggleDone(dog, 'sit', now);
  assert.equal(dog.xp, 0);
});

test('an unknown skill id is rejected without changing anything', () => {
  const dog = D.blank();
  assert.equal(D.toggleDone(dog, 'made-up', at(2026, 10, 18)), false);
  assert.equal(dog.xp, 0);
});

/* ---------- daily tasks and the full-day bonus ---------- */

test('daily walk and water tasks give 5 XP each and toggle off again', () => {
  const dog = D.blank();
  const now = at(2026, 10, 18);
  assert.equal(D.setDailyTask(dog, 'walk', now), true);
  assert.equal(dog.xp, 5);
  D.setDailyTask(dog, 'walk', now);
  assert.equal(dog.xp, 0);
});

test('automatic daily tasks cannot be toggled by hand', () => {
  const dog = D.blank();
  assert.equal(D.setDailyTask(dog, 'potty', at(2026, 10, 18)), false);
  assert.equal(D.setDailyTask(dog, 'train', at(2026, 10, 18)), false);
});

test('full day earns the +25 bonus once and loses it when a requirement is undone', () => {
  const dog = D.blank();
  dog.pref = 'both';
  const now = at(2026, 10, 18, 12);
  const t = D.dateKey(now);
  D.setDailyTask(dog, 'walk', now);
  D.setDailyTask(dog, 'water', now);
  for (let k = 0; k < 3; k++) D.logPotty(dog, 'pee', at(2026, 10, 18, 8 + k));
  for (const it of D.dailyIds(dog, t)) D.toggleDone(dog, it.id, now);
  assert.equal(dog.bonus[t], true);
  const xpWithBonus = dog.xp;
  D.reconcileBonus(dog, now);
  assert.equal(dog.xp, xpWithBonus, 'bonus is not counted twice');
  D.toggleDone(dog, D.dailyIds(dog, t)[0].id, now);
  assert.equal(dog.bonus[t], undefined, 'bonus removed when the day is incomplete');
});

test('dayStatus reports each requirement separately', () => {
  const dog = D.blank();
  const t = key(2026, 10, 18);
  const s = D.dayStatus(dog, t);
  assert.equal(s.walk, false);
  assert.equal(s.potty, false);
  assert.equal(s.all, false);
});

test('accidents do not count toward the three-breaks requirement', () => {
  const dog = D.blank();
  const now = at(2026, 10, 18, 12);
  D.logPotty(dog, 'accident', at(2026, 10, 18, 8));
  D.logPotty(dog, 'accident', at(2026, 10, 18, 9));
  D.logPotty(dog, 'pee', at(2026, 10, 18, 10));
  D.logPotty(dog, 'poop', at(2026, 10, 18, 11));
  assert.equal(D.dayStatus(dog, D.dateKey(now)).potty, false);
  D.logPotty(dog, 'pee', at(2026, 10, 18, 11, 30));
  assert.equal(D.dayStatus(dog, D.dateKey(now)).potty, true);
});

test('dailyIds is stable for a date and respects the environment preference', () => {
  const dog = D.blank();
  dog.pref = 'indoor';
  const a = D.dailyIds(dog, '2026-10-18').map(i => i.id);
  const b = D.dailyIds(dog, '2026-10-18').map(i => i.id);
  assert.deepEqual(a, b);
  assert.equal(a.length, 3);
  for (const it of D.dailyIds(dog, '2026-10-18')) assert.ok(it.env === 'indoor' || it.env === 'both');
});

test('streak counts consecutive full days and still counts when today is not finished yet', () => {
  const dog = D.blank();
  const now = at(2026, 10, 18);
  dog.bonus = { '2026-10-17': true, '2026-10-16': true, '2026-10-14': true };
  assert.equal(D.streak(dog, now), 2, 'counts from yesterday when today is open');
  dog.bonus['2026-10-18'] = true;
  assert.equal(D.streak(dog, now), 3, 'includes today once earned');
});

/* ---------- potty and meals ---------- */

test('logPotty rejects unknown types and records valid ones', () => {
  const dog = D.blank();
  assert.equal(D.logPotty(dog, 'nope', at(2026, 10, 18)), false);
  assert.equal(D.logPotty(dog, 'pee', at(2026, 10, 18)), true);
  assert.equal(dog.potty.length, 1);
});

test('nextPotty needs two breaks, then estimates from the average gap', () => {
  const dog = D.blank();
  assert.equal(D.nextPotty(dog, at(2026, 10, 18)), null);
  dog.potty = [{ t: at(2026, 10, 18, 8).getTime(), type: 'pee' }, { t: at(2026, 10, 18, 10).getTime(), type: 'poop' }];
  const next = D.nextPotty(dog, at(2026, 10, 18, 10, 30));
  assert.equal(next.gapMin, 120);
  assert.equal(next.dueNow, false);
  assert.equal(D.nextPotty(dog, at(2026, 10, 18, 13)).dueNow, true);
});

test('nextMeal returns the next scheduled time, rolling to tomorrow after the last meal', () => {
  const morning = D.nextMeal(at(2026, 10, 18, 6));
  assert.equal(morning.getHours(), 7);
  assert.equal(morning.getDate(), 18);
  const midday = D.nextMeal(at(2026, 10, 18, 13));
  assert.equal(midday.getHours(), 18);
  const late = D.nextMeal(at(2026, 10, 18, 20));
  assert.equal(late.getHours(), 7);
  assert.equal(late.getDate(), 19);
});

test('logMeal records a meal', () => {
  const dog = D.blank();
  D.logMeal(dog, at(2026, 10, 18));
  assert.equal(dog.meals.length, 1);
});

/* ---------- timelines ---------- */

test('hourly timeline counts every event once', () => {
  const dog = D.blank();
  dog.potty = [{ t: at(2026, 10, 18, 7).getTime(), type: 'pee' }, { t: at(2026, 10, 17, 7).getTime(), type: 'poop' }];
  dog.meals = [{ t: at(2026, 10, 18, 18).getTime() }];
  const t = D.timeline(dog, 'hour', at(2026, 10, 18));
  assert.equal(t.labels.length, 24);
  assert.equal(t.values.reduce((a, b) => a + b, 0), 3);
  assert.equal(t.values[7], 2);
  assert.equal(t.values[18], 1);
});

test('daily timeline covers the last 14 days', () => {
  const dog = D.blank();
  dog.potty = [{ t: at(2026, 10, 18, 9).getTime(), type: 'pee' }];
  const t = D.timeline(dog, 'day', at(2026, 10, 18));
  assert.equal(t.labels.length, 14);
  assert.equal(t.values[13], 1);
  assert.equal(t.values.reduce((a, b) => a + b, 0), 1);
});

test('monthly timeline covers the last 12 months and ignores older events', () => {
  const dog = D.blank();
  dog.potty = [{ t: at(2026, 10, 2).getTime(), type: 'pee' }, { t: at(2024, 1, 2).getTime(), type: 'pee' }];
  const t = D.timeline(dog, 'month', at(2026, 10, 18));
  assert.equal(t.labels.length, 12);
  assert.equal(t.values[11], 1);
  assert.equal(t.values.reduce((a, b) => a + b, 0), 1);
});

test('yearly timeline runs from the earliest year to this year', () => {
  const dog = D.blank();
  dog.potty = [{ t: at(2024, 6, 1).getTime(), type: 'pee' }];
  const t = D.timeline(dog, 'year', at(2026, 10, 18));
  assert.deepEqual(t.labels, ['2024', '2025', '2026']);
  assert.equal(t.values[0], 1);
});

/* ---------- comparisons ---------- */

test('week comparison splits events into this week and last week', () => {
  const dog = D.blank();
  const now = at(2026, 10, 18);
  dog.potty = [
    { t: at(2026, 10, 17, 9).getTime(), type: 'pee' },
    { t: at(2026, 10, 16, 9).getTime(), type: 'accident' },
    { t: at(2026, 10, 9, 9).getTime(), type: 'pee' },
  ];
  dog.meals = [{ t: at(2026, 10, 15, 9).getTime() }];
  const rows = D.weekCompare(dog, now);
  const byName = Object.fromEntries(rows.map(r => [r.name, r]));
  assert.equal(byName['Potty events'].current, 2);
  assert.equal(byName['Potty events'].previous, 1);
  assert.equal(byName['Accidents'].current, 1);
  assert.equal(byName['Meals'].current, 1);
});

test('environment comparison totals match the skill list', () => {
  const dog = D.blank();
  dog.done.sit = '2026-10-18';
  const rows = D.envCompare(dog);
  assert.equal(rows.reduce((a, r) => a + r.total, 0), 55);
  const both = rows.find(r => r.env === 'both');
  assert.equal(both.total, D.ITEMS.filter(i => i.env === 'both').length);
  assert.equal(rows.find(r => r.env === 'both').mastered, 1);
});

test('pee and poop breakdown covers only the requested days', () => {
  const dog = D.blank();
  dog.potty = [
    { t: at(2026, 10, 17, 9).getTime(), type: 'pee' },
    { t: at(2026, 10, 1, 9).getTime(), type: 'poop' },
    { t: at(2026, 9, 1, 9).getTime(), type: 'pee' },
  ];
  const c = D.pottyBreakdown(dog, at(2026, 10, 18), 30);
  assert.equal(c.pee, 1);
  assert.equal(c.poop, 1);
  assert.equal(c.accident, 0);
});

/* ---------- auto planner ---------- */

test('planner returns one entry per day, at most three skills per day, within the minutes budget', () => {
  const dog = D.blank();
  const plan = D.makePlan(dog, { env: 'both', minutes: 20, days: 7 }, at(2026, 10, 18));
  assert.equal(plan.length, 7);
  for (const day of plan) {
    assert.ok(day.items.length <= 3);
    assert.ok(day.items.reduce((a, it) => a + it.min, 0) <= 20);
  }
});

test('planner skips mastered skills and follows the environment choice', () => {
  const dog = D.blank();
  dog.done.name = '2026-10-01';
  const plan = D.makePlan(dog, { env: 'outdoor', minutes: 30, days: 3 }, at(2026, 10, 18));
  const all = plan.flatMap(d => d.items.map(i => i.id));
  assert.ok(!all.includes('name'));
  for (const it of plan.flatMap(d => d.items)) assert.ok(it.env === 'outdoor' || it.env === 'both');
});

test('planner clamps unsafe inputs instead of misbehaving', () => {
  const dog = D.blank();
  const plan = D.makePlan(dog, { env: 'bogus', minutes: 99999, days: -4 }, at(2026, 10, 18));
  assert.equal(plan.length, 1);
  assert.ok(plan[0].items.length > 0);
});

test('planner dates start today and move forward one day at a time', () => {
  const plan = D.makePlan(D.blank(), { env: 'both', minutes: 20, days: 3 }, at(2026, 10, 18));
  assert.deepEqual(plan.map(p => p.date), ['2026-10-18', '2026-10-19', '2026-10-20']);
});

/* ---------- controller: actions and rendering through a stub app context ---------- */

function stubContext(initialDog) {
  const calls = { commit: 0, refresh: 0, toast: [] };
  const state = { settings: { workspace: 'dog' }, dog: initialDog };
  D.init({
    getState: () => state,
    commit: () => { calls.commit++; },
    refresh: () => { calls.refresh++; },
    toast: m => calls.toast.push(m),
    isActive: () => true,
  });
  return { state, calls };
}

test('actions that change data call commit; navigation only refreshes', () => {
  const { state, calls } = stubContext(D.blank());
  D._act('tab', 'daily');
  assert.equal(D._ui.tab, 'daily');
  assert.equal(calls.commit, 0);
  assert.equal(calls.refresh, 1);
  D._act('toggleDone', 'sit');
  assert.equal(state.dog.done.sit !== undefined, true);
  assert.equal(calls.commit, 1);
});

test('unknown tab and filter values are ignored', () => {
  stubContext(D.blank());
  D._ui.tab = 'train';
  D._act('tab', '<script>');
  assert.equal(D._ui.tab, 'train');
  D._act('env', 'bogus');
  assert.notEqual(D._ui.env, 'bogus');
});

test('deleting a record needs its list name and id, and only removes that record', () => {
  const dog = D.normalizeDog({ weights: [{ id: 'w1', d: '2026-10-01', kg: 10 }, { id: 'w2', d: '2026-10-02', kg: 11 }] });
  const { state } = stubContext(dog);
  D._act('delete', 'weights:w1');
  assert.deepEqual(state.dog.weights.map(w => w.id), ['w2']);
  D._act('delete', 'notes:w2');
  assert.equal(state.dog.weights.length, 1, 'wrong list name does nothing');
  D._act('delete', 'weights:../../etc');
  assert.equal(state.dog.weights.length, 1, 'unknown id does nothing');
});

test('reset needs a second confirmation and then clears the dog data', () => {
  const dog = D.normalizeDog({ name: 'Rex', xp: 120 });
  const { state } = stubContext(dog);
  D._act('resetDo', null);
  assert.equal(state.dog.xp, 120, 'no reset without arming');
  D._act('resetArm', null);
  D._act('resetDo', null);
  assert.equal(state.dog.xp, 0);
  assert.equal(state.dog.name, '');
});

test('the rendered page escapes a malicious dog name', () => {
  stubContext(D.normalizeDog({ name: '<img src=x onerror=alert(1)>' }));
  const html = D.view();
  assert.ok(!html.includes('<img src=x'), 'raw markup must not appear');
  assert.ok(html.includes('&lt;img src=x'));
});

test('the training view renders every skill when all environments are shown', () => {
  stubContext(D.blank());
  D._ui.tab = 'train';
  D._ui.env = 'all';
  D._ui.open = null;
  const html = D.view();
  assert.equal((html.match(/class="panel pad dog-card"/g) || []).length, 55);
});
