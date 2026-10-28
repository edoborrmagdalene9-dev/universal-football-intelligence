'use strict';
const test=require('node:test'); const assert=require('node:assert/strict');
const e=require('../crainee-tactical-surprise-engine.js');
test('spatial engine bounds pitch and flags a meaningful final-third mismatch',()=>{
 const r=e.evaluateSpatialTacticalSurprise({ballPositionUnit:5000,attackingTeam:{creativity:9},defendingTeam:{lowBlockRating:3},homeTeam:{},awayTeam:{}});
 assert.equal(r.status,'SPATIAL_EDGE_FLAGGED'); assert.ok(r.spatialSurpriseScore>1.4);
});
test('spatial engine rejects out-of-range ball positions',()=>assert.throws(()=>e.evaluateSpatialTacticalSurprise({ballPositionUnit:6000}),/Expected number/));
test('tactical engine recognizes high line plus fast transition as a signal, not probability',()=>{
 const r=e.evaluateTacticalSurpriseEdge({currentSecond:4800,opponent:{defensiveLineHeight:9,fullbackDefenseRating:4,defenderFatigue:1.5},attackingTeam:{transitionSpeed:9,wingerDribbleRating:8,substitutesFreshness:1.2}});
 assert.equal(r.status,'TACTICAL_EDGE_FLAGGED'); assert.ok(r.limitations.length); assert.equal('confidenceRating' in r,false);
});
test('style engine flags asymmetric evidenced player styles',()=>{
 const r=e.evaluateChaosAndStyleMatchup({ballPositionUnit:5200,teamA:{name:'A',players:[{style:'Chaos_Dribbler'}]},teamB:{name:'B',players:[{style:'Slow_Defender'}]}});
 assert.equal(r.potentialAdvantageTeam,'A'); assert.equal(r.status,'STYLE_MISMATCH_FLAGGED');
});
test('empty styles stay neutral and engine returns all three modules',()=>{
 const r=e.evaluateTacticalSurprise({teamA:{players:[]},teamB:{players:[]}});
 assert.equal(r.engine,'Crainee Tactical Surprise Engine'); assert.equal(r.flaggedSignals,0); assert.ok(r.spatial&&r.tactical&&r.styles);
});
test('invalid player style arrays fail clearly',()=>assert.throws(()=>e.evaluateChaosAndStyleMatchup({teamA:{players:{}},teamB:{players:[]}}),/arrays/));
