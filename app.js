(() => {
'use strict';
const BASE='https://raw.githubusercontent.com/statsbomb/open-data/master/data/';
const $=id=>document.getElementById(id);
const STORE='ufi_workspace_v2';
const S={competitions:[],matches:[],liveFixtures:[],events:[],lineups:[],lineupsMatchId:null,selectedMatch:null,scenario:null,manualSelections:[],activity:[],players:[],subs:[],contexts:[],notes:[],backtests:[],slips:[],playerEventMatches:[],riskAudits:[],lastRiskAudit:null,lastSlip:null};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const now=()=>new Date().toISOString();
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove('show'),2800)}
function notice(id,msg,type=''){const e=$(id);if(e){e.className='notice'+(type?' '+type:'');e.textContent=msg}}
function go(view){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id==='view-'+view));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===view));window.scrollTo({top:0,behavior:'smooth'})}
document.querySelectorAll('.nav-item').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.go)));
function addActivity(msg){S.activity.unshift({msg,date:now()});S.activity=S.activity.slice(0,12);renderActivity()}
function persist(){const data={players:S.players,subs:S.subs,contexts:S.contexts,notes:S.notes,backtests:S.backtests,slips:S.slips,playerEventMatches:S.playerEventMatches,riskAudits:S.riskAudits,activity:S.activity};try{localStorage.setItem(STORE,JSON.stringify(data));return true}catch(e){toast('Browser storage is full; export workspace and remove old records.');return false}}
function restore(){try{const d=JSON.parse(localStorage.getItem(STORE)||'{}');for(const k of ['players','subs','contexts','notes','backtests','slips','playerEventMatches','riskAudits','activity'])if(Array.isArray(d[k]))S[k]=d[k]}catch(e){console.warn('Workspace restore failed',e)}renderAllSaved()}
function fmtDate(x){if(!x)return 'date unknown';const d=new Date(x);return Number.isNaN(+d)?String(x):d.toLocaleDateString()}
async function json(url){const r=await fetch(url);if(!r.ok)throw Error('HTTP '+r.status+' '+url.split('/').slice(-2).join('/'));return r.json()}
function pct(n){return (100*n).toFixed(2)+'%'}
function download(name,content,type='text/plain'){const u=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=u;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1000)}
function csv(rows){return rows.map(r=>r.map(x=>{const s=String(x??'');return '"'+s.replace(/"/g,'""')+'"'}).join(',')).join('\r\n')}
function matchName(m){return (m?.home_team?.home_team_name||'Home')+' vs '+(m?.away_team?.away_team_name||'Away')}
function chosenMatch(){return S.matches[Number($('matchSelect').value)]||null}
function competitionRows(){const names=[...new Set(S.competitions.map(c=>c.competition_name+'||'+c.competition_id))];$('competitionSelect').innerHTML='<option value="">Choose competition</option>'+names.map(x=>{const [name,id]=x.split('||');return '<option value="'+esc(id)+'">'+esc(name)+'</option>'}).join('');$('countCompetitions').textContent=S.competitions.length}
$('loadCompetitions').addEventListener('click',async e=>{const b=e.currentTarget;b.disabled=true;b.textContent='Connecting…';notice('dataStatus','Fetching public competition index…');try{S.competitions=await json(BASE+'competitions.json');competitionRows();$('netState').textContent='Source reachable';$('sourceHealth').textContent='Connected. '+S.competitions.length+' competition-season records are available from the public source.';notice('dataStatus','Loaded '+S.competitions.length+' competition-season entries. Choose a competition and season.','good');addActivity('Loaded StatsBomb competition index');toast('Competition data loaded.')}catch(err){notice('dataStatus','Could not load data: '+err.message+'. Check internet and try again.','error');$('sourceHealth').textContent='Source unavailable: '+err.message;$('netState').textContent='Offline / error'}finally{b.disabled=false;b.textContent='Connect & load competitions'}});
$('competitionSelect').addEventListener('change',()=>{const id=String($('competitionSelect').value);const rows=S.competitions.filter(c=>String(c.competition_id)===id);$('seasonSelect').innerHTML='<option value="">Choose season</option>'+rows.map(c=>'<option value="'+esc(c.season_id)+'">'+esc(c.season_name)+' · '+esc(c.season_id)+'</option>').join('');$('matchSelect').innerHTML='<option value="">Load matches first</option>';S.matches=[]});
$('loadMatches').addEventListener('click',async()=>{const cid=$('competitionSelect').value,sid=$('seasonSelect').value;if(!cid||!sid)return notice('dataStatus','Choose both competition and season first.','warning');notice('dataStatus','Loading match list…');try{S.matches=await json(BASE+'matches/'+cid+'/'+sid+'.json');S.matches.sort((a,b)=>String(b.match_date||'').localeCompare(String(a.match_date||'')));$('matchSelect').innerHTML='<option value="">Choose match</option>'+S.matches.map((m,i)=>'<option value="'+i+'">'+esc(m.match_date||'')+' · '+esc(matchName(m))+'</option>').join('');$('countMatches').textContent=S.matches.length;notice('dataStatus','Loaded '+S.matches.length+' matches. Select one and load its evidence.','good');addActivity('Loaded '+S.matches.length+' matches for '+$('competitionSelect').selectedOptions[0].textContent)}catch(err){notice('dataStatus','Match list could not be loaded: '+err.message,'error')}});
$('matchSelect').addEventListener('change',()=>{const m=chosenMatch();S.selectedMatch=m;if(!m)return;const summary=matchName(m)+' · '+(m.match_date||'date unknown')+' · match ID '+m.match_id;$('selectedSummary').textContent=summary;$('matchLabHeader').textContent=summary;const teams=[m.home_team?.home_team_name,m.away_team?.away_team_name].filter(Boolean);$('teamFocus').innerHTML='<option value="both">Both teams</option>'+teams.map(t=>'<option>'+esc(t)+'</option>').join('');});
$('loadSelectedMatch').addEventListener('click',async()=>{const m=chosenMatch();if(!m)return notice('dataStatus','Select a match first.','warning');notice('dataStatus','Fetching event data for '+matchName(m)+'…');try{S.selectedMatch=m;S.events=await json(BASE+'events/'+m.match_id+'.json');const shots=S.events.filter(e=>e.type?.name==='Shot');const xg=shots.reduce((a,e)=>a+(Number(e.shot?.statsbomb_xg)||0),0);$('countEvents').textContent=S.events.length;$('countShots').textContent=shots.length;$('countXg').textContent='Summed source xG: '+xg.toFixed(2);$('selectedSummary').textContent=matchName(m)+' · '+(m.match_date||'date unknown')+' · '+S.events.length+' events · '+shots.length+' shots · xG '+xg.toFixed(2);$('matchLabHeader').textContent=matchName(m)+' · '+(m.match_date||'date unknown');renderEvents();renderTactical();drawPitch();notice('dataStatus','Event data loaded. '+S.events.length+' events; '+shots.length+' shots. xG is summed only where supplied.','good');addActivity('Loaded event data for '+matchName(m));go('matchlab')}catch(err){notice('dataStatus','Event data unavailable for this match: '+err.message,'error')}});
$('loadSelectedLineups').addEventListener('click',async()=>{const m=chosenMatch();if(!m)return notice('dataStatus','Select a match first.','warning');try{S.lineups=await json(BASE+'lineups/'+m.match_id+'.json');S.lineupsMatchId=String(m.match_id);$('lineupResults').innerHTML=S.lineups.map(t=>'<h3>'+esc(t.team_name||'Team')+'</h3><table><thead><tr><th>Player</th><th>Position / role from source</th><th>Starter info</th></tr></thead><tbody>'+((t.lineup||[]).map(p=>'<tr><td>'+esc(p.player_name)+'</td><td>'+esc((p.positions||[]).map(z=>z.position).join(', ')||'Not specified')+'</td><td>'+esc((p.positions||[]).map(z=>z.start_reason||'').filter(Boolean).join(', ')||'Source does not label this clearly')+'</td></tr>').join('')||'<tr><td colspan="3">No lineup rows</td></tr>')+'</tbody></table>').join('');notice('dataStatus','Lineups loaded where available. Verify source structure and status.','good');addActivity('Loaded lineup data for '+matchName(m))}catch(err){notice('dataStatus','Lineups are unavailable for this match: '+err.message,'warning');$('lineupResults').innerHTML='<p class="muted">The source has no accessible lineup file for this match.</p>'}});
function eventTeam(e){return e.team?.name||''}function eventPlayer(e){return e.player?.name||''}function loc(e){return Array.isArray(e.location)?e.location:null}
function filteredEvents(){const team=$('teamFocus').value,filter=$('eventFilter').value,search=$('eventSearch').value.trim().toLowerCase();return S.events.filter(e=>(filter==='all'||e.type?.name===filter)&&(team==='both'||eventTeam(e)===team)&&(!search||(eventTeam(e)+' '+eventPlayer(e)+' '+(e.type?.name||'')).toLowerCase().includes(search)))}
function renderEvents(){const counts={};S.events.forEach(e=>counts[e.type?.name||'Unknown']=(counts[e.type?.name||'Unknown']||0)+1);$('eventTypes').innerHTML='<table><thead><tr><th>Event type</th><th>Count</th><th>Share</th></tr></thead><tbody>'+Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([k,v])=>'<tr><td>'+esc(k)+'</td><td>'+v+'</td><td>'+pct(v/(S.events.length||1))+'</td></tr>').join('')+'</tbody></table>';renderExplorer()}
function renderExplorer(){const es=filteredEvents();$('eventExplorer').innerHTML=es.length?'<table><thead><tr><th>Period</th><th>Minute</th><th>Team</th><th>Player</th><th>Event</th><th>Outcome / detail</th><th>Location</th><th>xG</th></tr></thead><tbody>'+es.slice(0,700).map(e=>{const l=loc(e);const detail=e.shot?.outcome?.name||e.pass?.outcome?.name||e.duel?.outcome?.name||e.interception?.outcome?.name||e.substitution?.replacement?.name||'';return '<tr><td>'+esc(e.period||'')+'</td><td>'+esc(e.minute??'')+':'+String(e.second??0).padStart(2,'0')+'</td><td>'+esc(eventTeam(e))+'</td><td>'+esc(eventPlayer(e))+'</td><td>'+esc(e.type?.name||'')+'</td><td>'+esc(detail)+'</td><td>'+esc(l?l.map(n=>Number(n).toFixed(1)).join(', '):'—')+'</td><td>'+ (Number.isFinite(e.shot?.statsbomb_xg)?e.shot.statsbomb_xg.toFixed(3):'—')+'</td></tr>'}).join('')+'</tbody></table><p class="muted">Showing '+Math.min(es.length,700)+' of '+es.length+' filtered events.</p>':'<p class="muted">No events match these filters.</p>';drawPitch();renderTactical()}
function renderTactical(){const es=filteredEvents(),shots=es.filter(e=>e.type?.name==='Shot'),passes=es.filter(e=>e.type?.name==='Pass'),goals=shots.filter(e=>e.shot?.outcome?.name==='Goal');$('tacticalStats').innerHTML=[['Events',es.length],['Shots',shots.length],['Goals',goals.length],['Passes',passes.length]].map(([k,v])=>'<article class="metric"><span>'+k+'</span><strong>'+v+'</strong></article>').join('')}
function drawPitch(){const c=$('pitchCanvas');if(!c)return;const ctx=c.getContext('2d'),w=c.width,h=c.height;ctx.clearRect(0,0,w,h);ctx.fillStyle='#17452e';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#a8d0ac';ctx.lineWidth=2;ctx.strokeRect(20,20,w-40,h-40);ctx.beginPath();ctx.moveTo(w/2,20);ctx.lineTo(w/2,h-20);ctx.stroke();ctx.beginPath();ctx.arc(w/2,h/2,54,0,Math.PI*2);ctx.stroke();ctx.strokeRect(20,h/2-95,105,190);ctx.strokeRect(w-125,h/2-95,105,190);ctx.strokeRect(20,h/2-47,45,94);ctx.strokeRect(w-65,h/2-47,45,94);const es=filteredEvents().filter(e=>loc(e));const max=Math.min(es.length,700);for(let i=0;i<max;i++){const e=es[i],l=loc(e);let x=20+(Math.max(0,Math.min(120,Number(l[0])))/120)*(w-40),y=20+(Math.max(0,Math.min(80,Number(l[1])))/80)*(h-40);ctx.beginPath();ctx.arc(x,y,e.type?.name==='Shot'?5:2.5,0,Math.PI*2);ctx.fillStyle=e.type?.name==='Shot'?(e.shot?.outcome?.name==='Goal'?'#ffe28c':'#ff8f8f'):(eventTeam(e)===(S.selectedMatch?.home_team?.home_team_name)?'#83f3ac':'#9cc7ff');ctx.fill()}$('pitchLegend').textContent='Plotted '+max+' located events. Source coordinates are normalized to the StatsBomb 120×80 pitch. Green/blue indicate teams; shots are red and goals gold.'}
['teamFocus','eventFilter','eventSearch'].forEach(id=>$(id).addEventListener('input',()=>{renderExplorer()}));
$('exportMatchData').addEventListener('click',()=>{if(!S.selectedMatch)return toast('Load a match first.');download('ufi-match-'+S.selectedMatch.match_id+'.json',JSON.stringify({match:S.selectedMatch,events:S.events,lineups:S.lineups},null,2),'application/json')});
$('exportFilteredEvents').addEventListener('click',()=>{const es=filteredEvents();download('ufi-events.csv',csv([['period','minute','second','team','player','event','outcome','x','y','xg'],...es.map(e=>{const l=loc(e)||[];return [e.period,e.minute,e.second,eventTeam(e),eventPlayer(e),e.type?.name,e.shot?.outcome?.name||e.pass?.outcome?.name,l[0],l[1],e.shot?.statsbomb_xg]})]),'text/csv')});
$('saveTeamContext').addEventListener('click',()=>{const team=$('ctxTeam').value.trim(),evidence=$('ctxEvidence').value.trim();if(!team||!evidence)return toast('Enter a team and context/evidence.');S.contexts.unshift({id:crypto.randomUUID(),team,formation:$('ctxFormation').value.trim(),evidence,date:now()});persist();renderContexts();addActivity('Saved user-supplied team context for '+team);$('ctxTeam').value='';$('ctxFormation').value='';$('ctxEvidence').value='';toast('Team context saved as user-supplied evidence.')});
function renderContexts(){$('teamContextList').innerHTML=S.contexts.length?'<table><thead><tr><th>Team</th><th>Shape</th><th>Context / evidence</th><th>Recorded</th><th></th></tr></thead><tbody>'+S.contexts.map(x=>'<tr><td>'+esc(x.team)+'</td><td>'+esc(x.formation||'Unknown')+'</td><td>'+esc(x.evidence)+'</td><td>'+fmtDate(x.date)+'</td><td><button class="button danger small" data-del-context="'+x.id+'">Delete</button></td></tr>').join('')+'</tbody></table>':'<p class="muted">No team context saved.</p>'}
$('teamContextList').addEventListener('click',e=>{const b=e.target.closest('[data-del-context]');if(!b)return;S.contexts=S.contexts.filter(x=>x.id!==b.dataset.delContext);persist();renderContexts()});
function clearPlayerForm(){['playerId','playerName','playerTeam','playerPosition','playerStyles','playerSource','playerNotes'].forEach(id=>$(id).value='');$('playerFoot').value='Unknown';$('playerWeakFoot').value='Unknown';$('playerConfidence').value='Medium'}
$('newPlayer').onclick=()=>{clearPlayerForm();go('players');$('playerName').focus()};
$('clearPlayer').onclick=clearPlayerForm;
$('savePlayer').onclick=()=>{const name=$('playerName').value.trim();if(!name)return notice('playerStatus','Enter a player name first.','warning');const id=$('playerId').value||crypto.randomUUID(),old=S.players.findIndex(p=>p.id===id);const p={id,name,team:$('playerTeam').value.trim(),position:$('playerPosition').value.trim(),foot:$('playerFoot').value,weakFoot:$('playerWeakFoot').value,styles:$('playerStyles').value.trim(),source:$('playerSource').value.trim(),confidence:$('playerConfidence').value,notes:$('playerNotes').value.trim(),updated:now()};if(old>=0)S.players[old]=p;else S.players.unshift(p);persist();renderPlayers();notice('playerStatus','Saved. Check source and confidence before treating this as a verified fact.','good');addActivity('Saved player evidence profile: '+name);clearPlayerForm()};

function buildPlayerEventProfile(){
 const match=S.selectedMatch;
 if(!match||!S.events.length){notice('playerEventProfileStatus','Load a match and its event data in Real match data first. No profile was generated.','warning');return;}
 const map=new Map(), substitutionTimeline=new Map();
 const matchEnd=Math.max(0,...S.events.map(e=>Number(e.minute)).filter(Number.isFinite));
 const ensure=(name,team)=>{if(!name)return null;const key=team+'||'+name;if(!map.has(key))map.set(key,{player:name,team,match_id:String(match.match_id),match_date:match.match_date||'',competition_id:match.competition?.competition_id??'',events:0,shots:0,goals:0,source_xg:0,xg_events:0,passes:0,completed_passes:0,carries:0,pressures:0,duels:0,interceptions:0,ball_recoveries:0,clearances:0,blocks:0,assists:0,key_passes:0,substitution_events:0,first_minute:null,last_minute:null,lineup_status:'not loaded',positions:'',appearance_status:'unknown',minutes_estimate:null,minutes_method:'unavailable',exposure_confidence:'insufficient evidence',evidence_scope:'single loaded match'});return map.get(key)};
 for(const e of S.events){
  const p=ensure(eventPlayer(e),eventTeam(e));if(!p)continue;
  p.events++;const minute=Number(e.minute);if(Number.isFinite(minute)){p.first_minute=p.first_minute===null?minute:Math.min(p.first_minute,minute);p.last_minute=p.last_minute===null?minute:Math.max(p.last_minute,minute)}
  const type=e.type?.name||'';
  if(type==='Shot'){p.shots++;if(e.shot?.outcome?.name==='Goal')p.goals++;if(Number.isFinite(e.shot?.statsbomb_xg)){p.source_xg+=e.shot.statsbomb_xg;p.xg_events++}if(e.shot?.key_pass_id)p.key_passes++}
  if(type==='Pass'){p.passes++;if(!e.pass?.outcome?.name)p.completed_passes++;if(e.pass?.goal_assist)p.assists++;if(e.pass?.shot_assist)p.key_passes++}
  if(type==='Carry')p.carries++;
  if(type==='Pressure')p.pressures++;
  if(type==='Duel')p.duels++;
  if(type==='Interception')p.interceptions++;
  if(type==='Ball Recovery')p.ball_recoveries++;
  if(type==='Clearance')p.clearances++;
  if(type==='Block')p.blocks++;
  if(type==='Substitution'){
   p.substitution_events++;
   const minute=Number(e.minute), incoming=e.substitution?.replacement?.name;
   if(Number.isFinite(minute)){const outKey=eventTeam(e)+'||'+eventPlayer(e);if(!substitutionTimeline.has(outKey))substitutionTimeline.set(outKey,{});substitutionTimeline.get(outKey).offMinute=minute;
    if(incoming){const inKey=eventTeam(e)+'||'+incoming;if(!substitutionTimeline.has(inKey))substitutionTimeline.set(inKey,{});substitutionTimeline.get(inKey).onMinute=minute;}}
  }
 }
 const lineupPlayers=new Map();
 for(const t of S.lineups||[])for(const lp of t.lineup||[]){
  const team=t.team_name||'', key=team+'||'+(lp.player_name||'');
  lineupPlayers.set(key,lp);
  ensure(lp.player_name,team);
 }
 for(const p of map.values()){
  const lp=lineupPlayers.get(p.team+'||'+p.player), timeline=substitutionTimeline.get(p.team+'||'+p.player)||{};
  if(lp){
   p.lineup_status='listed in loaded lineup';
   p.positions=(lp.positions||[]).map(z=>z.position||'').filter(Boolean).join('; ');
   const starts=(lp.positions||[]).some(z=>/starting\s*(xi|lineup)/i.test(z.start_reason||''));
   const explicitStart=(lp.positions||[]).some(z=>z.start_reason!=null&&String(z.start_reason).trim()!=='');
   if(starts){
    p.appearance_status='starter';
    const endMinute=Number.isFinite(timeline.offMinute)?timeline.offMinute:matchEnd;
    p.minutes_estimate=Math.max(0,endMinute);
    p.minutes_method=Number.isFinite(timeline.offMinute)?'starter to recorded substitution minute':'starter to last recorded match minute';
    p.exposure_confidence=Number.isFinite(timeline.offMinute)?'approximate; substitution recorded':'approximate; no substitution recorded';
   } else if(Number.isFinite(timeline.onMinute)){
    p.appearance_status='substitute appeared';
    p.minutes_estimate=Math.max(0,matchEnd-timeline.onMinute);
    p.minutes_method='recorded substitution minute to last recorded match minute';
    p.exposure_confidence='approximate; clock-minute difference';
   } else if(explicitStart){
    p.appearance_status='listed; appearance not evidenced';
   } else {
    p.appearance_status='lineup listed; starter status unclear';
   }
  } else if(Number.isFinite(timeline.onMinute)){
   p.appearance_status='substitute appeared';
   p.minutes_estimate=Math.max(0,matchEnd-timeline.onMinute);
   p.minutes_method='recorded substitution minute to last recorded match minute';
   p.exposure_confidence='approximate; lineup file missing';
  }
 }
 const rows=[...map.values()].sort((x,y)=>x.team.localeCompare(y.team)||x.player.localeCompare(y.player));
 S.playerEventProfile={match_id:String(match.match_id),match_date:match.match_date||'',match_name:matchName(match),built_at:now(),rows};
 $('playerEventProfileTable').innerHTML=rows.length?'<table><thead><tr><th>Player / team</th><th>Appearance / lineup</th><th>Estimated minutes*</th><th>Events</th><th>Shots</th><th>Goals</th><th>Source xG</th><th>Passes / completed</th><th>Carries</th><th>Pressures</th><th>Duels</th><th>Other actions</th><th>Observed minute range*</th></tr></thead><tbody>'+rows.map(p=>'<tr><td>'+esc(p.player)+'<br><span class="muted">'+esc(p.team)+'</span></td><td>'+esc(p.appearance_status)+' · '+esc(p.lineup_status)+(p.positions?' · '+esc(p.positions):'')+'</td><td>'+(p.minutes_estimate===null?'Unknown':p.minutes_estimate.toFixed(1))+'</td><td>'+p.events+'</td><td>'+p.shots+'</td><td>'+p.goals+'</td><td>'+(p.xg_events?p.source_xg.toFixed(3)+' ('+p.xg_events+' shots)':'Not supplied')+'</td><td>'+p.passes+' / '+p.completed_passes+'</td><td>'+p.carries+'</td><td>'+p.pressures+'</td><td>'+p.duels+'</td><td>I '+p.interceptions+' · R '+p.ball_recoveries+' · C '+p.clearances+' · B '+p.blocks+'</td><td>'+(p.first_minute===null?'—':p.first_minute+'–'+p.last_minute)+'</td></tr>').join('')+'</tbody></table><p class="muted">*Minutes are rough estimates from lineup start reasons, recorded substitution times and the last event minute; stoppage-time/period-clock details and red cards may make them inaccurate. Never treat these as verified minutes or calculate per-90 rates from them. First/last event times are not minutes played. Pass completion uses absence of a pass outcome as the event-data convention; coverage varies by competition and season.</p>':'<p class="muted">No player-attributed events found in the loaded match.</p>';
 notice('playerEventProfileStatus','Built '+rows.length+' player profiles from '+S.events.length+' loaded events for '+matchName(match)+'. Evidence scope: one match; no footedness or universal style inference.','good');
 addActivity('Built event-based player evidence for '+matchName(match));
 renderPlayerEventAggregate();
}
$('buildPlayerEventProfile').addEventListener('click',buildPlayerEventProfile);

function savePlayerEventMatch(){
 if(!S.playerEventProfile?.rows?.length){buildPlayerEventProfile();if(!S.playerEventProfile?.rows?.length)return;}
 const profile=S.playerEventProfile, matchId=String(profile.match_id);
 const existing=new Set(S.playerEventMatches.filter(r=>String(r.match_id)===matchId).map(r=>r.team+'||'+r.player));
 const fresh=profile.rows.filter(r=>!existing.has(r.team+'||'+r.player)).map(r=>({...r,source_name:'StatsBomb Open Data',source_url:'https://github.com/statsbomb/open-data',saved_at:now()}));
 if(!fresh.length){notice('playerEventAggregateStatus','This match and its player rows are already saved. No duplicate rows added.','warning');return;}
 S.playerEventMatches.push(...fresh);persist();renderPlayerEventAggregate();
 notice('playerEventAggregateStatus','Saved '+fresh.length+' player rows from '+profile.match_name+'. Load another match and repeat; same match/player/team rows are deduplicated.','good');
 addActivity('Saved '+fresh.length+' player-match evidence rows from '+profile.match_name);toast('Match profiles added to evidence dataset.');
}
function renderPlayerEventAggregate(){
 const rows=S.playerEventMatches||[], map=new Map();
 for(const r of rows){const key=(r.team||'')+'||'+(r.player||'');if(!map.has(key))map.set(key,{player:r.player,team:r.team,matches:new Set(),events:0,shots:0,goals:0,source_xg:0,xg_events:0,passes:0,completed_passes:0,carries:0,pressures:0,duels:0,interceptions:0,ball_recoveries:0,clearances:0,blocks:0,estimated_minutes:0,minutes_estimate_rows:0,appearances:0,first_date:'',last_date:'',match_ids:new Set()});
 const x=map.get(key);x.matches.add(String(r.match_id));x.match_ids.add(String(r.match_id));for(const k of ['events','shots','goals','source_xg','xg_events','passes','completed_passes','carries','pressures','duels','interceptions','ball_recoveries','clearances','blocks'])x[k]+=(Number(r[k])||0);if(r.minutes_estimate!==null&&r.minutes_estimate!==''&&Number.isFinite(Number(r.minutes_estimate))){x.estimated_minutes+=Number(r.minutes_estimate);x.minutes_estimate_rows++}if(['starter','substitute appeared'].includes(r.appearance_status))x.appearances++;
 const date=String(r.match_date||'');if(date&&(!x.first_date||date<x.first_date))x.first_date=date;if(date&&(!x.last_date||date>x.last_date))x.last_date=date;
 }
 const agg=[...map.values()].sort((x,y)=>y.matches.size-x.matches.size||x.player.localeCompare(y.player));
 $('playerEventAggregateTable').innerHTML=agg.length?'<table><thead><tr><th>Player / team</th><th>Matches</th><th>Appeared*</th><th>Est. minutes*</th><th>Events</th><th>Shots</th><th>Goals</th><th>Source xG</th><th>Passes / complete</th><th>Carries</th><th>Pressures</th><th>Duels</th><th>Defensive actions</th><th>Date window</th></tr></thead><tbody>'+agg.map(x=>'<tr><td>'+esc(x.player)+'<br><span class="muted">'+esc(x.team)+'</span></td><td>'+x.matches.size+'</td><td>'+x.appearances+'</td><td>'+(x.minutes_estimate_rows?x.estimated_minutes.toFixed(1)+' (approx.)':'Unknown')+'</td><td>'+x.events+'</td><td>'+x.shots+'</td><td>'+x.goals+'</td><td>'+(x.xg_events?x.source_xg.toFixed(3)+' ('+x.xg_events+' shots)':'Not supplied')+'</td><td>'+x.passes+' / '+x.completed_passes+'</td><td>'+x.carries+'</td><td>'+x.pressures+'</td><td>'+x.duels+'</td><td>I '+x.interceptions+' · R '+x.ball_recoveries+' · C '+x.clearances+' · B '+x.blocks+'</td><td>'+esc(x.first_date||'unknown')+' – '+esc(x.last_date||'unknown')+'</td></tr>').join('')+'</tbody></table><p class="muted">'+rows.length+' saved player-match rows · '+agg.length+' player/team aggregates. Event counts are totals, not per-90 rates. Appeared count and minute totals are approximate and only populated where lineup/substitution evidence supports an estimate; red cards and detailed match-clock corrections are not applied. Team changes and player identity across clubs need review.</p>':'<p class="muted">No saved match profiles yet. Load a StatsBomb match, build its player profile, then save it here. Repeat across matches to grow the evidence dataset.</p>';
}
$('savePlayerEventMatch').addEventListener('click',savePlayerEventMatch);
$('exportPlayerEventMatches').addEventListener('click',()=>{if(!S.playerEventMatches.length)return toast('Save at least one match profile first.');const fields=['match_id','match_date','player','team','lineup_status','positions','appearance_status','minutes_estimate','minutes_method','exposure_confidence','events','shots','goals','source_xg','xg_events','passes','completed_passes','carries','pressures','duels','interceptions','ball_recoveries','clearances','blocks','assists','key_passes','substitution_events','first_minute','last_minute','evidence_scope','source_name','source_url','saved_at'];download('ufi-multi-match-player-evidence.csv',csv([fields,...S.playerEventMatches.map(p=>fields.map(k=>p[k]??''))]),'text/csv')});
$('exportPlayerEventProfile').addEventListener('click',()=>{
 const profile=S.playerEventProfile;
 if(!profile?.rows?.length)return toast('Build a player event profile first.');
 const fields=['match_id','match_date','player','team','lineup_status','positions','appearance_status','minutes_estimate','minutes_method','exposure_confidence','events','shots','goals','source_xg','xg_events','passes','completed_passes','carries','pressures','duels','interceptions','ball_recoveries','clearances','blocks','assists','key_passes','substitution_events','first_minute','last_minute','evidence_scope'];
 download('ufi-player-event-profile-'+profile.match_id+'.csv',csv([fields,...profile.rows.map(p=>fields.map(k=>p[k]??''))]),'text/csv');
});

function renderPlayers(){const q=($('playerSearch')?.value||'').toLowerCase();const ps=S.players.filter(p=>(p.name+' '+p.team+' '+p.position+' '+p.styles).toLowerCase().includes(q));$('playerTable').innerHTML=ps.length?'<table><thead><tr><th>Player</th><th>Club / role</th><th>Foot</th><th>Weak-foot evidence</th><th>Style tags</th><th>Confidence</th><th>Source</th><th></th></tr></thead><tbody>'+ps.map(p=>'<tr><td>'+esc(p.name)+'</td><td>'+esc(p.team)+'<br>'+esc(p.position)+'</td><td>'+esc(p.foot)+'</td><td>'+esc(p.weakFoot)+'</td><td>'+esc(p.styles||'Not entered')+'</td><td>'+esc(p.confidence)+'</td><td>'+(p.source?'<a href="'+esc(p.source)+'" target="_blank" rel="noopener">Open source ↗</a>':'Not supplied')+'</td><td><button class="button small" data-edit-player="'+p.id+'">Edit</button> <button class="button danger small" data-delete-player="'+p.id+'">Delete</button></td></tr>').join('')+'</tbody></table>':'<p class="muted">No matching player profiles. Add one, or change your search.</p>'}
$('playerSearch').addEventListener('input',renderPlayers);
$('playerTable').addEventListener('click',e=>{const edit=e.target.closest('[data-edit-player]'),del=e.target.closest('[data-delete-player]');if(edit){const p=S.players.find(x=>x.id===edit.dataset.editPlayer);if(!p)return;const map={playerId:'id',playerName:'name',playerTeam:'team',playerPosition:'position',playerFoot:'foot',playerWeakFoot:'weakFoot',playerStyles:'styles',playerSource:'source',playerConfidence:'confidence',playerNotes:'notes'};Object.entries(map).forEach(([el,k])=>$(el).value=p[k]||'');go('players');window.scrollTo({top:0,behavior:'smooth'})}if(del){S.players=S.players.filter(x=>x.id!==del.dataset.deletePlayer);persist();renderPlayers();toast('Player profile deleted.')}});
$('saveSub').onclick=()=>{const who=$('subIn').value.trim();if(!who)return toast('Enter the substitute player name.');S.subs.unshift({id:crypto.randomUUID(),match:$('subMatch').value.trim(),inPlayer:who,outPlayer:$('subOut').value.trim(),minute:$('subMinute').value,impact:$('subImpact').value.trim(),date:now()});persist();renderSubs();addActivity('Saved substitution observation for '+who);['subMatch','subIn','subOut','subMinute','subImpact'].forEach(id=>$(id).value='');toast('Substitution observation saved.')};
function renderSubs(){$('subList').innerHTML=S.subs.length?'<table><thead><tr><th>Match</th><th>Minute</th><th>Entering</th><th>Leaving</th><th>Observation</th><th></th></tr></thead><tbody>'+S.subs.map(x=>'<tr><td>'+esc(x.match||'Unknown')+'</td><td>'+esc(x.minute||'—')+'</td><td>'+esc(x.inPlayer)+'</td><td>'+esc(x.outPlayer||'—')+'</td><td>'+esc(x.impact||'No impact note')+'</td><td><button class="button danger small" data-del-sub="'+x.id+'">Delete</button></td></tr>').join('')+'</tbody></table>':'<p class="muted">No substitution observations saved.</p>'}
$('subList').addEventListener('click',e=>{const b=e.target.closest('[data-del-sub]');if(!b)return;S.subs=S.subs.filter(x=>x.id!==b.dataset.delSub);persist();renderSubs()});
function poisson(l,k){let p=Math.exp(-l);for(let i=1;i<=k;i++)p*=l/i;return p}
function scenarioCalc(){const h=Number($('lambdaHome').value),a=Number($('lambdaAway').value),cap=Number($('scoreCap').value);if(!Number.isFinite(h)||!Number.isFinite(a)||h<0||a<0||h>12||a>12){notice('scenarioStatus','Expected goals must be between 0 and 12.','warning');return null}let grid=[],mass=0,hw=0,d=0,aw=0,over15=0,over25=0,over35=0,btts=0;for(let i=0;i<=cap;i++)for(let j=0;j<=cap;j++){const p=poisson(h,i)*poisson(a,j);grid.push({h:i,a:j,p});mass+=p;if(i>j)hw+=p;else if(i===j)d+=p;else aw+=p;if(i+j>1)over15+=p;if(i+j>2)over25+=p;if(i+j>3)over35+=p;if(i>0&&j>0)btts+=p}grid.sort((x,y)=>y.p-x.p);const norm=x=>x/mass;const out={home:$('scenarioHomeName').value.trim()||'Home',away:$('scenarioAwayName').value.trim()||'Away',matchId:String(chosenMatch()?.match_id??''),lambdaHome:h,lambdaAway:a,cap,mass,homeWin:norm(hw),draw:norm(d),awayWin:norm(aw),over15:norm(over15),over25:norm(over25),over35:norm(over35),btts:norm(btts),grid,top:grid[0],label:$('scenarioLabel').value.trim(),caveats:$('scenarioCaveats').value.trim(),checks:['checkLineup','checkVenue','checkRecent','checkOpponent','checkMarket','checkUncertainty'].filter(id=>$(id).checked)};S.scenario=out;return out}
$('runScenario').onclick=()=>{const s=scenarioCalc();if(!s)return;[['probHome',s.homeWin],['probDraw',s.draw],['probAway',s.awayWin],['probOver15',s.over15],['probOver25',s.over25],['probOver35',s.over35],['probBtts',s.btts]].forEach(([id,v])=>$(id).textContent=pct(v));$('probTopScore').textContent=s.top.h+'–'+s.top.a;$('scoreGrid').innerHTML='<table><thead><tr><th>Score</th><th>Probability (normalized grid)</th><th>Visual</th></tr></thead><tbody>'+s.grid.slice(0,35).map(x=>'<tr><td>'+esc(s.home)+' '+x.h+'–'+x.a+' '+esc(s.away)+'</td><td>'+pct(x.p/s.mass)+'</td><td><div style="height:7px;background:#243b2b;border-radius:6px;min-width:90px;overflow:hidden"><div style="height:100%;width:'+Math.max(1,x.p/s.grid[0].p*100)+'%;background:#83f3ac"></div></div></td></tr>').join('')+'</tbody></table>';$('scenarioStatus').textContent='Grid mass represented: '+pct(s.mass)+'. Tail omitted by cap: '+pct(Math.max(0,1-s.mass))+'. Probabilities normalized within grid; baseline assumes independent Poisson goals and does not incorporate all tactical/game-state effects.';addActivity('Calculated scenario for '+s.home+' vs '+s.away);toast('Scenario grid calculated.')};
$('saveForecast').onclick=()=>{const s=S.scenario||scenarioCalc();if(!s)return;$('btMatch').value=s.home+' vs '+s.away;$('btMethod').value='Independent Poisson baseline'+(s.label?' / '+s.label:'');$('btHome').value=(100*s.homeWin).toFixed(2);$('btDraw').value=(100*s.draw).toFixed(2);$('btAway').value=(100*s.awayWin).toFixed(2);$('btNotes').value='λ home='+s.lambdaHome+', away='+s.lambdaAway+'; cap='+s.cap+'; grid mass='+(100*s.mass).toFixed(2)+'%; caveats: '+s.caveats+'; checks completed: '+s.checks.join(', ');go('backtest');toast('Forecast copied to ledger form. Select actual result when known.')};
function normalizeTeamName(value){
 return String(value||'').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(fc|cf|sc|afc|club|football|soccer)\b/g,' ').replace(/[^a-z0-9]+/g,' ').trim().replace(/\s+/g,' ');
}
function parseFixtureText(value){
 const text=String(value||'').replace(/\s+/g,' ').trim();
 const m=text.match(/(.+?)\s+(?:vs?\.?|versus)\s+(.+?)(?=\s+(?:\||[-–—])\s+|$)/i);
 if(!m)return null;
 return {homeText:m[1].trim(),awayText:m[2].trim()};
}
function resolveSlipFixture(row){
 const raw=String(row.rawLine||row.label||'');
 if(!parseFixtureText(raw))return {status:'needs-opponent',matchId:'',matchDate:'',homeTeam:'',awayTeam:'',reason:'No explicit “Team A vs Team B” fixture found. Do not infer the opponent from a single team name.'};
 const whole=' '+normalizeTeamName(raw)+' ';
 const live=(S.liveFixtures||[]).filter(m=>{
  const h=normalizeTeamName(m.homeTeam),a=normalizeTeamName(m.awayTeam);
  return h&&a&&whole.includes(' '+h+' ')&&whole.includes(' '+a+' ');
 });
 const candidates=live.map(m=>({source:m.source||'live-fixture-feed',match_id:m.id||m.matchId,match_date:m.date,home_team:{home_team_name:m.homeTeam},away_team:{away_team_name:m.awayTeam},competition:m.competition,status:m.status,markets:m.markets||[],oddsTimestamp:m.oddsTimestamp||null}));
 const historical=(S.matches||[]).filter(m=>{
  const h=normalizeTeamName(m.home_team?.home_team_name),a=normalizeTeamName(m.away_team?.away_team_name);
  return h&&a&&whole.includes(' '+h+' ')&&whole.includes(' '+a+' ');
 }).map(m=>({...m,__source:'historical-statsbomb'}));
 const all=candidates.length?candidates:historical;
 if(all.length===1){
  const m=all[0],parsed=parseFixtureText(raw),h=normalizeTeamName(m.home_team?.home_team_name);
  const orientation=normalizeTeamName(parsed.homeText).includes(h)?'home-away':(normalizeTeamName(parsed.awayText).includes(h)?'away-home':'verify-orientation');
  return {status:'candidate-found',matchId:String(m.match_id??''),matchDate:String(m.match_date||''),homeTeam:m.home_team?.home_team_name||'',awayTeam:m.away_team?.away_team_name||'',orientation,source:m.source||m.__source||'loaded-fixture-list',competition:m.competition?.name||m.competition||'',fixtureStatus:m.status||'',reason:m.source==='live-fixture-feed'?'Matched to a current/upcoming public fixture feed. Confirm competition, kickoff, exact SportyBet market and odds.':'Matched to a historical StatsBomb fixture only; this does NOT verify a current/upcoming match.'};
 }
 if(all.length>1)return {status:'ambiguous',matchId:'',matchDate:'',homeTeam:'',awayTeam:'',reason:'Multiple fixtures match these team names. Add the date/competition and resolve manually.'};
 return {status:(S.liveFixtures.length||S.matches.length)?'not-found-in-loaded-list':'no-fixtures-loaded',matchId:'',matchDate:'',homeTeam:'',awayTeam:'',reason:(S.liveFixtures.length||S.matches.length)?'No matching fixture found in the current feed or loaded historical list.':'Load current fixtures before fixture matching.'};
}
function runSlipFixtureMatching(){
 const rows=S.manualSelections.map(row=>{const fixtureResolution=resolveSlipFixture(row);const sameFixture=String(row.fixtureResolution?.matchId||'')===String(fixtureResolution.matchId||'')&&row.fixtureResolution?.status===fixtureResolution.status;return {...row,fixtureResolution,marketEstimate:sameFixture?row.marketEstimate:null};});
 S.manualSelections=rows;
 renderManualSelections();
 const counts={};rows.forEach(r=>{const k=r.fixtureResolution.status;counts[k]=(counts[k]||0)+1});
 const labels={'candidate-found':'Candidate found','needs-opponent':'Opponent missing','ambiguous':'Ambiguous','not-found-in-loaded-list':'Not found in loaded list','no-fixtures-loaded':'No fixtures loaded'};
 $('fixtureMatchOutput').innerHTML='<p><b>Fixture matching audit</b></p><p>Rows checked: '+rows.length+' · '+Object.entries(counts).map(([k,v])=>esc(labels[k]||k)+': '+v).join(' · ')+'</p>'+(rows.length?'<div class="table-wrap"><table><thead><tr><th>Selection</th><th>Status</th><th>Candidate fixture</th><th>Date</th><th>Orientation</th><th>Reason / next action</th></tr></thead><tbody>'+rows.map(r=>{const f=r.fixtureResolution;return '<tr><td>'+esc(r.label)+'</td><td>'+esc(labels[f.status]||f.status)+'</td><td>'+esc(f.homeTeam&&f.awayTeam?f.homeTeam+' vs '+f.awayTeam:'—')+'</td><td>'+esc(f.matchDate||'—')+'</td><td>'+esc(f.orientation||'—')+'</td><td>'+esc(f.reason)+'</td></tr>'}).join('')+'</tbody></table></div>':'<p>No selections to match. Analyze a slip first.</p>')+'<p class="amber">A candidate is not a verified bookmaker fixture mapping. The loaded StatsBomb list covers selected competitions/seasons only; competition, exact date, kickoff and market settlement rules still need human confirmation.</p>';
 addActivity('Ran fixture candidate matching for '+rows.length+' slip selections');
}
function estimateSlipMarket(row,scenario){
 const text=String(row.rawLine||row.label||'').toLowerCase();
 const normalized=normalizeTeamName(text);
 const fixture=row.fixtureResolution;
 if(!fixture||fixture.status!=='candidate-found')return {status:'blocked',reason:'Resolve a unique fixture candidate first.'};
 if(fixture.source==='live-fixture-feed')return {status:'blocked',reason:'The historical StatsBomb scenario cannot be reused for a current fixture. A current-match model/data source is required.'};
 if(!scenario.matchId||String(scenario.matchId)!==String(fixture.matchId))return {status:'blocked',reason:'Scenario fixture ID does not match this exact fixture. Recalculate the scenario for the matched fixture.'};
 const same=(x,y)=>normalizeTeamName(x)===normalizeTeamName(y);
 if(!(same(fixture.homeTeam,scenario.home)&&same(fixture.awayTeam,scenario.away)))return {status:'blocked',reason:'Scenario home/away teams must match the candidate fixture in the same orientation. Set the scenario teams exactly as listed and rerun it.'};
 const odds=Number(row.odd);
 if(!Number.isFinite(odds)||odds<=1)return {status:'blocked',reason:'Valid decimal odds are required before comparing prices.'};
 const m=text.match(/\b(over|under)\s*(1\.5|2\.5|3\.5)\b/);
 let p=null,market='';
 if(/\bbtts\b|both teams to score|both teams score/.test(text)){p=scenario.btts;market='Both teams to score — YES';}
 else if(m){const line=Number(m[2]),over=scenario.grid.reduce((sum,g)=>sum+((g.h+g.a>line)?g.p:0),0)/scenario.mass;p=m[1]==='over'?over:1-over;market=(m[1]==='over'?'Over ':'Under ')+line+' goals';}
 else if(/\b(home win|home to win|home team to win|match result home|\b1x2\b)/.test(text)||normalized.includes(normalizeTeamName(scenario.home)+' win')||normalized.includes(normalizeTeamName(scenario.home)+' to win')){p=scenario.homeWin;market='Home win';}
 else if(/\b(draw|tie)\b/.test(text)){p=scenario.draw;market='Draw';}
 else if(/\b(away win|away to win|away team to win|match result away)\b/.test(text)||normalized.includes(normalizeTeamName(scenario.away)+' win')||normalized.includes(normalizeTeamName(scenario.away)+' to win')){p=scenario.awayWin;market='Away win';}
 else if(/\b1x\b|home or draw/.test(text)){p=scenario.homeWin+scenario.draw;market='Home or draw';}
 else if(/\bx2\b|draw or away/.test(text)){p=scenario.draw+scenario.awayWin;market='Draw or away';}
 else if(/\b12\b|home or away|no draw/.test(text)){p=scenario.homeWin+scenario.awayWin;market='Home or away';}
 else return {status:'unsupported',reason:'Market/selection wording is not specific enough for a safe probability mapping.'};
 p=Math.max(0,Math.min(1,p));
 return {status:'estimated',market,probability:p,implied:1/odds,ev:p*odds-1,scenarioLabel:scenario.label||'Independent Poisson baseline',reason:'Research estimate from the current independent-Poisson score grid only; verify selection, fixture and market settlement.'};
}
function runSlipMarketBridge(){
 const scenario=S.scenario;
 if(!scenario){notice('marketBridgeOutput','Calculate a scoreline scenario first. No market estimates were produced.','warning');return;}
 const rows=S.manualSelections.map(row=>({...row,marketEstimate:estimateSlipMarket(row,scenario)}));
 S.manualSelections=rows;renderManualSelections();
 const estimated=rows.filter(r=>r.marketEstimate.status==='estimated').length;
 $('marketBridgeOutput').innerHTML='<p><b>Scenario-to-market comparison</b></p><p>Scenario: '+esc(scenario.home)+' vs '+esc(scenario.away)+' · λ '+scenario.lambdaHome.toFixed(2)+' / '+scenario.lambdaAway.toFixed(2)+' · mapped estimates: '+estimated+'/'+rows.length+'</p>'+(rows.length?'<div class="table-wrap"><table><thead><tr><th>Selection</th><th>Market mapping</th><th>Model estimate</th><th>Odds-implied</th><th>Estimated EV</th><th>Status / caveat</th></tr></thead><tbody>'+rows.map(r=>{const e=r.marketEstimate||{},f=r.fixtureResolution||{};return '<tr><td>'+esc(r.label)+'</td><td>'+esc(e.market||'—')+'</td><td>'+(e.probability==null?'—':pct(e.probability))+'</td><td>'+(e.implied==null?'—':pct(e.implied))+'</td><td>'+(e.ev==null?'—':(e.ev*100).toFixed(1)+'%')+'</td><td>'+esc(e.reason||'Not evaluated')+' Fixture: '+esc(f.status||'not matched')+'</td></tr>'}).join('')+'</tbody></table></div>':'<p>Analyze a slip first.</p>')+'<p class="amber">These are experimental model comparisons, not betting recommendations. Only explicit, supported markets are mapped. A positive estimated EV is not evidence of a real edge until probabilities are calibrated out of sample and the exact bookmaker market is verified. This simple Poisson model assumes independent team goals and does not model bet correlations.</p>';
 addActivity('Compared '+rows.length+' slip selections against current scenario; '+estimated+' mapped');
}
function classifySlipMarket(line){
  const s=line.toLowerCase();
  if(/both teams to score|both teams score|\bbtts\b/.test(s))return 'Both teams to score';
  if(/double chance|\b1x\b|\bx2\b|\b12\b/.test(s))return 'Double chance';
  if(/over\s*\d|under\s*\d|total goals|goals over|goals under/.test(s))return 'Goals total';
  if(/\bcorner|corners\b/.test(s))return 'Corners';
  if(/\byellow cards?\b|\bred cards?\b|cards over|cards under/.test(s))return 'Cards';
  if(/\b(draw|home win|away win|to win|win in 90|match result|1x2)\b/.test(s))return 'Match result (1X2)';
  if(/\b(half time|first half|second half|ht|2nd half)\b/.test(s))return 'Half-time / period';
  if(/\b(handicap|asian handicap)\b/.test(s))return 'Handicap';
  if(/\b(player|shots on target|to score anytime|anytime goalscorer)\b/.test(s))return 'Player market';
  return 'Unclassified — verify';
}
function parseSlipLine(line,index){
  const tokens=[...line.matchAll(/(?<![\w.])(\d{1,3}\.\d{1,4})(?!\d)/g)];
  const valid=tokens.filter(m=>{const n=Number(m[1]);return n>1&&n<=1000});
  const last=valid[valid.length-1];
  const endsWithOdd=!!last&&line.trim().endsWith(last[1]);
  const odd=last?Number(last[1]):null;
  let confidence='low',warning='No confident decimal odds found; enter the odds manually.';
  if(last){
    confidence=(valid.length===1&&endsWithOdd)?'high':'medium';
    warning=valid.length>1?'Multiple decimal numbers found (possibly a goal line plus odds). Verify the final number is the selection price.':'Verify that the extracted price belongs to this selection.';
  }
  const label=last?line.replace(last[0],' ').replace(/\b(?:odds?|price)\s*[:=@]?\s*/ig,' ').replace(/\s+/g,' ').trim():line.trim();
  const market=classifySlipMarket(line);
  const fixtureMatch=line.match(/(.+?)\s+(?:vs?\.?|versus)\s+(.+?)(?=\s+(?:\||[-–—])\s+|$)/i);
  return {id:'ocr-'+index,label:label||line.trim(),odd,p:odd?1/odd:null,estimate:null,group:fixtureMatch?(fixtureMatch[1].trim()+' vs '+fixtureMatch[2].trim()):'',marketType:market,confidence,warning,rawLine:line.trim(),source:'OCR/text'};
}
$('analyzeSlip').onclick=()=>{
  const lines=$('slipInput').value.split(/\n/).map(x=>x.trim()).filter(Boolean);
  const rows=[];
  for(const line of lines){
    if(/^---\s*PHOTO\b/i.test(line)||/^page\s+\d+\s*$/i.test(line))continue;
    const parsed=parseSlipLine(line,rows.length);
    // Avoid treating headings or long OCR fragments with no price as selections.
    if(parsed.odd!==null||line.toLowerCase().includes('odds')||line.toLowerCase().includes('price')||parsed.marketType!=='Unclassified — verify'||parseFixtureText(line))rows.push(parsed);
  }
  S.manualSelections=rows.map(x=>({...x}));
  renderManualSelections();
  const valid=rows.filter(x=>x.odd!==null);
  const combined=valid.reduce((a,x)=>a*x.odd,1),stake=Math.max(0,Number($('slipStake').value)||0);
  S.lastSlip={rows,combined:valid.length?combined:null,stake,date:now()};
  const table=rows.length?'<div class="table-wrap"><table><thead><tr><th>Line / selection</th><th>Market guess</th><th>Odds read</th><th>Confidence</th><th>Review note</th></tr></thead><tbody>'+rows.map(x=>'<tr><td>'+esc(x.label)+'</td><td>'+esc(x.marketType)+'</td><td>'+(x.odd===null?'Not read':x.odd.toFixed(2))+'</td><td>'+esc(x.confidence)+'</td><td>'+esc(x.warning)+'</td></tr>').join('')+'</tbody></table></div>':'<p>No clear priced selection lines found. Check OCR text and add one selection per line where possible.';
  $('slipOutput').innerHTML=rows.length?'<p>Parsed '+rows.length+' possible selection line(s); '+valid.length+' have a readable decimal price. Every row still needs human verification.</p><div class="outcome-grid"><div><span>Priced rows</span><b>'+valid.length+'</b></div><div><span>Unpriced rows</span><b>'+(rows.length-valid.length)+'</b></div><div><span>Combined odds of priced rows only</span><b>'+(valid.length?combined.toFixed(2):'—')+'</b></div><div><span>Stake entered</span><b>₦'+stake.toLocaleString()+'</b></div><div><span>Return if all priced rows win</span><b>'+(valid.length?'₦'+(stake*combined).toLocaleString(undefined,{maximumFractionDigits:2}):'—')+'</b></div></div>'+table+'<p class="amber">OCR is not verification. Market labels and fixture names are best-effort text classification, not confirmed bookmaker market IDs. Combined odds and implied chance do not account for correlations, margin or true probabilities. Do not use the rows for modelling until the labels and prices are checked.</p>':'<p>No priced selection lines found. Try clearer screenshots, one selection per line, or paste the text manually.</p>';
  addActivity('Parsed '+rows.length+' slip text lines; '+valid.length+' had readable decimal odds');
  toast('Slip text parsed. Verify every selection and price.');
};
$('slipPhotos').addEventListener('change',e=>{const files=[...(e.target.files||[])];$('slipPhotoPreview').innerHTML=files.length?files.map((f,i)=>'<div>'+esc((i+1)+'. '+f.name)+' · '+Math.round(f.size/1024)+' KB</div>').join(''):'No slip photos selected yet.';notice('ocrStatus',files.length?'Selected '+files.length+' image(s). Run OCR, then carefully verify the extracted text.':'Choose one or more slip images.');});
$('ocrSlipPhotos').onclick=async()=>{const files=[...($('slipPhotos').files||[])];if(!files.length)return notice('ocrStatus','Choose at least one bet-slip photo first.','warning');if(!window.Tesseract)return notice('ocrStatus','OCR engine could not load. Check internet access, then refresh and try again.','error');const button=$('ocrSlipPhotos');button.disabled=true;let output=[];try{for(let i=0;i<files.length;i++){notice('ocrStatus','Reading photo '+(i+1)+' of '+files.length+'…');const result=await Tesseract.recognize(files[i],'eng',{logger:m=>{if(m.status==='recognizing text')notice('ocrStatus','Reading photo '+(i+1)+' of '+files.length+'… '+Math.round((m.progress||0)*100)+'%')}});output.push('--- PHOTO '+(i+1)+': '+files[i].name+' ---\n'+(result.data.text||''));}const extracted=output.join('\n\n');$('slipInput').value=$('slipInput').value.trim()?$('slipInput').value.trim()+'\n\n'+extracted:extracted;notice('ocrStatus','OCR finished for '+files.length+' image(s). Check team names, markets, odds, separators and any cut-off text before clicking Analyze slip. OCR text is a draft, not verified booking data.','good');addActivity('Extracted text from '+files.length+' slip photo(s)');}catch(err){notice('ocrStatus','OCR failed: '+(err?.message||'unknown error')+'. Try clearer screenshots or paste the text manually.','error')}finally{button.disabled=false;}};
$('addManualSelection').onclick=()=>{const label=$('manualSelection').value.trim(),odd=Number($('manualOdds').value),prob=$('manualProb').value===''?null:Number($('manualProb').value)/100;if(!label||!Number.isFinite(odd)||odd<=1)return toast('Enter a selection label and decimal odds above 1.');if(prob!==null&&(prob<0||prob>1))return toast('Independent probability must be 0–100%.');S.manualSelections.push({label,odd,p:1/odd,estimate:prob,group:$('manualGroup').value.trim()});renderManualSelections();['manualSelection','manualOdds','manualProb','manualGroup'].forEach(id=>$(id).value='')};
function renderManualSelections(){
 const rows=S.manualSelections;
 $('manualSelectionTable').innerHTML=rows.length?'<table><thead><tr><th>Selection</th><th>Market guess</th><th>Odds</th><th>Implied</th><th>Own estimate</th><th>Parse confidence</th><th>Correlation group</th><th></th></tr></thead><tbody>'+rows.map((x,i)=>'<tr><td>'+esc(x.label)+'</td><td>'+esc(x.marketType||'Manual')+'</td><td>'+(Number.isFinite(Number(x.odd))&&Number(x.odd)>1?Number(x.odd).toFixed(2):'Needs entry')+'</td><td>'+(Number.isFinite(Number(x.p))&&x.p!==null?pct(x.p):'—')+'</td><td>'+(x.estimate==null?'Not entered':pct(x.estimate))+'</td><td>'+esc(x.confidence||'manual')+(x.warning?'<br>'+esc(x.warning):'')+'</td><td>'+esc(x.group||'Not tagged')+'</td><td><button class="button danger small" data-remove-selection="'+i+'">Remove</button></td></tr>').join('')+'</tbody></table><p class="muted">Selections: '+rows.length+' · rows without verified odds are excluded from combined odds. Same-match selections may be correlated.</p>':'<p class="muted">No selections in current slip.</p>';
}
$('manualSelectionTable').addEventListener('click',e=>{const b=e.target.closest('[data-remove-selection]');if(!b)return;S.manualSelections.splice(Number(b.dataset.removeSelection),1);renderManualSelections()});
$('matchSlipFixtures').onclick=runSlipFixtureMatching;
$('bridgeSlipMarkets').onclick=runSlipMarketBridge;

const LIVE_LEAGUES=[
 ['eng.1','Premier League'],['esp.1','La Liga'],['ger.1','Bundesliga'],['ita.1','Serie A'],['fra.1','Ligue 1'],
 ['ned.1','Eredivisie'],['por.1','Primeira Liga'],['uefa.champions','Champions League'],['uefa.europa','Europa League'],
 ['usa.1','MLS'],['ksa.1','Saudi Pro League'],['tur.1','Turkish Super Lig']
];
async function fetchSportyBetUpcoming(){
 const endpoint='https://www.sportybet.com/api/ng/factsCenter/pcUpcomingEvents?sportId=sr%3Asport%3A1&marketId=1%2C18%2C10%2C29%2C11%2C26%2C36%2C14%2C60100&pageSize=100&pageNum=1&todayGames=false&timeline=168&_t='+Date.now();
 const payload=await json(endpoint);
 if(payload?.bizCode!==10000||!payload?.data)throw Error('SportyBet returned an unexpected response; no verified prices loaded.');
 const rows=[];
 for(const tournament of (payload.data.tournaments||[])){
  for(const ev of (tournament.events||[])){
   const home=ev.homeTeamName||ev.homeTeam?.name,away=ev.awayTeamName||ev.awayTeam?.name;
   if(!home||!away)continue;
   const markets=(ev.markets||[]).map(m=>({id:String(m.id||''),name:String(m.desc||m.name||''),specifier:m.specifier||'',status:m.status||'',outcomes:(m.outcomes||[]).filter(o=>o.isActive!==false).map(o=>({id:String(o.id||''),name:String(o.desc||o.name||''),odds:Number(o.odds),active:o.isActive!==false})).filter(o=>Number.isFinite(o.odds)&&o.odds>1)}));
   rows.push({id:String(ev.eventId||''),matchId:String(ev.eventId||''),date:ev.estimateStartTime?new Date(Number(ev.estimateStartTime)).toISOString():'',homeTeam:home,awayTeam:away,competition:tournament.name||tournament.categoryName||'SportyBet fixture',status:ev.matchStatus||'Scheduled',source:'sportybet-live-api',markets,oddsTimestamp:now()});
  }
 }
 if(!rows.length)throw Error('SportyBet returned no usable football fixtures.');
 return rows;
}
async async function loadLiveFixtures(){
 const button=$('loadLiveFixtures');if(button){button.disabled=true;button.textContent='Loading current fixtures…'}
 notice('liveFixtureOutput','Connecting to SportyBet fixture/market feed first, then using ESPN as a fallback. Browser access to SportyBet may be blocked by CORS.','');
 try{
  let sportyBetRows=[],sportyBetError='';
  try{sportyBetRows=await fetchSportyBetUpcoming();S.sportyBetFixtures=sportyBetRows}catch(e){sportyBetError=String(e?.message||e);S.sportyBetFixtures=[]}
  const nowDate=new Date(),endDate=new Date(nowDate.getTime()+7*86400000);
  const ymd=d=>d.getFullYear()+String(d.getMonth()+1).padStart(2,'0')+String(d.getDate()).padStart(2,'0');
  const dates=ymd(nowDate)+'-'+ymd(endDate);
  const results=await Promise.allSettled(LIVE_LEAGUES.map(async ([league,name])=>{
   const url='https://site.api.espn.com/apis/site/v2/sports/soccer/'+league+'/scoreboard?dates='+dates+'&limit=100';
   const data=await json(url);
   return (data.events||[]).map(ev=>{
    const comp=(ev.competitions||[])[0],teams=comp?.competitors||[];
    const home=teams.find(t=>t.homeAway==='home'),away=teams.find(t=>t.homeAway==='away');
    if(!home||!away)return null;
    return {id:String(ev.id||league+'-'+ev.date),date:ev.date||'',homeTeam:home.team?.displayName||home.team?.name||'',awayTeam:away.team?.displayName||away.team?.name||'',competition:name,status:ev.status?.type?.detail||ev.status?.type?.name||'Scheduled',url:ev.links?.[0]?.href||''};
   }).filter(x=>x&&x.homeTeam&&x.awayTeam);
  }));
  const good=results.filter(x=>x.status==='fulfilled').flatMap(x=>x.value);
  const failed=results.filter(x=>x.status==='rejected').length;
  const uniq=new Map();good.forEach(f=>uniq.set(f.id,f));
  const espnRows=[...uniq.values()];
  const allRows=[...sportyBetRows,...espnRows.filter(e=>!sportyBetRows.some(s=>normalizeTeamName(s.homeTeam)===normalizeTeamName(e.homeTeam)&&normalizeTeamName(s.awayTeam)===normalizeTeamName(e.awayTeam)))];
  S.liveFixtures=allRows.sort((a,b)=>String(a.date).localeCompare(String(b.date)));
  const rows=S.liveFixtures;
  $('liveFixtureOutput').innerHTML='<p><b>Current fixture feed:</b> '+rows.length+' fixtures found. SportyBet source: '+sportyBetRows.length+' fixtures with market prices; ESPN fallback: '+espnRows.length+' fixtures across '+(LIVE_LEAGUES.length-failed)+'/'+LIVE_LEAGUES.length+' league feeds.</p>'+(sportyBetError?'<p class="amber">SportyBet direct feed unavailable in this browser: '+esc(sportyBetError)+'. This may be a CORS/network restriction; do not treat ESPN fixtures as SportyBet odds.</p>':'')+
   (rows.length?'<div class="table-wrap"><table><thead><tr><th>Kickoff (feed timezone)</th><th>Fixture</th><th>Competition</th><th>Status</th></tr></thead><tbody>'+rows.map(f=>'<tr><td>'+esc(f.date?new Date(f.date).toLocaleString():'Not supplied')+'</td><td>'+esc(f.homeTeam+' vs '+f.awayTeam)+'</td><td>'+esc(f.competition)+'</td><td>'+esc(f.status)+'</td></tr>').join('')+'</tbody></table></div>':'<p>No fixtures returned. This may be an API/network limitation; it does not mean no matches are scheduled.</p>')+
   '<p class="amber">SportyBet odds are timestamped source prices, not guaranteed to match the price on your open slip. Market settlement rules, lineups, injuries and calibrated probabilities remain separate checks. ESPN fallback fixtures have no SportyBet prices. Use “Match slip fixtures” again after loading this feed.</p>';
  addActivity('Loaded '+rows.length+' public current/upcoming fixtures; '+failed+' league feeds failed');
  toast('Fixture feed loaded: '+rows.length+' matches');
 }catch(err){notice('liveFixtureOutput','Could not load public fixture feed: '+String(err?.message||err)+'. Check internet access and try again.','error')}
 finally{if(button){button.disabled=false;button.textContent='Load current & upcoming fixtures'}}
}
$('loadLiveFixtures').onclick=loadLiveFixtures;
$('runFullSlipAudit').onclick=async()=>{
 const button=$('runFullSlipAudit');
 if(!S.manualSelections.length){notice('strictAuditOutput','First upload your slip images or paste the extracted selections, click Analyze slip, and correct the teams/markets/odds.','warning');return;}
 button.disabled=true;button.textContent='Running full pipeline…';
 try{
  await loadLiveFixtures();
  runSlipFixtureMatching();
  await runStrictSlipAudit();
  const total=S.manualSelections.length;
  const latest=S.lastRiskAudit;
  const cut=latest?.rows?.filter(x=>x.status==='CUT').length||0;
  const hold=latest?.rows?.filter(x=>x.status==='HOLD — verify').length||0;
  const survivors=latest?.rows?.filter(x=>x.status==='SURVIVOR CANDIDATE').length||0;
  notice('liveFixtureOutput','Full pipeline finished: '+total+' selections checked; '+cut+' hard-stop CUT; '+hold+' HOLD for missing/uncertain evidence; '+survivors+' survivor candidates. Replacement picks are not auto-filled unless a candidate has an independently supported, fixture-specific estimate and odds. Review the per-leg table in the Strict Slip Auditor below.','');
 }catch(err){notice('strictAuditOutput','Full audit stopped safely: '+String(err?.message||err)+'. No bets were automatically placed or removed.','error')}
 finally{button.disabled=false;button.textContent='Run FULL slip audit (all stages)'}
};
const NEWS_BASE='https://api.gdeltproject.org/api/v2/doc/doc';
function riskNewsKeywords(title){
 const s=String(title||'').toLowerCase();
 const rules=[
  ['injury / fitness',/\binjur(?:y|ed|ies)\b|\bhamstring\b|\bmuscle\b|\bknock\b|\bfitness\b|\bfitness test\b|\bmedical\b|\breturn from injury\b/],
  ['availability / suspension',/\bsuspend(?:ed|sion)?\b|\bmiss(?:es|ing)\b|\bruled out\b|\bunavailable\b|\bwill not play\b|\bset to miss\b|\bban\b/],
  ['rotation / rest',/\brotat(?:e|ion|ed)\b|\brest(?:ed|ing)?\b|\bchanges to the lineup\b|\bchanged side\b|\bsecond string\b|\bpriorit(?:y|ise|ize)\b/],
  ['late lineup / uncertainty',/\bdoubt(?:ful)?\b|\bquestionable\b|\blate decision\b|\bstarting xi\b|\blineup\b|\bteam news\b|\bstarting eleven\b/],
  ['fixture congestion / fatigue',/\bfatigue\b|\bcongestion\b|\bthree games in\b|\bshort turnaround\b|\bextra time\b|\btravel\b/],
  ['motivation / context',/\brelegation\b|\btitle race\b|\bmust win\b|\bdead rubber\b|\brotation expected\b|\bcup tie\b/]
 ];
 return rules.filter(x=>x[1].test(s)).map(x=>x[0]);
}
async function fetchLiveFixtureNews(fixture){
 if(!fixture||fixture.status!=='candidate-found'||!fixture.homeTeam||!fixture.awayTeam) return {status:'blocked',checkedAt:now(),articles:[],riskTerms:[],message:'Cannot search news until a unique fixture candidate is matched.'};
 const query='"'+fixture.homeTeam+'" "'+fixture.awayTeam+'" (football OR soccer) (injury OR injured OR suspension OR suspended OR lineup OR team news OR rotation OR fitness OR doubtful OR unavailable)';
 const params=new URLSearchParams({query,mode:'ArtList',format:'json',maxrecords:'12',sort:'DateDesc',timespan:'7d'});
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
 try{
  const response=await fetch(NEWS_BASE+'?'+params.toString(),{signal:controller.signal,headers:{Accept:'application/json'}});
  if(!response.ok)throw Error('News service HTTP '+response.status);
  const data=await response.json();
  const articles=(Array.isArray(data.articles)?data.articles:[]).map(a=>({title:String(a.title||''),url:String(a.url||''),domain:String(a.domain||''),seenDate:String(a.seendate||''),language:String(a.language||''),terms:riskNewsKeywords(a.title)})).filter(a=>a.title&&/^https?:\/\//i.test(a.url));
  const riskTerms=[...new Set(articles.flatMap(a=>a.terms))];
  return {status:'live-results',checkedAt:now(),query,articles,riskTerms,message:articles.length?'Recent articles found. Headlines are signals only; open sources and confirm the facts.':'No matching articles found in this search window. This is not evidence of no team risk.'};
 }catch(err){
  return {status:'unavailable',checkedAt:now(),articles:[],riskTerms:[],message:'Live news could not be verified: '+(err?.name==='AbortError'?'request timed out':String(err?.message||err))};
 }finally{clearTimeout(timer);}
}
function scoreSlipLeg(row,news){
 const f=row.fixtureResolution||{},e=row.marketEstimate||null,reasons=[],warnings=[];
 let risk=0,hardStop=false;
 const cut=(n,reason)=>{risk+=n;reasons.push(reason);hardStop=true};
 const warn=(n,reason)=>{risk+=n;warnings.push(reason)};
 if(!(Number(row.odd)>1))cut(100,'Odds missing or invalid');
 if(row.confidence&&row.confidence!=='high')warn(22,'OCR confidence is not high; manually verify the selection and price');
 if(f.status!=='candidate-found')warn(35,'Fixture is not uniquely matched; cannot verify current fixture or kickoff');
 if(f.orientation==='verify-orientation')warn(35,'Home/away orientation needs manual verification');
 if(!e||e.status!=='estimated')warn(35,'No supported probability for this exact market. This is not proof the match is bad; hold it until a valid estimate exists.');
 if(e?.status==='estimated'){
  if(!Number.isFinite(e.probability)||e.probability<0||e.probability>1)cut(100,'Model probability is invalid');
  else if(e.probability<0.55)warn(28,'Experimental estimate is below the strict 55% threshold; reject unless independently validated');
  else if(e.probability<0.65)warn(10,'Estimated hit probability is below 65%');
  if(!Number.isFinite(e.ev)||e.ev<=0)warn(25,'Estimated expected value is not positive; price may be poor and the model is not calibrated');
  else if(e.ev<0.03)warn(8,'Estimated edge is under 3 percentage points and fragile');
 }
 const market=String(row.marketType||classifySlipMarket(row.rawLine||row.label||''));
 if(/Player market|Cards|Corners|Half-time|Handicap|Unclassified/.test(market))warn(15,'High-variance or unsupported-by-current-model market type: '+market);
 if(f.status==='candidate-found'){
  if(f.source==='historical-statsbomb')cut(100,'This is a historical StatsBomb match, not proof of a current/upcoming fixture.');
  const teams=[f.homeTeam,f.awayTeam].filter(Boolean).map(normalizeTeamName);
  const playerEvidence=(S.playerEventMatches||[]).some(p=>teams.includes(normalizeTeamName(p.team)))||(S.players||[]).some(p=>teams.includes(normalizeTeamName(p.team))&&p.source&&p.confidence);
  if(!playerEvidence)warn(8,'No saved player-event / sourced player-intelligence evidence for these teams');
  if(!S.lineups?.length||String(S.lineupsMatchId)!==String(f.matchId))warn(12,'No lineup file loaded for this exact fixture; availability and rotation remain unverified');
  const teamContext=(S.contexts||[]).some(c=>teams.includes(normalizeTeamName(c.team||c.teamName||'')));
  if(!teamContext)warn(5,'No saved team-context note found for this fixture');
 }
 if((S.backtests||[]).length<30)warn(10,'Fewer than 30 saved settled forecasts; predictive calibration is not established');
 if(news?.status==='unavailable')warn(18,'Live-news service unavailable; current availability risk remains unknown');
 else if(news?.status==='blocked')warn(20,'No fixture-specific live-news search possible');
 else if(news?.status==='live-results'){
  if(!news.articles.length)warn(12,'No matching reports found; absence of news is not clearance');
  if(news.riskTerms.includes('injury / fitness'))warn(25,'Headlines contain injury/fitness keywords. Verify named player, team, date and original report before treating this as a real risk.');
  if(news.riskTerms.includes('availability / suspension'))warn(28,'Headlines contain availability/suspension keywords; source text has not been verified.');
  if(news.riskTerms.includes('rotation / rest'))warn(18,'Headlines contain rotation/rest keywords; verify this exact fixture.');
  if(news.riskTerms.includes('late lineup / uncertainty'))warn(12,'Recent headlines mention lineup/selection uncertainty');
  if(news.riskTerms.includes('fixture congestion / fatigue'))warn(8,'Recent headlines mention congestion/fatigue');
  if(news.riskTerms.includes('motivation / context'))warn(5,'Recent headlines mention a context/motivation factor');
 }
 const status=hardStop?'CUT':risk>=12?'HOLD — verify':'SURVIVOR CANDIDATE';
 return {riskScore:Math.min(100,risk),status,hardStop,reasons,warnings,probability:e?.status==='estimated'?e.probability:null,ev:e?.status==='estimated'?e.ev:null,newsStatus:news?.status||'not checked'};
}
function matchSportyBetPrice(row,fixture){
 const markets=Array.isArray(fixture?.markets)?fixture.markets:[];
 if(fixture?.source!=='sportybet-live-api'||!markets.length)return {status:'unavailable',reason:'No SportyBet markets attached to this exact fixture.'};
 const raw=String(row.rawLine||row.label||'').toLowerCase();
 const compact=s=>String(s||'').toLowerCase().replace(/[^a-z0-9.]+/g,' ').replace(/\s+/g,' ').trim();
 const text=compact(raw),lineOdd=Number(row.odd),kind=String(row.marketType||classifySlipMarket(raw));
 const marketKindMatch=m=>{
  const n=compact(m.name);
  if(kind==='Goals total')return /total goals|over\/under|goal line|goals/.test(n);
  if(kind==='Both teams to score')return /both teams|btts/.test(n);
  if(kind==='Match result (1X2)')return /1x2|match result|full time result|winner/.test(n);
  if(kind==='Double chance')return /double chance/.test(n);
  if(kind==='Corners')return /corner/.test(n);
  if(kind==='Cards')return /card|booking/.test(n);
  if(kind==='Player market')return /player|shots|goalscorer|on target/.test(n);
  return n.length>0&&text.includes(n);
 };
 const matches=[];
 for(const m of markets){
  if(!marketKindMatch(m))continue;
  for(const o of (m.outcomes||[])){
   const outcome=compact(o.name);
   const outcomeMentioned=outcome.length>=2&&text.includes(outcome);
   const teamMentioned=[fixture.homeTeam,fixture.awayTeam].some(t=>compact(t).length>2&&text.includes(compact(t)));
   const priceDifference=Number.isFinite(lineOdd)?Math.abs(lineOdd-o.odds):null;
   if(outcomeMentioned&&teamMentioned)matches.push({marketId:m.id,marketName:m.name,outcomeId:o.id,outcomeName:o.name,sourceOdds:o.odds,slipOdds:Number.isFinite(lineOdd)?lineOdd:null,priceDifference,oddsTimestamp:fixture.oddsTimestamp});
  }
 }
 if(!matches.length)return {status:'unmatched',reason:'SportyBet fixture exists, but UFI could not confidently map both the precise market and outcome from the slip text.',candidateMarkets:markets.length};
 const best=matches.sort((a,b)=>(a.priceDifference??999)-(b.priceDifference??999))[0];
 if(best.priceDifference!==null&&best.priceDifference<=0.02)return {...best,status:'exact-market-and-price-match',reason:'Market, outcome and displayed decimal price match the source feed within 0.02.'};
 return {...best,status:'market-mapped-price-differs',reason:'Possible market/outcome match, but the source price differs from the slip price; do not treat the price as verified.'};
}
async function runStrictSlipAudit(){
 const button=$('runStrictAudit');button.disabled=true;button.textContent='Fetching live news & auditing…';
 try{
  if(!S.manualSelections.length){notice('strictAuditOutput','Analyze a slip or add selections first.','warning');return;}
  const rows=[];
  for(let i=0;i<S.manualSelections.length;i++){
   const row=S.manualSelections[i],fixture=row.fixtureResolution||{};
   notice('strictAuditOutput','Searching recent news and scoring leg '+(i+1)+' of '+S.manualSelections.length+'…');
   const news=await fetchLiveFixtureNews(fixture);
   row.liveNews=news;
   row.sportyBetMarketMatch=matchSportyBetPrice(row,fixture);
   const estimate=(row.marketEstimate&&String(row.marketEstimate.fixtureId||'')===String(fixture.matchId||''))?row.marketEstimate:((S.scenario&&fixture.source!=='live-fixture-feed'&&String(S.scenario.matchId||'')===String(fixture.matchId||''))?{...estimateSlipMarket(row,S.scenario),fixtureId:String(fixture.matchId||''),modelSource:'experimental-scoreline-scenario'}:null);
   row.marketEstimate=estimate;
   row.riskAudit=scoreSlipLeg(row,news);
   row.extendedAudit=window.UFI400Audit?.evaluate(row,news,S)||null;
   rows.push({...row,audit:{index:i,fixture,estimate,news,...row.riskAudit,extendedAudit:row.extendedAudit,sportyBetMarketMatch:row.sportyBetMarketMatch}});
  }
  const survivors=rows.filter(r=>r.audit.status==='SURVIVOR CANDIDATE').sort((a,b)=>(b.audit.probability??-1)-(a.audit.probability??-1));
  const cut=rows.filter(r=>r.audit.status==='CUT');
  const hold=rows.filter(r=>r.audit.status==='HOLD — verify');
  const replacements=survivors.filter(r=>r.source==='replacement');
  const original=survivors.find(r=>r.source!=='replacement');
  const picks=[{label:'Game 1 — highest-probability surviving original',row:original||null},{label:'Game 2 — replacement A (surviving candidate)',row:replacements[0]||null},{label:'Game 3 — replacement B (next surviving candidate)',row:replacements[1]||null}];
  S.lastRiskAudit={date:now(),pipelineVersion:'UFI strict audit v3 + 400-signal registry',aiCouncil:S.aiCouncilLast?{status:S.aiCouncilLast.status,successfulModels:S.aiCouncilLast.successfulModels,generatedAt:S.aiCouncilLast.generatedAt,models:(S.aiCouncilLast.models||[]).map(m=>({provider:m.provider,model:m.model,status:m.status,error:m.error||null,assessment:m.parsed?.summary||null,traps:(m.parsed?.traps||[]).slice(0,8),missingEvidence:(m.parsed?.missing_evidence||[]).slice(0,10)}))}:null,newsProvider:'GDELT DOC 2.0 public article search',fixtureProvider:S.sportyBetFixtures?.length?'SportyBet public web API (unofficial) + ESPN fallback':'ESPN public scoreboards; SportyBet feed unavailable',sportyBetOddsFetched:(S.sportyBetFixtures||[]).length,sportyBetOddsTimestamp:S.sportyBetFixtures?.[0]?.oddsTimestamp||null,replacementSearch:{status:'not-qualified',reason:'Current fixture discovery is available, but UFI does not yet have an integrated, verified odds feed plus a calibrated per-fixture prediction model for unseen replacement matches. No replacement is fabricated.',candidateFixturesAvailable:(S.liveFixtures||[]).length},newsWindow:'last 7 days',workspaceEvidence:{playerRecords:S.players.length,playerMatchProfiles:S.playerEventMatches.length,substitutionNotes:S.subs.length,teamContextNotes:S.contexts.length,savedSettledForecasts:S.backtests.length,loadedLineupMatchId:S.lineupsMatchId||null},extendedSignalAudit:{version:'UFI 400-signal registry v1',totalChecks:400,perSelection:rows.map(r=>({label:r.label,counts:r.extendedAudit?.counts||{},coveragePercent:r.extendedAudit?.coveragePercent??0,failures:(r.extendedAudit?.failures||[]).map(x=>({id:x.id,name:x.name,detail:x.detail})),needsData:(r.extendedAudit?.needsData||[]).slice(0,30).map(x=>({id:x.id,name:x.name,detail:x.detail}))}))},rows:rows.map(r=>{const f=r.audit.fixture||{};const teams=[f.homeTeam,f.awayTeam].filter(Boolean).map(normalizeTeamName);return {id:r.id||('selection-'+r.audit.index),label:r.label,rawLine:r.rawLine||r.label,marketType:r.marketType||classifySlipMarket(r.rawLine||r.label||''),odds:r.odd,source:r.source||'manual/OCR',fixture:f,newsStatus:r.audit.newsStatus,articles:r.audit.news?.articles||[],riskScore:r.audit.riskScore,status:r.audit.status,reasons:r.audit.reasons,warnings:r.audit.warnings,probability:r.audit.probability,probabilitySource:r.marketEstimate?.modelSource||(r.marketEstimate?.status==='estimated'?'scenario model':'none'),ev:r.audit.ev,evidence:{fixtureMatched:f.status==='candidate-found',currentFixtureFeedMatch:f.source==='live-fixture-feed',historicalFixtureOnly:f.source==='historical-statsbomb',validDecimalOdds:Number(r.odd)>1,liveNewsStatus:r.audit.newsStatus,newsArticleCount:r.audit.news?.articles?.length||0,playerEvidenceAvailable:(S.playerEventMatches||[]).some(p=>teams.includes(normalizeTeamName(p.team)))||(S.players||[]).some(p=>teams.includes(normalizeTeamName(p.team))&&p.source&&p.confidence),lineupEvidenceLoaded:!!S.lineups?.length&&String(S.lineupsMatchId)===String(f.matchId),teamContextAvailable:(S.contexts||[]).some(c=>teams.includes(normalizeTeamName(c.team||c.teamName||''))),settledForecastCount:(S.backtests||[]).length,probabilityAvailable:r.audit.probability!=null,probabilityCalibrated:false,liveSportyBetOddsVerified:r.sportyBetMarketMatch?.status==='exact-market-and-price-match',sportyBetMarketMatch:r.sportyBetMarketMatch?.status||'unmatched',sportyBetMarketMatchReason:r.sportyBetMarketMatch?.reason||'No source market match',sportyBetMarketCount:(f.markets||[]).length,sportyBetOddsTimestamp:f.oddsTimestamp||null,liveSportyBetPricesAvailable:!!(f.source==='sportybet-live-api'&&(f.markets||[]).length)}}}),cutCount:cut.length,holdCount:hold.length,survivorCount:survivors.length,shortlist:picks.map(p=>({slot:p.label,selection:p.row?.label||null,probability:p.row?.audit.probability??null,odds:p.row?.odd??null,ev:p.row?.audit.ev??null}))};
  S.riskAudits.unshift(S.lastRiskAudit);S.riskAudits=S.riskAudits.slice(0,100);persist();
  const listNews=r=>r.audit.news?.articles?.length?'<ul>'+r.audit.news.articles.slice(0,4).map(a=>'<li><a target="_blank" rel="noopener noreferrer" href="'+esc(a.url)+'">'+esc(a.title)+'</a> <small>'+esc(a.domain)+' · '+esc(a.seenDate||'date unavailable')+'</small>'+(a.terms.length?' <b>Signals: '+esc(a.terms.join(', '))+'</b>':'')+'</li>').join('')+'</ul>':'<small>'+esc(r.audit.news?.message||'No news status')+'</small>';
  const table=rows.length?'<div class="table-wrap"><table><thead><tr><th>Selection</th><th>Risk / 100</th><th>Decision</th><th>Model P / EV</th><th>SportyBet market match</th><th>Reasons & live source headlines</th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+esc(r.label)+'<br><small>'+esc(r.audit.fixture.homeTeam&&r.audit.fixture.awayTeam?r.audit.fixture.homeTeam+' vs '+r.audit.fixture.awayTeam:'Unmatched fixture')+'</small></td><td>'+r.audit.riskScore+'</td><td><b>'+esc(r.audit.status)+'</b></td><td>'+(r.audit.probability==null?'—':pct(r.audit.probability))+'<br>'+(r.audit.ev==null?'EV —':(r.audit.ev*100).toFixed(1)+'% EV')+'</td><td>'+(r.audit.reasons.length?'<b>Cut reasons</b><ul>'+r.audit.reasons.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'')+(r.audit.warnings.length?'<b>Warnings</b><ul>'+r.audit.warnings.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>':'')+listNews(r)+'</td></tr>').join('')+'</tbody></table></div>':'<p>No selections to audit.</p>';
  const extendedSummary=rows.map(r=>{const x=r.extendedAudit;return '<li><b>'+esc(r.label)+'</b>: '+(x?x.total+' signals; '+(x.counts.ASSESSED||0)+' assessed; '+(x.counts.NEEDS_DATA||0)+' need data; '+(x.counts.FAIL||0)+' failed':'400-signal registry unavailable')+'. Coverage '+(x?x.coveragePercent:0)+'%.</li>'}).join('');
  const traps='<h3>🧠 400-SIGNAL AUDIT COVERAGE</h3><p>Each selection is checked against 400 named signals across 20 domains. NEEDS_DATA means evidence is not connected or loaded; it is not a pass and not proof a bet is bad.</p><ul>'+extendedSummary+'</ul><h3>❌ TRAPS REMOVED</h3>'+(cut.length?'<ul>'+cut.map(r=>'<li><b>'+esc(r.label)+'</b> — '+esc(r.audit.reasons.join('; ')||'Hard-stop validation failed')+'</li>').join('')+'</ul>':'<p>No hard-stop cuts were proven by the current evidence. This does NOT mean every leg is safe.</p>')+'<h3>🟠 HOLD — DO NOT TREAT AS CLEARED</h3>'+(hold.length?'<ul>'+hold.map(r=>'<li><b>'+esc(r.label)+'</b> — '+esc(r.audit.warnings.join('; ')||r.audit.reasons.join('; '))+'</li>').join('')+'</ul>':'<p>No holds.</p>');
  const shortlist='<h3>🔎 REPLACEMENT SEARCH</h3><p>Current fixture feed contains '+(S.liveFixtures||[]).length+' candidate fixtures, including '+(S.sportyBetFixtures||[]).length+' SportyBet fixtures with source prices. <b>No automatic replacement is qualified yet</b> because market-to-selection matching and calibrated, fixture-specific prediction validation are not yet established. The app will not invent replacement probabilities.</p><h3>✅ FINAL 3-GAME SECURE SLIP — QUALIFIED CANDIDATES ONLY</h3><p class="amber">“Secure” is a requested format, not a guarantee. A slot stays empty unless it passes the same fixture, market, price and evidence checks.</p><ol>'+picks.map(p=>'<li><b>'+esc(p.label)+'</b>: '+(p.row?esc(p.row.label)+' · '+pct(p.row.audit.probability)+' experimental estimated probability · odds '+Number(p.row.odd).toFixed(2)+' · EV '+(p.row.audit.ev==null?'not established':(p.row.audit.ev*100).toFixed(1)+'%'):'<span class="amber">NO QUALIFIED CANDIDATE — no evidence-backed replacement is currently available</span>')+'</li>').join('')+'</ol>';
  const cutButton=cut.length?'<button id="removeCutLegsNow" class="button danger">Remove '+cut.length+' CUT leg(s) from current slip</button>':'';
  $('strictAuditOutput').innerHTML='<p><b>Live risk audit completed:</b> '+esc(S.lastRiskAudit.date)+' · news search window: 7 days · '+rows.length+' legs checked · <b>'+cut.length+' CUT</b> · '+hold.length+' HOLD · '+survivors.length+' survivor candidates.</p>'+traps+shortlist+cutButton+table+'<p class="amber">News is discovered by GDELT article search and may be incomplete, duplicated, late or wrong. Headlines are risk signals, not verified injury reports. Open the original article. Scenario probabilities come from the app’s current experimental score model, not a proven edge. A leg is only a survivor candidate—not a guarantee.</p>';
  $('removeCutLegsNow')?.addEventListener('click',()=>{
   const removedIndexes=new Set(rows.filter(r=>r.audit.status==='CUT').map(r=>r.audit.index));
   S.manualSelections=S.manualSelections.filter((r,i)=>!removedIndexes.has(i));
   renderManualSelections();notice('strictAuditOutput','Removed '+cut.length+' CUT leg(s) from the current slip. Re-run fixture matching, scenario bridge and risk audit after adding replacements.','good');
   addActivity('Removed '+cut.length+' CUT legs from slip after risk audit');
  });
  if(S.aiCouncilLast) renderAICouncilRiskBridge(S.aiCouncilLast);
  addActivity('Live strict risk audit: '+cut.length+' cut, '+hold.length+' hold, '+survivors.length+' survivor candidates');toast('Live audit finished. Review headlines and cut reasons.');
 }catch(err){notice('strictAuditOutput','Risk audit stopped: '+String(err?.message||err)+'. No selections were automatically removed.','error');}
 finally{button.disabled=false;button.textContent='Fetch live news + run strict risk audit';}
}
$('runStrictAudit').onclick=runStrictSlipAudit;
$('exportStrictAudit').onclick=()=>{if(!S.lastRiskAudit)return toast('Run the live risk audit first.');download('ufi-live-strict-slip-audit.json',JSON.stringify(S.lastRiskAudit,null,2),'application/json');};
$('markReplacement').onclick=()=>{const n=Number($('replacementIndex').value);if(!Number.isInteger(n)||n<0||n>=S.manualSelections.length)return toast('Enter a valid row number from 0.');S.manualSelections[n].source='replacement';renderManualSelections();toast('Marked as replacement candidate. Re-run market bridge and audit.');};

$('exportSlipReview').onclick=()=>{if(!S.manualSelections.length)return toast('Analyze a slip first.');const rows=[['selection','market_guess','decimal_odds','implied_probability','independent_estimate','parse_confidence','correlation_group','fixture_status','candidate_match_id','candidate_match_date','candidate_home_team','candidate_away_team','candidate_orientation','fixture_reason','warning','raw_line','source'],...S.manualSelections.map(x=>{const f=x.fixtureResolution||{};return [x.label,x.marketType||'',x.odd??'',x.p??'',x.estimate??'',x.confidence||'',x.group||'',f.status||'not_checked',f.matchId||'',f.matchDate||'',f.homeTeam||'',f.awayTeam||'',f.orientation||'',f.reason||'',x.warning||'',x.rawLine||x.label,x.source||'manual']})];download('ufi-slip-review.csv',csv(rows),'text/csv;charset=utf-8');toast('Slip review CSV exported. Verify it before modelling.');};
$('saveSlipAnalysis').onclick=()=>{if(!S.manualSelections.length)return toast('Analyze or add selections first.');const allPriced=S.manualSelections.every(x=>Number.isFinite(Number(x.odd))&&Number(x.odd)>1);const item={id:crypto.randomUUID(),date:now(),selections:S.manualSelections,combinedOdds:allPriced?S.manualSelections.reduce((a,x)=>a*Number(x.odd),1):null,stake:Number($('slipStake').value)||0,needsReview:!allPriced||S.manualSelections.some(x=>x.confidence!=='high')};S.slips.unshift(item);persist();addActivity('Saved slip analysis with '+item.selections.length+' selections');toast('Slip analysis saved in this browser.')};
function renderBacktests(){const rows=S.backtests;$('btTotal').textContent=rows.length;if(!rows.length){$('btAccuracy').textContent='—';$('btBrier').textContent='—';$('btLogloss').textContent='—';$('calibrationSummary').textContent='No settled forecasts. Save forecasts with actual results after the match.';$('backtestTable').innerHTML='<p class="muted">No forecasts logged yet.</p>';return}const acc=rows.filter(x=>['H','D','A'][x.probs.indexOf(Math.max(...x.probs))]===x.result).length/rows.length;const brier=rows.reduce((a,x)=>a+x.probs.reduce((s,p,i)=>s+(p-(['H','D','A'][i]===x.result?1:0))**2,0),0)/rows.length;const logloss=rows.reduce((a,x)=>a-Math.log(Math.max(1e-15,x.probs[['H','D','A'].indexOf(x.result)])),0)/rows.length;$('btAccuracy').textContent=pct(acc);$('btBrier').textContent=brier.toFixed(4);$('btLogloss').textContent=logloss.toFixed(4);$('calibrationSummary').textContent='Mean scores over '+rows.length+' settled records. Lower Brier and log loss are better. Accuracy alone ignores confidence quality; evaluate chronologically and compare against a baseline.';$('backtestTable').innerHTML='<table><thead><tr><th>Match</th><th>Method</th><th>Forecast H/D/A</th><th>Actual</th><th>Brier</th><th>Logged</th><th></th></tr></thead><tbody>'+rows.slice().reverse().map(x=>{const y=['H','D','A'].indexOf(x.result),br=x.probs.reduce((s,p,i)=>s+(p-(i===y?1:0))**2,0);return '<tr><td>'+esc(x.match)+'</td><td>'+esc(x.method||'Not specified')+'</td><td>'+x.probs.map(pct).join(' / ')+'</td><td>'+esc(x.result)+'</td><td>'+br.toFixed(4)+'</td><td>'+fmtDate(x.date)+'</td><td><button class="button danger small" data-delete-bt="'+x.id+'">Delete</button></td></tr>'}).join('')+'</tbody></table>'}
$('saveBacktest').onclick=()=>{const match=$('btMatch').value.trim();if(!match)return notice('btStatus','Enter a match identifier.','warning');const raw=[Number($('btHome').value),Number($('btDraw').value),Number($('btAway').value)];if(raw.some(x=>!Number.isFinite(x)||x<0)||raw.reduce((a,b)=>a+b,0)<=0)return notice('btStatus','Probabilities must be non-negative and have a positive total.','error');const total=raw.reduce((a,b)=>a+b,0),probs=raw.map(x=>x/total);const row={id:crypto.randomUUID(),match,method:$('btMethod').value.trim(),rawProbabilities:raw,probs,result:$('btResult').value,notes:$('btNotes').value.trim(),date:now()};S.backtests.push(row);persist();renderBacktests();addActivity('Saved settled forecast for '+match);notice('btStatus','Saved. Entered probabilities were normalized from total '+total.toFixed(2)+'%.','good');toast('Forecast saved.')};
$('backtestTable').addEventListener('click',e=>{const b=e.target.closest('[data-delete-bt]');if(!b)return;S.backtests=S.backtests.filter(x=>x.id!==b.dataset.deleteBt);persist();renderBacktests()});
$('exportBacktest').onclick=()=>download('ufi-backtest.csv',csv([['match','method','home_probability','draw_probability','away_probability','actual','notes','date'],...S.backtests.map(x=>[x.match,x.method,...x.probs,x.result,x.notes,x.date])]),'text/csv');
$('clearBacktest').onclick=()=>{if(confirm('Delete all saved forecast records from this browser? Export first if needed.')){S.backtests=[];persist();renderBacktests();toast('Backtest ledger cleared.')}};
$('saveNote').onclick=()=>{const title=$('noteTitle').value.trim(),body=$('noteBody').value.trim();if(!title||!body)return toast('Add a note title and its content.');S.notes.unshift({id:crypto.randomUUID(),title,type:$('noteType').value,source:$('noteSource').value.trim(),body,date:now()});persist();renderNotes();addActivity('Saved research note: '+title);['noteTitle','noteSource','noteBody'].forEach(id=>$(id).value='');toast('Research note saved.')};
function renderNotes(){const q=($('noteSearch').value||'').toLowerCase(),ns=S.notes.filter(n=>(n.title+' '+n.type+' '+n.body+' '+n.source).toLowerCase().includes(q));$('notesList').innerHTML=ns.length?ns.map(n=>'<article class="note-card"><div class="note-meta"><span>'+esc(n.type)+' · '+fmtDate(n.date)+'</span><span>'+ (n.source?'<a href="'+esc(n.source)+'" target="_blank" rel="noopener">Source ↗</a>':'No source link')+'</span></div><h3>'+esc(n.title)+'</h3><p>'+esc(n.body)+'</p><button class="button danger small" data-delete-note="'+n.id+'">Delete note</button></article>').join(''):'<p class="muted">No matching notes.</p>'}
$('noteSearch').addEventListener('input',renderNotes);
$('notesList').addEventListener('click',e=>{const b=e.target.closest('[data-delete-note]');if(!b)return;S.notes=S.notes.filter(n=>n.id!==b.dataset.deleteNote);persist();renderNotes()});
function renderActivity(){$('activityFeed').innerHTML=S.activity.length?S.activity.slice(0,8).map(a=>'<div class="activity-item">'+esc(a.msg)+'<small>'+new Date(a.date).toLocaleString()+'</small></div>').join(''):'<p class="muted">No activity yet.</p>'}
function renderAllSaved(){renderPlayers();renderSubs();renderContexts();renderNotes();renderBacktests();renderPlayerEventAggregate();renderActivity();$('metricPlayers').textContent=S.players.length;$('metricForecasts').textContent=S.backtests.length;$('metricNotes').textContent=S.notes.length}
$('exportAll').onclick=()=>{const data={app:'Universal Football Intelligence',version:3,exported_at:now(),players:S.players,subs:S.subs,contexts:S.contexts,notes:S.notes,backtests:S.backtests,slips:S.slips,playerEventMatches:S.playerEventMatches,riskAudits:S.riskAudits,activity:S.activity};download('ufi-workspace-backup.json',JSON.stringify(data,null,2),'application/json');toast('Workspace backup exported.')};
$('importAll').addEventListener('change',async e=>{const f=e.target.files?.[0];if(!f)return;try{const d=JSON.parse(await f.text());for(const k of ['players','subs','contexts','notes','backtests','slips','playerEventMatches','riskAudits','activity'])if(Array.isArray(d[k]))S[k]=d[k];persist();renderAllSaved();toast('Workspace imported. Review imported records and sources.');addActivity('Imported workspace backup')}catch(err){toast('Import failed: invalid JSON workspace file.')}finally{e.target.value=''}});
$('resetWorkspace').onclick=()=>{if(!confirm('This permanently clears saved UFI records from this browser. Export a backup first if needed.'))return;localStorage.removeItem(STORE);for(const k of ['players','subs','contexts','notes','backtests','slips','playerEventMatches','riskAudits','activity'])S[k]=[];renderAllSaved();notice('settingsStatus','Local workspace cleared. Loaded match data in memory may remain until you refresh.','good');toast('Local workspace reset.')};


function renderAICouncilRiskBridge(result){
 if(!result||!S.lastRiskAudit)return;
 const flags=(result.models||[]).flatMap(m=>(m.parsed?.traps||[]).map(t=>({provider:m.provider,selection:t.selection||'Unspecified leg',concern:t.concern||'Concern not specified',evidenceLevel:t.evidence_level||'unknown',action:t.action||'HOLD'}))).slice(0,24);
 S.lastRiskAudit.aiCouncil={status:result.status,successfulModels:result.successfulModels,generatedAt:result.generatedAt,models:(result.models||[]).map(m=>({provider:m.provider,model:m.model,status:m.status,error:m.error||null,assessment:m.parsed?.summary||null,traps:(m.parsed?.traps||[]).slice(0,8),missingEvidence:(m.parsed?.missing_evidence||[]).slice(0,10)}))};
 S.lastRiskAudit.aiReviewFlags=flags;
 const groups={};flags.forEach(f=>{const k=String(f.selection||'Unspecified leg').trim().toLowerCase();(groups[k]||(groups[k]={label:f.selection,providers:new Set(),concerns:[]})).providers.add(f.provider);groups[k].concerns.push(f.concern)});const repeated=Object.values(groups).filter(g=>g.providers.size>=2);
 const out=$('strictAuditOutput');
 if(out){
  out.querySelector('#aiCouncilRiskBridge')?.remove();
  const box=document.createElement('div');box.id='aiCouncilRiskBridge';box.className='notice warning';
  box.innerHTML='<h3>🤖 AI COUNCIL CROSS-CHECK — ADVISORY ONLY</h3><p>'+esc(result.status)+' · '+Number(result.successfulModels||0)+' model(s) responded. These flags do not change deterministic CUT/HOLD decisions.</p>'+(repeated.length?'<h4>Repeated concerns across models</h4><ul>'+repeated.map(g=>'<li><b>'+esc(g.label)+'</b> — flagged by '+esc([...g.providers].join(', '))+'; '+esc([...new Set(g.concerns)].join('; '))+'</li>').join('')+'</ul>':'<p>No exact selection concern was repeated across two or more models. This is not evidence that selections are safe; review single-model flags and disagreements.</p>')+(flags.length?'<h4>All advisory flags</h4><ul>'+flags.map(f=>'<li><b>'+esc(f.selection)+'</b> — '+esc(f.concern)+' <small>['+esc(f.provider)+'; '+esc(f.evidenceLevel)+']</small></li>').join('')+'</ul>':'<p>No structured AI trap flags were parsed. This is not evidence that selections are safe.</p>')+'<p class="muted">Verify every AI claim against source evidence. Unverified flags remain questions, not facts.</p>';
  out.appendChild(box);
 }
}

window.UFI_AI_CONTEXT = () => {
 const countBy=(items,keyFn)=>(items||[]).reduce((o,x)=>{const k=keyFn(x)||'Unknown';o[k]=(o[k]||0)+1;return o;},{});
 const match=S.selectedMatch||{};
 const teamName=t=>typeof t==='string'?t:(t?.home_team_name||t?.away_team_name||t?.name||'');
 const eventTypes=countBy(S.events,e=>e.type?.name||e.type||e.event_type);
 const shots=(S.events||[]).filter(e=>(e.type?.name||e.type)==='Shot');
 const xg=shots.reduce((n,e)=>n+(Number(e.shot?.statsbomb_xg??e.statsbomb_xg)||0),0);
 return {
  generatedAt:now(),
  dataInventory:{competitionsLoaded:(S.competitions||[]).length,matchesLoaded:(S.matches||[]).length,currentUpcomingFixtures:(S.liveFixtures||[]).length,eventsLoaded:(S.events||[]).length,lineupRows:(S.lineups||[]).length,lineupMatchId:S.lineupsMatchId||null,playerProfiles:(S.players||[]).length,playerMatchProfiles:(S.playerEventMatches||[]).length,substitutionNotes:(S.subs||[]).length,teamContextNotes:(S.contexts||[]).length,savedForecasts:(S.backtests||[]).length,researchNotes:(S.notes||[]).length,previousRiskAudits:(S.riskAudits||[]).length},
  selectedMatch:Object.keys(match).length?{id:match.match_id||match.id||null,date:match.match_date||match.date||null,home:teamName(match.home_team)||match.home_team_name||null,away:teamName(match.away_team)||match.away_team_name||null,competition:match.competition?.competition_name||match.competition_name||null,season:match.season?.season_name||match.season_name||null,score:match.home_score!=null?[match.home_score,match.away_score]:null,eventTypeCounts:eventTypes,shotCount:shots.length,summedSourceXg:Number(xg.toFixed(3)),lineupsLoaded:!!S.lineups.length&&String(S.lineupsMatchId)===String(match.match_id||match.id)}:null,
  scenario:S.scenario?{home:$('scenarioHomeName')?.value,away:$('scenarioAwayName')?.value,homeLambda:Number($('lambdaHome')?.value),awayLambda:Number($('lambdaAway')?.value),source:'UFI experimental scoreline scenario; not calibrated unless backtest proves it'}:null,
  currentSelections:(S.manualSelections||[]).map((r,i)=>({row:i,selection:r.label,rawLine:r.rawLine||null,market:r.marketType||null,decimalOdds:Number(r.odd)||null,independentProbability:r.p!=null?Number(r.p):r.estimate!=null?Number(r.estimate):null,confidence:r.confidence||'unknown',fixture:r.fixtureResolution?{status:r.fixtureResolution.status,source:r.fixtureResolution.source,matchId:r.fixtureResolution.matchId,date:r.fixtureResolution.matchDate,home:r.fixtureResolution.homeTeam,away:r.fixtureResolution.awayTeam,reason:r.fixtureResolution.reason}:null,marketEstimate:r.marketEstimate?{status:r.marketEstimate.status,probability:r.marketEstimate.probability,ev:r.marketEstimate.ev,source:r.marketEstimate.modelSource,fixtureId:r.marketEstimate.fixtureId}:null,newsStatus:r.liveNews?.status||null,newsCount:r.liveNews?.articles?.length||0})),
  latestRiskAudit:S.lastRiskAudit?{date:S.lastRiskAudit.date,pipelineVersion:S.lastRiskAudit.pipelineVersion,cutCount:S.lastRiskAudit.cutCount,holdCount:S.lastRiskAudit.holdCount,survivorCount:S.lastRiskAudit.survivorCount,replacementSearch:S.lastRiskAudit.replacementSearch,workspaceEvidence:S.lastRiskAudit.workspaceEvidence,rows:(S.lastRiskAudit.rows||[]).map(r=>({label:r.label,status:r.status,riskScore:r.riskScore,reasons:r.reasons,warnings:r.warnings,probability:r.probability,probabilitySource:r.probabilitySource,ev:r.ev,evidence:r.evidence,newsStatus:r.newsStatus,articleTitles:(r.articles||[]).slice(0,4).map(a=>({title:a.title,url:a.url,date:a.seenDate}))}))}:null,
  playerEvidence:(S.players||[]).slice(0,80).map(p=>({name:p.name,team:p.team,position:p.position,preferredFoot:p.foot||p.preferredFoot||'Unknown',weakFoot:p.weakFoot||'Unknown',styles:p.styles||p.playerStyles||'',confidence:p.confidence||'unknown',source:p.source||null})),
  substitutionEvidence:(S.subs||[]).slice(0,60),
  teamContext:(S.contexts||[]).slice(0,60),
  playerMatchProfiles:(S.playerEventMatches||[]).slice(0,80),
  backtestSummary:{n:(S.backtests||[]).length,methods:[...new Set((S.backtests||[]).map(x=>x.method).filter(Boolean))],latest:(S.backtests||[]).slice(-10).map(x=>({match:x.match,method:x.method,probs:x.probs,result:x.result,date:x.date}))},
  researchNotes:(S.notes||[]).slice(0,30).map(n=>({title:n.title,type:n.type,source:n.source,body:String(n.body||'').slice(0,500)})),
  physicsAndModelRules:'Physics layers require measured inputs. Ball drag/Magnus/spin affect flight, not directly match outcome. Pitch control needs tracking coordinates, speeds, acceleration and reaction assumptions; event locations are not full tracking. Fit time-stamped attack/defence rates; compare Poisson/Dixon-Coles and simple baselines; validate on unseen results with log loss, Brier/RPS and calibration. EV requires independent calibrated probability and exact market price, accounting for vig and correlation. Kelly is stake sizing, not prediction. Unknown lineup, injuries, weak foot, tracking, weather, odds or calibration must remain unknown. LLM opinions are evidence triage only.'
 };
};
window.UFI_ATTACH_AI_COUNCIL = result => {
 S.aiCouncilLast=result;
 if(S.lastRiskAudit) renderAICouncilRiskBridge(result);
 addActivity('AI council review: '+(result?.successfulModels||0)+' models responded; status '+(result?.status||'unknown')); 
 persist();
};

renderAllSaved();renderManualSelections();
if(location.protocol==='file:')$('netState').textContent='Local file mode';
else $('netState').textContent='Ready';
})();
