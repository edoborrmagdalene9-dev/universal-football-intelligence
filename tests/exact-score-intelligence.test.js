const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function boot() {
  const elements = new Map();
  const store = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      id, value: '', innerHTML: '', textContent: '', className: '',
      handlers: {}, addEventListener(type, fn) { this.handlers[type] = fn; },
      click() { this.handlers.click?.(); }
    });
    return elements.get(id);
  };
  get('esiHome').value = 'Home';
  get('esiAway').value = 'Away';
  get('esiLambdaHome').value = '1.45';
  get('esiLambdaAway').value = '1.20';
  get('esiTopK').value = '5';
  const context = {
    document: { getElementById: get },
    localStorage: {
      getItem(k) { return store.get(k) ?? '[]'; },
      setItem(k, v) { store.set(k, v); }
    },
    URL: { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} },
    Blob: class Blob { constructor(parts) { this.parts = parts; } },
    confirm: () => true,
    Date, Math, Number, String, JSON, Array, Object, Set,
    console
  };
  vm.runInNewContext(fs.readFileSync('exact-score-intelligence.js', 'utf8'), context);
  context.window = context;\n  return { get, store, context };
}

test('scoreline grid renders normalized 1X2 probabilities and scorelines', () => {
  const { get } = boot();
  get('esiCalculate').click();
  const html = get('esiSummary').innerHTML;
  assert.match(html, /Home win/);
  assert.match(html, /Draw/);
  assert.match(html, /Away win/);
  const firstThree = [...html.matchAll(/<b>([0-9]+\.[0-9]+)%<\/b>/g)].slice(0, 3).map(m => Number(m[1]));
  assert.equal(firstThree.length, 3);
  assert.ok(Math.abs(firstThree.reduce((a,b)=>a+b,0)-100) < 0.1);
  assert.match(get('esiGrid').innerHTML, /Probability/);
});

test('forecast snapshots persist separately in local storage', () => {
  const { get, store } = boot();
  get('esiCalculate').click();
  get('esiSaveForecast').click();
  const records = JSON.parse(store.get('ufi_exact_score_intelligence_v1'));
  assert.equal(records.length, 1);
  assert.equal(records[0].type, 'forecast');
  assert.equal(records[0].top5.length, 5);
  assert.ok(records[0].createdAt);
});

test('post-match audit permits unknown cause and preserves score evidence', () => {
  const { get, store } = boot();
  get('esiPostMatch').value = 'Test FC vs Sample FC';
  get('esiSelected').value = '2-1';
  get('esiFinal').value = '2-3';
  get('esiReason').value = 'unknown';
  get('esiSavePostmortem').click();
  const records = JSON.parse(store.get('ufi_exact_score_intelligence_v1'));
  assert.equal(records[0].type, 'postmortem');
  assert.equal(records[0].reason, 'unknown');
  assert.equal(records[0].selectedScore, '2-1');
  assert.equal(records[0].finalScore, '2-3');
});



test('historical CSV estimator applies team-specific rates with a strict date cutoff', () => {
  const { context } = boot();
  const header = 'date,home_team,away_team,home_goals,away_goals';
  const rows = [];
  for (let i = 1; i <= 24; i++) {
    const day = String(i).padStart(2, '0');
    rows.push('2025-01-' + day + ',Alpha FC,Beta FC,' + (i % 3 === 0 ? 3 : 2) + ',' + (i % 4 === 0 ? 0 : 1));
  }
  const estimator = context.UFIHistoricalRateEstimator;
  const parsed = estimator.parseCsv([header, ...rows].join('\\n'));
  const rates = estimator.estimateRates(parsed, 'Alpha FC', 'Beta FC', '2025-02-01');
  assert.equal(rates.matchesUsed, 24);
  assert.notEqual(rates.lambdaHome.toFixed(2), '1.45');
  assert.notEqual(rates.lambdaAway.toFixed(2), '1.20');
  assert.equal(rates.homeAppearances, 24);
  assert.equal(rates.awayAppearances, 24);
});

test('historical estimator refuses insufficient history and missing cutoff', () => {
  const { context } = boot();
  const estimator = context.UFIHistoricalRateEstimator;
  const parsed = estimator.parseCsv('date,home_team,away_team,home_goals,away_goals\\n2025-01-01,Alpha,Beta,1,0');
  assert.throws(() => estimator.estimateRates(parsed, 'Alpha', 'Beta', '2025-02-01'), /Need at least 20 earlier matches/);
  assert.throws(() => estimator.estimateRates(parsed, 'Alpha', 'Beta', ''), /valid forecast kickoff\/cutoff date/);
});
