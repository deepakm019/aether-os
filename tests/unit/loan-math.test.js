// Unit tests for the loan maths. Run with: npm run test:unit
// The module lives inline in index.html (<script id="loan-math">), so the tests read it from there.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function loadLoanMath() {
  const html = fs.readFileSync(path.join(__dirname, '..', '..', 'index.html'), 'utf8');
  const m = html.match(/<script id="loan-math">([\s\S]*?)<\/script>/);
  if (!m) throw new Error('loan-math script block not found in index.html');
  const win = {};
  new Function('window', 'globalThis', m[1])(win, win);
  return win.LoanMath;
}
const L = loadLoanMath();
const near = (a, b, tol = 0.01) => assert.ok(Math.abs(a - b) <= tol, `expected ${b}, got ${a}`);

test('EMI matches the standard formula', () => {
  // 20,00,000 at 9% for 180 months: 20285.33 a month (checked independently).
  near(L.emi(2000000, 9, 180), 20285.3317, 0.001);
});

test('zero-rate loans split the principal evenly', () => {
  assert.equal(L.emi(120000, 0, 12), 10000);
  assert.equal(L.schedule(120000, 0, 10000).months, 12);
});

test('schedule clears the loan and interest equals payments minus principal', () => {
  const P = 500000, rate = 8.5, months = 60;
  const payment = L.emi(P, rate, months);
  const s = L.schedule(P, rate, payment);
  assert.equal(s.months, months);
  assert.ok(s.rows[s.rows.length - 1].balance < 0.01);
  const paid = s.rows.reduce((a, r) => a + r.payment, 0);
  near(s.totalInterest, paid - P, 0.01);
});

test('tenure from EMI round-trips the original tenure', () => {
  for (const n of [12, 60, 180, 360]) {
    const e = L.emi(1000000, 7.25, n);
    assert.equal(L.tenureFromEmi(1000000, 7.25, e), n, `tenure ${n}`);
  }
});

test('an EMI that does not cover interest never clears the loan', () => {
  assert.equal(L.tenureFromEmi(100000, 12, 500), Infinity);
  const s = L.schedule(100000, 12, 500);
  assert.equal(s.neverRepays, true);
  assert.equal(s.rows.length, 0);
});

test('yearly groups add up to the schedule totals', () => {
  const s = L.schedule(800000, 9, L.emi(800000, 9, 150));
  const years = L.yearly(s.rows);
  assert.equal(years.length, Math.ceil(150 / 12));
  const interest = years.reduce((a, y) => a + y.interest, 0);
  near(interest, s.totalInterest, 0.01);
  assert.ok(years[years.length - 1].balance < 0.01);
});

test('validateLoan accepts a good loan and reports each bad field', () => {
  const good = { name: 'Home', principal: 1000000, rate: 8, remainingMonths: 120, emi: null };
  assert.deepEqual(L.validateLoan(good), []);
  assert.ok(L.validateLoan({ ...good, name: '  ' }).length > 0);
  assert.ok(L.validateLoan({ ...good, principal: 0 }).length > 0);
  assert.ok(L.validateLoan({ ...good, rate: 75 }).length > 0);
  assert.ok(L.validateLoan({ ...good, remainingMonths: 12.5 }).length > 0);
  assert.ok(L.validateLoan({ ...good, remainingMonths: 601 }).length > 0);
  const trap = L.validateLoan({ ...good, principal: 100000, rate: 12, emi: 500 });
  assert.match(trap.join(' '), /never end/);
});

test('normalizeLoan clamps and defaults bad stored values', () => {
  const n = L.normalizeLoan({ id: 'x', name: '  Car  ', type: 'Spaceship', principal: '5000.456', rate: 999,
    rateType: 'Weird', remainingMonths: -4, emi: 'abc', asOf: 'yesterday' });
  assert.equal(n.name, 'Car');
  assert.equal(n.type, 'Other');
  assert.equal(n.principal, 5000.46);
  assert.equal(n.rate, L.MAX_RATE);
  assert.equal(n.rateType, 'Fixed');
  assert.equal(n.remainingMonths, 1);
  assert.equal(n.emi, null);
  assert.equal(n.asOf, null);
});

test('summarize uses the entered EMI and flags when it differs from the calculated one', () => {
  const base = { principal: 1000000, rate: 9, remainingMonths: 120, emi: null };
  const calc = L.summarize(base);
  near(calc.emi, L.emi(1000000, 9, 120), 0.001);
  assert.equal(calc.emiDiffers, false);
  const higher = L.summarize({ ...base, emi: calc.emi * 1.5 });
  assert.equal(higher.emiDiffers, true);
  assert.ok(higher.months < 120, 'a higher EMI should finish sooner');
  assert.ok(higher.totalInterest < calc.totalInterest);
});

// ---- Phase 2: penalties, prepayment simulator, settings ----
const base = { principal: 2000000, rate: 9, remainingMonths: 180, emi: null,
  penaltyType: 'None', penaltyValue: 0, penaltyBasis: 'Prepaid', lockInEnd: null, freePrepayPct: 0 };
const withPenalty = (o) => ({ ...base, ...o });

test('no penalty is charged when the loan has none', () => {
  const p = L.penaltyFor(base, 500000, 2000000, 0, 18, true);
  assert.equal(p.total, 0);
  assert.equal(p.chargeable, 500000);
});

test('percentage penalty applies to the prepaid amount, with tax on top', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2 });
  const p = L.penaltyFor(loan, 500000, 2000000, 0, 18, true);
  assert.equal(p.penalty, 10000);
  assert.equal(p.tax, 1800);
  assert.equal(p.total, 11800);
});

test('outstanding-basis penalty uses the whole balance', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2, penaltyBasis: 'Outstanding' });
  assert.equal(L.penaltyFor(loan, 500000, 2000000, 0, 0, true).penalty, 40000);
});

test('flat penalty is a fixed amount', () => {
  const loan = withPenalty({ penaltyType: 'Flat', penaltyValue: 5000 });
  assert.equal(L.penaltyFor(loan, 300000, 2000000, 0, 0, true).penalty, 5000);
});

test('the yearly free allowance is used before any penalty', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2, freePrepayPct: 20 });
  // 20% of 20,00,000 is 4,00,000 free; 1,00,000 of it already used this year, so 3,00,000 is free.
  const p = L.penaltyFor(loan, 500000, 2000000, 100000, 0, true);
  assert.equal(p.free, 300000);
  assert.equal(p.chargeable, 200000);
  assert.equal(p.penalty, 4000);
});

test('no penalty once the lock-in has ended', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2, lockInEnd: '2027-01-01' });
  assert.equal(L.penaltyActive(loan, '2026-06-01'), true);
  assert.equal(L.penaltyActive(loan, '2027-01-01'), false);
  assert.equal(L.penaltyFor(loan, 500000, 2000000, 0, 0, false).penalty, 0);
});

test('addMonthsKey keeps the day and clamps to month end', () => {
  assert.equal(L.addMonthsKey('2026-10-24', 3), '2027-01-24');
  assert.equal(L.addMonthsKey('2026-01-31', 1), '2026-02-28');
});

test('prepaying with the EMI kept finishes sooner and saves interest', () => {
  const sim = L.prepaySimulate(withPenalty({}), { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  assert.ok(sim.shorten.interestSaved > 0);
  assert.ok(sim.shorten.months < 180);
  assert.equal(sim.shorten.emi, sim.emi);
  // Reduce keeps the tenure and lowers the EMI instead.
  assert.ok(sim.reduce.emi < sim.emi);
  assert.equal(sim.reduce.months, 180);
  assert.ok(sim.reduce.emiSaved > 0);
});

test('net saving subtracts the penalty and the growth you give up', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2 });
  const plain = L.prepaySimulate(loan, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  assert.equal(plain.penalty.total, 10000);
  assert.equal(plain.growthForgone, 0);
  assert.equal(plain.shorten.net, round(plain.shorten.interestSaved - 10000));
  const withGrowth = L.prepaySimulate(loan, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: 7, todayKey: '2026-10-24' });
  const expectedGrowth = 500000 * (Math.pow(1 + 0.07 / 12, 180) - 1);
  near(withGrowth.growthForgone, expectedGrowth, 0.01);
  near(withGrowth.shorten.net, withGrowth.shorten.interestSaved - 10000 - expectedGrowth, 0.02);
});

test('closing the loan now saves all the remaining interest', () => {
  const loan = withPenalty({});
  const sim = L.prepaySimulate(loan, { month: 0, amount: null, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  assert.equal(sim.full, true);
  assert.ok(Math.abs(sim.payNow - 2000000) < 0.01);
  near(sim.shorten.interestSaved, sim.contInterest, 0.01);
});

test('closing later uses the balance at that month, not the original principal', () => {
  const loan = withPenalty({});
  const sim = L.prepaySimulate(loan, { month: 36, amount: null, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  assert.ok(sim.balance < 2000000 && sim.balance > 1500000, `balance ${sim.balance}`);
  assert.equal(sim.onDate, '2029-10-24');
});

test('break-even counts the months of interest needed to recover the penalty', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2 });
  const sim = L.prepaySimulate(loan, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  // Interest avoided per month at the start is 500000 * 9% / 12 = 3750; 10000 / 3750 rounds up to 3 months.
  assert.equal(sim.breakEvenMonths, 3);
});

test('tax on the penalty is included in cash needed', () => {
  const loan = withPenalty({ penaltyType: 'Percent', penaltyValue: 2 });
  const sim = L.prepaySimulate(loan, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 18, savingsRate: null, todayKey: '2026-10-24' });
  assert.equal(sim.payNow, 511800);
});

test('simulator reports why when there is nothing to prepay', () => {
  const sim = L.prepaySimulate(withPenalty({ emi: 100, principal: 100000, rate: 12 }), { month: 0, amount: 1000, todayKey: '2026-10-24' });
  assert.match(sim.invalid, /never clears/);
});

test('settings default to neutral values and clamp bad input', () => {
  const d = L.normalizeLoanSettings({});
  assert.deepEqual(d, { penaltyTaxRate: 0, defaultMode: 'Shorten', savingsRate: null, logTransaction: false, logDecision: true,
    returnTaxPct: 0, stockConservative: null, stockBase: null, stockOptimistic: null, highRateThreshold: null,
    emergencyMonths: null, liquidSavings: null, monthlyExpenses: null });
  const c = L.normalizeLoanSettings({ penaltyTaxRate: 900, defaultMode: 'Nope', savingsRate: 80, logDecision: false });
  assert.equal(c.penaltyTaxRate, 50);
  assert.equal(c.defaultMode, 'Shorten');
  assert.equal(c.savingsRate, 30);
  assert.equal(c.logDecision, false);
});

test('validateLoan checks penalty and allowance ranges', () => {
  const good = { name: 'X', principal: 100000, rate: 8, remainingMonths: 60, emi: null };
  assert.deepEqual(L.validateLoan({ ...good, penaltyType: 'Percent', penaltyValue: 2 }), []);
  assert.ok(L.validateLoan({ ...good, penaltyType: 'Percent', penaltyValue: 25 }).length > 0);
  assert.ok(L.validateLoan({ ...good, penaltyType: 'Flat', penaltyValue: -1 }).length > 0);
  assert.ok(L.validateLoan({ ...good, freePrepayPct: 150 }).length > 0);
});

test('normalizeLoan keeps penalty terms and clears penalty values when there is no penalty', () => {
  const n = L.normalizeLoan({ name: 'A', penaltyType: 'Percent', penaltyValue: 3, lockInEnd: '2027-06-30', freePrepayPct: 20, status: 'Closed', closedOn: '2026-10-01' });
  assert.equal(n.penaltyValue, 3);
  assert.equal(n.lockInEnd, '2027-06-30');
  assert.equal(n.freePrepayPct, 20);
  assert.equal(n.status, 'Closed');
  assert.equal(n.closedOn, '2026-10-01');
  const none = L.normalizeLoan({ name: 'B', penaltyType: 'None', penaltyValue: 9 });
  assert.equal(none.penaltyValue, 0);
  assert.equal(L.normalizeLoan({ name: 'C' }).status, 'Active');
});

function round(v) { return Math.round(v * 100) / 100; }

// ---- Phase 3: comparison with other uses of the cash, and guidance ----
test('compareOptions ranks prepay against savings and each stock case, as annual rates', () => {
  const opts = L.compareOptions({ amount: 500000, months: 120, prepayGain: 400000, savingsRate: 7,
    stock: { conservative: 4, base: 10, optimistic: 14 }, returnTaxPct: 0 });
  const keys = opts.map(o => o.key);
  assert.deepEqual(keys, ['prepay', 'savings', 'stock-conservative', 'stock-base', 'stock-optimistic']);
  const savings = opts.find(o => o.key === 'savings');
  // Monthly compounding at 7% a year is an effective 7.23% a year.
  near(savings.annual, (Math.pow(1 + 0.07 / 12, 12) - 1) * 100, 0.001);
  const base = opts.find(o => o.key === 'stock-base');
  assert.equal(base.guaranteed, false);
  assert.equal(opts.find(o => o.key === 'prepay').guaranteed, true);
});

test('compareOptions leaves out what the user has not set', () => {
  const opts = L.compareOptions({ amount: 500000, months: 60, prepayGain: 1000, savingsRate: null, stock: {} });
  assert.deepEqual(opts.map(o => o.key), ['prepay']);
});

test('tax on returns lowers savings and stock gains but not the prepay saving', () => {
  const tax0 = L.compareOptions({ amount: 100000, months: 60, prepayGain: 20000, savingsRate: 8, returnTaxPct: 0 });
  const tax20 = L.compareOptions({ amount: 100000, months: 60, prepayGain: 20000, savingsRate: 8, returnTaxPct: 20 });
  assert.equal(tax20.find(o => o.key === 'prepay').annual, tax0.find(o => o.key === 'prepay').annual);
  assert.ok(tax20.find(o => o.key === 'savings').annual < tax0.find(o => o.key === 'savings').annual);
});

test('a loan costing more than savings is kept, and the advice says to invest instead', () => {
  const loan = { type: 'Personal', rate: 12, rateType: 'Fixed', lockInEnd: null };
  const opts = L.compareOptions({ amount: 200000, months: 60, prepayGain: 40000, savingsRate: 7, stock: {} });
  const a = L.adviseLoan(loan, { options: opts, rateThreshold: null, emergencyMonths: null, liquidMonths: null, penaltyNow: 0, prepayGain: 40000 });
  assert.equal(a.headline.tone, 'consider');
  assert.match(a.headline.text, /Keep the loan/);
});

test('a loan that beats savings is prepaid, and the advice says why', () => {
  const loan = { type: 'Personal', rate: 14, rateType: 'Fixed', lockInEnd: null };
  const opts = L.compareOptions({ amount: 200000, months: 60, prepayGain: 90000, savingsRate: 6, stock: {} });
  const a = L.adviseLoan(loan, { options: opts, rateThreshold: null, emergencyMonths: null, liquidMonths: null, penaltyNow: 0, prepayGain: 90000 });
  assert.equal(a.headline.text, 'Prepaying beats the alternatives');
});

test('an emergency fund below the target comes first, whatever the loan', () => {
  const loan = { type: 'Personal', rate: 18, rateType: 'Fixed', lockInEnd: null };
  const opts = L.compareOptions({ amount: 200000, months: 60, prepayGain: 90000, savingsRate: 6, stock: {} });
  const a = L.adviseLoan(loan, { options: opts, rateThreshold: null, emergencyMonths: 6, liquidMonths: 2.5, penaltyNow: 0, prepayGain: 90000 });
  assert.equal(a.headline.tone, 'hold');
  assert.match(a.headline.text, /emergency fund first \(2\.5 of 6 months/);
});

test('credit card debt is cleared first', () => {
  const loan = { type: 'Credit card', rate: 36, rateType: 'Fixed', lockInEnd: null };
  const a = L.adviseLoan(loan, { options: [], rateThreshold: null, emergencyMonths: null, liquidMonths: null, penaltyNow: 0, prepayGain: 0 });
  assert.equal(a.headline.text, 'Clear this first');
  assert.ok(a.points.some(p => /Card debt/.test(p.text)));
});

test('a rate at or above the threshold is paid down first', () => {
  const loan = { type: 'Personal', rate: 15, rateType: 'Fixed', lockInEnd: null };
  const a = L.adviseLoan(loan, { options: [], rateThreshold: 14, emergencyMonths: null, liquidMonths: null, penaltyNow: 0, prepayGain: 0 });
  assert.equal(a.headline.text, 'Pay this down first');
});

test('a penalty that ends later is flagged with the date', () => {
  const loan = { type: 'Home', rate: 8.5, rateType: 'Floating', lockInEnd: '2027-06-30' };
  const a = L.adviseLoan(loan, { options: [], rateThreshold: null, emergencyMonths: null, liquidMonths: null, penaltyNow: 10000, prepayGain: -2000 });
  assert.ok(a.points.some(p => /2027-06-30/.test(p.text) && p.tone === 'hold'));
});

test('stock disclaimer appears whenever a stock option is shown', () => {
  const loan = { type: 'Home', rate: 8, rateType: 'Floating', lockInEnd: null };
  const opts = L.compareOptions({ amount: 100000, months: 60, prepayGain: 5000, savingsRate: null, stock: { base: 10 } });
  const a = L.adviseLoan(loan, { options: opts, rateThreshold: null, emergencyMonths: null, liquidMonths: null, penaltyNow: 0, prepayGain: 5000 });
  assert.ok(a.points.some(p => /not guaranteed/.test(p.text)));
});

test('settings reject out-of-range returns and keep empty values empty', () => {
  const n = L.normalizeLoanSettings({ stockBase: 500, stockConservative: '', returnTaxPct: 90, highRateThreshold: 'x' });
  assert.equal(n.stockBase, 60);
  assert.equal(n.stockConservative, null);
  assert.equal(n.returnTaxPct, 50);
  assert.equal(n.highRateThreshold, null);
});

test('prepaying the whole balance earns about the loan rate, not the interest-to-cash ratio', () => {
  // 24 lakh at 8.5% over 180 months: closing now stops the EMIs, so the true return is the loan rate.
  const loan = { principal: 2400000, rate: 8.5, remainingMonths: 180, emi: null, penaltyType: 'None',
    penaltyValue: 0, penaltyBasis: 'Prepaid', lockInEnd: null, freePrepayPct: 0 };
  const sim = L.prepaySimulate(loan, { month: 0, amount: null, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  const expected = (Math.pow(1 + 0.085 / 12, 12) - 1) * 100;
  near(sim.shorten.annualRate, expected, 0.05);
  near(sim.reduce.annualRate, expected, 0.05);
});

test('a partial prepayment earns about the loan rate too', () => {
  const loan = { principal: 2400000, rate: 8.5, remainingMonths: 180, emi: null, penaltyType: 'None',
    penaltyValue: 0, penaltyBasis: 'Prepaid', lockInEnd: null, freePrepayPct: 0 };
  const sim = L.prepaySimulate(loan, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  const expected = (Math.pow(1 + 0.085 / 12, 12) - 1) * 100;
  near(sim.shorten.annualRate, expected, 0.05);
});

test('a penalty lowers the true return of prepaying', () => {
  const loan = { principal: 2400000, rate: 8.5, remainingMonths: 180, emi: null, penaltyType: 'Percent',
    penaltyValue: 3, penaltyBasis: 'Prepaid', lockInEnd: null, freePrepayPct: 0 };
  const plain = L.prepaySimulate({ ...loan, penaltyType: 'None' }, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  const pen = L.prepaySimulate(loan, { month: 0, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  assert.ok(pen.shorten.annualRate < plain.shorten.annualRate);
});

test('the headline ignores the optimistic stock case but still notes it', () => {
  const loan = { type: 'Personal', rate: 9, rateType: 'Fixed', lockInEnd: null };
  const opts = L.compareOptions({ amount: 200000, months: 60, prepayGain: 90000, savingsRate: 4,
    stock: { base: 5, optimistic: 20 } });
  const prepay = opts.find(o => o.key === 'prepay');
  const a = L.adviseLoan(loan, { options: opts, rateThreshold: null, emergencyMonths: null, liquidMonths: null, penaltyNow: 0, prepayGain: 90000 });
  assert.ok(prepay.annual > 5, 'prepay should beat the base case in this setup');
  assert.equal(a.headline.text, 'Prepaying beats the alternatives');
  assert.ok(a.points.some(p => /optimistic stock case/.test(p.text)));
});

test('simulator balance paths start at the loan and end at zero after a prepayment', () => {
  const loan = { principal: 2400000, rate: 8.5, remainingMonths: 180, emi: null, penaltyType: 'None',
    penaltyValue: 0, penaltyBasis: 'Prepaid', lockInEnd: null, freePrepayPct: 0 };
  const sim = L.prepaySimulate(loan, { month: 12, amount: 500000, usedThisYear: 0, taxRatePct: 0, savingsRate: null, todayKey: '2026-10-24' });
  assert.equal(sim.series.keep[0], 2400000);
  assert.equal(sim.series.keep.length, sim.series.shorten.length);
  // After the prepayment the shortened path is below the kept path at every later month.
  assert.ok(sim.series.shorten[13] < sim.series.keep[13]);
  assert.ok(sim.series.shorten[sim.series.shorten.length - 1] < 1);
  // The kept path reaches zero at the end of the original tenure.
  assert.ok(sim.series.keep[180] < 1);
});
