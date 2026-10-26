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
  return { get, store };
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


test('historical CSV estimator applies team-specific rates instead of silently reusing defaults', async () => {
  const { get } = boot();
  const header = 'date,home_team,away_team,home_goals,away_goals';
  const rows = [];
  for (let i = 1; i <= 24; i++) {
    const day = String(i).padStart(2, '0');
    rows.push('2025-01-' + day + ',Alpha FC,Beta FC,' + (i % 3 === 0 ? 3 : 2) + ',' + (i % 4 === 0 ? 0 : 1));
  }
  get('esiHome').value = 'Alpha FC';
  get('esiAway').value = 'Beta FC';
  get('esiHistoryCutoff').value = '2025-02-01';
  get('esiHistoricalCsv').files = [{ text: async () => [header, ...rows].join('\\n') }];
  await get('esiHistoricalCsv').handlers.change({ target: get('esiHistoricalCsv') });
  get('esiEstimateRates').click();
  assert.notEqual(get('esiLambdaHome').value, '1.45');
  assert.notEqual(get('esiLambdaAway').value, '1.20');
  assert.match(get('esiRateStatus').textContent, /24 prior matches/);
  assert.match(get('esiForecastSource').value, /historical results CSV/);
});

test('historical estimator refuses insufficient history rather than guessing', async () => {
  const { get } = boot();
  get('esiHome').value = 'Alpha';
  get('esiAway').value = 'Beta';
  get('esiHistoricalCsv').files = [{ text: async () => 'date,home_team,away_team,home_goals,away_goals\\n2025-01-01,Alpha,Beta,1,0' }];
  await get('esiHistoricalCsv').handlers.change({ target: get('esiHistoricalCsv') });
  get('esiEstimateRates').click();
  assert.match(get('esiRateStatus').textContent, /Need at least 20 earlier matches/);
  assert.equal(get('esiLambdaHome').value, '1.45');
  assert.equal(get('esiLambdaAway').value, '1.20');
});
