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
 function matchFanNarrative(candidates,conditions={}){
  if(!Array.isArray(candidates))throw new TypeError('candidates must be an array');
  const missing=conditions.missingKeyPlayers===undefined?[]:conditions.missingKeyPlayers;if(!Array.isArray(missing)||missing.some(x=>typeof x!=='string'))throw new TypeError('missingKeyPlayers must be an array of names');
  const impacts={missingKeyPlayers:missing.length?1.4:1,weather:conditions.heavyRain===true?1.2:1,referee:finite(conditions.refereeDisruption,1,0.5,2.5,'refereeDisruption')};
  return candidates.map(c=>{const m=String(c.finalAdjustedScore).match(/^(\d+):(\d+)$/);if(!m)throw new TypeError('invalid finalAdjustedScore');const h=+m[1],a=+m[2];let narrative;
   if(h<a&&missing.length)narrative='Post-match narrative hypothesis: fans may cite absent key starters ('+missing.join(', ')+').';
   else if(h===a)narrative='Post-match narrative hypothesis: both fan bases may describe a tight tactical deadlock.';
   else if(h<a)narrative='Post-match narrative hypothesis: home-side fans may discuss defensive or finishing failures.';
   else narrative='Post-match narrative hypothesis: winning-side fans may describe a dominant performance.';
   return {scoreline:c.finalAdjustedScore,qualityScore:Number((c.frictionScore*impacts.missingKeyPlayers*impacts.weather*impacts.referee).toFixed(2)),expectedFanReaction:narrative,zoneOrigin:c.rawZone,unit:c.unit,frictionScore:c.frictionScore,contextFactors:impacts,interpretation:'Narrative matching is descriptive context, not evidence that this scoreline is more likely.'};
  }).sort((a,b)=>b.qualityScore-a.qualityScore);
 }
 function runPipeline(data={},conditions={},isHomeFavorite=true,options={}){const raw=runPositionalMicroSimulations(data),realistic=applyRealitySupervisor(raw,isHomeFavorite,options),ranked=matchFanNarrative(realistic,conditions);
  return {engine:'Crainee Subconscious Neural Databank & Fan Narrative Engine',version:1,pitchUnits:PITCH_TOTAL_UNITS,stepUnits:STEP_UNITS,positionsEvaluated:raw.length,rawPositionalCandidates:raw,realisticCandidates:realistic,rankedCandidates:ranked,selectedScorelines:ranked.slice(0,finite(options.finalLimit,5,1,50,'finalLimit')),confidence:null,confidenceStatus:'NOT_ESTIMATED',caveats:['No actual player tracking, biometric, sentiment corpus or live feed is connected by this module.','The 5400 grid is sampled every 180 units; it is not a microsecond simulation or measured pitch tracking.','Equal line treatment uses the same feature formula for all zones; this is a heuristic, not a trained neural network.','Fan narrative is a descriptive hypothesis, not predictive evidence or a probability.','Validate on chronological held-out matches against simple baselines before claiming predictive improvement.']};
 }
 const api={PITCH_TOTAL_UNITS,STEP_UNITS,runPositionalMicroSimulations,applyRealitySupervisor,matchFanNarrative,runPipeline};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.CraineeSubconsciousNarrativeEngine=api;
})(typeof globalThis!=='undefined'?globalThis:this);
