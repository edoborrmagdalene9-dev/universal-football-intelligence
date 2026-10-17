(() => {
'use strict';
const BASE='https://raw.githubusercontent.com/statsbomb/open-data/master/data/';
const $=id=>document.getElementById(id);
const STORE='ufi_workspace_v2';
const S={competitions:[],matches:[],events:[],lineups:[],selectedMatch:null,scenario:null,manualSelections:[],activity:[],players:[],subs:[],contexts:[],notes:[],backtests:[],slips:[],playerEventMatches:[],lastSlip:null};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const now=()=>new Date().toISOString();
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toast.timer);toast.timer=setTimeout(()=>t.classList.remove('show'),2800)}
function notice(id,msg,type=''){const e=$(id);if(e){e.className='notice'+(type?' '+type:'');e.textContent=msg}}
function go(view){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id==='view-'+view));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===view));window.scrollTo({top:0,behavior:'smooth'})}
document.querySelectorAll('.nav-item').forEach(b=>b.addEventListener('click',()=>go(b.dataset.view)));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.go)));
function addActivity(msg){S.activity.unshift({msg,date:now()});S.activity=S.activity.slice(0,12);renderActivity()}
function persist(){const data={players:S.players,subs:S.subs,contexts:S.contexts,notes:S.notes,backtests:S.backtests,slips:S.slips,playerEventMatches:S.playerEventMatches,activity:S.activity};try{localStorage.setItem(STORE,JSON.stringify(data));return true}catch(e){toast('Browser storage is full; export workspace and remove old records.');return false}}
function restore(){try{const d=JSON.parse(localStorage.getItem(STORE)||'{}');for(const k of ['players','subs','contexts','notes','backtests','slips','playerEventMatches','activity'])if(Array.isArray(d[k]))S[k]=d[k]}catch(e){console.warn('Workspace restore failed',e)}renderAllSaved()}
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
$('loadSelectedLineups').addEventListener('click',async()=>{const m=chosenMatch();if(!m)return notice('dataStatus','Select a match first.','warning');try{S.lineups=await json(BASE+'lineups/'+m.match_id+'.json');$('lineupResults').innerHTML=S.lineups.map(t=>'<h3>'+esc(t.team_name||'Team')+'</h3><table><thead><tr><th>Player</th><th>Position / role from source</th><th>Starter info</th></tr></thead><tbody>'+((t.lineup||[]).map(p=>'<tr><td>'+esc(p.player_name)+'</td><td>'+esc((p.positions||[]).map(z=>z.position).join(', ')||'Not specified')+'</td><td>'+esc((p.positions||[]).map(z=>z.start_reason||'').filter(Boolean).join(', ')||'Source does not label this clearly')+'</td></tr>').join('')||'<tr><td colspan="3">No lineup rows</td></tr>')+'</tbody></table>').join('');notice('dataStatus','Lineups loaded where available. Verify source structure and status.','good');addActivity('Loaded lineup data for '+matchName(m))}catch(err){notice('dataStatus','Lineups are unavailable for this match: '+err.message,'warning');$('lineupResults').innerHTML='<p class="muted">The source has no accessible lineup file for this match.</p>'}});
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
function scenarioCalc(){const h=Number($('lambdaHome').value),a=Number($('lambdaAway').value),cap=Number($('scoreCap').value);if(!Number.isFinite(h)||!Number.isFinite(a)||h<0||a<0||h>12||a>12){notice('scenarioStatus','Expected goals must be between 0 and 12.','warning');return null}let grid=[],mass=0,hw=0,d=0,aw=0,over15=0,over25=0,over35=0,btts=0;for(let i=0;i<=cap;i++)for(let j=0;j<=cap;j++){const p=poisson(h,i)*poisson(a,j);grid.push({h:i,a:j,p});mass+=p;if(i>j)hw+=p;else if(i===j)d+=p;else aw+=p;if(i+j>1)over15+=p;if(i+j>2)over25+=p;if(i+j>3)over35+=p;if(i>0&&j>0)btts+=p}grid.sort((x,y)=>y.p-x.p);const norm=x=>x/mass;const out={home:$('scenarioHomeName').value.trim()||'Home',away:$('scenarioAwayName').value.trim()||'Away',lambdaHome:h,lambdaAway:a,cap,mass,homeWin:norm(hw),draw:norm(d),awayWin:norm(aw),over15:norm(over15),over25:norm(over25),over35:norm(over35),btts:norm(btts),grid,top:grid[0],label:$('scenarioLabel').value.trim(),caveats:$('scenarioCaveats').value.trim(),checks:['checkLineup','checkVenue','checkRecent','checkOpponent','checkMarket','checkUncertainty'].filter(id=>$(id).checked)};S.scenario=out;return out}
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
 const candidates=(S.matches||[]).filter(m=>{
  const h=normalizeTeamName(m.home_team?.home_team_name),a=normalizeTeamName(m.away_team?.away_team_name);
  return h&&a&&whole.includes(' '+h+' ')&&whole.includes(' '+a+' ');
 });
 if(candidates.length===1){
  const m=candidates[0],parsed=parseFixtureText(raw),h=normalizeTeamName(m.home_team?.home_team_name);
  const orientation=normalizeTeamName(parsed.homeText).includes(h)?'home-away':(normalizeTeamName(parsed.awayText).includes(h)?'away-home':'verify-orientation');
  return {status:'candidate-found',matchId:String(m.match_id??''),matchDate:String(m.match_date||''),homeTeam:m.home_team?.home_team_name||'',awayTeam:m.away_team?.away_team_name||'',orientation,reason:'Unique team pair found in the loaded StatsBomb list. Verify date, competition, kickoff and market manually.'};
 }
 if(candidates.length>1)return {status:'ambiguous',matchId:'',matchDate:'',homeTeam:'',awayTeam:'',reason:'Multiple loaded fixtures contain both team names. Add date/competition and resolve manually.'};
 return {status:S.matches.length?'not-found-in-loaded-list':'no-fixtures-loaded',matchId:'',matchDate:'',homeTeam:'',awayTeam:'',reason:S.matches.length?'No unique team pair found in the currently loaded competition/season.':'Load a competition, season and match list before fixture matching.'};
}
function runSlipFixtureMatching(){
 const rows=S.manualSelections.map(row=>({...row,fixtureResolution:resolveSlipFixture(row)}));
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
  return {id:'ocr-'+index,label:label||line.trim(),odd,p:odd?1/odd:null,estimate:null,group:fixtureMatch?(fixtureMatch.homeText+' vs '+fixtureMatch.awayText):'',marketType:market,confidence,warning,rawLine:line.trim(),source:'OCR/text'};
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
$('exportAll').onclick=()=>{const data={app:'Universal Football Intelligence',version:3,exported_at:now(),players:S.players,subs:S.subs,contexts:S.contexts,notes:S.notes,backtests:S.backtests,slips:S.slips,playerEventMatches:S.playerEventMatches,activity:S.activity};download('ufi-workspace-backup.json',JSON.stringify(data,null,2),'application/json');toast('Workspace backup exported.')};
$('importAll').addEventListener('change',async e=>{const f=e.target.files?.[0];if(!f)return;try{const d=JSON.parse(await f.text());for(const k of ['players','subs','contexts','notes','backtests','slips','activity'])if(Array.isArray(d[k]))S[k]=d[k];persist();renderAllSaved();toast('Workspace imported. Review imported records and sources.');addActivity('Imported workspace backup')}catch(err){toast('Import failed: invalid JSON workspace file.')}finally{e.target.value=''}});
$('resetWorkspace').onclick=()=>{if(!confirm('This permanently clears saved UFI records from this browser. Export a backup first if needed.'))return;localStorage.removeItem(STORE);for(const k of ['players','subs','contexts','notes','backtests','slips','playerEventMatches','activity'])S[k]=[];renderAllSaved();notice('settingsStatus','Local workspace cleared. Loaded match data in memory may remain until you refresh.','good');toast('Local workspace reset.')};
renderAllSaved();renderManualSelections();
if(location.protocol==='file:')$('netState').textContent='Local file mode';
else $('netState').textContent='Ready';
})();
