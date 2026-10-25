const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function boot(){
 const els=new Map();
 const get=id=>{if(!els.has(id))els.set(id,{id,value:'',checked:false,innerHTML:'',textContent:'',files:[],handlers:{},addEventListener(t,f){this.handlers[t]=f},click(){this.handlers.click?.()}});return els.get(id)};
 for(const [id,value] of Object.entries({lmsMinute:'70',lmsScoreH:'1',lmsScoreA:'0',lmsRemH:'0.4',lmsRemA:'0.3',lmsShockLimit:'10',lmsOddsSnapshots:'[]',lmsMinHistory:'3',lmsWindow:'5',lmsWeatherBase:'',lmsWeatherLat:'',lmsWeatherLon:'',lmsWeatherDate:'',lmsWeatherHour:'15'}))get(id).value=value;
 let ready;
 const document={getElementById:get,addEventListener:(name,fn)=>{if(name==='DOMContentLoaded')ready=fn},createElement:()=>({click(){},set href(v){},set download(v){}})};
 vm.runInNewContext(fs.readFileSync('live-market-shock-backtest.js','utf8'),{document,Math,Number,String,JSON,Array,Object,Date,Map,Set,URL,URLSearchParams,Blob,console,fetch:async()=>{throw Error('not configured')},FileReader:function(){}});
 ready();
 return get;
}
function snapshots(a,b,first,second){
 return JSON.stringify([
 {timestamp:a,home:first[0],draw:first[1],away:first[2]},
 {timestamp:b,home:second[0],draw:second[1],away:second[2]}
 ]);
}
test('market shock pauses rather than force-fitting a large odds move',()=>{
 const g=boot(),now=Date.now();
 g('lmsOddsSnapshots').value=snapshots(new Date(now-12000).toISOString(),new Date(now-2000).toISOString(),[2.6,3.0,2.7],[1.65,3.5,4.8]);
 g('lmsRun').click();
 assert.match(g('lmsOutput').innerHTML,/PAUSE \/ DISCARD CURRENT FORECAST/);
 assert.match(g('lmsOutput').innerHTML,/Conditional score branches/);
});
test('stale odds are rejected',()=>{
 const g=boot(),now=Date.now();
 g('lmsOddsSnapshots').value=snapshots(new Date(now-240000).toISOString(),new Date(now-230000).toISOString(),[2.2,3.1,3.2],[2.18,3.1,3.25]);
 g('lmsRun').click();
 assert.match(g('lmsOutput').innerHTML,/DISCARD \/ HOLD/);
 assert.match(g('lmsOutput').innerHTML,/STALE/);
});
test('malformed or missing timestamped odds do not produce a forecast',()=>{
 const g=boot();g('lmsOddsSnapshots').value=JSON.stringify([{home:2,draw:3,away:4},{home:2,draw:3,away:4}]);g('lmsRun').click();
 assert.match(g('lmsOutput').innerHTML,/needs an ISO timestamp/);
});
test('future-dated odds are rejected',()=>{
 const g=boot(),now=Date.now();
 g('lmsOddsSnapshots').value=snapshots(new Date(now+60000).toISOString(),new Date(now+70000).toISOString(),[2.2,3.1,3.2],[2.18,3.1,3.25]);
 g('lmsRun').click();
 assert.match(g('lmsOutput').innerHTML,/FUTURE-DATED/);
});
