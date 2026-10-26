/* Live market-shock monitor + chronological exact-score backtest.
 * Uses explicit source timestamps; never treats odds movement as proof of a goal.
 * Browser module is additive and does not replace the existing engines.
 */
(() => {
'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const finite=(x)=>Number.isFinite(Number(x));
function poisson(k,lambda){if(k<0)return 0;let p=Math.exp(-lambda);for(let i=1;i<=k;i++)p*=lambda/i;return p}
function implied(row){
 const keys=['home','draw','away'];const raw=keys.map(k=>1/Number(row[k]));
 if(raw.some((v,i)=>!Number.isFinite(v)||Number(row[keys[i]])<=1))throw Error('Every 1X2 decimal price must be > 1.00.');
 const sum=raw.reduce((a,b)=>a+b,0);return raw.map(v=>v/sum);
}
function parseSourceTime(value){
 if(!value)return NaN;
 let s=String(value).trim().replace(' ','T');
 if(!(s.endsWith('Z')||s.endsWith('z')||/[+-][0-9]{2}:?[0-9]{2}$/.test(s)))s+='Z';
 return Date.parse(s);
}
function parseOdds(){
 const rows=JSON.parse($('lmsOddsSnapshots').value||'[]');
 if(!Array.isArray(rows)||rows.length<2)throw Error('Enter at least two timestamped odds snapshots as a JSON array.');
 const valid=rows.map(r=>{
  if(!r.timestamp)throw Error('Every odds snapshot needs an ISO timestamp.');
  const ts=Date.parse(r.timestamp);if(!Number.isFinite(ts))throw Error('Invalid odds timestamp: '+r.timestamp);
  const sourceTs=r.sourceUpdatedAt?parseSourceTime(r.sourceUpdatedAt):ts;
  if(!Number.isFinite(sourceTs))throw Error('Invalid provider source-update timestamp: '+r.sourceUpdatedAt);
  return {...r,ts,sourceTs,p:implied(r)}
 }).sort((a,b)=>a.ts-b.ts);
 if(valid[0].ts===valid[1].ts)throw Error('The two latest snapshots need distinct capture timestamps.');
 return valid;
}
function runMarket(){
 const out=$('lmsOutput');
 try{
  const snaps=parseOdds(),a=snaps[snaps.length-2],b=snaps[snaps.length-1],now=Date.now();
  const rawAge=(now-b.sourceTs)/1000,age=Math.max(0,rawAge),gap=(b.ts-a.ts)/1000;
  const minute=clamp(Number($('lmsMinute').value)||0,0,120),h=Math.max(0,Math.floor(Number($('lmsScoreH').value)||0)),away=Math.max(0,Math.floor(Number($('lmsScoreA').value)||0));
  const lh=clamp(Number($('lmsRemH').value)||0,0,4),la=clamp(Number($('lmsRemA').value)||0,0,4);
  const changes=b.p.map((p,i)=>p-a.p[i]),maxAbs=Math.max(...changes.map(Math.abs));
  const maxRel=Math.max(...['home','draw','away'].map(k=>Math.abs(Number(a[k])-Number(b[k]))/Number(a[k])));
  const shockLimit=(Number($('lmsShockLimit').value)||10)/100;
  const stale=rawAge < -5 || age>120 || gap>900 || gap<1;
  const shock=maxAbs>=shockLimit||maxRel>=0.25;
  const reasons=[];
  if(rawAge < -5)reasons.push('FUTURE-DATED snapshot — source clock or timestamp is invalid.'); else if(stale)reasons.push('STALE / badly spaced odds snapshots — do not use them to update a live forecast.');
  if(shock)reasons.push('MARKET SHOCK — material price movement; suspend scoreline approval and re-check events, VAR, cards, injuries and feed timestamps.');
  if(!stale&&!shock)reasons.push('No configured shock threshold crossed. This is not proof that the market is correct.');
  // Small bounded adjustment only for modest, fresh moves. A large move causes a HOLD, not chasing.
  let adjH=0,adjA=0,decision='MONITOR';
  if(stale){decision='DISCARD / HOLD';}
  else if(shock){decision='PAUSE / DISCARD CURRENT FORECAST';}
  else {
   adjH=clamp((changes[0]-changes[2])*0.35,-0.20,0.20);
   adjA=clamp((changes[2]-changes[0])*0.35,-0.20,0.20);
  }
  const finalH=[],finalA=[];
  for(let i=0;i<=5;i++)for(let j=0;j<=5;j++)finalH.push({h:h+i,a:away+j,p:poisson(i,lh*(1+adjH))*poisson(j,la*(1+adjA))});
  const sum=finalH.reduce((s,x)=>s+x.p,0)||1;finalH.forEach(x=>x.p/=sum);finalH.sort((x,y)=>y.p-x.p);
  const details=['home','draw','away'].map((k,i)=>({k,from:a[k],to:b[k],probFrom:a.p[i],probTo:b.p[i],delta:changes[i]}));
  out.innerHTML='<div class="notice '+(stale||shock?'warning':'')+'"><b>'+esc(decision)+'</b><br>Snapshot interval: '+gap.toFixed(1)+' s · Latest source age: '+age.toFixed(1)+' s · Current state: '+h+'–'+away+' at '+minute+'′.<br>'+reasons.map(esc).join('<br>')+'</div>'+
  '<div class="table-wrap"><table><thead><tr><th>Market</th><th>Odds before</th><th>Odds now</th><th>De-vig probability shift</th></tr></thead><tbody>'+
  details.map(d=>'<tr><td>'+d.k.toUpperCase()+'</td><td>'+Number(d.from).toFixed(2)+'</td><td>'+Number(d.to).toFixed(2)+'</td><td>'+((d.delta*100)>=0?'+':'')+(d.delta*100).toFixed(2)+' pp</td></tr>').join('')+
  '</tbody></table></div>'+
  '<p><b>Conditional score branches (remaining-goal xG supplied by user):</b> '+finalH.slice(0,5).map(x=>x.h+'–'+x.a+' ('+(x.p*100).toFixed(1)+'%)').join(' · ')+'</p>'+
  '<p class="muted">Adjustment applied: home '+(adjH*100).toFixed(1)+'%, away '+(adjA*100).toFixed(1)+'%. Large or stale moves are never force-fit into a prediction. Market prices are not verified match events; refresh the event feed and confirm score/minute first.</p>';
 }catch(e){out.innerHTML='<div class="notice warning">'+esc(e.message)+'</div>'}
}
function csvParse(text){
 const lines=text.replace(String.fromCharCode(65279),'').split(String.fromCharCode(10)).map(x=>x.replaceAll(String.fromCharCode(13),'')).filter(x=>x.trim());
 if(lines.length<2)throw Error('CSV needs a header and at least two match rows.');
 const split=line=>{const out=[];let cur='',q=false;for(let i=0;i<line.length;i++){const c=line[i];if(c==='"'&&line[i+1]==='"'&&q){cur+='"';i++}else if(c==='"')q=!q;else if(c===','&&!q){out.push(cur);cur=''}else cur+=c}out.push(cur);return out};
 const headers=split(lines[0]).map(x=>x.trim().toLowerCase());const rows=lines.slice(1).map(line=>{const vals=split(line);const o={};headers.forEach((h,i)=>o[h]=(vals[i]||'').trim());return o});
 const required=['date','home_team','away_team','home_goals','away_goals'];for(const k of required)if(!headers.includes(k))throw Error('Missing CSV column: '+k);
 const dated=rows.map(r=>({...r,hg:Number(r.home_goals),ag:Number(r.away_goals)}));
 const validIsoDate=value=>/^\\d{4}-\\d{2}-\\d{2}$/.test(value)&&!Number.isNaN(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
 const badDate=dated.find(r=>r.date&&!validIsoDate(r.date));
 if(badDate)throw Error('Invalid date "'+badDate.date+'". Use YYYY-MM-DD for every row so the chronological walk-forward test cannot leak future results into earlier forecasts.');
 return dated.filter(r=>r.date&&r.home_team&&r.away_team&&Number.isInteger(r.hg)&&Number.isInteger(r.ag)&&r.hg>=0&&r.ag>=0).sort((a,b)=>a.date.localeCompare(b.date));
}
function poissonDist(lam,cap=9){const p=[Math.exp(-lam)];for(let k=1;k<=cap;k++)p.push(p[k-1]*lam/k);return p}
function gridProb(hg,ag,lh,la){const hp=poissonDist(lh),ap=poissonDist(la);return Math.max(1e-12,(hp[hg]||0)*(ap[ag]||0))}
function runBacktest(){
 const out=$('lmsBacktestOutput'),file=$('lmsBacktestFile').files[0];
 if(!file){out.innerHTML='<div class="notice warning">Choose a historical CSV first.</div>';return}
 const reader=new FileReader();reader.onload=()=>{
 try{
  const rows=csvParse(String(reader.result||''));if(rows.length<30)throw Error('Only '+rows.length+' valid rows. For meaningful evaluation, load at least 30 chronologically ordered matches; 100+ is preferable.');
  const minHistory=Math.max(3,Number($('lmsMinHistory').value)||5), window=Math.max(5,Number($('lmsWindow').value)||10);
  const teamHist=new Map(),leagueHist=new Map(),results=[];let skipped=0;
  const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:1.25;
  const hist=(map,k)=>map.get(k)||[];
  // Date-batched walk-forward: all forecasts on a date are produced before that date's results are added.
  for(let start=0;start<rows.length;){
   let end=start+1;while(end<rows.length&&rows[end].date===rows[start].date)end++;
   const batch=rows.slice(start,end);
   for(const r of batch){
    const league=(r.league||r.league_code||'ALL').trim()||'ALL',home=r.home_team,away=r.away_team;
    const hh=hist(teamHist,league+'|'+home),ah=hist(teamHist,league+'|'+away),lhist=hist(leagueHist,league);
    if(hh.length<minHistory||ah.length<minHistory||lhist.length<minHistory){skipped++;continue}
    const last=(arr,key)=>arr.slice(-window).map(x=>x[key]);
    const leagueHome=mean(lhist.map(x=>x.hg)),leagueAway=mean(lhist.map(x=>x.ag));
    const attackH=mean(last(hh,'scored'))/Math.max(.2,leagueHome);
    const defenceA=mean(last(ah,'conceded'))/Math.max(.2,leagueHome);
    const attackA=mean(last(ah,'scored'))/Math.max(.2,leagueAway);
    const defenceH=mean(last(hh,'conceded'))/Math.max(.2,leagueAway);
    const modelH=clamp(leagueHome*attackH*defenceA,.08,4.5),modelA=clamp(leagueAway*attackA*defenceH,.08,4.5);
    const baseH=clamp(leagueHome,.08,4.5),baseA=clamp(leagueAway,.08,4.5);
    const modelP=gridProb(r.hg,r.ag,modelH,modelA),baseP=gridProb(r.hg,r.ag,baseH,baseA);
    const top=(h,a)=>{let best={h:0,a:0,p:0};for(let i=0;i<=7;i++)for(let j=0;j<=7;j++){const p=gridProb(i,j,h,a);if(p>best.p)best={h:i,a:j,p}}return best};
    const mp=top(modelH,modelA),bp=top(baseH,baseA);
    results.push({date:r.date,home,away,actual:r.hg+'-'+r.ag,model:mp.h+'-'+mp.a,modelProb:mp.p,base:bp.h+'-'+bp.a,baseProb:bp.p,modelNll:-Math.log(modelP),baseNll:-Math.log(baseP),modelHit:mp.h===r.hg&&mp.a===r.ag,baseHit:bp.h===r.hg&&bp.a===r.ag});
   }
   // Update only after every fixture on this date has been forecast.
   for(const r of batch){
    const league=(r.league||r.league_code||'ALL').trim()||'ALL';
    for(const [team,scored,conceded] of [[r.home_team,r.hg,r.ag],[r.away_team,r.ag,r.hg]]){
     const key=league+'|'+team,arr=hist(teamHist,key);arr.push({scored,conceded});if(arr.length>window*3)arr.shift();teamHist.set(key,arr);
    }
    const la=hist(leagueHist,league);la.push({hg:r.hg,ag:r.ag});if(la.length>500)la.shift();leagueHist.set(league,la);
   }
   start=end;
  }
  if(!results.length)throw Error('No out-of-sample rows. Reduce minimum history or supply more matches per league.');
  const n=results.length,modelNll=results.reduce((s,r)=>s+r.modelNll,0)/n,baseNll=results.reduce((s,r)=>s+r.baseNll,0)/n;
  const modelHit=results.filter(r=>r.modelHit).length/n,baseHit=results.filter(r=>r.baseHit).length/n;
  const win=modelNll<baseNll;
  out.innerHTML='<div class="metrics"><article class="metric"><span>Out-of-sample matches</span><strong>'+n+'</strong><small>'+skipped+' rows held back for history warm-up</small></article><article class="metric"><span>Model exact-score top-1</span><strong>'+(modelHit*100).toFixed(2)+'%</strong><small>Hit rate is noisy</small></article><article class="metric"><span>Model exact-score log loss</span><strong>'+modelNll.toFixed(3)+'</strong><small>Lower is better</small></article><article class="metric"><span>Baseline log loss</span><strong>'+baseNll.toFixed(3)+'</strong><small>League-average Poisson</small></article></div>'+
  '<div class="notice '+(win?'':'warning')+'"><b>'+(win?'Rolling team-rate model beat':'Rolling team-rate model did not beat')+' the league-average baseline on this sample.</b> This is a walk-forward diagnostic, not proof of a betting edge. Test-set dates were not randomly shuffled. Results may still be affected by source coverage and CSV quality.</div>'+
  '<div class="table-wrap"><table><thead><tr><th>Date</th><th>Match</th><th>Actual</th><th>Model top score</th><th>Baseline top score</th><th>Model NLL</th><th>Baseline NLL</th></tr></thead><tbody>'+
  results.slice(-100).map(r=>'<tr><td>'+esc(r.date)+'</td><td>'+esc(r.home)+' – '+esc(r.away)+'</td><td>'+r.actual+'</td><td>'+r.model+(r.modelHit?' ✓':'')+'</td><td>'+r.base+(r.baseHit?' ✓':'')+'</td><td>'+r.modelNll.toFixed(3)+'</td><td>'+r.baseNll.toFixed(3)+'</td></tr>').join('')+
  '</tbody></table></div><button id="lmsDownloadBacktest" class="button">Download backtest CSV</button>';
  $('lmsDownloadBacktest').addEventListener('click',()=>{const header='date,home,away,actual,model_top_score,baseline_top_score,model_exact_score_logloss,baseline_exact_score_logloss,model_hit,baseline_hit\n';const body=results.map(r=>[r.date,r.home,r.away,r.actual,r.model,r.base,r.modelNll.toFixed(6),r.baseNll.toFixed(6),r.modelHit,r.baseHit].map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\n');const blob=new Blob([header+body],{type:'text/csv'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='ufi-walkforward-exact-score-backtest.csv';a.click();URL.revokeObjectURL(url)});
 }catch(e){out.innerHTML='<div class="notice warning">'+esc(e.message)+'</div>'}
 };reader.readAsText(file);
}
async function runWeather(){
 const out=$('lmsWeatherOutput');
 try{
  const base=($('lmsWeatherBase').value||($('esiApiBase')&&$('esiApiBase').value)||'').trim().replace(/[/]+$/,'');
  if(!$('lmsWeatherLat').value.trim()||!$('lmsWeatherLon').value.trim())throw Error('Enter verified stadium coordinates; blank coordinates are not valid.');
  const lat=Number($('lmsWeatherLat').value),lon=Number($('lmsWeatherLon').value),day=$('lmsWeatherDate').value,hour=Number($('lmsWeatherHour').value);
  if(!Number.isFinite(lat)||lat < -90||lat>90||!Number.isFinite(lon)||lon < -180||lon>180)throw Error('Enter valid stadium latitude and longitude.');
  if(!day||!Number.isInteger(hour)||hour<0||hour>23)throw Error('Enter match date and UTC hour (0–23).');
  out.textContent='Loading weather…';
  let url,backend=Boolean(base);
  const params={latitude:String(lat),longitude:String(lon),hourly:'temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m',timezone:'UTC'};
  if(base){
   if(!base.toLowerCase().startsWith('https://'))throw Error('Weather backend must use HTTPS.');
   url=base+'/api/weather?'+new URLSearchParams({lat:String(lat),lon:String(lon),date:day,hour:String(hour)});
  }else{
   const today=new Date().toISOString().slice(0,10);
   if(day<today){url='https://archive-api.open-meteo.com/v1/archive?'+new URLSearchParams({...params,start_date:day,end_date:day})}
   else{url='https://api.open-meteo.com/v1/forecast?'+new URLSearchParams({...params,forecast_days:'16'})}
  }
  const response=await fetch(url,{headers:{Accept:'application/json'}});
  const data=await response.json();
  if(!response.ok||data.error)throw Error(data.reason||data.error||('Weather endpoint HTTP '+response.status));
  let w=data.weather||{},matched=data.matchedHourUtc||'';
  if(!backend){
   const times=data.hourly&&data.hourly.time||[],indices=times.map((t,i)=>({t,i})).filter(x=>x.t.startsWith(day+'T'));
   if(!indices.length)throw Error('Open-Meteo has no hourly data for that date; forecast requests cover up to 16 days ahead.');
   const chosen=indices.reduce((best,x)=>Math.abs(Number(x.t.slice(11,13))-hour)<Math.abs(Number(best.t.slice(11,13))-hour)?x:best);
   const val=key=>data.hourly[key]&&data.hourly[key][chosen.i]!==undefined?data.hourly[key][chosen.i]:null;
   w={temperatureC:val('temperature_2m'),relativeHumidityPct:val('relative_humidity_2m'),precipitationMm:val('precipitation'),windSpeedKmh:val('wind_speed_10m')};
   matched=chosen.t;
  }
  const fetched=Number(data.fetchedAt||Date.now()/1000);
  out.innerHTML='<b>Weather source:</b> '+esc(backend?(data.source||'Open-Meteo via UFI backend'):'Open-Meteo direct')+' · matched '+esc(matched)+' UTC<br>Temperature: '+esc(w.temperatureC??'unknown')+' °C · Humidity: '+esc(w.relativeHumidityPct??'unknown')+'% · Precipitation: '+esc(w.precipitationMm??'unknown')+' mm · Wind: '+esc(w.windSpeedKmh??'unknown')+' km/h<br><span class="muted">Fetched '+new Date(fetched*1000).toISOString()+'. Grid-cell estimate, not a stadium sensor. Verify coordinates and kickoff time.</span>';
 }catch(e){out.innerHTML='<div class="notice warning">'+esc(e.message)+'</div>'}
}
let autoOddsTimer=null,autoOddsSnapshots=[];
async function pollProviderOdds(){
 const status=$('lmsAutoStatus');
 try{
  const base=$('lmsAutoBase').value.trim().replace(/[/]+$/,'');
  const fixture=($('lmsAutoFixture').value.trim()||(($('esiProviderFixtureId')&&$('esiProviderFixtureId').value)||'').trim()),bookmaker=$('lmsAutoBookmaker').value.trim(),market=$('lmsAutoMarket').value.trim();
  if(fixture&&!$('lmsAutoFixture').value.trim())$('lmsAutoFixture').value=fixture;
  if(!base||!base.toLowerCase().startsWith('https://'))throw Error('Enter the deployed UFI HTTPS backend URL.');
  if(!/^[0-9]+$/.test(fixture)||!/^[0-9]+$/.test(bookmaker)||!/^[0-9]+$/.test(market))throw Error('Fixture, bookmaker and market IDs must be numeric.');
  const url=base+'/api/inplay-odds?'+new URLSearchParams({id:fixture,bookmaker,market});
  const response=await fetch(url,{headers:{Accept:'application/json'}});
  const payload=await response.json();
  if(!response.ok||payload.error)throw Error(payload.error||('In-play odds HTTP '+response.status));
  const root=payload.data||{},rows=Array.isArray(root.data)?root.data:(Array.isArray(payload.data)?payload.data:[]);
  const label=r=>String(r.label||r.name||'').trim().toLowerCase();
  const pick=names=>rows.find(r=>names.includes(label(r)));
  const home=pick(['home','1']),draw=pick(['draw','x']),away=pick(['away','2']);
  if(!home||!draw||!away)throw Error('Provider returned no complete Home/Draw/Away trio for this bookmaker/market. Verify market ID, bookmaker ID and plan access.');
  const sourceUpdatedAt=[home,draw,away].map(r=>r.latest_bookmaker_update||r.updated_at||'').filter(Boolean).sort().slice(-1)[0]||'';
  const snap={timestamp:new Date(Number(payload.fetchedAt||Date.now()/1000)*1000).toISOString(),sourceUpdatedAt,home:Number(home.value),draw:Number(draw.value),away:Number(away.value),source:'Sportmonks',fixtureId:fixture,bookmakerId:bookmaker,marketId:market};
  if([snap.home,snap.draw,snap.away].some(v=>!Number.isFinite(v)||v<=1))throw Error('Provider returned invalid decimal odds.');
  autoOddsSnapshots.push(snap);autoOddsSnapshots=autoOddsSnapshots.slice(-20);
  $('lmsOddsSnapshots').value=JSON.stringify(autoOddsSnapshots,null,2);
  status.innerHTML='Polling every 5 seconds · '+esc(payload.source||'Sportmonks')+' · latest fetch '+esc(snap.timestamp)+' · source update '+esc(sourceUpdatedAt||'not supplied')+' · '+autoOddsSnapshots.length+' snapshots captured.';
  if(autoOddsSnapshots.length>=2)runMarket();
 }catch(e){status.innerHTML='<span class="warning-text">'+esc(e.message)+'</span>';if(/token|HTTP 4|HTTP 5|plan|entitlement/i.test(e.message)){if(autoOddsTimer){clearInterval(autoOddsTimer);autoOddsTimer=null}}}
}
function startAutoOdds(){
 if(autoOddsTimer)clearInterval(autoOddsTimer);
 autoOddsSnapshots=[];
 $('lmsOddsSnapshots').value='[]';
 pollProviderOdds();
 autoOddsTimer=setInterval(pollProviderOdds,5000);
 $('lmsAutoStatus').textContent='Starting provider odds polling…';
}
function stopAutoOdds(){
 if(autoOddsTimer)clearInterval(autoOddsTimer);
 autoOddsTimer=null;
 $('lmsAutoStatus').textContent='Automatic odds polling stopped.';
}
function syncLiveScore(payload){
 try{
  const fixtureId=String(($('lmsAutoFixture').value||($('esiProviderFixtureId')&&$('esiProviderFixtureId').value)||'')).trim();
  if(!fixtureId)return;
  const root=payload&&payload.data,rows=Array.isArray(root)?root:(Array.isArray(root&&root.data)?root.data:(Array.isArray(root&&root.data&&root.data.data)?root.data.data:[]));
  const f=rows.find(x=>String(x.id??x.fixture_id??x.fixtureId??'')===fixtureId);if(!f)return;
  let h=null,a=null;
  const direct=f.score;
  if(direct&&typeof direct==='object'){
   const dh=direct.home??direct.homeScore??direct.home_score,da=direct.away??direct.awayScore??direct.away_score;
   if(dh!=null&&da!=null&&Number.isInteger(Number(dh))&&Number.isInteger(Number(da))){h=Number(dh);a=Number(da);}
  }
  if((h===null||a===null)&&f.home_score!=null&&f.away_score!=null&&Number.isInteger(Number(f.home_score))&&Number.isInteger(Number(f.away_score))){h=Number(f.home_score);a=Number(f.away_score);}
  if(h===null||a===null){
   const scores=Array.isArray(f.scores)?f.scores:[],current=scores.filter(s=>String(s.description||'').toUpperCase()==='CURRENT');
   for(const s of current){
    const side=String(s.score&&s.score.participant||s.participant&&s.participant.meta&&s.participant.meta.location||s.location||'').toLowerCase();
    const goals=Number(s.score&&s.score.goals!==undefined?s.score.goals:s.goals);
    if(!Number.isInteger(goals)||goals<0)continue;
    if(side==='home')h=goals;if(side==='away')a=goals;
   }
  }
  if(h===null||a===null)return;
  $('lmsScoreH').value=String(h);$('lmsScoreA').value=String(a);
  const minute=Number((f.state&&f.state.minute) ?? (f.status&&f.status.clock) ?? f.minute ?? f.elapsed);
  if(Number.isFinite(minute)&&minute>=0)$('lmsMinute').value=String(minute);
  const status=$('lmsAutoStatus');if(status)status.innerHTML+=' · score synced from live feed: '+h+'–'+a+(Number.isFinite(minute)?' at '+minute+'′':'');
 }catch(_){/* Keep unknown score unknown if provider schema is incomplete. */}
}
if(typeof window!=='undefined'&&window.addEventListener)window.addEventListener('ufi:live-feed',event=>syncLiveScore(event.detail));
document.addEventListener('DOMContentLoaded',()=>{
 $('lmsRun').addEventListener('click',runMarket);
 $('lmsBacktestRun').addEventListener('click',runBacktest);
 $('lmsWeatherRun').addEventListener('click',runWeather);
 $('lmsAutoStart').addEventListener('click',startAutoOdds);
 $('lmsAutoStop').addEventListener('click',stopAutoOdds);
});
})();
