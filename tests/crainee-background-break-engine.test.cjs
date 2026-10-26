const test=require('node:test');const assert=require('node:assert/strict');
const {simulateMatchBreakScenarios}=require('../crainee-background-break-engine.js');
test('defaults do not silently assume underdog scored first',()=>{
 const r=simulateMatchBreakScenarios({});
 assert.equal(r.underdogHeadStart,false);assert.equal(r.headStartMultiplier,1);
 assert.ok(r.confidence>=0&&r.confidence<=100);assert.equal(r.confidenceStatus,'HEURISTIC_SIGNAL_PERCENT_NOT_CALIBRATED_PROBABILITY');
 assert.equal(r.confidenceIsProbability,false);
});
test('head start increases rupture signal with same other inputs',()=>{
 const base={ballPositionUnit:5400,favorite:{defenderErrorTendency:10},underdog:{attackerTransitionPacing:10},environment:{isHeavyRainOrWind:true},referee:{whistleFrequencyChaos:2}};
 const no=simulateMatchBreakScenarios({...base,underdogScoredFirst:false});
 const yes=simulateMatchBreakScenarios({...base,underdogScoredFirst:true});
 assert.ok(yes.ruptureIndex>no.ruptureIndex);
});
test('broken structure retains heuristic confidence signal without claiming probability',()=>{
 const r=simulateMatchBreakScenarios({ballPositionUnit:5400,underdogScoredFirst:true,favorite:{defenderErrorTendency:10},underdog:{attackerTransitionPacing:10},environment:{isHeavyRainOrWind:true},referee:{whistleFrequencyChaos:2}});
 assert.equal(r.simulationStatus,'MATCH_STRUCTURE_BREAK_SIGNAL');
 assert.ok(r.exactScoreExploration.some(x=>x.score==='0-3'));
 assert.ok(r.confidence>=0&&r.confidence<=100);assert.equal(r.confidenceIsProbability,false);
 assert.equal(r.confidenceStatus,'HEURISTIC_SIGNAL_PERCENT_NOT_CALIBRATED_PROBABILITY');
});
test('validates pitch and input bounds',()=>{
 assert.throws(()=>simulateMatchBreakScenarios({ballPositionUnit:6000}),/ballPositionUnit/);
 assert.throws(()=>simulateMatchBreakScenarios({favorite:{defenderErrorTendency:99}}),/defenderErrorTendency/);
});
