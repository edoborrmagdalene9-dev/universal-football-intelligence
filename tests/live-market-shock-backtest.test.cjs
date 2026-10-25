const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function boot(fetchImpl=async()=>{throw Error('not configured')}){
 const els=new Map();
 const get=id=>{if(!els.has(id))els.set(id,{id,value:'',checked:false,innerHTML:'',textContent:'',files:[],handlers:{},addEventListener(t,f){this.handlers[t]=f},click(){return this.handlers.click?.()}});return els.get(id)};
 for(const [id,value] of Object.entries({lmsMinute:'70',lmsScoreH:'1',lmsScoreA:'0',lmsRemH:'0.4',lmsRemA:'0.3',lmsShockLimit:'10',lmsOddsSnapshots:'[]',lmsMinHistory:'3',lmsWindow:'5',lmsWeatherBase:'',lmsWeatherLat:'',lmsWeatherLon:'',lmsWeatherDate:'',lmsWeatherHour:'15'}))get(id).value=value;
 let ready;const win={handler:null,addEventListener:(name,fn)=>{if(name==='ufi:live-feed')win.handler=fn}};
 const document={getElementById:get,addEventListener:(name,fn)=>{if(name==='DOMContentLoaded')ready=fn},createElement:()=>({click(){},set href(v){},set download(v){}})};
 const Reader=function(){this.readAsText=file=>{this.result=file.content;this.onload()}};
 vm.runInNewContext(fs.readFileSync('live-market-shock-backtest.js','utf8'),{document,window:win,CustomEvent:function(){},Math,Number,String,JSON,Array,Object,Date,Map,Set,URL,URLSearchParams,Blob,console,fetch:fetchImpl,FileReader:Reader});
 ready();get.emitLive=payload=>win.handler?.({detail:payload});
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

test('walk-forward historical test uses earlier rows and reports baseline comparison',()=>{
 const g=boot();
 const rows=['date,home_team,away_team,home_goals,away_goals,league'];
 for(let i=0;i<40;i++){
  const date=new Date(Date.UTC(2025,0,1+i)).toISOString().slice(0,10);
  const home=i%2===0?'Team A':'Team B',away=i%2===0?'Team B':'Team A';
  rows.push([date,home,away,i%4,(i+1)%3,'Test League'].join(','));
 }
 g('lmsBacktestFile').files=[{content:rows.join('\n')}];
 g('lmsBacktestRun').click();
 assert.match(g('lmsBacktestOutput').innerHTML,/Out-of-sample matches/);
 assert.match(g('lmsBacktestOutput').innerHTML,/league-average baseline/);
 assert.match(g('lmsBacktestOutput').innerHTML,/Model exact-score log loss/);
});

test('weather lookup works directly without a backend URL',async()=>{
 const today=new Date().toISOString().slice(0,10);
 const g=boot(async()=>({ok:true,json:async()=>({hourly:{time:[today+'T15:00'],temperature_2m:[27],relative_humidity_2m:[70],precipitation:[0.2],wind_speed_10m:[12]}})}));
 g('lmsWeatherLat').value='6.45';g('lmsWeatherLon').value='3.40';g('lmsWeatherDate').value=today;g('lmsWeatherHour').value='15';
 await g('lmsWeatherRun').click();
 assert.match(g('lmsWeatherOutput').innerHTML,/Open-Meteo direct/);
 assert.match(g('lmsWeatherOutput').innerHTML,/27 °C/);
});

test('selected live fixture updates current score and minute automatically',()=>{
 const g=boot();g('lmsAutoFixture').value='9876';
 g.emitLive({data:{data:[{id:9876,state:{minute:67},scores:[
  {description:'CURRENT',score:{participant:'home',goals:2}},
  {description:'CURRENT',score:{participant:'away',goals:1}}
 ]}]}});
 assert.equal(g('lmsScoreH').value,'2');assert.equal(g('lmsScoreA').value,'1');assert.equal(g('lmsMinute').value,'67');
});
