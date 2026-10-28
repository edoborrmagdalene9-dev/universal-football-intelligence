/* Crainee Subconscious Neural Databank & Fan Narrative Engine. Heuristic scenarios only. */
'use strict';
(function(root){
 const PITCH_TOTAL_UNITS=5400, STEP_UNITS=180, ZONES=['DEFENSE','MIDFIELD','ATTACK'];
 const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
 function finite(v,d,min,max,name){const n=v===undefined||v===null||v===''?d:Number(v);if(!Number.isFinite(n)||n<min||n>max)throw new TypeError(name+' must be a finite number between '+min+' and '+max);return n;}
 function line(s,z,side){const x=(s&&s[z])||{};return {height:finite(x.height,180,140,220,side+'.'+z+'.height'),composure:finite(x.composure,7,1,10,side+'.'+z+'.composure'),footSkill:finite(x.footSkill,5,0,10,side+'.'+z+'.footSkill'),styleFit:finite(x.styleFit,5,0,10,side+'.'+z+'.styleFit')};}
 function runPositionalMicroSimulations(data={}){
  if(!data||typeof data!=='object'||Array.isArray(data))throw new TypeError('matchData must be an object');
  const home=data.homeSquad||{},away=data.awaySquad||{},out=[];
  for(let unit=0;unit<=PITCH_TOTAL_UNITS;unit+=STEP_UNITS){
   const zone=unit<=1800?'DEFENSE':unit<=3600?'MIDFIELD':'ATTACK',h=line(home,zone,'homeSquad'),a=line(away,zone,'awaySquad');
   const hp=h.height/20+h.composure+h.footSkill+h.styleFit,ap=a.height/20+a.composure+a.footSkill+a.styleFit,friction=Math.abs(hp-ap);
   out.push({unit,zone,scoreline:clamp(Math.floor(hp/8+(friction%2)),0,5)+':'+clamp(Math.floor(ap/8+(friction%3)),0,5),friction:Number(friction.toFixed(4)),homeLinePower:Number(hp.toFixed(4)),awayLinePower:Number(ap.toFixed(4))});
  }return out;
 }
 function applyRealitySupervisor(candidates,isHomeFavorite=true,options={}){
  if(!Array.isArray(candidates))throw new TypeError('candidates must be an array');
  const maxH=finite(options.maxHomeGoals,5,0,20,'maxHomeGoals'),maxA=finite(options.maxAwayGoals,4,0,20,'maxAwayGoals'),base=isHomeFavorite?{home:2,away:1}:{home:1,away:1},out=[];
  for(const c of candidates){if(!c||typeof c.scoreline!=='string')continue;const m=c.scoreline.match(/^(\d+):(\d+)$/);if(!m)continue;const h=+m[1]+base.home,a=+m[2]+base.away;
   if(h<=maxH&&a<=maxA&&h+a>0)out.push({rawZone:c.zone,unit:c.unit,finalAdjustedScore:h+':'+a,frictionScore:finite(c.friction,0,0,10000,'friction'),baseVector:base,rawScoreline:c.scoreline});}
  const seen=new Set(),diverse=[];for(const c of out){const k=c.finalAdjustedScore+'|'+c.rawZone;if(!seen.has(k)){seen.add(k);diverse.push(c);}}
  return diverse.slice(0,finite(options.limit,20,1,200,'limit'));
 }
 function calculateCrossDomainSignals(signalSequences=[]){
  if(!Array.isArray(signalSequences))throw new TypeError('signalSequences must be an array');
  return signalSequences.map((entry,index)=>{
   const values=Array.isArray(entry)?entry:(entry&&Array.isArray(entry.values)?entry.values:null);
   if(!values||values.length<2||values.some(v=>!Number.isFinite(Number(v))))throw new TypeError('each cross-domain signal needs at least two finite numeric values');
   const nums=values.map(Number),mean=nums.reduce((a,b)=>a+b,0)/nums.length,variance=nums.reduce((s,v)=>s+(v-mean)**2,0)/nums.length;
   const scale=Math.max(Math.abs(mean),Math.sqrt(variance),1e-9),momentum=(nums[nums.length-1]-nums[0])/scale;
   const volatility=Math.sqrt(variance)/scale,meanReversion=Math.abs(nums[nums.length-1]-mean)/scale;
   return {index,label:entry&&entry.label?String(entry.label):'numeric-sequence-'+(index+1),samples:nums.length,momentum:Number(momentum.toFixed(4)),volatility:Number(volatility.toFixed(4)),meanReversion:Number(meanReversion.toFixed(4)),patternSignal:Number(clamp((Math.abs(momentum)+volatility+meanReversion)/3,0,2).toFixed(4)),interpretation:'Generic numeric-pattern features only; source-domain relevance to football must be validated.'};
  });
 }
 function buildFanReactionCandidates(scoreline,conditions,homeGoals,awayGoals){
  const result=homeGoals===awayGoals?'DRAW':homeGoals>awayGoals?'HOME_WIN':'AWAY_WIN';
  const missing=conditions.missingKeyPlayers||[],homeName=conditions.homeTeamName||'Home team',awayName=conditions.awayTeamName||'Away team';
  const reactions=[];
  const add=(team,theme,text,fit)=>reactions.push({team,theme,text,fit:Number(clamp(fit,0,1).toFixed(3))});
  if(result==='DRAW'){add('both','tight-game','Both fan bases discuss a close tactical battle and missed chances.',0.7);add('both','missed-opportunity','Supporters ask why their team failed to turn chances into a win.',0.65);}
  else {const winner=result==='HOME_WIN'?homeName:awayName,loser=result==='HOME_WIN'?awayName:homeName;
   add(winner,'dominance',winner+' fans celebrate a deserved or clinical win.',0.62);
   add(loser,'referee-complaint',loser+' fans question refereeing decisions.',conditions.refereeDisruption>1.2?0.9:0.42);
   add(loser,'defensive-error',loser+' fans blame a defensive lapse or transition failure.',conditions.defensiveErrorSignal>0.5?0.9:0.58);
   add(loser,'finishing',loser+' fans blame missed chances or poor finishing.',0.62);
   if(missing.length)add(loser,'missing-starters',loser+' fans point to unavailable players: '+missing.join(', ')+'.',0.95);
   if(conditions.heavyRain)add(loser,'weather',loser+' fans say weather and pitch conditions disrupted the game.',0.82);
   if(conditions.homeAwayStreak)add(loser,'streak',loser+' fans point to the team streak: '+String(conditions.homeAwayStreak)+'.',0.72);
   if(conditions.coachPressure)add(loser,'coach',loser+' fans question the coach and substitutions.',0.72);
  }
  if(Array.isArray(conditions.fanNarratives))for(const n of conditions.fanNarratives){if(n&&typeof n.text==='string')add(n.team||'both',n.theme||'custom',n.text,finite(n.fit,0.5,0,1,'fanNarrative.fit'));}
  return reactions.map(r=>({...r,scoreline,matchContextFit:Number((r.fit*(conditions.heavyRain?1.08:1)*(conditions.missingKeyPlayers&&conditions.missingKeyPlayers.length&&r.theme==='missing-starters'?1.12:1)).toFixed(4))}));
 }
 function matchFanNarrative(candidates,conditions={}){
  if(!Array.isArray(candidates))throw new TypeError('candidates must be an array');
  const missing=conditions.missingKeyPlayers===undefined?[]:conditions.missingKeyPlayers;if(!Array.isArray(missing)||missing.some(x=>typeof x!=='string'))throw new TypeError('missingKeyPlayers must be an array of names');
  const impacts={missingKeyPlayers:missing.length?1.4:1,weather:conditions.heavyRain===true?1.2:1,referee:finite(conditions.refereeDisruption,1,0.5,2.5,'refereeDisruption')};
  const crossDomain=calculateCrossDomainSignals(conditions.crossDomainSignals||[]);
  return candidates.map(c=>{const m=String(c.finalAdjustedScore).match(/^(\d+):(\d+)$/);if(!m)throw new TypeError('invalid finalAdjustedScore');const h=+m[1],a=+m[2];let narrative;
   if(h<a&&missing.length)narrative='Post-match narrative hypothesis: fans may cite absent key starters ('+missing.join(', ')+').';
   else if(h===a)narrative='Post-match narrative hypothesis: both fan bases may describe a tight tactical deadlock.';
   else if(h<a)narrative='Post-match narrative hypothesis: home-side fans may discuss defensive or finishing failures.';
   else narrative='Post-match narrative hypothesis: winning-side fans may describe a dominant performance.';
   const reactions=buildFanReactionCandidates(c.finalAdjustedScore,conditions,h,a);
   const bestReaction=reactions.slice().sort((x,y)=>y.matchContextFit-x.matchContextFit)[0]||{team:'both',theme:'general',text:narrative,matchContextFit:0.5};
   const contradiction=Number(clamp((Math.abs(h-a)/Math.max(h+a,1))*0.25+(conditions.defensiveErrorSignal?clamp(Number(conditions.defensiveErrorSignal),0,1)*0.25:0)+(conditions.tacticalShiftSignal?clamp(Number(conditions.tacticalShiftSignal),0,1)*0.25:0),0,1).toFixed(4));
   const crossSignal=crossDomain.length?crossDomain.reduce((s,x)=>s+x.patternSignal,0)/crossDomain.length:0;
   const quality=Number((c.frictionScore*impacts.missingKeyPlayers*impacts.weather*impacts.referee + bestReaction.matchContextFit*10 + contradiction*5 + crossSignal).toFixed(2));
   return {scoreline:c.finalAdjustedScore,qualityScore:quality,expectedFanReaction:bestReaction.text,fanReactionCandidates:reactions,selectedFanReaction:bestReaction,zoneOrigin:c.rawZone,unit:c.unit,frictionScore:c.frictionScore,contradictionSignal:contradiction,crossDomainSignals:crossDomain,contextFactors:impacts,interpretation:'Fan reaction fit materially contributes to ranking as requested; it is a heuristic, not evidence of a calibrated probability.'};
  }).sort((a,b)=>b.qualityScore-a.qualityScore);
 }
 function runPipeline(data={},conditions={},isHomeFavorite=true,options={}){const raw=runPositionalMicroSimulations(data),realistic=applyRealitySupervisor(raw,isHomeFavorite,options),ranked=matchFanNarrative(realistic,conditions);
  return {engine:'Crainee Subconscious Neural Databank & Fan Narrative Engine',version:2,pitchUnits:PITCH_TOTAL_UNITS,stepUnits:STEP_UNITS,positionsEvaluated:raw.length,rawPositionalCandidates:raw,realisticCandidates:realistic,rankedCandidates:ranked,selectedScorelines:ranked.slice(0,finite(options.finalLimit,5,1,50,'finalLimit')),confidence:null,confidenceStatus:'NOT_ESTIMATED',caveats:['No actual player tracking, biometric, sentiment corpus or live feed is connected by this module.','The 5400 grid is sampled every 180 units; it is not a microsecond simulation or measured pitch tracking.','Equal line treatment uses the same feature formula for all zones; this is a heuristic, not a trained neural network.','Fan narrative is a descriptive hypothesis, not predictive evidence or a probability.','Validate on chronological held-out matches against simple baselines before claiming predictive improvement.']};
 }
 const api={PITCH_TOTAL_UNITS,STEP_UNITS,runPositionalMicroSimulations,applyRealitySupervisor,calculateCrossDomainSignals,buildFanReactionCandidates,matchFanNarrative,runPipeline};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.CraineeSubconsciousNarrativeEngine=api;
})(typeof globalThis!=='undefined'?globalThis:this);
