/* UFI Live Correct-Score + Player Chaos Engine
 * Experimental research module. No live provider is implied by manual inputs.
 * Probabilities are model outputs, not guarantees; calibrate with chronological holdouts.
 */
(() => {
'use strict';
const $ = id => document.getElementById(id);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const n=id=>Number($(id).value);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>(100*x).toFixed(2)+'%';
function factorial(k){let f=1;for(let i=2;i<=k;i++)f*=i;return f}
function pois(k,l){if(l===0)return k===0?1:0;return Math.exp(-l+k*Math.log(l)-Math.log(factorial(k)))}
function tau(h,a,lambda,mu,rho){
 if(h===0&&a===0)return 1-lambda*mu*rho;
 if(h===0&&a===1)return 1+lambda*rho;
 if(h===1&&a===0)return 1+mu*rho;
 if(h===1&&a===1)return 1-rho;
 return 1;
}
function parsePlayers(id){
 try { const x=JSON.parse($(id).value||'[]'); if(!Array.isArray(x))throw Error('must be a JSON array'); return x; }
 catch(e){throw Error(id+' must contain a valid JSON array ('+e.message+').')}
}
function profileChaos(players, pressing){
 return players.map(p=>{
  const foot=String(p.dominantFoot||'unknown').toLowerCase();
  const side=String(p.positionSide||'').toLowerCase();
  const forced=pressing && ((foot==='right'&&side==='left')||(foot==='left'&&side==='right'));
  const footPenalty=forced?0.18:0;
  const observed=clamp(Number(p.rIndex)||0,0,1);
  const r=clamp(observed+footPenalty,0,1);
  return {...p,rIndex:r,footPenalty,virtualRed:r>=0.75};
 });
}
function calc(){
 const home=($('lcsHome').value||'Home').trim(), away=($('lcsAway').value||'Away').trim();
 const live=$('lcsMode').value==='live', minute=clamp(n('lcsMinute')||0,0,120);
 const sh=Math.max(0,Math.floor(n('lcsCurrentHome')||0)), sa=Math.max(0,Math.floor(n('lcsCurrentAway')||0));
 let lh=clamp(n('lcsXgHome')||0,0,6), la=clamp(n('lcsXgAway')||0,0,6);
 const rho=clamp(n('lcsRho')||0,-0.15,0.15), pressing=$('lcsPressing').checked;
 const odds=Number($('lcsOver15Odds').value), combinedBaseline=(Number($('lcsXgHome').value)||0)+(Number($('lcsXgAway').value)||0);
 const filterPassed=Number.isFinite(odds)&&odds>=1.08&&odds<=1.35&&combinedBaseline>=2.60;
 const leagueProfile=$('lcsLeague').value;
 const ph=profileChaos(parsePlayers('lcsPlayersHome'),pressing), pa=profileChaos(parsePlayers('lcsPlayersAway'),pressing);
 const redH=ph.filter(p=>p.virtualRed).length, redA=pa.filter(p=>p.virtualRed).length;
 const tcsH=ph.reduce((s,p)=>s+p.rIndex,0)+(Number($('lcsVolHome').value)||0);
 const tcsA=pa.reduce((s,p)=>s+p.rIndex,0)+(Number($('lcsVolAway').value)||0);
 // Player anomaly adjustments are explicitly heuristic and bounded.
 lh=clamp(lh-0.35*redH,0,6); la=clamp(la-0.35*redA,0,6);
 // Defensive concession adjustment transfers a bounded fraction of expected goals to opponent.
 lh=clamp(lh+0.25*redA,0,6); la=clamp(la+0.25*redH,0,6);
 let remH=lh, remA=la;
 if(live){
  const remain=clamp((1-minute/90),0,1);
  const decay=Math.pow(remain,1.15);
  remH=lh*decay; remA=la*decay;
 }
 const discarded=redH>=2||redA>=2||tcsH>=Number($('lcsTcsLimit').value)||tcsA>=Number($('lcsTcsLimit').value);
 const cardH=Number($('lcsRedHome').value)||0, cardA=Number($('lcsRedAway').value)||0;
 // Explicit real red cards: penalize carded team's attack, increase opponent's attack; bounded.
 remH=clamp(remH-0.40*cardH+0.65*cardA,0,6);
 remA=clamp(remA-0.40*cardA+0.65*cardH,0,6);
 const volatility=minute<20 && live && (sh+sa)>0 ? 1.25:1;
 remH=clamp(remH*volatility,0,6); remA=clamp(remA*volatility,0,6);
 const rows=[]; let mass=0;
 for(let i=0;i<=sh+10;i++)for(let j=0;j<=sa+10;j++){
  const gh=i-sh, ga=j-sa; if(gh<0||ga<0)continue;
  let p=pois(gh,remH)*pois(ga,remA);
  if(!live) p*=Math.max(0,tau(i,j,lh,la,rho));
  rows.push({h:i,a:j,p}); mass+=p;
 }
 const adjustedMass=rows.reduce((s,r)=>s+r.p,0);
 if(adjustedMass>0) rows.forEach(r=>r.p/=adjustedMass);
 rows.sort((x,y)=>y.p-x.p);
 const top=rows.slice(0,4);
 const profilesComplete=ph.length===11&&pa.length===11;
 const green=!discarded&&filterPassed&&profilesComplete&&tcsH<Number($('lcsTcsLimit').value)*0.65&&tcsA<Number($('lcsTcsLimit').value)*0.65&&redH===0&&redA===0;
 const status=discarded?'MATCH DISCARDED: High Randomness Anomaly Detected (TCS Exceeded Limits).':green?'GREEN LIGHT: Low Randomness / Model Filters Passed (experimental, not validated confidence).':'CAUTION: Elevated randomness or model risk. Do not apply maximum model weight.';
 $('lcsOutput').innerHTML='<div class="notice '+(discarded?'warning':green?'good':'warning')+'"><b>'+esc(status)+'</b></div>'+
 '<div class="notice '+(filterPassed?'good':'warning')+'"><b>Candidate filter: '+(filterPassed?'YES':'NO / INCOMPLETE')+'</b> — Over 1.5 odds '+(Number.isFinite(odds)?odds.toFixed(2):'not supplied')+'; combined baseline xG '+combinedBaseline.toFixed(2)+' (target ≥ 2.60). Target lower-tier league selected: '+(leagueProfile==='target'?'yes':leagueProfile==='major'?'no':'unknown')+'. Odds and league classification are user-entered and not verified by a feed.</div>'+
 '<div class="outcome-grid"><div><span>Home remaining xG*</span><b>'+remH.toFixed(2)+'</b></div><div><span>Away remaining xG*</span><b>'+remA.toFixed(2)+'</b></div><div><span>Home TCS</span><b>'+tcsH.toFixed(2)+'</b></div><div><span>Away TCS</span><b>'+tcsA.toFixed(2)+'</b></div></div>'+
 (discarded?'<p class="muted">Prediction suppressed by circuit breaker. The scorelines below are intentionally withheld.</p>':
 '<h3>Top 4 final-score scenarios</h3><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Final score</th><th>Model probability</th></tr></thead><tbody>'+top.map((r,i)=>'<tr><td>'+(i+1)+'</td><td><b>'+r.h+'–'+r.a+'</b></td><td>'+pct(r.p)+'</td></tr>').join('')+'</tbody></table></div>'+
 '<p class="muted">*Remaining xG is a heuristic derived from entered baseline rates and time decay, not provider-verified live xG. Top four probabilities do not sum to 100%. Displayed score-grid mass: '+pct(mass)+'.</p>')+
 '<h3>Player anomaly audit</h3><div class="form-grid two"><div><b>'+esc(home)+'</b><p>Virtual red flags: '+redH+' · TCS: '+tcsH.toFixed(2)+'</p>'+playerTable(ph)+'</div><div><b>'+esc(away)+'</b><p>Virtual red flags: '+redA+' · TCS: '+tcsA.toFixed(2)+'</p>'+playerTable(pa)+'</div></div>'+
 '<p class="muted">'+(!profilesComplete?'Green-light approval withheld: provide all 11 starting-player profiles for both teams; missing profiles are unknown. ':'')+'Inverse-foot rule adds 0.18 to R-Index for right-footed players in a left-side role or left-footed players in a right-side role when high pressing is toggled. This is a hypothesis, not an empirically established universal effect. “Virtual red” is a simulation penalty only; it is not a real sending-off.</p>';
}
function playerTable(ps){if(!ps.length)return '<p class="muted">No player profiles entered; player-level risk is unavailable, not zero.</p>';return '<div class="table-wrap"><table><thead><tr><th>Player</th><th>R-Index</th><th>Foot penalty</th><th>Flag</th></tr></thead><tbody>'+ps.map(p=>'<tr><td>'+esc(p.name||'Unnamed')+'</td><td>'+p.rIndex.toFixed(2)+'</td><td>'+(p.footPenalty*100).toFixed(0)+'%</td><td>'+(p.virtualRed?'VIRTUAL RED':'—')+'</td></tr>').join('')+'</tbody></table></div>'}
$('lcsRun').addEventListener('click',()=>{try{calc()}catch(e){$('lcsOutput').innerHTML='<div class="notice warning">'+esc(e.message)+'</div>'}});
function scoreFromFixture(f){
 const s=f?.score;
 if(s&&typeof s==='object'){
  const h=s.home??s.homeScore??s.home_score,a=s.away??s.awayScore??s.away_score;
  if(Number.isInteger(Number(h))&&Number.isInteger(Number(a))&&h!==null&&a!==null)return {h:Number(h),a:Number(a)};
 }
 if(f?.home_score!=null&&f?.away_score!=null&&Number.isFinite(Number(f.home_score))&&Number.isFinite(Number(f.away_score)))return {h:Number(f.home_score),a:Number(f.away_score)};
 if(Array.isArray(f?.scores)){
  const sides=f.scores.map(x=>({side:String(x?.score?.participant??x?.participant??x?.description??x?.type?.name??'').toLowerCase(),goals:x?.score?.goals??x?.goals}));
  const h=sides.find(x=>x.side.includes('home')),a=sides.find(x=>x.side.includes('away'));
  if(h&&a&&Number.isFinite(Number(h.goals))&&Number.isFinite(Number(a.goals)))return {h:Number(h.goals),a:Number(a.goals)};
 }
 return null;
}
window.addEventListener('ufi:fixture-selected',event=>{
 const detail=event.detail||{},f=detail.fixture||{},status=f.status&&typeof f.status==='object'?f.status:{};
 const home=f.homeTeam||f.home_team||f.participants?.find?.(x=>String(x?.meta?.location||'').toLowerCase()==='home')?.name;
 const away=f.awayTeam||f.away_team||f.participants?.find?.(x=>String(x?.meta?.location||'').toLowerCase()==='away')?.name;
 if(home)$('lcsHome').value=home;if(away)$('lcsAway').value=away;
 const score=scoreFromFixture(f);if(score){$('lcsCurrentHome').value=score.h;$('lcsCurrentAway').value=score.a;}
 const stateText=String(f?.state?.name||f?.state?.short_name||f?.status||'').toLowerCase();
 const hasLiveState=typeof status.started==='boolean'||/live|in.?play|finished|ended/.test(stateText);
 const live=status.started===true||/live|in.?play/.test(stateText);
 if(hasLiveState)$('lcsMode').value=live?'live':'prematch';
 const clock=status.clock??f?.time?.minute??f?.minute;
 const minuteMatch=String(clock??'').match(/\d{1,3}/);if(live&&minuteMatch)$('lcsMinute').value=Math.min(120,Number(minuteMatch[0]));
 const note=$('lcsFeedStatus');if(note)note.textContent='Selected fixture from '+(detail.source||'provider')+(detail.fallbackUsed?' (fallback source)':'')+'. Team names'+(score?' and sourced score':'')+' updated where available. Expected-goal rates, player profiles and tactical fields remain manual unless verified source data is connected.';
});
$('lcsMode').addEventListener('change',()=>{$('lcsMinuteWrap').style.display=$('lcsMode').value==='live'?'block':'none'});
$('lcsExample').addEventListener('click',()=>{
 $('lcsPlayersHome').value=JSON.stringify([{name:'Home Player A',dominantFoot:'Right',positionSide:'left',rIndex:0.12},{name:'Home Player B',dominantFoot:'Left',positionSide:'left',rIndex:0.2}],null,2);
 $('lcsPlayersAway').value=JSON.stringify([{name:'Away Player A',dominantFoot:'Right',positionSide:'right',rIndex:0.1},{name:'Away Player B',dominantFoot:'Left',positionSide:'right',rIndex:0.18}],null,2);
});
})();
