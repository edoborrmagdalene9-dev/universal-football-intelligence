/* Universal Match State + All-Event Simulation + Low-Variance Trap Engine
 * Research prototype. Manual inputs only; no live data source is implied.
 */
(() => {
'use strict';
const $=id=>document.getElementById(id), clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=id=>Number($(id).value);
function readJson(id, fallback){try{const x=JSON.parse($(id).value||JSON.stringify(fallback));if(!x||typeof x!=='object')throw Error('Expected JSON object/array');return x}catch(e){throw Error(id+': '+e.message)}}
function poisson(k,l){let p=Math.exp(-l);for(let i=1;i<=k;i++)p*=l/i;return p}
function scores(h,a,lh,la,live){const out=[];for(let i=h;i<=h+8;i++)for(let j=a;j<=a+8;j++){out.push({h:i,a:j,p:poisson(i-h,lh)*poisson(j-a,la)})}const sum=out.reduce((s,x)=>s+x.p,0)||1;out.forEach(x=>x.p/=sum);return out.sort((x,y)=>y.p-x.p)}
function run(){
 const home=$('umeHome').value.trim()||'Home',away=$('umeAway').value.trim()||'Away',minute=clamp(num('umeMinute')||0,0,120);
 const live=$('umeLive').checked, curH=Math.max(0,Math.floor(num('umeScoreH')||0)),curA=Math.max(0,Math.floor(num('umeScoreA')||0));
 const state=readJson('umeState',{});
 const events=readJson('umeEvents',[]);
 if(!Array.isArray(events))throw Error('Event timeline must be a JSON array.');
 const hprof=state.home||{},aprof=state.away||{},env=state.environment||{},ref=state.referee||{};
 let lh=clamp(num('umeXgH')||0,0,6),la=clamp(num('umeXgA')||0,0,6);
 const notes=[],zoneRisk={home:0,away:0};let mds=0,drift=0,ss=0,reds=0,warning=false,woodwork=0,setpieces=0;
 // Structural baseline: low-block + dominant opposing possession suppresses high-danger expected goals.
 function stagnation(team,opponent){const low=String(team.block||'').toLowerCase()==='low';const poss=Number(opponent.possessionShare)||50;return low&&poss>=60?0.22:0}
 const stagH=stagnation(hprof,aprof),stagA=stagnation(aprof,hprof);
 lh*=1-stagH;la*=1-stagA;
 const ppdaH=Number(hprof.ppda),ppdaA=Number(aprof.ppda);
 const staminaH=clamp(Number(hprof.staminaDip80)||0,0,0.5),staminaA=clamp(Number(aprof.staminaDip80)||0,0,0.5);
 if(live&&minute>=60){lh*=1-staminaH*Math.min(1,(minute-60)/20);la*=1-staminaA*Math.min(1,(minute-60)/20)}
 // Environmental/referee factors are bounded and modest until empirically calibrated.
 const rain=clamp(Number(env.rain)||0,0,1),wind=clamp(Number(env.wind)||0,0,1),pitch=String(env.pitch||'normal').toLowerCase();
 const envFactor=clamp(1-0.08*rain-0.06*wind-(pitch==='poor'?0.08:0),0.65,1.05);lh*=envFactor;la*=envFactor;
 const strict=clamp(Number(ref.strictness)||0,0,1);let yellows={home:0,away:0};
 for(const e of events){
  const type=String(e.type||'').toLowerCase(),team=e.team==='away'?'away':'home',opp=team==='home'?'away':'home';
  const t=team==='home'?'H':'A',o=team==='home'?'A':'H';let level=1;
  if(['foul','yellow','minor_foul'].includes(type)){yellows[team]++;zoneRisk[team]+=.15;mds+=.08+strict*.05;notes.push('Level 1 · '+type+' ('+team+'): aggression and late-card risk updated.')}
  else if(['red','second_yellow','direct_red'].includes(type)){reds++;level=2;if(team==='home'){lh=Math.max(0,lh-.40);la=Math.min(6,la+.35)}else{la=Math.max(0,la-.40);lh=Math.min(6,lh+.35)}mds+=.6;notes.push('Level 2 · red card ('+team+'): attack and concession rates adjusted.')}
  else if(['manager_red','bench_red'].includes(type)){drift+=.10;mds+=.2;level=2;notes.push('Level 2 · bench/manager red: positioning drift increased.')}
  else if(['key_playmaker_out','playmaker_injury'].includes(type)){if(team==='home')lh*=.8;else la*=.8;level=2;notes.push('Level 2 · key playmaker out: transition velocity reduced 20%.')}
  else if(['keeper_injury','keeper_sub'].includes(type)){if(team==='home')la*=1.25;else lh*=1.25;level=2;notes.push('Level 2 · keeper change: opposing conversion factor +25% (experimental).')}
  else if(['attacking_sub','formation_attack'].includes(type)){if(team==='home')lh*=1.08;else la*=1.08;level=2;notes.push('Level 2 · attacking tactical switch: attacking branch widened.')}
  else if(['defensive_sub','formation_defend'].includes(type)){if(team==='home')lh*=.94;else la*=.94;level=2;notes.push('Level 2 · defensive switch: attack expectation reduced slightly.')}
  else if(['var_goal_cancelled','var_cancellation'].includes(type)){if(team==='home')la*=1.15;else lh*=1.15;mds+=.35;level=2;notes.push('Level 2 · VAR goal cancellation: opposing momentum +15% (10-minute heuristic).')}
  else if(type==='penalty_scored'){if(team==='home')lh=Math.max(lh,0)+.0;else la=Math.max(la,0)+.0;notes.push('Penalty scored: current score must be updated by the data operator.')}
  else if(type==='penalty_missed'){if(team==='home')la*=1.05;else lh*=1.05;mds+=.15;notes.push('Missed penalty: opposing momentum drift increased.')}
  else if(['controversial_call','officiating_delay','pitch_degradation'].includes(type)){mds+=.4;warning=true;level=3;notes.push('Level 3 · '+type+': virtual caution; check market divergence and reduce model weight.')}
  else if(type==='early_goal'){lh*=1.3;la*=1.3;level=2;notes.push('Level 2 · early goal: open-play factor ×1.3.')}
  else if(type==='woodwork'){woodwork++;mds+=.08;notes.push('Pressure spike: woodwork event counted.')}
  else if(type==='set_piece'){setpieces++;notes.push('Pressure spike: set-piece sequence counted.')}
  else if(type==='own_goal'||type==='defensive_howler'){if(team==='home')la=Math.max(la,0);else lh=Math.max(lh,0);mds+=.2;notes.push('Mechanical-defect mark: clean-sheet probability for the affected side is treated as zero for this phase; update current score if goal was awarded.')}
  else if(type==='non_dominant_foot_error'){mds+=.12;warning=true;notes.push('Pressing vulnerability metric increased after non-dominant-foot error.')}
  else if(type==='transition'){ss+=1}
  else if(type==='box_entry'){ss+=1}
  else if(type==='high_disruption'){mds+=.5;warning=true;level=3;notes.push('Level 3 · high disruption: odds divergence check recommended.')}
  if(e.critical===true||type==='multi_red_anomaly')mds+=1;
 }
 // Late desperation expands the trailing team's attacking branch and counter exposure.
 if(live&&minute>=75&&Math.abs(curH-curA)===1){if(curH<curA)lh*=1.15;else la*=1.15;mds+=.05;notes.push('Late desperation phase: trailing-side attack expectation +15% (heuristic).')}
 // Tempo / entropy / trap metrics use the operator-entered event evidence and profile fields.
 const transitions=Math.max(0,Number(state.transitions)||0),entries=Math.max(0,Number(state.finalThirdEntries)||0),progressive=Math.max(0,Number(state.progressivePasses)||0);
 const expectedTransitions=Math.max(1,Number(state.expectedTransitions)||8),expectedEntries=Math.max(1,Number(state.expectedFinalThirdEntries)||12);
 const tempoRate=(transitions+progressive*.15+entries*.2)/(expectedTransitions+expectedEntries*.2);
 const tsi=clamp(1-tempoRate,0,1),entropy=clamp(Number(state.entropy)||((mds+drift+woodwork*.08+setpieces*.03)/3),0,1);
 const lvts=clamp((stagH+stagA)/.44*.45+tsi*.35+(1-entropy)*.20,0,1);
 const tcs=clamp(mds+drift+reds*.45+zoneRisk.home+zoneRisk.away,0,10);
 const limit=Number($('umeChaosLimit').value)||2.5;
 const discarded=reds>=2||mds>=limit||tcs>=limit*1.8;
 const trap=lvts>=.68&&!discarded;
 if(trap){lh*=.78;la*=.78;warning=true;notes.push('TRAP GAME LOCKED: Low-Variance Sterile Environment Confirmed (Shifting to Tight Score Matrix).')}
 if(warning&&!discarded){lh*=.94;la*=.94}
 lh=clamp(lh,0,6);la=clamp(la,0,6);
 const top=scores(curH,curA,lh,la,live).slice(0,3);
 const green=!discarded&&!warning&&mds<.5&&tcs<limit&&stagH+stagA<.1;
 const flag=discarded?'MATCH DISCARDED: High Multi-Event Anomaly.':trap?'TRAP GAME LOCKED: Low-Variance Sterile Environment Confirmed (Shifting to Tight Score Matrix).':green?'UNIVERSAL SIMULATION APPROVED: Clean Multi-Outcome Verification.':'VIRTUAL CAUTION: Structural/event anomaly detected; reduce model weight and review data.';
 $('umeOutput').innerHTML='<div class="notice '+(discarded||warning?'warning':'good')+'"><b>'+esc(flag)+'</b></div>'+
 '<div class="outcome-grid"><div><span>Home adjusted remaining xG*</span><b>'+lh.toFixed(2)+'</b></div><div><span>Away adjusted remaining xG*</span><b>'+la.toFixed(2)+'</b></div><div><span>Tempo Suppression Index</span><b>'+tsi.toFixed(2)+'</b></div><div><span>Entropy / LVTS</span><b>'+entropy.toFixed(2)+' / '+lvts.toFixed(2)+'</b></div><div><span>Match Disruption Score</span><b>'+mds.toFixed(2)+'</b></div><div><span>Team Chaos Score</span><b>'+tcs.toFixed(2)+'</b></div></div>'+
 (discarded?'<p>Predictions suppressed by the Level 4 circuit breaker.</p>':'<h3>Top 3 final-score branches</h3><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Final score</th><th>Model probability</th></tr></thead><tbody>'+top.map((x,i)=>'<tr><td>'+(i+1)+'</td><td><b>'+x.h+'–'+x.a+'</b></td><td>'+(x.p*100).toFixed(2)+'%</td></tr>').join('')+'</tbody></table></div>')+
 '<h3>State shift audit</h3><ul>'+notes.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>'+
 '<p class="muted">This simulation is deterministic from manually entered state/events; it does not detect events automatically or run a millisecond feed. Environment, referee, fatigue, SSIS, TSI, entropy and LVTS are heuristic prototypes and need chronological historical validation. *Adjusted remaining xG is not provider-verified xG.</p>';
}
$('umeRun').addEventListener('click',()=>{try{run()}catch(e){$('umeOutput').innerHTML='<div class="notice warning">'+esc(e.message)+'</div>'}});
$('umeExample').addEventListener('click',()=>{
 $('umeState').value=JSON.stringify({home:{block:'low',ppda:12,staminaDip80:.15,possessionShare:38},away:{block:'mid',ppda:9,staminaDip80:.1,possessionShare:62},environment:{pitch:'normal',rain:.2,wind:.1,temperatureC:23},referee:{strictness:.5,avgYellow:4.2,avgRed:.15,penaltyIndex:1},transitions:3,expectedTransitions:8,finalThirdEntries:4,expectedFinalThirdEntries:12,progressivePasses:10,entropy:.25},null,2);
 $('umeEvents').value=JSON.stringify([{type:'foul',team:'home'},{type:'box_entry',team:'away'},{type:'set_piece',team:'away'}],null,2);
});
})();
