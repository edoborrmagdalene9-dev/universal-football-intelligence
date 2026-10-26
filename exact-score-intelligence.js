/* UFI Exact-Score Intelligence — additive research module.
   Transparent Poisson scenario grid, forecast snapshots and evidence-first post-mortems.
   This is not a calibrated live model or betting recommendation. */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const KEY = 'ufi_exact_score_intelligence_v1';
const clamp = (x,a,b) => Math.max(a,Math.min(b,x));
const num = id => Number($(id)?.value);
const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = x => (100*x).toFixed(2)+'%';
const stamp = () => new Date().toISOString();
let ledger = [];
try { const saved=JSON.parse(localStorage.getItem(KEY)||'[]'); if(Array.isArray(saved)) ledger=saved; } catch (_) {}
function save(){try{localStorage.setItem(KEY,JSON.stringify(ledger));}catch(e){status('Storage unavailable. Export your records before leaving this page.',true)}}
function status(msg,bad=false){const el=$('esiStatus');if(el){el.textContent=msg;el.className='notice '+(bad?'warning':'good')}}
function factorial(n){let v=1;for(let i=2;i<=n;i++)v*=i;return v}
function pois(k,lambda){return Math.exp(-lambda)*Math.pow(lambda,k)/factorial(k)}
function grid(h,a,cap=7){
 h=clamp(h,0.05,6);a=clamp(a,0.05,6);
 const rows=[];let mass=0;
 for(let i=0;i<=cap;i++)for(let j=0;j<=cap;j++){const p=pois(i,h)*pois(j,a);rows.push({home:i,away:j,p});mass+=p}
 rows.sort((x,y)=>y.p-x.p);
 return {rows,mass,tail:Math.max(0,1-mass),h,a};
}
function renderGrid(){
 const home=($('esiHome').value||'Home').trim(), away=($('esiAway').value||'Away').trim();
 const h=num('esiLambdaHome'), a=num('esiLambdaAway'), odds=num('esiOdds'), k=clamp(Math.floor(num('esiTopK')||5),1,12);
 if(!Number.isFinite(h)||!Number.isFinite(a)||h<=0||a<=0)return status('Enter positive expected-goal rates for both teams.',true);
 const g=grid(h,a), top=g.rows.slice(0,k), shortlist=top.reduce((s,x)=>s+x.p,0);
 const H=g.rows.filter(x=>x.home>x.away).reduce((s,x)=>s+x.p,0),D=g.rows.filter(x=>x.home===x.away).reduce((s,x)=>s+x.p,0),A=g.rows.filter(x=>x.home<x.away).reduce((s,x)=>s+x.p,0);
 const exact=top[0];
 $('esiSummary').innerHTML='<div class="outcome-grid"><div><span>Home win</span><b>'+pct(H)+'</b></div><div><span>Draw</span><b>'+pct(D)+'</b></div><div><span>Away win</span><b>'+pct(A)+'</b></div><div><span>Top '+k+' scores combined</span><b>'+pct(shortlist)+'</b></div></div><p><b>Highest individual scoreline in this baseline:</b> '+exact.home+'–'+exact.away+' at '+pct(exact.p)+'. This is not a strong prediction by itself.</p><p class="muted">Score-grid mass shown: '+pct(g.mass)+' · Tail beyond 0–'+7+' goals: '+pct(g.tail)+'. Independent Poisson baseline; no lineup, live-event, tactical or market calibration is implied.</p>';
 $('esiGrid').innerHTML='<table><thead><tr><th>Rank</th><th>Scoreline</th><th>Probability</th><th>Fair odds (1/p)</th></tr></thead><tbody>'+top.map((r,i)=>'<tr><td>'+(i+1)+'</td><td><b>'+r.home+'–'+r.away+'</b></td><td>'+pct(r.p)+'</td><td>'+(r.p>0?(1/r.p).toFixed(2):'—')+'</td></tr>').join('')+'</tbody></table>';
 if(Number.isFinite(odds)&&odds>1){const raw=1/odds;$('esiOddsCheck').innerHTML='<p>Odds '+odds.toFixed(2)+' imply a raw break-even probability of <b>'+pct(raw)+'</b> before bookmaker margin. Compare this only with a validated probability for the exact same score and market; this simple tool cannot establish value.</p>'}else $('esiOddsCheck').textContent='Enter decimal odds above 1 to see the raw break-even probability.';
 status('Scenario recalculated. Baseline only; do not interpret as a validated edge.');
}
function recordForecast(){
 const h=num('esiLambdaHome'),a=num('esiLambdaAway');
 if(!(h>0&&a>0))return status('Calculate a scenario with positive goal rates first.',true);
 const g=grid(h,a), top=g.rows.slice(0,5);
 ledger.unshift({id:'ESI-'+Date.now(),type:'forecast',createdAt:stamp(),match:($('esiHome').value||'Home')+' vs '+($('esiAway').value||'Away'),kickoff: $('esiKickoff').value||null,homeLambda:h,awayLambda:a,top5:top.map(x=>({score:x.home+'-'+x.away,probability:Number(x.p.toFixed(8))})),odds:num('esiOdds')>1?num('esiOdds'):null,model:'independent Poisson baseline; cap 7; not calibrated',notes:$('esiForecastNotes').value||'',source:$('esiForecastSource').value||''});
 save();renderLedger();status('Timestamped forecast snapshot saved locally. It will not be overwritten by post-match results.');
}
function recordPostmortem(){
 const match=$('esiPostMatch').value.trim();
 if(!match)return status('Enter the fixture name for the post-match audit.',true);
 const item={id:'PM-'+Date.now(),type:'postmortem',createdAt:stamp(),match,finalScore:$('esiFinal').value.trim(),selectedScore:$('esiSelected').value.trim(),minuteScore:$('esiLiveState').value.trim(),timeline:$('esiTimeline').value.trim(),shotsXg:$('esiShotsXg').value.trim(),lineupsCards:$('esiLineupsCards').value.trim(),reason:$('esiReason').value,source:$('esiPostSource').value.trim(),lesson:$('esiLesson').value.trim()};
 ledger.unshift(item);save();renderLedger();status('Post-match audit saved. The cause remains a hypothesis unless the source evidence supports it.');
}
function renderLedger(){
 const host=$('esiLedger');if(!host)return;
 if(!ledger.length){host.innerHTML='<p class="muted">No forecast snapshots or post-match audits saved yet.</p>';return}
 host.innerHTML='<table><thead><tr><th>Type</th><th>Match</th><th>Saved</th><th>Record</th></tr></thead><tbody>'+ledger.slice(0,100).map((x,i)=>'<tr><td>'+esc(x.type)+'</td><td>'+esc(x.match)+'</td><td>'+esc(x.createdAt)+'</td><td>'+(x.type==='forecast'?esc((x.top5||[]).map(z=>z.score+' '+pct(z.probability)).join(' · ')):'Selected '+esc(x.selectedScore||'unknown')+'; final '+esc(x.finalScore||'unknown')+'; reason '+esc(x.reason||'unknown'))+'</td></tr>').join('')+'</tbody></table><p class="muted">Showing up to 100 most recent records. Saved only in this browser until exported.</p>';
}
function download(name,data,type){const url=URL.createObjectURL(new Blob([data],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url)}
$('esiCalculate')?.addEventListener('click',renderGrid);
$('esiSaveForecast')?.addEventListener('click',recordForecast);
$('esiSavePostmortem')?.addEventListener('click',recordPostmortem);
$('esiExport')?.addEventListener('click',()=>download('ufi-exact-score-ledger.json',JSON.stringify(ledger,null,2),'application/json'));
$('esiExportCsv')?.addEventListener('click',()=>{const rows=[['type','createdAt','match','kickoff','homeLambda','awayLambda','top5','odds','selectedScore','finalScore','minuteScore','reason','source','notes','lesson']];ledger.forEach(x=>rows.push([x.type,x.createdAt,x.match,x.kickoff||'',x.homeLambda??'',x.awayLambda??'',JSON.stringify(x.top5||[]),x.odds??'',x.selectedScore||'',x.finalScore||'',x.minuteScore||'',x.reason||'',x.source||x.sourceUrl||'',x.notes||'',x.lesson||'']));const csv=rows.map(r=>r.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');download('ufi-exact-score-ledger.csv',csv,'text/csv')});
$('esiClear')?.addEventListener('click',()=>{if(!confirm('Delete the local exact-score ledger? Export a backup first if needed.'))return;ledger=[];save();renderLedger();status('Local exact-score ledger cleared.')});
renderLedger();

/* Optional secret-safe live provider proxy. The browser never receives the provider token. */
const API_KEY = 'ufi_exact_score_api_base_v1';
let feedTimer = null;
const DEFAULT_API_BASE = 'https://universal-football-intelligence.onrender.com';
const feedBase = () => String($('esiApiBase')?.value || DEFAULT_API_BASE).trim().replace(/\\/+$/, '');
function feedStatus(msg,bad=false){const el=$('esiFeedStatus');if(el){el.textContent=msg;el.className='notice '+(bad?'warning':'good')}}
function safeBase(){
 const base=feedBase();
 try { const u=new URL(base); if(u.protocol!=='https:' && u.hostname!=='localhost' && u.hostname!=='127.0.0.1') throw new Error(); return u.origin=== 'null' ? '' : base; }
 catch(_){feedStatus('Enter a valid HTTPS backend URL (localhost is allowed for local testing).',true);return ''}
}
async function fetchFeed(path){
 const base=safeBase(); if(!base) throw new Error('Backend URL is missing or invalid.');
 const response=await fetch(base+path,{headers:{Accept:'application/json'},cache:'no-store'});
 if(!response.ok) throw new Error('Backend returned HTTP '+response.status);
 const body=await response.json(); if(body && body.ok===false) throw new Error(body.error||'Provider error');
 return body;
}
function unwrapRows(payload){
 const root=payload?.data;
 if(Array.isArray(root)) return root;
 if(Array.isArray(root?.data)) return root.data;
 if(Array.isArray(root?.data?.data)) return root.data.data;
 return [];
}
function getTeamNames(f){
 const participants=f?.participants||[];
 const names=participants.map(p=>p?.name||p?.participant?.name||p?.meta?.location).filter(Boolean);
 return {home:names[0]||f?.home_team||f?.name||'Home',away:names[1]||f?.away_team||'Away'};
}
function renderFeed(payload,label){
 const rows=unwrapRows(payload);
 const host=$('esiFeedOutput'); if(!host)return;
 if(!rows.length){host.innerHTML='<p class="muted">No fixture rows returned. Check provider coverage, date and subscription. Raw response metadata: '+esc(JSON.stringify({source:payload?.source,fetchedAt:payload?.fetchedAt,cacheHit:payload?.cacheHit}).slice(0,500))+'</p>';return}
 host.innerHTML='<p class="muted">Source: '+esc(payload?.source||'provider')+' · fetched '+esc(payload?.fetchedAt?new Date(payload.fetchedAt*1000).toISOString():'time unavailable')+' · '+esc(label)+' · '+rows.length+' row(s). Click a row to copy its team names into the scenario.</p><table><thead><tr><th>Fixture</th><th>Status</th><th>Score</th><th>Fixture ID</th></tr></thead><tbody>'+rows.slice(0,100).map(f=>{const n=getTeamNames(f);const id=f?.id??f?.fixture_id??'';const status=f?.state?.name||f?.state?.short_name||f?.status||'Unknown';const scores=Array.isArray(f?.scores)?f.scores.map(s=>s?.score?.goals??s?.score??'').filter(x=>x!=='').join(' - '):((f?.home_score??'?')+' - '+(f?.away_score??'?'));return '<tr><td><button class="button small esiFixturePick" data-home="'+esc(n.home)+'" data-away="'+esc(n.away)+'" data-id="'+esc(id)+'">'+esc(n.home+' vs '+n.away)+'</button></td><td>'+esc(status)+'</td><td>'+esc(scores)+'</td><td>'+esc(id)+'</td></tr>'}).join('')+'</tbody></table><details><summary>Inspect source response</summary><pre>'+esc(JSON.stringify(payload,null,2).slice(0,20000))+'</pre></details>';
 host.querySelectorAll('.esiFixturePick').forEach(b=>b.addEventListener('click',()=>{$('esiHome').value=b.dataset.home;$('esiAway').value=b.dataset.away;if($('esiProviderFixtureId'))$('esiProviderFixtureId').value=b.dataset.id||'';feedStatus('Fixture selected. Team names are populated; goal rates are NOT inferred from this feed yet. Load historical results and validate a model before using probabilities.');}));
}
async function loadLive(){
 try{const data=await fetchFeed('/api/live');renderFeed(data,'live matches');if(typeof window!=='undefined'&&typeof CustomEvent!=='undefined')window.dispatchEvent(new CustomEvent('ufi:live-feed',{detail:data}));feedStatus('Live feed refreshed. Scores/events are sourced data; exact-score live probabilities remain unavailable until the conditional model is validated.');}
 catch(e){feedStatus('Live feed unavailable: '+e.message,true)}
}
async function loadDateFixtures(){
 try{const d=$('esiFeedDate')?.value||new Date().toISOString().slice(0,10);const data=await fetchFeed('/api/fixtures?date='+encodeURIComponent(d));renderFeed(data,'fixtures on '+d);feedStatus('Fixture list loaded. Missing provider fields remain unknown.');}
 catch(e){feedStatus('Fixture list unavailable: '+e.message,true)}
}
async function loadFixtureDetails(){
 const id=String($('esiProviderFixtureId')?.value||'').trim();if(!/^\\d+$/.test(id))return feedStatus('Choose a fixture row or enter a numeric provider fixture ID.',true);
 try{const data=await fetchFeed('/api/fixture?id='+encodeURIComponent(id));const host=$('esiFeedOutput');if(host)host.innerHTML='<p class="muted">Detailed provider response · '+esc(data?.source||'provider')+' · '+esc(data?.fetchedAt?new Date(data.fetchedAt*1000).toISOString():'timestamp unavailable')+'</p><pre>'+esc(JSON.stringify(data,null,2).slice(0,30000))+'</pre>';feedStatus('Fixture detail loaded. Check source timestamps and missing fields; no model probability is claimed from raw events alone.');}
 catch(e){feedStatus('Fixture details unavailable: '+e.message,true)}
}
$('esiConnectFeed')?.addEventListener('click',()=>{const base=safeBase();if(!base)return;try{localStorage.setItem(API_KEY,base)}catch(_){}if(feedTimer)clearInterval(feedTimer);loadLive();feedTimer=setInterval(loadLive,10000);});
$('esiLoadFixtures')?.addEventListener('click',loadDateFixtures);
$('esiLoadFixtureDetails')?.addEventListener('click',loadFixtureDetails);
$('esiStopFeed')?.addEventListener('click',()=>{if(feedTimer)clearInterval(feedTimer);feedTimer=null;feedStatus('Automatic refresh stopped.')});
try{const savedBase=localStorage.getItem(API_KEY);if($('esiApiBase'))$('esiApiBase').value=savedBase||DEFAULT_API_BASE;}catch(_){if($('esiApiBase'))$('esiApiBase').value=DEFAULT_API_BASE;}
if($('esiFeedDate'))$('esiFeedDate').value=new Date().toISOString().slice(0,10);

})();
