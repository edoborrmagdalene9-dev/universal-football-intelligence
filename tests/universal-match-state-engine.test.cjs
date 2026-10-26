const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function boot(){
 const els=new Map();const get=id=>{if(!els.has(id))els.set(id,{id,value:'',checked:false,innerHTML:'',style:{},handlers:{},addEventListener(t,f){this.handlers[t]=f},click(){this.handlers.click?.()}});return els.get(id)};
 for(const [id,value] of Object.entries({umeHome:'Home',umeAway:'Away',umeMinute:'35',umeScoreH:'1',umeScoreA:'0',umeXgH:'1.3',umeXgA:'1.1',umeChaosLimit:'2.5',umeState:'{}',umeEvents:'[]'}))get(id).value=value;
 get('umeLive').checked=true;
 vm.runInNewContext(fs.readFileSync('universal-match-state-engine.js','utf8'),{document:{getElementById:get},window:{addEventListener(){}},Math,Number,String,JSON,Array,Object,Date,console});
 return get;
}
test('event engine conditions outcomes on the live score and returns three branches',()=>{
 const g=boot();g('umeRun').click();const h=g('umeOutput').innerHTML;
 assert.match(h,/Top 3 final-score branches/);assert.doesNotMatch(h,/<td><b>0–0<\/b><\/td>/);
});
test('multiple red-card anomalies trigger Level 4 discard',()=>{
 const g=boot();g('umeEvents').value=JSON.stringify([{type:'red',team:'home'},{type:'red',team:'away'}]);g('umeRun').click();
 assert.match(g('umeOutput').innerHTML,/MATCH DISCARDED: High Multi-Event Anomaly/);
 assert.match(g('umeOutput').innerHTML,/Predictions suppressed/);
});
test('low tempo locks the model into trap-game mode without discarding',()=>{
 const g=boot();g('umeState').value=JSON.stringify({home:{block:'low',possessionShare:35},away:{block:'low',possessionShare:65},transitions:0,expectedTransitions:10,finalThirdEntries:0,expectedFinalThirdEntries:12,progressivePasses:0,entropy:0.1});
 g('umeRun').click();assert.match(g('umeOutput').innerHTML,/TRAP GAME LOCKED/);assert.doesNotMatch(g('umeOutput').innerHTML,/MATCH DISCARDED/);
});
test('malformed event JSON produces visible error',()=>{
 const g=boot();g('umeEvents').value='not-json';g('umeRun').click();assert.match(g('umeOutput').innerHTML,/umeEvents/);
});
