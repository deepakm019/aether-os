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
