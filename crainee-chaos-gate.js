(function(){
'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=n=>'₦'+Number(n).toLocaleString('en-NG',{maximumFractionDigits:2});
function squadScore(players){
 if(!Array.isArray(players)||players.length===0)throw Error('Each team needs a non-empty players JSON array.');
 let total=0,assumptions=[];
 players.forEach((p,i)=>{
  if(!p||typeof p!=='object')throw Error('Player row '+(i+1)+' must be an object.');
  const marketValue=p.marketValue==null?1000000:Number(p.marketValue);
  const age=p.age==null?26:Number(p.age);
  const caps=p.caps==null?30:Number(p.caps);
  if(!Number.isFinite(marketValue)||marketValue<0||!Number.isFinite(age)||age<15||age>60||!Number.isFinite(caps)||caps<0)throw Error('Invalid marketValue, age or caps for player row '+(i+1)+'.');
  if(p.marketValue==null||p.age==null||p.caps==null)assumptions.push((p.name||('Player '+(i+1)))+': defaulted '+[p.marketValue==null?'marketValue':'',p.age==null?'age':'',p.caps==null?'caps':''].filter(Boolean).join(', '));
  const ageWeight=Math.exp(-0.015*Math.pow(age-27,2));
  const expWeight=Math.log10(caps+10);
  total+=marketValue*ageWeight*expWeight;
 });
 return {score:total,assumptions};
}
function evaluate(){
 const out=$('caOutput');
 try{
  const currentRaw=$('caCurrentSecond').value,bankrollRaw=$('caBankroll').value;
  if(currentRaw===''||bankrollRaw==='')throw Error('Enter elapsed seconds and bankroll (use 0 if you do not want a stake cap).');
  const current=Number(currentRaw),bankroll=Number(bankrollRaw);
  if(!Number.isFinite(current)||current<0||current>6000)throw Error('Elapsed seconds must be between 0 and 6000, including stoppage time.');
  if(!Number.isFinite(bankroll)||bankroll<0)throw Error('Bankroll must be zero or greater.');
  const home=squadScore(JSON.parse($('caHomeSquad').value||'null')),away=squadScore(JSON.parse($('caAwaySquad').value||'null'));
  const referee=JSON.parse($('caReferee').value||'{}');
  const first=referee.avgWhistleGap1to45==null?120:Number(referee.avgWhistleGap1to45);
  const second=referee.avgWhistleGap45to90==null?85:Number(referee.avgWhistleGap45to90);
  if(!Number.isFinite(first)||first<=0||!Number.isFinite(second)||second<=0)throw Error('Referee whistle gaps must be positive numbers in seconds.');
  const elapsed=Math.min(MATCH_TOTAL_SECONDS,current),isSecondHalf=current>HALF_TIME_SECONDS;
  const activeGap=isSecondHalf?second:first,flow=Math.min(1.2,activeGap/100);
  const assets=home.score+away.score;
  const power=Math.max(0,Math.min(1,Math.log10(assets+1)/15));
  const timeWeight=elapsed/MATCH_TOTAL_SECONDS;
  const composite=power*flow*(1+timeWeight);
  const phase=isSecondHalf?'Second Half (45m - 90m)':'First Half (1m - 45m)';
  const common='<p>Elapsed time: '+Math.floor(current/60)+' minutes ('+current+'s; regulation frame '+elapsed+'/5400s). Phase: '+phase+'. Active average whistle gap: '+activeGap+' seconds.</p><p>Squad asset score: home '+home.score.toFixed(0)+'; away '+away.score.toFixed(0)+'. Normalized squad power: '+power.toFixed(3)+'. Referee flow factor: '+flow.toFixed(3)+'. Time weight: '+timeWeight.toFixed(3)+'.</p>';
  if(composite<0.25){
   out.innerHTML='<b>DISCARDED — composite score below 0.250.</b><p>Score: '+composite.toFixed(3)+'. The supplied squad/referee/time heuristic did not meet the experimental threshold.</p>'+common;
   return;
  }
  const riskPct=Math.min(0.05,Math.max(0,0.05*composite));
  const stake=bankroll*riskPct;
  const assumptions=home.assumptions.concat(away.assumptions);
  out.innerHTML='<b>Survived current heuristic gate — not a betting approval.</b><p>Composite score: '+composite.toFixed(3)+' (threshold 0.250).</p>'+common+'<p>Heuristic stake cap: '+(riskPct*100).toFixed(2)+'% of entered bankroll = '+money(stake)+'. Hard ceiling is 5%; if bankroll is zero, cap is ₦0.</p>'+(assumptions.length?'<p><b>Defaulted inputs:</b> '+esc(assumptions.join('; '))+'</p>':'<p>All player market values, ages and caps were supplied.</p>')+'<p class="muted">This score is not a calibrated win probability or measured positive expected value. It does not account for player minutes, injuries, replacement quality, league/market calibration, or actual referee event distributions. A larger squad valuation does not automatically mean a bet has an edge.</p>';
 }catch(e){out.innerHTML='<b>Cannot clear match.</b><br>'+esc(e.message);}
}
function example(){
 $('caCurrentSecond').value='1800';$('caBankroll').value='10000';
 $('caHomeSquad').value=JSON.stringify([{name:'Home A',marketValue:25000000,age:27,caps:40},{name:'Home B',marketValue:18000000,age:25,caps:25},{name:'Home C',marketValue:12000000,age:29,caps:55}],null,2);
 $('caAwaySquad').value=JSON.stringify([{name:'Away A',marketValue:20000000,age:26,caps:35},{name:'Away B',marketValue:15000000,age:24,caps:20},{name:'Away C',marketValue:9000000,age:30,caps:45}],null,2);
 $('caReferee').value=JSON.stringify({avgWhistleGap1to45:120,avgWhistleGap45to90:85},null,2);
}
const MATCH_TOTAL_SECONDS=5400,HALF_TIME_SECONDS=2700;
if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',()=>{
 if(!$('caRun'))return;
 $('caRun').addEventListener('click',evaluate);
 $('caExample').addEventListener('click',example);
 $('caClear').addEventListener('click',()=>{['caHomeSquad','caAwaySquad','caReferee'].forEach(id=>$(id).value='');$('caOutput').textContent='Cleared. No match is cleared by default.'});
});
if(typeof module!=='undefined'&&module.exports)module.exports={evaluateAdvancedMatchRiskAndEdge:function(matchData,userBankroll){
 const current=Number(matchData.currentSecond||0);
 if(!Array.isArray(matchData.homeTeam?.players)||!Array.isArray(matchData.awayTeam?.players)||!matchData.referee)throw Error('Provide homeTeam.players, awayTeam.players and referee.');
 function calc(players){if(!Array.isArray(players)||players.length===0)throw Error('Each team requires a non-empty players array');return players.reduce((acc,p)=>{const value=p.marketValue==null?1000000:Number(p.marketValue),age=p.age==null?26:Number(p.age),caps=p.caps==null?30:Number(p.caps);if(!Number.isFinite(value)||value<0||!Number.isFinite(age)||age<15||age>60||!Number.isFinite(caps)||caps<0)throw Error('Invalid player attributes');return acc+value*Math.exp(-0.015*Math.pow(age-27,2))*Math.log10(caps+10)},0)}
 const hs=calc(matchData.homeTeam.players),as=calc(matchData.awayTeam.players),ref=matchData.referee,second=current>2700;
 const gap=Number((second?ref.avgWhistleGap45to90:ref.avgWhistleGap1to45)??(second?85:120));
 if(!Number.isFinite(gap)||gap<=0||!Number.isFinite(Number(userBankroll))||Number(userBankroll)<0)throw Error('Invalid referee gap or bankroll');
 const flow=Math.min(1.2,gap/100),power=Math.max(0,Math.min(1,Math.log10(hs+as+1)/15)),time=Math.min(5400,Math.max(0,current))/5400,score=power*flow*(1+time),pct=score<0.25?0:Math.min(0.05,Math.max(0,0.05*score));
 return {status:score<0.25?'DISCARDED':'SURVIVED_AND_APPROVED',currentMatchTime:Math.floor(current/60)+' minutes ('+current+'s / 5400s)',matchPhase:second?'Second Half (45m - 90m)':'First Half (1m - 45m)',activeWhistleGap:gap+' seconds average between whistles',squadPowerIndex:power.toFixed(3),refereeFlowFactor:flow.toFixed(3),compositeEdgeScore:score.toFixed(3),maxSafeStakeLimit:(pct*100).toFixed(2)+'%',recommendedStakeAmount:(Number(userBankroll)*pct).toFixed(2),reason:score<0.25?'Composite score below 0.250':'Passed heuristic only; not proof of positive EV'};
}};
})();