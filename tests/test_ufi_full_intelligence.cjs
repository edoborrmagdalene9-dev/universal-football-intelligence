'use strict';
const assert=require('node:assert/strict');
global.CraineeChaosGate=require('../crainee-chaos-gate.js');
global.CraineeTacticalSurprise=require('../crainee-tactical-surprise-engine.js');
global.CraineeBackgroundBreakEngine=require('../crainee-background-break-engine.js');
global.CraineeUnconventionalOutcomeEngine=require('../crainee-unconventional-outcome-engine.js');
global.CraineeSubconsciousNarrativeEngine=require('../crainee-subconscious-narrative-engine.js');
global.UFI400Audit={evaluate:()=>({checks:[{id:'UFI-001',name:'fixture identity',status:'NEEDS_DATA',detail:'missing'}]})};
const UFI=require('../ufi-full-intelligence.js');

const suite=UFI.runCraineeSuite({fixtureId:'unit-test',homeTeam:'Home',awayTeam:'Away',mainModelScore:{home:2,away:1}});
assert.equal(suite.unconventional.unconventionalShortlist.length,20);
assert.equal(suite.unconventional.confidenceStatus,'NOT_ESTIMATED');
assert.equal(suite.chaos.status,'NEEDS_DATA');
assert.equal(suite.tactical.status,'NEEDS_DATA');
assert.equal(suite.background.status,'NEEDS_DATA');
assert.equal(suite.subconscious.status,'NEEDS_DATA');

const chaos=UFI.runCraineeSuite({chaos:{
 currentSecond:1200,
 homeTeam:{players:[{marketValue:1000000,age:26,caps:10}]},
 awayTeam:{players:[{marketValue:900000,age:27,caps:12}]},
 referee:{avgWhistleGap1to45:100,avgWhistleGap45to90:90}
}});
assert.ok(['DISCARDED','SURVIVED_AND_APPROVED'].includes(chaos.chaos.status));

const fixture={homeTeam:'Home FC',awayTeam:'Away FC',odds:[{title:'Book A',markets:[
 {key:'h2h',outcomes:[{name:'Home FC',price:2},{name:'Draw',price:3.5},{name:'Away FC',price:4}]},
 {key:'totals',outcomes:[{name:'Over',point:2.5,price:1.9},{name:'Under',point:2.5,price:1.9}]}
]}]};
const markets=UFI.marketSelections(fixture);
assert.ok(Math.abs(markets.find(x=>x.market==='1X2'&&x.selection==='Home').evidence.no_vig_probability-(0.5/(0.5+1/3.5+1/4)))<1e-10);
assert.equal(markets.find(x=>x.market==='Over Under'&&x.selection==='Over 2.5').evidence.no_vig_probability,0.5);
assert.ok(markets.some(x=>x.market==='DC12'&&x.odds===null));
assert.ok(markets.some(x=>x.market==='Team Multigoals 1-3'&&x.side==='home'&&x.odds===null));

const audit=UFI.run400Audit({fixture_id:'f',home:'Home',away:'Away',kickoff:'2026-11-25T12:00:00Z'},
 {selection:'Home',odds:2,evidence:{signal_checks:{'UFI-001':{status:'ASSESSED',source:'test feed',detail:'fixture verified'}}}},0.6);
assert.equal(audit.checks[0].status,'ASSESSED');
assert.equal(audit.coveragePercent,100);
const noSlips=UFI.buildTwoSlips([{fixture:{fixture_id:'x'},audit:{selections:[{decision:'NEEDS_DATA',odds:2}]}}]);
assert.equal(noSlips.status,'NO_QUALIFYING_SELECTIONS');
const odds=[2,3,5,1.5,4,5];
const candidates=odds.map((price,i)=>({fixture:{fixture_id:'fixture-'+i,home:'H'+i,away:'A'+i,kickoff:'2026-11-25T12:00:00Z'},
 audit:{selections:[{decision:'REVIEW_ONLY',market:'Market '+i,selection:'Pick '+i,odds:price,expected_value_per_unit:0.05}]}}));
const slips=UFI.buildTwoSlips(candidates);
assert.equal(slips.status,'TWO_SLIPS_BUILT');
assert.equal(slips.slip_a.combined_odds,30);
assert.equal(slips.slip_b.combined_odds,30);
assert.equal(slips.slip_a.stake_units,1);
assert.equal(slips.slip_b.stake_units,1);
assert.equal(new Set(slips.slip_a.items.map(x=>x.fixture.fixture_id)).size,slips.slip_a.items.length);
assert.equal(new Set(slips.slip_b.items.map(x=>x.fixture.fixture_id)).size,slips.slip_b.items.length);

console.log('UFI full-intelligence browser orchestration tests passed.');
