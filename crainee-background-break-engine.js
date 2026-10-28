/* Crainee Background Engine: Match-Can-Break-This-Way Simulator.
 * Additive scenario signal engine. Rupture scores are heuristic indices, not probabilities.
 */
'use strict';
(function(root){
 const PITCH_TOTAL_UNITS=5400;
 const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
 function number(v,fallback,min,max,name){
  const n=v===undefined||v===null||v===''?fallback:Number(v);
  if(!Number.isFinite(n)||n<min||n>max)throw new TypeError(name+' must be between '+min+' and '+max);
  return n;
 }
 function simulateMatchBreakScenarios(matchData={}){
  const grid=number(matchData.ballPositionUnit,2700,0,PITCH_TOTAL_UNITS,'ballPositionUnit');
  const underdog=matchData.underdog||{};
  const favorite=matchData.favorite||{};
  const environment=matchData.environment||{};
  const referee=matchData.referee||{};
  const headStart=matchData.underdogScoredFirst===true;
  const headStartMultiplier=headStart?1.6:1.0;
  const errorRate=number(favorite.defenderErrorTendency,7,1,10,'favorite.defenderErrorTendency');
  const transition=number(underdog.attackerTransitionPacing,8,1,10,'underdog.attackerTransitionPacing');
  const exploitation=(errorRate*0.1)*(transition*0.1)*headStartMultiplier;
  const weather=environment.isHeavyRainOrWind===true?1.3:1.0;
  const whistle=number(referee.whistleFrequencyChaos,1.2,0.5,2.5,'referee.whistleFrequencyChaos');
  const environmental=weather*whistle;
  const spatial=(grid/PITCH_TOTAL_UNITS)*environmental;
  const rupture=exploitation*spatial*2.5;
  const threshold=number(matchData.breakThreshold,2.0,0.1,20,'breakThreshold');
  const broken=rupture>=threshold;
  const paths=[
   {id:'underdog-head-start',active:headStart,label:'Underdog scores first',description:'The favourite must chase; transition space may open.'},
   {id:'defensive-error-chain',active:errorRate>=7&&transition>=7,label:'Defensive error chain',description:'A defensive mistake meets a fast transition attack.'},
   {id:'weather-friction',active:weather>1,label:'Heavy rain or wind',description:'Conditions may disrupt passing rhythm.'},
   {id:'referee-disruption',active:whistle>=1.5,label:'High whistle disruption',description:'Frequent stoppages may break match rhythm.'},
   {id:'spatial-fracture',active:grid>=3600,label:'Advanced pitch position',description:'Ball position is in the attacking/final-third range of the 5400-unit grid.'}
  ];
  const outcomeCandidates=broken?
   (headStart?[{score:'0-2',label:'Underdog shock win'},{score:'0-3',label:'Underdog blowout'},{score:'1-3',label:'Open upset'}]:[{score:'1-2',label:'Late collapse'},{score:'0-2',label:'Favourite collapse'},{score:'2-3',label:'Chaotic high-scoring upset'}]):
   [{score:'0-0',label:'Low-event draw'},{score:'1-1',label:'Level match'},{score:'1-0 / 0-1',label:'Narrow result'}];
  return {
   engine:'Crainee Background Engine: Match-Can-Break-This-Way Simulator',version:1,
   simulationStatus:broken?'MATCH_STRUCTURE_BREAK_SIGNAL':'SCRIPT_NOT_BROKEN_BY_THIS_HEURISTIC',
   pitchGridCoordinate:grid+' / '+PITCH_TOTAL_UNITS,
   underdogHeadStart:headStart,headStartMultiplier:Number(headStartMultiplier.toFixed(3)),
   errorExploitationScore:Number(exploitation.toFixed(4)),
   environmentalChaosFactor:Number(environmental.toFixed(4)),
   spatialFractureIndex:Number(spatial.toFixed(4)),
   ruptureIndex:Number(rupture.toFixed(4)),breakThreshold:threshold,
   scenarioPaths:paths,exactScoreExploration:outcomeCandidates,
   interpretation:broken?'A structural-break scenario is flagged for exploration; this is not a prediction or a calibrated upset probability.':'This input combination did not cross the heuristic threshold; unexpected scores remain possible.',
   confidence:Number(clamp((rupture/threshold)*100,0,100).toFixed(1)),
   confidenceStatus:'HEURISTIC_SIGNAL_PERCENT_NOT_CALIBRATED_PROBABILITY',
   confidenceIsProbability:false,
   limitations:[
    'The confidence percentage is retained as a heuristic signal-strength indicator derived from ruptureIndex / breakThreshold, capped at 100; it is not the chance of an upset and is not calibrated.',
    'A head start is only active when underdogScoredFirst is explicitly true; missing input is not silently treated as true.',
    'A scoreline cannot be inferred reliably from these inputs alone.',
    'Weather, referee and player values must be supplied; this module does not imply automatic live-data feeds.',
    'The 5400-unit coordinate is a simplified position signal, not full pitch tracking.'
   ]
  };
 }
 const api={simulateMatchBreakScenarios,PITCH_TOTAL_UNITS};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 root.CraineeBackgroundBreakEngine=api;
})(typeof globalThis!=='undefined'?globalThis:this);
