/* Crainee Unconventional Outcome Engine
 * Additive scenario explorer. Candidate exploration is deliberately independent of odds.
 * Scenario scores are diversity/coverage scores, NOT calibrated outcome probabilities.
 */
'use strict';
(function(root){
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  function int(v, fallback, min, max, name){
    const n=v===undefined||v===null||v===''?fallback:Number(v);
    if(!Number.isInteger(n)||n<min||n>max) throw new TypeError(name+' must be an integer from '+min+' to '+max);
    return n;
  }
  function hashSeed(seed){
    let h=2166136261; for(const c of String(seed)){h^=c.charCodeAt(0);h=Math.imul(h,16777619);}
    return h>>>0;
  }
  function rng(seed){
    let state=hashSeed(seed)||0x6d2b79f5;
    return ()=>{state+=0x6D2B79F5;let t=state;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};
  }
  const scoreKey=s=>s.home+'-'+s.away;
  function uniqueScores(items){
    const seen=new Set(); return items.filter(x=>{const k=scoreKey(x);if(seen.has(k))return false;seen.add(k);return true;});
  }
  function normalizeScore(s){
    if(!s||typeof s!=='object') throw new TypeError('score must be an object');
    return {home:int(s.home,0,0,15,'home goals'),away:int(s.away,0,0,15,'away goals')};
  }
  function generateUnconventionalOutcomes(input={}){
    const seed=input.seed===undefined?'crainee-'+Date.now():String(input.seed);
    if(seed.length>128) throw new TypeError('seed must be 128 characters or fewer');
    const count=int(input.candidateCount,12,4,40,'candidateCount');
    const main=normalizeScore(input.mainModelScore||{home:2,away:1});
    const random=rng(seed);
    const homeName=String(input.homeTeam||'Home').slice(0,80), awayName=String(input.awayTeam||'Away').slice(0,80);
    const maxGoals=int(input.maxGoals,5,2,10,'maxGoals');
    const scenarios=[
      {id:'early-underdog-goal',label:'Underdog scores early',description:'An early goal forces the favourite to chase and opens transition space.',homeBias:-0.45,awayBias:0.7,variance:1.0},
      {id:'red-card-disruption',label:'Red-card tactical break',description:'A sending-off disrupts the original shape; either side can exploit the extra space.',homeBias:0,awayBias:0,variance:1.65},
      {id:'favourite-dominates-blanks',label:'Favourite dominates but blanks',description:'Territory and chances do not become goals; a draw or narrow loss remains possible.',homeBias:-0.65,awayBias:-0.1,variance:0.75},
      {id:'underdog-clinical',label:'Underdog converts few chances',description:'The underdog scores efficiently from limited opportunities.',homeBias:-0.15,awayBias:0.85,variance:1.15},
      {id:'chaotic-open-game',label:'Open, chaotic match',description:'An early swing or broken structure produces a high-variance scoreline.',homeBias:0.1,awayBias:0.1,variance:1.8},
      {id:'late-equaliser',label:'Late equaliser',description:'A late push changes a narrow lead into a draw.',homeBias:0.15,awayBias:0.25,variance:0.9}
    ];
    const pool=[];
    // Anchor a wide score grid so unlikely outcomes aren't excluded by the favourite model.
    for(let h=0;h<=maxGoals;h++) for(let a=0;a<=maxGoals;a++){
      if(h===main.home&&a===main.away) continue;
      const distance=Math.abs(h-main.home)+Math.abs(a-main.away);
      const rarity=(h===0?0.55:0)+(a===0?0.55:0)+(h>=4||a>=4?0.65:0)+(h<a?0.35:0);
      pool.push({home:h,away:a,explorationScore:Number((distance+rarity+random()*0.8).toFixed(4)),distanceFromMain:distance,scenarioId:null,scenarioLabel:'Wide score-space exploration',scenarioDescription:'Generated outside the main model’s exact-score pick; not a probability estimate.'});
    }
    const scenarioScores=[];
    scenarios.forEach(sc=>{
      // Randomly perturb a broad goal baseline; seed fixes all draws and ordering.
      const baseH=clamp(Math.round(main.home+sc.homeBias+(random()-0.5)*sc.variance*4),0,maxGoals);
      const baseA=clamp(Math.round(main.away+sc.awayBias+(random()-0.5)*sc.variance*4),0,maxGoals);
      for(let j=0;j<3;j++){
        const h=clamp(baseH+Math.round((random()-0.5)*sc.variance*3),0,maxGoals);
        const a=clamp(baseA+Math.round((random()-0.5)*sc.variance*3),0,maxGoals);
        if(h===main.home&&a===main.away) continue;
        scenarioScores.push({home:h,away:a,explorationScore:Number((Math.abs(h-main.home)+Math.abs(a-main.away)+sc.variance+random()).toFixed(4)),distanceFromMain:Math.abs(h-main.home)+Math.abs(a-main.away),scenarioId:sc.id,scenarioLabel:sc.label,scenarioDescription:sc.description});
      }
    });
    const merged=uniqueScores(scenarioScores.concat(pool).sort((a,b)=>b.explorationScore-a.explorationScore));
    const unconventional=merged.slice(0,count).map((s,i)=>({...s,rank:i+1,score:scoreKey(s),homeTeam:homeName,awayTeam:awayName,classification:'EXPLORED_POSSIBILITY',probability:null,probabilityStatus:'NOT_ESTIMATED'}));
    return {engine:'Crainee Unconventional Outcome Engine',version:1,seed,seedHash:hashSeed(seed),reproducible:true,mainModelScore:{...main,score:scoreKey(main)},homeTeam:homeName,awayTeam:awayName,conventionalShortlist:input.conventionalShortlist?input.conventionalShortlist.map(normalizeScore).map(s=>({...s,score:scoreKey(s),classification:'CONVENTIONAL_REFERENCE',probabilityStatus:'NOT_RECOMPUTED'})):[],unconventionalShortlist:unconventional,scenarioPaths:scenarios.map(s=>({id:s.id,label:s.label,description:s.description})),method:'Odds-independent score-space exploration with seeded scenario perturbations and diversity ranking.',limitations:['Exploration score is not a probability or evidence of correctness.','Randomness creates coverage, not predictive skill; validate on untouched fixtures before claiming improvement.','Red cards and early goals are hypothetical paths, not assertions about what will happen.']};
  }
  const api={generateUnconventionalOutcomes};
  if(typeof module!=='undefined'&&module.exports) module.exports=api;
  root.CraineeUnconventionalOutcomeEngine=api;
})(typeof globalThis!=='undefined'?globalThis:this);
