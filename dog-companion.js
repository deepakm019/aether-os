/* AstralSurge OS: dog training companion.
   Pure logic first (testable in Node, see tests/unit), then a small renderer and one delegated click handler.
   All dog data lives in state.dog and is saved through the app's persist() pipeline, so it is encrypted with the rest of the vault. */
(function (root) {
  'use strict';

  var DAY = 864e5;

  // 55 skills, most important first. Fields: id, name, environment, cartoon prop, minutes, items needed, steps (separated by |).
  var ROWS = [
    ['name', 'Name recognition', 'both', 'treat', 5, 'Small soft treats; quiet room', 'Say the name once in a bright voice|Mark and treat when he looks at you|Repeat 10 times, 3 sessions a day'],
    ['look', 'Look at me (eye contact)', 'both', 'treat', 5, 'Treats; clear floor', 'Hold a treat by your eye|Say "Look" and mark when he meets your gaze|Slowly add 2 seconds of gaze'],
    ['sit', 'Sit', 'both', 'treat', 5, 'Treats', 'Lure nose up and back with a treat|Say "Sit" when his bottom touches down|Mark, treat, repeat; fade the lure'],
    ['come', 'Come (recall) indoors', 'indoor', 'ball', 5, 'Treats; long leash optional', 'Crouch, cheerful voice, say "Come"|Reward generously when he arrives|Practice from different rooms'],
    ['leave', 'Leave it', 'both', 'treat', 5, 'Low-value and high-value treats', 'Close hand on low-value treat, say "Leave it"|Reward when he backs off|Progress to uncovered treat on floor'],
    ['drop', 'Drop it', 'both', 'ball', 5, 'Two toys, one better than the other', 'Offer a trade: toy for a better treat|Say "Drop" and treat when he releases|Practice with toy in hand'],
    ['stay', 'Stay (short)', 'both', 'mat', 5, 'Treats; mat or spot', 'Ask Sit, say "Stay", open palm|Wait 2 seconds, return and reward|Add distance one step at a time'],
    ['down', 'Down', 'both', 'mat', 5, 'Treats; mat', 'Lure nose to floor, then slide forward|Say "Down" when elbows touch floor|Mark, treat, repeat'],
    ['loose_in', 'Loose-leash walking (indoor)', 'indoor', 'leash', 8, 'Leash, harness, treats', 'Walk a hallway; stop when leash tightens|Reward when slack, keep reward at your side|Add turns and distractions slowly'],
    ['wait_door', 'Wait at doors', 'indoor', 'mat', 5, 'Treats; door', 'Ask Sit, open door a crack|Close if he moves; open when he waits|Build to full opening'],
    ['settle', 'Settle on bed', 'indoor', 'mat', 10, 'Bed or mat; chew toy', 'Toss a treat onto the bed|Say "Settle" and reward calm lying|Lengthen time; add noise gradually'],
    ['crate', 'Crate comfort', 'indoor', 'crate', 10, 'Crate with soft bed; treats', 'Feed meals near the open crate|Close for seconds, reward, open|Build duration slowly'],
    ['heel', 'Heel (position)', 'outdoor', 'leash', 8, 'Leash, treats', 'Keep his shoulder at your knee|Step off and mark when in position|Add turns and pace changes'],
    ['touch', 'Touch (hand target)', 'both', 'treat', 5, 'Treats; open palm', 'Present palm; mark when nose touches it|Say "Touch" before presenting|Move hand to new places'],
    ['gentle', 'Gentle treat take', 'both', 'treat', 5, 'Flat treats', 'Hold treat in closed fist|Reward gentle sniff or lick|Open hand only when he is calm'],
    ['paws', 'Paw handling', 'both', 'treat', 5, 'Treats', 'Touch a paw briefly, then treat|Hold a second longer each time|Practice before nail trims'],
    ['ears', 'Ear handling', 'both', 'treat', 5, 'Treats; cotton ball', 'Touch ear base lightly, treat|Lift and check gently|Add cleaning slowly'],
    ['teeth', 'Teeth and mouth handling', 'both', 'treat', 5, 'Finger brush or wet gauze; treats', 'Touch lips, treat|Lift lip for one second|Add a brushing motion'],
    ['brush', 'Brushing and coat handling', 'both', 'brush', 8, 'Soft brush; treats', 'Brush one short stroke, treat|Build strokes over days|Include belly and legs'],
    ['nails', 'Nail trim acclimation', 'both', 'treat', 5, 'Clipper or file (no cutting yet); treats', 'Show the tool, treat|Touch a paw with the tool|Trim one nail only when relaxed'],
    ['bath', 'Bath acclimation', 'indoor', 'bowl', 10, 'Tub or sink; lukewarm water; towel; treats', 'Lure into empty tub|Add a little warm water, reward|Build up to a rinse'],
    ['bowl_wait', 'Wait for food', 'indoor', 'bowl', 5, 'Food bowl; treats', 'Hold bowl; wait for sit|Lower bowl when calm|Release with "Okay"'],
    ['off', 'Off (no jumping)', 'both', 'treat', 5, 'Treats', 'Turn away when paws touch you|Reward four paws down|Ask Sit for greetings'],
    ['greet', 'Polite greeting', 'both', 'treat', 5, 'Treats; a helper', 'Helper enters, dog sits|Reward sit, ignore jumps|Repeat with new people'],
    ['place', 'Go to place (mat)', 'indoor', 'mat', 5, 'Mat or bed; treats', 'Toss a treat onto the mat|Cue "Go to place" and mark when he steps on|Add duration and distance'],
    ['fetch', 'Fetch', 'outdoor', 'ball', 10, 'Ball or toy; open area', 'Toss a short distance|Encourage return; trade for a treat|Lengthen throws slowly'],
    ['recall_out', 'Recall outdoors (long line)', 'outdoor', 'leash', 10, 'Long line 5–10 m; high-value treats', 'Let the line run, call "Come"|Reward at arrival|Add distractions gradually'],
    ['leash_walk', 'Leash walk outdoors', 'outdoor', 'leash', 15, 'Leash, harness, treats', 'Start on a quiet street|Reward loose leash every few steps|Increase distance over weeks'],
    ['distract', 'Ignore distractions', 'outdoor', 'treat', 10, 'Treats; quiet park', 'Watch the distance from the distraction|Reward attention to you|Move closer slowly'],
    ['curb', 'Wait at curb', 'outdoor', 'leash', 5, 'Leash; treats', 'Stop at curb, ask Sit|Wait until you say "Okay"|Practice at every crossing'],
    ['traffic', 'Calm with traffic noise', 'outdoor', 'leash', 8, 'Distance from the road; treats', 'Stand far enough for calm|Reward focus on you|Move closer over sessions'],
    ['dogs_meet', 'Meet other dogs politely', 'outdoor', 'ball', 10, 'Calm friendly dog; leash; treats', 'Walk parallel at a distance|Reward calm sniffs|End before he gets excited'],
    ['car', 'Calm car rides', 'outdoor', 'car', 10, 'Parked car; crate or harness; treats', 'Sit in parked car with door open|Reward calm; short trips|Lengthen trips over time'],
    ['trail', 'Trail manners', 'outdoor', 'leash', 15, 'Leash; water; treats', 'Stay on trail|Check in every few minutes|Reward return to you'],
    ['recall_hike', 'Recall on a hike', 'outdoor', 'ball', 10, 'Long line; high-value treat', 'Practice on long line first|Call "Come" as he moves away|Reward generously'],
    ['potty_cue', 'Potty on cue', 'outdoor', 'mat', 10, 'Leash; treats; a cue word', 'Take outside after meals|Say "Go potty" once he sniffs|Reward immediately'],
    ['swim', 'Water introduction', 'outdoor', 'ball', 10, 'Shallow water; life vest optional; treats', 'Let him step into shallows|Reward calm|Build depth gradually'],
    ['shake', 'Shake (paw)', 'both', 'treat', 5, 'Treats', 'Hold treat in closed fist|Lift a paw and mark|Add cue "Shake"'],
    ['roll', 'Roll over', 'both', 'treat', 8, 'Treats', 'Lure nose over shoulder|Continue the roll and mark|Add cue "Roll"'],
    ['spin', 'Spin', 'both', 'treat', 5, 'Treats', 'Lure in a circle|Mark at full turn|Fade the lure'],
    ['bow', 'Bow', 'both', 'treat', 5, 'Treats', 'Lure head down and front legs forward|Mark when down|Add a cue'],
    ['hide_seek', 'Hide and seek', 'both', 'ball', 10, 'Toy; treats', 'Hide a toy in the room|Say "Find it"|Hide in harder spots'],
    ['scent', 'Scent search (indoor)', 'indoor', 'treat', 10, 'Small treats in a cup', 'Hide a treat in a cup|Say "Search"|Hide in more places'],
    ['tug', 'Tug (impulse control)', 'both', 'ball', 8, 'Tug toy', 'Start tug; say "Drop" when cued|Resume play after release|Keep rules consistent'],
    ['find_it', 'Find it', 'both', 'treat', 8, 'Treats', 'Toss a treat|Say "Find it"|Increase distance'],
    ['target', 'Target stick', 'both', 'treat', 8, 'Target stick or pen; treats', 'Touch nose to stick, mark|Move stick and reward|Add distance'],
    ['back_up', 'Back up', 'both', 'treat', 5, 'Treats', 'Lure a step back|Mark and reward|Add cue "Back"'],
    ['jumps', 'Low jumps', 'outdoor', 'ball', 8, 'Low bar or pole; treats', 'Walk over the pole|Lower jump gradually|Reward the finish'],
    ['balance', 'Balance on wobble board', 'indoor', 'mat', 8, 'Wobble board or cushion', 'Stand on board with treats|Hold four paws|Add gentle movement'],
    ['stairs', 'Stairs', 'indoor', 'leash', 8, 'Stairs; leash; treats', 'Reward a step onto first stair|Build steps|Practice up and down'],
    ['crowd', 'Calm in crowds', 'outdoor', 'leash', 10, 'Leash; quiet area; treats', 'Watch crowd from a distance|Reward calm|Move closer slowly'],
    ['noise', 'Noise desensitization', 'indoor', 'ball', 10, 'Recorded sounds at low volume; treats', 'Play sound quietly|Reward calm|Raise volume slowly'],
    ['doorbell', 'Doorbell response', 'indoor', 'mat', 10, 'Doorbell audio or helper; treats', 'Ring at low volume; cue to mat|Reward on mat|Build to realistic doorbell'],
    ['quiet', 'Quiet on cue', 'both', 'treat', 5, 'Treats', 'Let him bark once; say "Quiet" and treat when he stops|Build quiet time|Use the cue sparingly'],
    ['platform', 'Four feet on platform', 'indoor', 'mat', 8, 'Sturdy box or platform; treats', 'Lure front paws up|Mark when two paws are on|Build to four paws']
  ];

  var ITEMS = ROWS.map(function (r, i) {
    return { i: i + 1, id: r[0], n: r[1], env: r[2], prop: r[3], min: r[4], req: r[5], steps: r[6].split('|'), xp: Math.max(10, 30 - Math.floor(i / 3)) };
  });
  var IDX = {};
  ITEMS.forEach(function (it) { IDX[it.id] = it; });

  var DAILY_TASKS = [
    ['walk', 'Walk of 20 minutes or more'],
    ['water', 'Fresh water checked'],
    ['potty', 'Potty breaks logged (3 or more, logged automatically)'],
    ['train', "Complete today's 3 training items (automatic)"]
  ];
  var MEAL_HOURS = [7, 12, 18];
  var TABS = [
    ['train', 'Train'], ['daily', 'Daily'], ['care', 'Potty and meals'], ['health', 'Health'],
    ['timeline', 'Timeline'], ['calendar', 'Calendar'], ['compare', 'Compare'], ['planner', 'Auto planner'], ['profile', 'Profile']
  ];
  var VAX_REFERENCE = [
    ['6–8 weeks', 'First distemper combo (DHPP) dose'],
    ['10–12 weeks', 'DHPP booster; deworming and parasite check'],
    ['12–16 weeks', 'Rabies (regional rules apply); last DHPP'],
    ['Yearly or per vet', 'Booster schedule, weight and dental check'],
    ['Ongoing', 'Flea, tick and heartworm prevention (ask your vet)']
  ];
  var LIMITS = { potty: 2000, meals: 2000, weights: 1000, vax: 300, notes: 500, noteLen: 500, nameLen: 40, vaxLen: 80 };
  var PET_TYPES = ['pee', 'poop', 'accident'];
  var FILTERS = ['both', 'indoor', 'outdoor'];

  /* ---------- small helpers ---------- */
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function dateKey(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function addDays(key, n) {
    var p = key.split('-').map(Number);
    return dateKey(new Date(p[0], p[1] - 1, p[2] + n));
  }
  function isKey(s) { return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(s); }
  function plainObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
  function uid(p) { return p + Math.random().toString(36).slice(2, 10); }
  function clampNum(v, min, max, fb) {
    var n = Number(v);
    if (!isFinite(n)) return fb;
    return Math.min(max, Math.max(min, n));
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function cleanText(v, max) {
    return String(v == null ? '' : v).replace(/[\u0000-\u001f\u007f]/g, ' ').trim().slice(0, max);
  }
  function envOk(itemEnv, filter) {
    return filter === 'all' || filter === 'both' || itemEnv === 'both' || itemEnv === filter;
  }
  function keysBetween(endKey, n) {
    var out = [];
    for (var i = n - 1; i >= 0; i--) out.push(addDays(endKey, -i));
    return out;
  }
  function sortByTime(list) { return list.sort(function (a, b) { return a.t - b.t; }); }

  /* ---------- state shape ---------- */
  function blank() {
    return { name: '', xp: 0, pref: 'both', done: {}, daily: {}, bonus: {}, potty: [], meals: [], weights: [], vax: [], notes: [] };
  }

  // Validates untrusted (imported or stored) data. Never throws; drops anything malformed.
  function normalizeDog(raw) {
    var src = plainObj(raw) ? raw : {};
    var out = blank();
    out.name = cleanText(src.name, LIMITS.nameLen);
    out.xp = Math.round(clampNum(src.xp, 0, 1e7, 0));
    out.pref = FILTERS.indexOf(src.pref) >= 0 ? src.pref : 'both';
    if (plainObj(src.done)) {
      Object.keys(src.done).forEach(function (id) {
        if (IDX[id] && isKey(src.done[id])) out.done[id] = src.done[id];
      });
    }
    if (plainObj(src.daily)) {
      Object.keys(src.daily).forEach(function (d) {
        if (!isKey(d) || !plainObj(src.daily[d])) return;
        out.daily[d] = { walk: src.daily[d].walk === true, water: src.daily[d].water === true };
      });
    }
    if (plainObj(src.bonus)) {
      Object.keys(src.bonus).forEach(function (d) { if (isKey(d) && src.bonus[d] === true) out.bonus[d] = true; });
    }
    var list = function (v) { return Array.isArray(v) ? v : []; };
    out.potty = sortByTime(list(src.potty).filter(function (p) {
      return plainObj(p) && isFinite(Number(p.t)) && Number(p.t) > 0 && PET_TYPES.indexOf(p.type) >= 0;
    }).map(function (p) {
      return { id: typeof p.id === 'string' && p.id.length <= 40 ? p.id : uid('p'), t: Number(p.t), type: p.type };
    })).slice(-LIMITS.potty);
    out.meals = sortByTime(list(src.meals).filter(function (m) {
      return plainObj(m) && isFinite(Number(m.t)) && Number(m.t) > 0;
    }).map(function (m) { return { t: Number(m.t) }; })).slice(-LIMITS.meals);
    out.weights = list(src.weights).filter(function (w) {
      return plainObj(w) && isKey(w.d) && Number(w.kg) > 0 && Number(w.kg) < 500;
    }).map(function (w) {
      return { id: typeof w.id === 'string' && w.id.length <= 40 ? w.id : uid('w'), d: w.d, kg: Math.round(Number(w.kg) * 10) / 10 };
    }).slice(-LIMITS.weights);
    out.vax = list(src.vax).filter(function (v) {
      return plainObj(v) && isKey(v.d) && cleanText(v.name, LIMITS.vaxLen).length > 0;
    }).map(function (v) {
      return { id: typeof v.id === 'string' && v.id.length <= 40 ? v.id : uid('v'), d: v.d, name: cleanText(v.name, LIMITS.vaxLen) };
    }).slice(-LIMITS.vax);
    out.notes = list(src.notes).filter(function (n) {
      return plainObj(n) && isKey(n.d) && cleanText(n.text, LIMITS.noteLen).length > 0;
    }).map(function (n) {
      return { id: typeof n.id === 'string' && n.id.length <= 40 ? n.id : uid('n'), d: n.d, text: cleanText(n.text, LIMITS.noteLen) };
    }).slice(-LIMITS.notes);
    return out;
  }

  /* ---------- daily logic ---------- */
  function dailyIds(dog, dateStr) {
    var pool = ITEMS.filter(function (it) { return envOk(it.env, dog.pref); });
    var idx = Math.floor(new Date(dateStr + 'T12:00:00').getTime() / DAY);
    var out = [];
    for (var k = 0; k < 3; k++) {
      out.push(pool[(((idx * 3 + k) % pool.length) + pool.length) % pool.length]);
    }
    return out;
  }
  function countPotty(dog, key) {
    return dog.potty.filter(function (p) { return p.type !== 'accident' && dateKey(new Date(p.t)) === key; }).length;
  }
  function dayStatus(dog, key) {
    var d = dog.daily[key] || { walk: false, water: false };
    var potty = countPotty(dog, key) >= 3;
    var train = dailyIds(dog, key).every(function (it) { return dog.done[it.id] === key; });
    return { walk: d.walk, water: d.water, potty: potty, train: train, all: d.walk && d.water && potty && train };
  }
  // Keeps the full-day bonus (+25 XP, once per day) in step with the day's status.
  function reconcileBonus(dog, now) {
    var key = dateKey(now);
    var all = dayStatus(dog, key).all;
    if (all && !dog.bonus[key]) { dog.bonus[key] = true; dog.xp += 25; }
    else if (!all && dog.bonus[key]) { delete dog.bonus[key]; dog.xp = Math.max(0, dog.xp - 25); }
  }
  function toggleDone(dog, id, now) {
    var it = IDX[id];
    if (!it) return false;
    if (dog.done[id]) { delete dog.done[id]; dog.xp = Math.max(0, dog.xp - it.xp); }
    else { dog.done[id] = dateKey(now); dog.xp += it.xp; }
    reconcileBonus(dog, now);
    return true;
  }
  function setDailyTask(dog, key, now) {
    if (key !== 'walk' && key !== 'water') return false;
    var t = dateKey(now);
    var day = dog.daily[t] || (dog.daily[t] = { walk: false, water: false });
    day[key] = !day[key];
    dog.xp = Math.max(0, dog.xp + (day[key] ? 5 : -5));
    reconcileBonus(dog, now);
    return true;
  }
  function streak(dog, now) {
    var key = dateKey(now);
    var cur = dog.bonus[key] ? key : addDays(key, -1);
    var n = 0;
    while (dog.bonus[cur] && n < 3650) { n++; cur = addDays(cur, -1); }
    return n;
  }

  /* ---------- potty, meals, timelines ---------- */
  function logPotty(dog, type, now) {
    if (PET_TYPES.indexOf(type) < 0) return false;
    dog.potty.push({ id: uid('p'), t: now.getTime(), type: type });
    if (dog.potty.length > LIMITS.potty) dog.potty.splice(0, dog.potty.length - LIMITS.potty);
    reconcileBonus(dog, now);
    return true;
  }
  function logMeal(dog, now) {
    dog.meals.push({ t: now.getTime() });
    if (dog.meals.length > LIMITS.meals) dog.meals.splice(0, dog.meals.length - LIMITS.meals);
    return true;
  }
  // Estimate of the next toilet break from the average gap across recent breaks (accidents excluded).
  function nextPotty(dog, now) {
    var p = dog.potty.filter(function (x) { return x.type !== 'accident'; }).slice(-20);
    if (p.length < 2) return null;
    var gap = (p[p.length - 1].t - p[0].t) / (p.length - 1);
    var due = p[p.length - 1].t + gap;
    return { gapMin: Math.round(gap / 60000), due: due, dueNow: due <= now.getTime() };
  }
  function nextMeal(now) {
    for (var i = 0; i < MEAL_HOURS.length; i++) {
      var d = new Date(now);
      d.setHours(MEAL_HOURS[i], 0, 0, 0);
      if (d > now) return d;
    }
    var t = new Date(now);
    t.setDate(t.getDate() + 1);
    t.setHours(MEAL_HOURS[0], 0, 0, 0);
    return t;
  }
  function timeline(dog, range, now) {
    var events = dog.potty.map(function (p) { return p.t; }).concat(dog.meals.map(function (m) { return m.t; }));
    var labels = [], values = [], note = '';
    var today = dateKey(now);
    if (range === 'hour') {
      for (var h = 0; h < 24; h++) { labels.push(pad(h)); values.push(0); }
      events.forEach(function (t) { values[new Date(t).getHours()]++; });
      note = 'Typical hour of day across all logs. Total events: ' + events.length + '.';
    } else if (range === 'day') {
      var keys = keysBetween(today, 14);
      keys.forEach(function (k) { labels.push(k.slice(5)); values.push(0); });
      events.forEach(function (t) { var i = keys.indexOf(dateKey(new Date(t))); if (i >= 0) values[i]++; });
      note = 'Last 14 days.';
    } else if (range === 'month') {
      for (var m = 11; m >= 0; m--) {
        var d = new Date(now.getFullYear(), now.getMonth() - m, 1);
        labels.push(d.toLocaleDateString(undefined, { month: 'short' }));
        values.push(0);
      }
      events.forEach(function (t) {
        var d = new Date(t);
        var diff = (now.getFullYear() - d.getFullYear()) * 12 + (now.getMonth() - d.getMonth());
        if (diff >= 0 && diff < 12) values[11 - diff]++;
      });
      note = 'Last 12 months.';
    } else {
      var thisYear = now.getFullYear();
      var first = events.length ? Math.min(thisYear, Math.min.apply(null, events.map(function (t) { return new Date(t).getFullYear(); }))) : thisYear;
      for (var y = first; y <= thisYear; y++) { labels.push(String(y)); values.push(0); }
      events.forEach(function (t) { values[new Date(t).getFullYear() - first]++; });
      note = 'Yearly totals.';
    }
    return { labels: labels, values: values, note: note };
  }

  /* ---------- comparisons ---------- */
  function weekCompare(dog, now) {
    var today = dateKey(now);
    var thisWeek = keysBetween(today, 7);
    var lastWeek = keysBetween(addDays(today, -7), 7);
    function metrics(keys) {
      var set = {};
      keys.forEach(function (k) { set[k] = true; });
      var pot = dog.potty.filter(function (p) { return set[dateKey(new Date(p.t))]; });
      return [
        ['Potty events', pot.length],
        ['Accidents', pot.filter(function (p) { return p.type === 'accident'; }).length],
        ['Meals', dog.meals.filter(function (m) { return set[dateKey(new Date(m.t))]; }).length],
        ['Skills mastered', Object.keys(dog.done).filter(function (id) { return set[dog.done[id]]; }).length]
      ];
    }
    var a = metrics(thisWeek), b = metrics(lastWeek);
    return a.map(function (row, i) { return { name: row[0], current: row[1], previous: b[i][1] }; });
  }
  function envCompare(dog) {
    return ['indoor', 'outdoor', 'both'].map(function (env) {
      var total = ITEMS.filter(function (it) { return it.env === env; }).length;
      var mastered = ITEMS.filter(function (it) { return it.env === env && dog.done[it.id]; }).length;
      return { env: env, total: total, mastered: mastered, pct: total ? Math.round(mastered / total * 100) : 0 };
    });
  }
  function pottyBreakdown(dog, now, days) {
    var set = {};
    keysBetween(dateKey(now), days).forEach(function (k) { set[k] = true; });
    var c = { pee: 0, poop: 0, accident: 0 };
    dog.potty.forEach(function (p) { if (set[dateKey(new Date(p.t))]) c[p.type]++; });
    return c;
  }

  /* ---------- auto planner ---------- */
  function makePlan(dog, opts, now) {
    var filter = FILTERS.indexOf(opts.env) >= 0 ? opts.env : 'both';
    var minutes = clampNum(opts.minutes, 5, 240, 20);
    var days = clampNum(opts.days, 1, 60, 7);
    var pool = ITEMS.filter(function (it) { return !dog.done[it.id] && envOk(it.env, filter); });
    if (!pool.length) pool = ITEMS.filter(function (it) { return envOk(it.env, filter); });
    var today = dateKey(now), out = [], cursor = 0;
    for (var d = 0; d < days; d++) {
      var budget = minutes, picked = [], guard = 0;
      while (guard++ < pool.length * 2 && picked.length < 3) {
        var it = pool[cursor % pool.length];
        cursor++;
        if (picked.indexOf(it) < 0 && it.min <= budget) { picked.push(it); budget -= it.min; }
        if (budget < 5) break;
      }
      out.push({ date: addDays(today, d), items: picked });
    }
    return out;
  }

  /* ---------- rendering ---------- */
  var ART_PROPS = {
    treat: '<circle cx="28" cy="62" r="9" fill="var(--accent)"/><circle cx="28" cy="62" r="4" fill="var(--panel)"/>',
    ball: '<circle cx="26" cy="94" r="10" fill="var(--accent)"/><path d="M18 94h16" stroke="var(--panel)" stroke-width="2"/>',
    leash: '<path d="M26 40 Q6 70 30 104" stroke="var(--accent2)" stroke-width="4" fill="none" stroke-linecap="round"/>',
    mat: '<rect x="8" y="98" width="44" height="8" rx="3" fill="var(--accent2)"/>',
    bowl: '<path d="M12 84h38q-2 14-19 14T12 84z" fill="var(--accent2)"/>',
    brush: '<rect x="10" y="78" width="34" height="10" rx="3" fill="var(--accent2)"/><path d="M16 88v8M25 88v8M34 88v8" stroke="var(--accent2)" stroke-width="3"/>',
    crate: '<rect x="6" y="60" width="44" height="44" fill="none" stroke="var(--accent2)" stroke-width="3"/><path d="M18 60v44M30 60v44M42 60v44" stroke="var(--accent2)" stroke-width="2"/>',
    car: '<rect x="4" y="88" width="46" height="18" rx="5" fill="var(--accent2)"/><circle cx="16" cy="108" r="5" fill="var(--fg)"/><circle cx="40" cy="108" r="5" fill="var(--fg)"/>'
  };
  function art(prop, label) {
    return '<svg class="dog-art" viewBox="0 0 160 120" role="img" aria-label="Cartoon dog with ' + esc(label) + '">' +
      '<ellipse cx="82" cy="114" rx="58" ry="4" fill="var(--line)"/>' +
      '<rect x="74" y="78" width="9" height="30" rx="4" fill="#c9a27a"/>' +
      '<rect x="92" y="78" width="9" height="30" rx="4" fill="#c9a27a"/>' +
      '<ellipse cx="88" cy="72" rx="30" ry="20" fill="#c9a27a"/>' +
      '<path d="M112 70 q16 -18 10 -30" stroke="#c9a27a" stroke-width="7" fill="none" stroke-linecap="round"/>' +
      '<circle cx="120" cy="46" r="17" fill="#c9a27a"/>' +
      '<ellipse cx="108" cy="32" rx="6" ry="11" fill="#8a6442" transform="rotate(-20 108 32)"/>' +
      '<ellipse cx="132" cy="32" rx="6" ry="11" fill="#8a6442" transform="rotate(20 132 32)"/>' +
      '<circle cx="126" cy="44" r="2.6" fill="var(--fg)"/>' +
      '<circle cx="134" cy="52" r="3.2" fill="var(--fg)"/>' +
      '<path d="M124 57 q5 4 10 -1" stroke="var(--fg)" stroke-width="2" fill="none"/>' +
      (ART_PROPS[prop] || ART_PROPS.treat) + '</svg>';
  }
  function barChart(labels, values) {
    var W = 640, H = 240, p = { l: 40, r: 12, t: 16, b: 40 };
    var max = Math.max.apply(null, [1].concat(values));
    var bw = (W - p.l - p.r) / labels.length;
    var s = '';
    for (var k = 0; k <= 4; k++) {
      var y = H - p.b - (H - p.t - p.b) * k / 4;
      s += '<line x1="' + p.l + '" y1="' + y + '" x2="' + (W - p.r) + '" y2="' + y + '" stroke="var(--line)" stroke-dasharray="3 4"/>' +
        '<text x="' + (p.l - 6) + '" y="' + (y + 4) + '" text-anchor="end" font-size="11" fill="var(--muted2)">' + Math.round(max * k / 4) + '</text>';
    }
    values.forEach(function (v, i) {
      var h = (H - p.t - p.b) * v / max, x = p.l + i * bw + bw * 0.15, yy = H - p.b - h;
      s += '<rect x="' + x.toFixed(1) + '" y="' + yy.toFixed(1) + '" width="' + (bw * 0.7).toFixed(1) + '" height="' + h.toFixed(1) + '" rx="4" fill="var(--accent2)"><title>' + esc(labels[i]) + ': ' + v + '</title></rect>';
      if (labels.length <= 14 || i % 2 === 0) {
        s += '<text x="' + (x + bw * 0.35).toFixed(1) + '" y="' + (H - p.b + 16) + '" text-anchor="middle" font-size="10" fill="var(--muted2)">' + esc(labels[i]) + '</text>';
      }
    });
    return '<svg class="dog-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Activity chart">' + s + '</svg>';
  }
  function pairChart(labels, a, b, na, nb) {
    var W = 640, H = 220, p = { l: 40, r: 12, t: 24, b: 36 };
    var max = Math.max.apply(null, [1].concat(a, b));
    var bw = (W - p.l - p.r) / labels.length;
    var s = '';
    labels.forEach(function (l, i) {
      var x = p.l + i * bw + bw * 0.18, w = bw * 0.3;
      var ha = (H - p.t - p.b) * a[i] / max, hb = (H - p.t - p.b) * b[i] / max;
      s += '<rect x="' + x.toFixed(1) + '" y="' + (H - p.b - ha).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + ha.toFixed(1) + '" rx="3" fill="var(--accent2)"><title>' + esc(na) + ': ' + a[i] + '</title></rect>';
      s += '<rect x="' + (x + w + 4).toFixed(1) + '" y="' + (H - p.b - hb).toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + hb.toFixed(1) + '" rx="3" fill="var(--accent)"><title>' + esc(nb) + ': ' + b[i] + '</title></rect>';
      s += '<text x="' + (p.l + i * bw + bw / 2).toFixed(1) + '" y="' + (H - p.b + 16) + '" text-anchor="middle" font-size="11" fill="var(--muted2)">' + esc(l) + '</text>';
    });
    s += '<text x="' + p.l + '" y="14" font-size="11" fill="var(--accent2)">■ ' + esc(na) + '</text>' +
      '<text x="' + (p.l + 120) + '" y="14" font-size="11" fill="var(--accent)">■ ' + esc(nb) + '</text>';
    return '<svg class="dog-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Comparison chart">' + s + '</svg>';
  }
  function envChip(env) {
    if (env === 'indoor') return '<span class="chip accent">Indoor</span>';
    if (env === 'outdoor') return '<span class="chip warn">Outdoor</span>';
    return '<span class="chip">Indoor and outdoor</span>';
  }
  function metric(label, value) {
    return '<div class="panel metric"><div class="label">' + esc(label) + '</div><div class="value">' + esc(value) + '</div></div>';
  }
  function fmtDay(key) {
    var p = key.split('-').map(Number);
    return new Date(p[0], p[1] - 1, p[2]).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  }
  function fmtStamp(t) {
    return new Date(t).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  function tabBar(active) {
    return '<div class="tabs" role="tablist" aria-label="Dog training sections">' + TABS.map(function (t) {
      return '<button class="tab' + (t[0] === active ? ' active' : '') + '" data-dog-act="tab" data-dog-val="' + t[0] + '"' +
        (t[0] === active ? ' aria-current="page"' : '') + '>' + esc(t[1]) + '</button>';
    }).join('') + '</div>';
  }
  function seg(list, active, act) {
    return '<div class="tabs" role="group">' + list.map(function (x) {
      return '<button class="tab' + (x[0] === active ? ' active' : '') + '" data-dog-act="' + act + '" data-dog-val="' + x[0] + '">' + esc(x[1]) + '</button>';
    }).join('') + '</div>';
  }

  function viewTrain(dog) {
    var list = ITEMS.filter(function (it) { return envOk(it.env, ui.env); });
    var cards = list.map(function (it) {
      return '<button class="panel pad dog-card" data-dog-act="open" data-dog-val="' + it.id + '">' +
        art(it.prop, it.n) +
        '<span class="row" style="justify-content:space-between"><span class="chip">#' + it.i + '</span>' +
        (dog.done[it.id] ? '<span class="chip good">Mastered</span>' : '') + '</span>' +
        '<span class="dog-block" style="font-family:var(--serif,inherit);font-weight:800">' + esc(it.n) + '</span>' +
        '<span class="row">' + envChip(it.env) + '<span class="chip">' + it.min + ' min</span><span class="chip">' + it.xp + ' XP</span></span>' +
        '</button>';
    }).join('');
    var detail = '';
    var d = IDX[ui.open];
    if (d) {
      detail = '<section class="panel pad section"><div class="grid grid-2"><div>' + art(d.prop, d.n) + '</div><div style="min-width:0">' +
        '<div class="row" style="margin-bottom:6px">' + envChip(d.env) + '<span class="chip">Step ' + d.i + ' of ' + ITEMS.length + '</span><span class="chip">' + d.min + ' min</span></div>' +
        '<h2>' + esc(d.n) + '</h2><p><strong>You need:</strong> ' + esc(d.req) + '</p>' +
        '<h3 style="margin-top:12px">Step by step</h3><ol class="dog-steps">' + d.steps.map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('') + '</ol>' +
        '<div class="actions"><button class="btn' + (dog.done[d.id] ? '' : ' primary') + '" data-dog-act="toggleDone" data-dog-val="' + d.id + '">' +
        (dog.done[d.id] ? 'Undo mastered' : 'Mark mastered (+' + d.xp + ' XP)') + '</button>' +
        '<button class="btn" data-dog-act="closeItem">Close</button></div></div></div></section>';
    }
    return '<section class="section"><div class="row" style="justify-content:space-between;margin-bottom:10px">' +
      seg([['all', 'All'], ['indoor', 'Indoor'], ['outdoor', 'Outdoor']], ui.env, 'env') +
      '<span class="muted-line">' + Object.keys(dog.done).length + ' of ' + ITEMS.length + ' mastered</span></div>' +
      '<p class="muted-line">Ordered from most important to fun extras. Start at the top and move down once each skill is steady.</p>' +
      '<div class="grid grid-3 section">' + cards + '</div>' + detail + '</section>';
  }

  function viewDaily(dog, now) {
    var key = dateKey(now), s = dayStatus(dog, key);
    var rows = [
      ['walk', 'Walk of 20 minutes or more', s.walk],
      ['water', 'Fresh water checked', s.water]
    ].map(function (r) {
      return '<div class="row"><div class="row-main"><div class="row-title">' + esc(r[1]) + '</div><div class="row-meta">+5 XP</div></div>' +
        '<button class="btn mini' + (r[2] ? ' primary' : '') + '" data-dog-act="task" data-dog-val="' + r[0] + '">' + (r[2] ? 'Done' : 'Mark done') + '</button></div>';
    }).join('');
    var auto = '<div class="row"><div class="row-main"><div class="row-title">Potty breaks logged (3 or more)</div><div class="row-meta">' + countPotty(dog, key) + ' logged today</div></div><span class="chip ' + (s.potty ? 'good' : '') + '">' + (s.potty ? 'Done' : 'Automatic') + '</span></div>';
    var trainRow = '<div class="row"><div class="row-main"><div class="row-title">Complete the 3 training items</div><div class="row-meta">' + dailyIds(dog, key).filter(function (it) { return dog.done[it.id] === key; }).length + ' of 3 done today</div></div><span class="chip ' + (s.train ? 'good' : '') + '">' + (s.train ? 'Done' : 'Automatic') + '</span></div>';
    var items = dailyIds(dog, key).map(function (it) {
      var done = dog.done[it.id] === key;
      return '<div class="row"><div class="row-main"><div class="row-title">' + esc(it.n) + '</div><div class="row-meta">' + it.min + ' min · ' + it.xp + ' XP</div></div>' +
        '<button class="btn mini' + (done ? '' : ' primary') + '" data-dog-act="toggleDone" data-dog-val="' + it.id + '">' + (done ? 'Undo' : 'Mark mastered') + '</button></div>';
    }).join('');
    return '<section class="section grid grid-2"><div class="panel"><div class="panel-header"><h2>Daily care</h2><small>' + esc(fmtDay(key)) + '</small></div><div class="list">' + rows + auto + trainRow + '</div></div>' +
      '<div class="panel"><div class="panel-header"><h2>Today’s 3 training items</h2><small>rotates each day</small></div><div class="list">' + items + '</div></div>' +
      '<div class="panel pad" style="grid-column:1/-1"><div class="row"><span class="chip accent">Full-day streak: ' + streak(dog, now) + ' days</span>' +
      '<span class="chip">' + (s.all ? 'Full-day bonus earned today (+25 XP)' : 'Full-day bonus needs all four items') + '</span></div></div></section>';
  }

  function viewCare(dog, now) {
    var next = nextPotty(dog, now);
    var nextText = next ? (next.dueNow ? 'Next break is due now (average gap ' + next.gapMin + ' min).' : 'Next break around ' + new Date(next.due).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }) + ' (average gap ' + next.gapMin + ' min).') : 'Log a few breaks to estimate the next one.';
    var recentPotty = dog.potty.slice(-8).reverse().map(function (p) {
      return '<div class="row"><div class="row-main"><div class="row-title">' + esc(p.type) + '</div><div class="row-meta">' + esc(fmtStamp(p.t)) + '</div></div></div>';
    }).join('') || '<div class="empty"><strong>Nothing logged yet</strong>Tap Pee, Poop or Accident above.</div>';
    var recentMeals = dog.meals.slice(-8).reverse().map(function (m) {
      return '<div class="row"><div class="row-main"><div class="row-title">Meal</div><div class="row-meta">' + esc(fmtStamp(m.t)) + '</div></div></div>';
    }).join('') || '<div class="empty"><strong>No meals logged yet</strong></div>';
    return '<section class="section grid grid-2">' +
      '<div class="panel pad"><h2>Potty log</h2><div class="actions" style="margin-top:0">' +
      '<button class="btn primary" data-dog-act="potty" data-dog-val="pee">Pee</button>' +
      '<button class="btn primary" data-dog-act="potty" data-dog-val="poop">Poop</button>' +
      '<button class="btn" data-dog-act="potty" data-dog-val="accident">Accident</button></div>' +
      '<p class="muted-line" style="margin-top:12px">' + esc(nextText) + '</p><div class="list" style="margin-top:12px">' + recentPotty + '</div></div>' +
      '<div class="panel pad"><h2>Meals</h2><p class="muted-line">Scheduled at 07:00, 12:00 and 18:00. Adjust these to your vet’s advice.</p>' +
      '<div class="actions" style="margin-top:0"><button class="btn primary" data-dog-act="meal">Log a meal now</button></div>' +
      '<p class="muted-line" style="margin-top:12px">Next scheduled meal at ' + esc(new Date(nextMeal(now)).toLocaleString(undefined, { weekday: 'short', hour: '2-digit', minute: '2-digit' })) + '.</p>' +
      '<div class="list" style="margin-top:12px">' + recentMeals + '</div></div></section>';
  }

  function viewHealth(dog) {
    var weights = dog.weights.slice().reverse().map(function (w) {
      return '<div class="row"><div class="row-main"><div class="row-title">' + w.kg + ' kg</div><div class="row-meta">' + esc(fmtDay(w.d)) + '</div></div>' +
        '<button class="btn mini" data-dog-act="delete" data-dog-val="weights:' + esc(w.id) + '">Remove</button></div>';
    }).join('') || '<div class="empty"><strong>No weights yet</strong></div>';
    var vax = dog.vax.slice().sort(function (a, b) { return a.d < b.d ? 1 : -1; }).map(function (v) {
      return '<div class="row"><div class="row-main"><div class="row-title">' + esc(v.name) + '</div><div class="row-meta">' + esc(fmtDay(v.d)) + '</div></div>' +
        '<button class="btn mini" data-dog-act="delete" data-dog-val="vax:' + esc(v.id) + '">Remove</button></div>';
    }).join('') || '<div class="empty"><strong>No vaccines or visits yet</strong></div>';
    var notes = dog.notes.slice().reverse().map(function (n) {
      return '<div class="row"><div class="row-main"><div class="row-title">' + esc(n.text) + '</div><div class="row-meta">' + esc(fmtDay(n.d)) + '</div></div>' +
        '<button class="btn mini" data-dog-act="delete" data-dog-val="notes:' + esc(n.id) + '">Remove</button></div>';
    }).join('') || '<div class="empty"><strong>No notes yet</strong></div>';
    var today = dateKey(new Date());
    return '<section class="section"><div class="note-box">This page keeps records only. It is not veterinary advice. Confirm every vaccine and medicine with your vet.</div>' +
      '<div class="grid grid-2 section">' +
      '<div class="panel"><div class="panel-header"><h2>Weight</h2></div><div class="pad">' +
      '<div class="row"><div class="field"><label for="dogWDate">Date</label><input type="date" id="dogWDate" value="' + today + '"></div>' +
      '<div class="field"><label for="dogWKg">Kg</label><input type="number" step="0.1" min="0" id="dogWKg" placeholder="kg"></div>' +
      '<button class="btn primary" data-dog-act="addWeight">Add weight</button></div></div><div class="list">' + weights + '</div></div>' +
      '<div class="panel"><div class="panel-header"><h2>Vaccines and vet visits</h2></div><div class="pad">' +
      '<div class="row"><div class="field"><label for="dogVDate">Date</label><input type="date" id="dogVDate" value="' + today + '"></div>' +
      '<div class="field" style="flex:1;min-width:140px"><label for="dogVName">Name</label><input type="text" id="dogVName" maxlength="80" placeholder="e.g. DHPP booster"></div>' +
      '<button class="btn primary" data-dog-act="addVax">Add</button></div></div><div class="list">' + vax + '</div></div>' +
      '<div class="panel" style="grid-column:1/-1"><div class="panel-header"><h2>Health notes</h2></div><div class="pad">' +
      '<div class="row"><div class="field"><label for="dogNDate">Date</label><input type="date" id="dogNDate" value="' + today + '"></div>' +
      '<div class="field" style="flex:1;min-width:160px"><label for="dogNText">Note</label><input type="text" id="dogNText" maxlength="500" placeholder="Symptom, appetite, energy, medicine given"></div>' +
      '<button class="btn primary" data-dog-act="addNote">Add note</button></div></div><div class="list">' + notes + '</div></div>' +
      '</div><div class="panel section"><div class="panel-header"><h2>Reference puppy schedule</h2><small>typical timing only</small></div><div class="table-wrap"><table class="table"><thead><tr><th>Age</th><th>Usual item</th></tr></thead><tbody>' +
      VAX_REFERENCE.map(function (r) { return '<tr><td>' + esc(r[0]) + '</td><td>' + esc(r[1]) + '</td></tr>'; }).join('') +
      '</tbody></table></div></div></section>';
  }

  function viewTimeline(dog, now) {
    var t = timeline(dog, ui.range, now);
    return '<section class="section panel pad"><div class="row" style="justify-content:space-between;margin-bottom:8px"><h2>Activity timeline</h2>' +
      seg([['hour', 'Hourly'], ['day', 'Daily'], ['month', 'Monthly'], ['year', 'Yearly']], ui.range, 'range') + '</div>' +
      '<p class="muted-line">Potty events and meals.</p>' + barChart(t.labels, t.values) +
      '<p class="muted-line" style="margin-top:8px">' + esc(t.note) + '</p></section>';
  }

  function viewCalendar(dog, now) {
    var m = ui.month;
    var first = new Date(m.getFullYear(), m.getMonth(), 1).getDay();
    var days = new Date(m.getFullYear(), m.getMonth() + 1, 0).getDate();
    var cells = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(function (d) { return '<div class="muted-line" style="text-align:center">' + d + '</div>'; }).join('');
    for (var b = 0; b < first; b++) cells += '<span></span>';
    for (var d = 1; d <= days; d++) {
      var key = dateKey(new Date(m.getFullYear(), m.getMonth(), d));
      var dots = [];
      if (dog.potty.some(function (p) { return dateKey(new Date(p.t)) === key; })) dots.push('var(--accent2)');
      if (dog.vax.some(function (v) { return v.d === key; })) dots.push('var(--accent)');
      if (dog.weights.some(function (w) { return w.d === key; })) dots.push('var(--amber,#e0a94a)');
      cells += '<button class="dog-day' + (ui.day === key ? ' sel' : '') + '" data-dog-act="calDay" data-dog-val="' + key + '">' + d +
        '<span class="dog-dots">' + dots.map(function (c) { return '<i style="background:' + c + '"></i>'; }).join('') + '</span></button>';
    }
    var detail = '<p class="muted-line">Tap a day to see its entries.</p>';
    if (ui.day) {
      var lines = [];
      dog.vax.filter(function (v) { return v.d === ui.day; }).forEach(function (v) { lines.push('Vaccine or visit: ' + esc(v.name)); });
      dog.weights.filter(function (w) { return w.d === ui.day; }).forEach(function (w) { lines.push('Weight: ' + w.kg + ' kg'); });
      dog.notes.filter(function (n) { return n.d === ui.day; }).forEach(function (n) { lines.push('Note: ' + esc(n.text)); });
      dog.potty.filter(function (p) { return dateKey(new Date(p.t)) === ui.day; }).forEach(function (p) {
        lines.push(esc(new Date(p.t).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })) + ' potty: ' + esc(p.type));
      });
      detail = '<h3>' + esc(fmtDay(ui.day)) + '</h3>' + (lines.length ? lines.map(function (l) { return '<div class="row-meta" style="padding:4px 0">' + l + '</div>'; }).join('') : '<p class="muted-line">Nothing logged.</p>');
    }
    return '<section class="section panel pad"><div class="row" style="justify-content:space-between;margin-bottom:10px">' +
      '<button class="btn" data-dog-act="calNav" data-dog-val="-1">Previous</button><h2 style="margin:0">' + esc(m.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })) + '</h2>' +
      '<button class="btn" data-dog-act="calNav" data-dog-val="1">Next</button></div>' +
      '<div class="dog-cal">' + cells + '</div>' +
      '<div class="row muted-line" style="margin-top:10px"><span><i class="dog-key" style="background:var(--accent2)"></i>potty</span><span><i class="dog-key" style="background:var(--accent)"></i>vaccine or visit</span><span><i class="dog-key" style="background:var(--amber,#e0a94a)"></i>weight</span></div>' +
      '<div class="section">' + detail + '</div></section>';
  }

  function viewCompare(dog, now) {
    var head, body, chart;
    if (ui.cmp === 'week') {
      var rows = weekCompare(dog, now);
      head = '<tr><th>Measure</th><th>This week</th><th>Last week</th><th>Change</th></tr>';
      body = rows.map(function (r) {
        var diff = r.current - r.previous;
        return '<tr><td>' + esc(r.name) + '</td><td>' + r.current + '</td><td>' + r.previous + '</td><td>' + (diff > 0 ? '+' : '') + diff + '</td></tr>';
      }).join('');
      chart = pairChart(rows.map(function (r) { return r.name; }), rows.map(function (r) { return r.current; }), rows.map(function (r) { return r.previous; }), 'This week', 'Last week');
    } else if (ui.cmp === 'env') {
      var env = envCompare(dog);
      head = '<tr><th>Type</th><th>Mastered</th><th>Total</th><th>Progress</th></tr>';
      body = env.map(function (r) { return '<tr><td>' + esc(r.env) + '</td><td>' + r.mastered + '</td><td>' + r.total + '</td><td>' + r.pct + '%</td></tr>'; }).join('');
      chart = pairChart(env.map(function (r) { return r.env; }), env.map(function (r) { return r.mastered; }), env.map(function (r) { return r.total; }), 'Mastered', 'Total');
    } else {
      var c = pottyBreakdown(dog, now, 30);
      head = '<tr><th>Type</th><th>Last 30 days</th></tr>';
      body = '<tr><td>Pee</td><td>' + c.pee + '</td></tr><tr><td>Poop</td><td>' + c.poop + '</td></tr><tr><td>Accidents</td><td>' + c.accident + '</td></tr>';
      chart = pairChart(['Pee', 'Poop', 'Accident'], [c.pee, c.poop, c.accident], [0, 0, 0], 'Count', 'Unused');
    }
    return '<section class="section panel pad"><div class="row" style="margin-bottom:10px">' +
      seg([['week', 'This week vs last week'], ['env', 'Indoor vs outdoor'], ['potty', 'Pee vs poop']], ui.cmp, 'cmp') + '</div>' +
      '<div class="table-wrap"><table class="table"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>' +
      '<div style="margin-top:12px">' + chart + '</div></section>';
  }

  function viewPlanner(dog, now) {
    var plan = ui.plan ? ui.plan.map(function (p) {
      return '<div class="card" style="margin-bottom:10px"><h3>' + esc(fmtDay(p.date)) + '</h3>' +
        (p.items.length ? '<ul class="dog-steps">' + p.items.map(function (it) { return '<li><strong>' + esc(it.n) + '</strong> ' + envChip(it.env) + ' <span class="muted-line">' + it.min + ' min</span></li>'; }).join('') + '</ul>' : '<p class="muted-line">Rest day: walk and potty breaks.</p>') +
        '</div>';
    }).join('') : '<p class="muted-line">Choose options and generate a plan.</p>';
    return '<section class="section panel pad"><p class="muted-line">Builds a plan from skills you have not mastered yet. Each day fits your time budget.</p>' +
      '<div class="grid grid-3 section">' +
      '<div class="field"><label for="dogPlEnv">Environment</label><select id="dogPlEnv">' +
      [['both', 'Both'], ['indoor', 'Indoor'], ['outdoor', 'Outdoor']].map(function (o) { return '<option value="' + o[0] + '"' + (ui.plEnv === o[0] ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="field"><label for="dogPlMin">Minutes per day</label><select id="dogPlMin">' +
      [10, 20, 30].map(function (m) { return '<option value="' + m + '"' + (ui.plMin === m ? ' selected' : '') + '>' + m + '</option>'; }).join('') +
      '</select></div>' +
      '<div class="field"><label for="dogPlDays">Days</label><select id="dogPlDays">' +
      [7, 14, 28].map(function (n) { return '<option value="' + n + '"' + (ui.plDays === n ? ' selected' : '') + '>' + n + '</option>'; }).join('') +
      '</select></div></div>' +
      '<div class="actions"><button class="btn primary" data-dog-act="planGen">Generate plan</button></div>' +
      '<div class="section">' + plan + '</div></section>';
  }

  function viewProfile(dog) {
    return '<section class="section grid grid-2">' +
      '<div class="panel pad"><h2>Dog profile</h2><div class="row"><div class="field" style="flex:1;min-width:0"><label for="dogName">Name</label>' +
      '<input type="text" id="dogName" maxlength="40" value="' + esc(dog.name) + '" placeholder="Dog’s name"></div>' +
      '<button class="btn primary" data-dog-act="saveName">Save</button></div>' +
      '<p class="muted-line" style="margin-top:10px">Dog data is saved in your encrypted vault and included in backups.</p></div>' +
      '<div class="panel pad"><h2>Reset dog data</h2><p class="muted-line">Clears logs, XP and skills for the dog companion. Your other app data is not changed.</p>' +
      (ui.armReset
        ? '<div class="danger-note">This erases the dog companion data on this device.</div><div class="actions"><button class="btn" data-dog-act="resetDo">Yes, erase dog data</button><button class="btn" data-dog-act="resetCancel">Cancel</button></div>'
        : '<div class="actions"><button class="btn" data-dog-act="resetArm">Reset dog data</button></div>') +
      '</div></section>';
  }

  /* ---------- view and controller ---------- */
  var ui = {
    tab: 'train', env: 'all', open: null, range: 'hour', cmp: 'week',
    month: null, day: null, plan: null, plEnv: 'both', plMin: 20, plDays: 7, armReset: false
  };
  ui.month = new Date(new Date().getFullYear(), new Date().getMonth(), 1);

  var ctx = null;
  function dog() {
    var s = ctx.getState();
    if (!s.dog || typeof s.dog !== 'object') s.dog = normalizeDog(null);
    return s.dog;
  }

  function view() {
    var d = dog(), now = new Date();
    var lvl = Math.floor(d.xp / 100) + 1;
    var body;
    switch (ui.tab) {
      case 'daily': body = viewDaily(d, now); break;
      case 'care': body = viewCare(d, now); break;
      case 'health': body = viewHealth(d); break;
      case 'timeline': body = viewTimeline(d, now); break;
      case 'calendar': body = viewCalendar(d, now); break;
      case 'compare': body = viewCompare(d, now); break;
      case 'planner': body = viewPlanner(d, now); break;
      case 'profile': body = viewProfile(d); break;
      default: body = viewTrain(d);
    }
    return '<div class="page"><div class="eyebrow">Dog training</div><div class="h1">' + (d.name ? esc(d.name) + '’s training' : 'Training companion') + '</div>' +
      '<div class="lead">Train every day, track care, and earn XP. Everything here is saved in your encrypted vault.</div>' +
      '<section class="section grid grid-3">' + metric('Level', lvl) + metric('XP', d.xp) + metric('Full-day streak', streak(d, now) + ' days') + '</section>' +
      '<div class="bar section" style="margin-top:10px"><i style="width:' + (d.xp % 100) + '%"></i></div>' +
      '<section class="section">' + tabBar(ui.tab) + '</section>' + body + '</div>';
  }

  function act(name, val) {
    var d = dog(), now = new Date();
    var changed = false, invalid = null;
    switch (name) {
      case 'tab': if (TABS.some(function (t) { return t[0] === val; })) ui.tab = val; break;
      case 'env': if (FILTERS.indexOf(val) >= 0 || val === 'all') ui.env = val; break;
      case 'open': ui.open = IDX[val] ? val : null; break;
      case 'closeItem': ui.open = null; break;
      case 'toggleDone': changed = toggleDone(d, val, now); break;
      case 'task': changed = setDailyTask(d, val, now); break;
      case 'potty': changed = logPotty(d, val, now); break;
      case 'meal': changed = logMeal(d, now); break;
      case 'addWeight': {
        var wd = document.getElementById('dogWDate').value || dateKey(now);
        var kg = parseFloat(document.getElementById('dogWKg').value);
        if (!isKey(wd) || !(kg > 0 && kg < 500)) { invalid = 'Enter a date and a weight between 0 and 500 kg'; break; }
        d.weights.push({ id: uid('w'), d: wd, kg: Math.round(kg * 10) / 10 });
        d.weights = d.weights.slice(-LIMITS.weights);
        changed = true; break;
      }
      case 'addVax': {
        var vd = document.getElementById('dogVDate').value || dateKey(now);
        var vn = cleanText(document.getElementById('dogVName').value, LIMITS.vaxLen);
        if (!isKey(vd) || !vn) { invalid = 'Add a name for the vaccine or visit'; break; }
        d.vax.push({ id: uid('v'), d: vd, name: vn });
        d.vax = d.vax.slice(-LIMITS.vax);
        document.getElementById('dogVName').value = '';
        changed = true; break;
      }
      case 'addNote': {
        var nd = document.getElementById('dogNDate').value || dateKey(now);
        var nt = cleanText(document.getElementById('dogNText').value, LIMITS.noteLen);
        if (!isKey(nd) || !nt) { invalid = 'Add a note'; break; }
        d.notes.push({ id: uid('n'), d: nd, text: nt });
        d.notes = d.notes.slice(-LIMITS.notes);
        document.getElementById('dogNText').value = '';
        changed = true; break;
      }
      case 'delete': {
        var sep = String(val).indexOf(':');
        var list = String(val).slice(0, sep), id = String(val).slice(sep + 1);
        if (['weights', 'vax', 'notes'].indexOf(list) >= 0 && sep > 0) {
          var before = d[list].length;
          d[list] = d[list].filter(function (r) { return r.id !== id; });
          changed = d[list].length !== before;
        }
        break;
      }
      case 'range': if (['hour', 'day', 'month', 'year'].indexOf(val) >= 0) ui.range = val; break;
      case 'cmp': if (['week', 'env', 'potty'].indexOf(val) >= 0) ui.cmp = val; break;
      case 'calNav': ui.month = new Date(ui.month.getFullYear(), ui.month.getMonth() + clampNum(val, -24, 24, 0), 1); break;
      case 'calDay': if (isKey(val)) ui.day = val; break;
      case 'planGen': {
        ui.plEnv = document.getElementById('dogPlEnv').value;
        ui.plMin = Number(document.getElementById('dogPlMin').value) || 20;
        ui.plDays = Number(document.getElementById('dogPlDays').value) || 7;
        ui.plan = makePlan(d, { env: ui.plEnv, minutes: ui.plMin, days: ui.plDays }, now);
        break;
      }
      case 'saveName': {
        d.name = cleanText(document.getElementById('dogName').value, LIMITS.nameLen);
        changed = true; break;
      }
      case 'resetArm': ui.armReset = true; break;
      case 'resetCancel': ui.armReset = false; break;
      case 'resetDo': {
        if (ui.armReset) { ctx.getState().dog = normalizeDog(null); ui.armReset = false; ui.open = null; changed = true; }
        break;
      }
      default: break;
    }
    if (invalid && ctx.toast) ctx.toast(invalid);
    if (changed) { reconcileBonus(d, now); ctx.commit(); }
    else ctx.refresh();
  }

  function onClick(e) {
    if (!ctx || !ctx.isActive()) return;
    var el = e.target && e.target.closest ? e.target.closest('[data-dog-act]') : null;
    if (!el) return;
    act(el.getAttribute('data-dog-act'), el.getAttribute('data-dog-val'));
  }

  function init(context) {
    ctx = context;
    ctx.getState().dog = normalizeDog(ctx.getState().dog);
    if (!init.bound && typeof document !== 'undefined') {
      document.addEventListener('click', onClick);
      init.bound = true;
    }
  }

  var api = {
    ITEMS: ITEMS, IDX: IDX, DAILY_TASKS: DAILY_TASKS, TABS: TABS, VAX_REFERENCE: VAX_REFERENCE, LIMITS: LIMITS,
    normalizeDog: normalizeDog, blank: blank, dailyIds: dailyIds, dayStatus: dayStatus, reconcileBonus: reconcileBonus,
    toggleDone: toggleDone, setDailyTask: setDailyTask, streak: streak, logPotty: logPotty, logMeal: logMeal,
    nextPotty: nextPotty, nextMeal: nextMeal, timeline: timeline, weekCompare: weekCompare, envCompare: envCompare,
    pottyBreakdown: pottyBreakdown, makePlan: makePlan, dateKey: dateKey, addDays: addDays, esc: esc, art: art,
    view: view, init: init, _ui: ui, _act: act
  };

  var host = typeof window !== 'undefined' ? window : root;
  host.DogCompanion = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
