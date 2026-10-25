/* Crainee Tactical Surprise Engine — additive, evidence-aware heuristic.
 * Scores tactical mismatch signals; it does NOT output calibrated probabilities.
 */
'use strict';
const PITCH_TOTAL_UNITS = 5400;
const MATCH_TOTAL_SECONDS = 5400;
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
const num = (v, fallback, lo, hi) => {
  const n = v === undefined || v === null || v === '' ? fallback : Number(v);
  if (!Number.isFinite(n) || n < lo || n > hi) throw new TypeError(`Expected number in [${lo}, ${hi}]`);
  return n;
};
function evaluateSpatialTacticalSurprise(matchData = {}) {
  const ball = num(matchData.ballPositionUnit, 2700, 0, PITCH_TOTAL_UNITS);
  const home = matchData.homeTeam || {}, away = matchData.awayTeam || {};
  const attack = matchData.attackingTeam || home, defense = matchData.defendingTeam || away;
  let zone, shear;
  if (ball <= 1800) {
    zone = 'Defensive Zone (0–1800)';
    shear = num(attack.forwardComposure, 8, 1, 10) / num(defense.pressIntensity, 7, 1, 10);
  } else if (ball <= 3600) {
    zone = 'Midfield Zone (1800–3600)';
    shear = Math.abs(num(home.midfieldRating, 6, 1, 10) - num(away.midfieldRating, 6, 1, 10)) + 1;
  } else {
    zone = 'Attacking / Final Third (3600–5400)';
    shear = num(attack.creativity, 8, 1, 10) / num(defense.lowBlockRating, 5, 1, 10);
  }
  const stretch = 1 + Math.abs(ball - 2700) / 2700;
  const score = shear * stretch;
  const passed = score >= 1.4;
  return {status: passed ? 'SPATIAL_EDGE_FLAGGED' : 'DISCARDED_SPATIALLY', pitchZone: zone,
    ballGridUnit: `${ball} / ${PITCH_TOTAL_UNITS}`, zoneShearFactor: round(shear),
    spatialStretchingMultiplier: round(stretch), spatialSurpriseScore: round(score),
    reason: passed ? 'Spatial mismatch signal flagged for review; not a probability.' : 'Spatial score below heuristic threshold.',
    limitations: ['A one-dimensional 0–5400 coordinate is not full player tracking.', 'Ratings are supplied or defaulted; this score is not calibrated.']};
}
function evaluateTacticalSurpriseEdge(matchData = {}) {
  const second = num(matchData.currentSecond, 0, 0, MATCH_TOTAL_SECONDS);
  const opponent = matchData.opponent || {}, attack = matchData.attackingTeam || {};
  const line = num(opponent.defensiveLineHeight, 5, 1, 10);
  const speed = num(attack.transitionSpeed, 5, 1, 10);
  const spaceBehind = line * speed / 100;
  const winger = num(attack.wingerDribbleRating, 7, 1, 10);
  const fullback = num(opponent.fullbackDefenseRating, 5, 1, 10);
  const fullbackMismatch = clamp(winger / fullback, 0.5, 2);
  const time = second / MATCH_TOTAL_SECONDS;
  const fatigue = Math.exp(0.7 * time); // deliberately restrained, bounded by match time
  const freshness = num(attack.substitutesFreshness, 1, 0.5, 2);
  const opponentFatigue = num(opponent.defenderFatigue, 1, 0.5, 2);
  const shock = freshness * opponentFatigue * fatigue;
  const score = spaceBehind * fullbackMismatch * shock * (1 + time);
  const passed = score >= 0.18;
  return {status: passed ? 'TACTICAL_EDGE_FLAGGED' : 'DISCARDED_TACTICALLY',
    currentMatchTime: `${Math.floor(second / 60)}m / 90m (${second}s)`,
    spaceBehindFactor: round(spaceBehind), fullbackMismatchFactor: round(fullbackMismatch),
    fatigueMultiplier: round(fatigue), substitutionFatigueFactor: round(shock),
    tacticalSurpriseScore: round(score),
    exploitType: line >= 7 && speed >= 7 ? 'High-line space exploitation' :
      winger > fullback ? 'Winger/fullback mismatch' : second >= 3600 ? 'Late-game fatigue window' : 'No dominant single pattern',
    reason: passed ? 'Tactical mismatch signal flagged for review; no confidence percentage inferred.' : 'Tactical score below heuristic threshold.',
    limitations: ['Requires reliable tactical/player inputs; no automatic tracking feed is implied.', 'Score is not an upset probability.']};
}
function evaluateChaosAndStyleMatchup(matchData = {}) {
  const ball = num(matchData.ballPositionUnit, 2700, 0, PITCH_TOTAL_UNITS);
  const teamA = matchData.teamA || {name:'Team A', players:[]}, teamB = matchData.teamB || {name:'Team B', players:[]};
  const allowed = new Set(['Chaos_Dribbler','Counter_Press_Monster']);
  function friction(players, opponents) {
    if (!Array.isArray(players) || !Array.isArray(opponents)) throw new TypeError('team players must be arrays');
    let total = 0;
    for (const p of players) {
      if (!p || typeof p.style !== 'string') continue;
      if (p.style === 'Chaos_Dribbler' && opponents.some(o => o && o.style === 'Slow_Defender')) total += 2.5;
      if (p.style === 'Counter_Press_Monster' && opponents.some(o => o && o.style === 'Deep_Playmaker')) total += 2;
    }
    return total;
  }
  const a = friction(teamA.players || [], teamB.players || []);
  const b = friction(teamB.players || [], teamA.players || []);
  const volatility = Math.abs(ball - 2700) / 2700;
  const raw = a - b;
  const solved = Math.sign(raw) * Math.pow(Math.abs(raw), 1.5) * (1 + volatility);
  const passed = Math.abs(solved) >= 3;
  return {status: passed ? 'STYLE_MISMATCH_FLAGGED' : 'NORMAL_LINEAR_MATCH',
    teamAStyleFriction: round(a), teamBStyleFriction: round(b), gridVolatility: round(volatility),
    chaosIndex: round(solved), potentialAdvantageSide: passed ? (solved > 0 ? 'teamA' : 'teamB') : null,
    potentialAdvantageTeam: passed ? (solved > 0 ? teamA.name : teamB.name) : null,
    reason: passed ? 'Style-friction anomaly flagged for tactical review; not a winner prediction.' : 'No style-friction anomaly crossed the heuristic threshold.',
    limitations: ['Player styles must be evidenced, not guessed.', 'Nonlinear transform and threshold are heuristic and need historical validation.']};
}
function evaluateTacticalSurprise(matchData = {}) {
  const spatial = evaluateSpatialTacticalSurprise(matchData);
  const tactical = evaluateTacticalSurpriseEdge(matchData);
  const styles = evaluateChaosAndStyleMatchup(matchData);
  const flagged = [spatial, tactical, styles].filter(x => /FLAGGED|LOCKED/.test(x.status)).length;
  return {engine:'Crainee Tactical Surprise Engine', flaggedSignals:flagged, spatial, tactical, styles,
    summary: flagged ? `${flagged} of 3 heuristic signal groups flagged; inspect the underlying evidence.` : 'No strong heuristic mismatch signal; this does not mean an upset is impossible.',
    forecastWarning:'These are heuristic mismatch scores, NOT calibrated probabilities or proof of value. Validate on chronological unseen matches before using for forecasts.'};
}
function round(n) { return Number(n.toFixed(3)); }
if (typeof module !== 'undefined' && module.exports) module.exports = {evaluateSpatialTacticalSurprise,evaluateTacticalSurpriseEdge,evaluateChaosAndStyleMatchup,evaluateTacticalSurprise,PITCH_TOTAL_UNITS,MATCH_TOTAL_SECONDS};
if (typeof window !== 'undefined') {
  window.CraineeTacticalSurprise = {evaluateSpatialTacticalSurprise,evaluateTacticalSurpriseEdge,evaluateChaosAndStyleMatchup,evaluateTacticalSurprise};
  document.addEventListener('DOMContentLoaded', function() {
    if (!document.querySelector('#view-tactical-surprise') || !document.querySelector('[data-view="tactical-surprise"]')) {
      const nav = document.querySelector('#navigation'), main = document.querySelector('.main');
      if (!nav || !main) return;
      const button = document.createElement('button'); button.className='nav-item'; button.dataset.view='tactical-surprise'; button.innerHTML='<span>⌖</span> Tactical Surprise'; nav.appendChild(button);
      const section=document.createElement('section'); section.className='view'; section.id='view-tactical-surprise';
      section.innerHTML='<div class="page-heading"><div><div class="eyebrow">ADDITIVE EXPERIMENTAL MODULE</div><h1>Crainee Tactical Surprise Engine</h1><p>Pitch grid, high-line transitions, winger/fullback mismatch, fatigue and player-style friction. Existing engines remain unchanged.</p></div></div><div class="panel"><div class="form-grid three"><label>Ball position (0–5400)<input id="ts-ball" type="number" min="0" max="5400" value="4500"></label><label>Match second (0–5400)<input id="ts-time" type="number" min="0" max="5400" value="4200"></label><label>High defensive line (1–10)<input id="ts-line" type="number" min="1" max="10" value="8"></label><label>Transition speed (1–10)<input id="ts-speed" type="number" min="1" max="10" value="9"></label><label>Winger dribbling (1–10)<input id="ts-winger" type="number" min="1" max="10" value="8"></label><label>Fullback defence (1–10)<input id="ts-fullback" type="number" min="1" max="10" value="5"></label><label>Attack creativity (1–10)<input id="ts-creativity" type="number" min="1" max="10" value="8"></label><label>Defensive low-block rating (1–10)<input id="ts-block" type="number" min="1" max="10" value="5"></label><label>Sub freshness (0.5–2)<input id="ts-fresh" type="number" min="0.5" max="2" step="0.1" value="1.2"></label><label>Defender fatigue (0.5–2)<input id="ts-fatigue" type="number" min="0.5" max="2" step="0.1" value="1.3"></label></div><p class="muted">Player styles are optional JSON arrays; enter only styles supported by evidence.</p><label>Team A players JSON<textarea id="ts-a" rows="3">[{"style":"Chaos_Dribbler"}]</textarea></label><label>Team B players JSON<textarea id="ts-b" rows="3">[{"style":"Slow_Defender"},{"style":"Deep_Playmaker"}]</textarea></label><div class="form-actions"><button class="button primary" id="ts-run">Evaluate tactical signals</button><button class="button ghost" id="ts-example">Load example</button></div><div id="ts-result" class="notice" aria-live="polite">Enter match evidence and evaluate. Defaults are illustrative only.</div></div>';
      main.appendChild(section);
      nav.addEventListener('click', e=>{const b=e.target.closest('[data-view="tactical-surprise"]');if(!b)return;document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id==='view-tactical-surprise'));nav.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n===b));});
      const get=id=>Number(document.getElementById(id).value);
      const run=()=>{try{const result=evaluateTacticalSurprise({ballPositionUnit:get('ts-ball'),currentSecond:get('ts-time'),attackingTeam:{transitionSpeed:get('ts-speed'),wingerDribbleRating:get('ts-winger'),creativity:get('ts-creativity'),substitutesFreshness:get('ts-fresh')},opponent:{defensiveLineHeight:get('ts-line'),fullbackDefenseRating:get('ts-fullback'),lowBlockRating:get('ts-block'),defenderFatigue:get('ts-fatigue')},defendingTeam:{lowBlockRating:get('ts-block')},homeTeam:{midfieldRating:6},awayTeam:{midfieldRating:6},teamA:{name:'Team A',players:JSON.parse(document.getElementById('ts-a').value)},teamB:{name:'Team B',players:JSON.parse(document.getElementById('ts-b').value)}});document.getElementById('ts-result').textContent=JSON.stringify(result,null,2);}catch(e){document.getElementById('ts-result').textContent='Input error: '+e.message;}};
      document.getElementById('ts-run').addEventListener('click',run);
      document.getElementById('ts-example').addEventListener('click',()=>{document.getElementById('ts-ball').value=4500;document.getElementById('ts-time').value=4200;document.getElementById('ts-line').value=8;document.getElementById('ts-speed').value=9;document.getElementById('ts-winger').value=8;document.getElementById('ts-fullback').value=5;document.getElementById('ts-a').value='[{"style":"Chaos_Dribbler"}]';document.getElementById('ts-b').value='[{"style":"Slow_Defender"},{"style":"Deep_Playmaker"}]';run();});
    }
  });
}
