const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function boot() {
  const elements = new Map();
  const get = id => {
    if (!elements.has(id)) elements.set(id, {
      id, value: '', innerHTML: '', textContent: '', className: '', checked: false,
      style: {}, handlers: {},
      addEventListener(type, fn) { this.handlers[type] = fn; },
      click() { this.handlers.click?.(); }
    });
    return elements.get(id);
  };
  Object.assign(get('lcsHome'), { value: 'Home' });
  Object.assign(get('lcsAway'), { value: 'Away' });
  Object.assign(get('lcsMode'), { value: 'live' });
  Object.assign(get('lcsMinute'), { value: '45' });
  Object.assign(get('lcsCurrentHome'), { value: '1' });
  Object.assign(get('lcsCurrentAway'), { value: '0' });
  Object.assign(get('lcsXgHome'), { value: '1.4' });
  Object.assign(get('lcsXgAway'), { value: '1.1' });
  Object.assign(get('lcsRho'), { value: '-0.05' });
  Object.assign(get('lcsRedHome'), { value: '0' });
  Object.assign(get('lcsRedAway'), { value: '0' });
  Object.assign(get('lcsVolHome'), { value: '0' });
  Object.assign(get('lcsVolAway'), { value: '0' });
  Object.assign(get('lcsTcsLimit'), { value: '5' });
  const context = { document: { getElementById: get }, window: { addEventListener() {} }, Math, Number, String, JSON, Array, Object, Date, console };
  vm.runInNewContext(fs.readFileSync('live-correct-score-chaos-engine.js', 'utf8'), context);
  return get;
}

test('live score engine renders score-conditioned scenarios and does not output an impossible lower score', () => {
  const get = boot();
  get('lcsRun').click();
  const html = get('lcsOutput').innerHTML;
  assert.match(html, /Top 4 final-score scenarios/);
  assert.doesNotMatch(html, /<td><b>0–0<\/b><\/td>/);
  assert.match(html, /remaining xG/);
});

test('missing player profiles cannot receive green-light approval', () => {
  const get = boot();
  get('lcsRun').click();
  assert.match(get('lcsOutput').innerHTML, /Green-light approval withheld/);
  assert.doesNotMatch(get('lcsOutput').innerHTML, /GREEN LIGHT: Low Randomness/);
});

test('two virtual red flags trigger match discard and suppress predictions', () => {
  const get = boot();
  const players = Array.from({length:11}, (_,i)=>({name:'H'+i,dominantFoot:'Right',positionSide:'center',rIndex:i<2?0.9:0.1}));
  get('lcsPlayersHome').value = JSON.stringify(players);
  get('lcsPlayersAway').value = JSON.stringify(Array.from({length:11},(_,i)=>({name:'A'+i,dominantFoot:'Right',positionSide:'center',rIndex:0.1})));
  get('lcsRun').click();
  const html = get('lcsOutput').innerHTML;
  assert.match(html, /MATCH DISCARDED/);
  assert.match(html, /scorelines below are intentionally withheld/);
});

test('invalid player JSON is surfaced as a visible error', () => {
  const get = boot();
  get('lcsPlayersHome').value = '{bad json';
  get('lcsRun').click();
  assert.match(get('lcsOutput').innerHTML, /valid JSON array/);
});
