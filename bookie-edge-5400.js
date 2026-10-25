(function(){
'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>(100*x).toFixed(2)+'%';
function evaluate(){
 const out=$('beOutput');
 try{
  const minute=Number($('beMinute').value),maxAge=Number($('beMaxAge').value),minEV=Number($('beMinEV').value)/100,maxUncertainty=Number($('beMaxUncertainty').value)/100,minSamples=Number($('beMinSamples').value),minSnapshots=Number($('beMinSnapshots').value),minProb=Number($('beMinProbability').value)/100,minEdge=Number($('beMinEdge').value)/100;
  if(!Number.isFinite(minute)||minute<0||minute>130||!Number.isFinite(maxAge)||maxAge<1||![minEV,maxUncertainty,minSamples,minSnapshots,minProb,minEdge].every(Number.isFinite))throw Error('Check the gate settings; values must be numeric and valid.');
  const candidates=JSON.parse($('beCandidates').value||'[]');
  if(!Array.isArray(candidates)||!candidates.length)throw Error('Enter at least one candidate.');
  const now=Date.now(),elapsedSeconds=Math.min(5400,Math.max(0,Math.floor(Math.min(minute,90)*60))),checkpointCount=elapsedSeconds;
  const results=candidates.map((c,i)=>{
   const reasons=[];
   const odds=Number(c.odds),p=Number(c.modelProbability),market=Number(c.marketProbability),unc=Number(c.uncertainty),samples=Number(c.validationMatches),snaps=Number(c.snapshots);
   const sourceMs=Date.parse(c.sourceUpdatedAt||'');
   const valid=Number.isFinite(odds)&&odds>1&&Number.isFinite(p)&&p>0&&p<1&&Number.isFinite(market)&&market>=0&&market<=1&&Number.isFinite(unc)&&unc>=0&&unc<=1&&Number.isFinite(samples)&&samples>=0&&Number.isFinite(snaps)&&snaps>=0&&Number.isFinite(sourceMs);
   if(!valid)reasons.push('Missing/invalid odds, probabilities, uncertainty, validation counts or source timestamp');
   const age=valid?(now-sourceMs)/1000:Infinity;
   if(valid&&age< -5)reasons.push('Provider source timestamp is in the future');
   if(valid&&age>maxAge)reasons.push('Stale source odds ('+Math.round(age)+' seconds old)');
   if(valid&&samples<minSamples)reasons.push('Insufficient independent out-of-sample validation matches');
   if(valid&&snaps<minSnapshots)reasons.push('Too few distinct timestamped market snapshots');
   if(valid&&unc>maxUncertainty)reasons.push('Probability uncertainty exceeds limit');
   if(valid&&p<minProb)reasons.push('Model probability below configured floor');
   const conservativeP=valid?Math.max(0,p-1.645*unc):0;
   const conservativeEV=valid?conservativeP*odds-1: -1;
   const conservativeEdge=valid?conservativeP-market: -1;
   if(valid&&conservativeEV<minEV)reasons.push('Conservative net EV '+pct(conservativeEV)+' below required '+pct(minEV));
   if(valid&&conservativeEdge<minEdge)reasons.push('Conservative edge versus supplied market probability '+(conservativeEdge*100).toFixed(2)+'pp below threshold');
   const survive=reasons.length===0;
   return {selection:c.selection||('Candidate '+(i+1)),odds,modelProbability:p,marketProbability:market,uncertainty:unc,conservativeP,conservativeEV,conservativeEdge,age,survive,reasons};
  });
  const approved=results.filter(x=>x.survive).length;
  const rows=results.map(r=>'<tr><td>'+esc(r.selection)+'</td><td>'+esc(Number.isFinite(r.odds)?r.odds.toFixed(2):'—')+'</td><td>'+esc(Number.isFinite(r.modelProbability)?pct(r.modelProbability):'—')+'</td><td>'+esc(Number.isFinite(r.conservativeP)?pct(r.conservativeP):'—')+'</td><td>'+esc(Number.isFinite(r.conservativeEV)?pct(r.conservativeEV):'—')+'</td><td>'+esc(Number.isFinite(r.conservativeEdge)?(r.conservativeEdge*100).toFixed(2)+'pp':'—')+'</td><td><b>'+ (r.survive?'SURVIVES CURRENT GATE':'DISCARD')+'</b><br>'+esc(r.reasons.join('; ')||'All configured filters passed on this evaluation only')+'</td></tr>').join('');
  out.innerHTML='<b>'+approved+' / '+results.length+' candidates pass the current gate.</b><br>Match clock: '+minute+'′ · 5400-second frame: '+checkpointCount+' elapsed checkpoints out of 5400 (90 minutes).<p class="muted">The gate evaluated current supplied data once. It cannot prove 5400 future observations will pass. Re-run when new source data arrives; repeated unchanged inputs are not independent evidence.</p><div class="table-wrap"><table><thead><tr><th>Selection</th><th>Odds</th><th>Model P</th><th>Conservative P</th><th>Conservative EV</th><th>Edge</th><th>Decision / reason</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
 }catch(e){out.innerHTML='<b>Cannot approve any selection.</b><br>'+esc(e.message); }
}
function example(){
 const ts=new Date().toISOString();
 $('beCandidates').value=JSON.stringify([
  {selection:'Example A — strong hypothetical',odds:2.5,modelProbability:0.5,marketProbability:0.38,uncertainty:0.015,sourceUpdatedAt:ts,validationMatches:600,snapshots:5},
  {selection:'Example B — weak hypothetical',odds:3.1,modelProbability:0.3,marketProbability:0.32,uncertainty:0.06,sourceUpdatedAt:ts,validationMatches:600,snapshots:5},
  {selection:'Example C — stale price',odds:4.5,modelProbability:0.28,marketProbability:0.21,uncertainty:0.02,sourceUpdatedAt:'2020-01-01T00:00:00Z',validationMatches:900,snapshots:6}
 ],null,2);
}
document.addEventListener('DOMContentLoaded',()=>{
 if(!$('beRun'))return;
 $('beRun').addEventListener('click',evaluate);
 $('beExample').addEventListener('click',example);
 $('beClear').addEventListener('click',()=>{$('beCandidates').value='';$('beOutput').textContent='Cleared. No candidate is approved by default.'});
});
})();
