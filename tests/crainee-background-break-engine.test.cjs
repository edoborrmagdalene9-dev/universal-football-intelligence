const test=require('node:test');const assert=require('node:assert/strict');
const {simulateMatchBreakScenarios}=require('../crainee-background-break-engine.js');
test('defaults do not silently assume underdog scored first',()=>{
 const r=simulateMatchBreakScenarios({});
 assert.equal(r.underdogHeadStart,false);assert.equal(r.headStartMultiplier,1);
 assert.equal(r.confidence,null);assert.equal(r.confidenceStatus,'NOT_ESTIMATED');
});
test('head start increases rupture signal with same other inputs',()=>{
 const base={ballPositionUnit:5400,favorite:{defenderErrorTendency:10},underdog:{attackerTransitionPacing:10},environment:{isHeavyRainOrWind:true},referee:{whistleFrequencyChaos:2}};
 const no=simulateMatchBreakScenarios({...base,underdogScoredFirst:false});
 const yes=simulateMatchBreakScenarios({...base,underdogScoredFirst:true});
 assert.ok(yes.ruptureIndex>no.ruptureIndex);
});
test('broken structure provides score candidates but never confidence probability',()=>{
 const r=simulateMatchBreakScenarios({ballPositionUnit:5400,underdogScoredFirst:true,favorite:{defenderErrorTendency:10},underdog:{attackerTransitionPacing:10},environment:{isHeavyRainOrWind:true},referee:{whistleFrequencyChaos:2}});
 assert.equal(r.simulationStatus,'MATCH_STRUCTURE_BREAK_SIGNAL');
 assert.ok(r.exactScoreExploration.some(x=>x.score==='0-3'));
 assert.equal(r.confidence,null);
});
test('validates pitch and input bounds',()=>{
 assert.throws(()=>simulateMatchBreakScenarios({ballPositionUnit:6000}),/ballPositionUnit/);
 assert.throws(()=>simulateMatchBreakScenarios({favorite:{defenderErrorTendency:99}}),/defenderErrorTendency/);
});
