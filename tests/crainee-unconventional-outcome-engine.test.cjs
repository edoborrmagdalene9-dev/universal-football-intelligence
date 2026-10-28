const test=require('node:test'); const assert=require('node:assert/strict');
const {generateUnconventionalOutcomes}=require('../crainee-unconventional-outcome-engine.js');
test('generates unconventional shortlist separate from conventional reference',()=>{
 const r=generateUnconventionalOutcomes({seed:'fixed-123',mainModelScore:{home:2,away:1},candidateCount:12,conventionalShortlist:[{home:2,away:1},{home:1,away:1}]});
 assert.equal(r.unconventionalShortlist.length,12);
 assert.equal(r.mainModelScore.score,'2-1');
 assert.equal(r.conventionalShortlist.length,2);
 assert.ok(r.unconventionalShortlist.every(x=>x.classification==='EXPLORED_POSSIBILITY'&&x.probability===null));
 assert.ok(r.unconventionalShortlist.every(x=>x.score!=='2-1'));
});
test('same seed and inputs reproduce exact results',()=>{
 const input={seed:'replay-me',mainModelScore:{home:2,away:1},candidateCount:15};
 assert.deepEqual(generateUnconventionalOutcomes(input),generateUnconventionalOutcomes(input));
});
test('different seeds can explore different ranked scorelines',()=>{
 const a=generateUnconventionalOutcomes({seed:'seed-a',candidateCount:20});
 const b=generateUnconventionalOutcomes({seed:'seed-b',candidateCount:20});
 assert.notDeepEqual(a.unconventionalShortlist,b.unconventionalShortlist);
});
test('includes named alternate realities and validates bounds',()=>{
 const r=generateUnconventionalOutcomes({seed:'paths'});
 assert.ok(r.scenarioPaths.some(x=>x.id==='red-card-disruption'));
 assert.ok(r.scenarioPaths.some(x=>x.id==='favourite-dominates-blanks'));
 assert.throws(()=>generateUnconventionalOutcomes({candidateCount:100}),/candidateCount/);
 assert.throws(()=>generateUnconventionalOutcomes({mainModelScore:{home:-1,away:0}}),/home goals/);
});
