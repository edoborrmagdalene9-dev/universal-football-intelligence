/* UFI full-stack browser orchestrator.
 * Calls the existing Crainee engines only when their required source inputs exist.
 * Runs the 400-signal registry, calculator, provider market scan and backend audit.
 */
(function(root){
'use strict';
const DEFAULT_BACKEND='https://universal-football-intelligence.onrender.com';
const DEFAULT_SPORTS=[
 'soccer_epl','soccer_england_championship','soccer_spain_la_liga','soccer_germany_bundesliga',
 'soccer_italy_serie_a','soccer_france_ligue_one','soccer_uefa_champs_league','soccer_uefa_europa_league',
 'soccer_netherlands_eredivisie','soccer_portugal_primeira_liga','soccer_belgium_first_div',
 'soccer_turkey_super_league','soccer_usa_mls','soccer_brazil_campeonato','soccer_australia_aleague','soccer_japan_j_league'
];
const LEAGUES={
 soccer_epl:'E0',soccer_england_championship:'E1',soccer_spain_la_liga:'SP1',
 soccer_germany_bundesliga:'D1',soccer_italy_serie_a:'I1',soccer_france_ligue_one:'F1',
 soccer_netherlands_eredivisie:'N1',soccer_portugal_primeira_liga:'P1',
 soccer_belgium_first_div:'B1',soccer_turkey_super_league:'T1'
};
const byId=id=>typeof document!=='undefined'?document.getElementById(id):null;
function has(v){return v!==undefined&&v!==null&&v!=='';}
function finite(v){return typeof v==='number'&&Number.isFinite(v);}\nfunction hasNumber(v){return v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));}
function need(status,reason){return {status:status||'NEEDS_DATA',reason};}
function runCraineeSuite(input){
 const out={},ev=input||{};
 const chaos= root.CraineeChaosGate;
 const tactical=root.CraineeTacticalSurprise;
 const background=root.CraineeBackgroundBreakEngine;
 const unconventional=root.CraineeUnconventionalOutcomeEngine;
 const subconscious=root.CraineeSubconsciousNarrativeEngine;
 const c=ev.chaos||{};
 const chaosPlayers=[...(c.homeTeam?.players||[]),...(c.awayTeam?.players||[])];
 const chaosReady=Array.isArray(c.homeTeam?.players)&&c.homeTeam.players.length>0&&Array.isArray(c.awayTeam?.players)&&c.awayTeam.players.length>0&&
  chaosPlayers.every(p=>p&&finite(p.marketValue)&&finite(p.age)&&finite(p.caps))&&
  finite(c.currentSecond)&&finite(c.referee?.avgWhistleGap1to45)&&finite(c.referee?.avgWhistleGap45to90);
 if(chaos&&chaosReady){try{out.chaos=chaos.evaluateAdvancedMatchRiskAndEdge(c,0);out.chaos.interpretation='Existing squad/referee heuristic only; not a calibrated probability or EV gate.';}catch(e){out.chaos=need('ERROR',e.message);}}
 else out.chaos=need('NEEDS_DATA','Requires sourced home/away player market values, ages, caps, elapsed seconds and referee whistle-gap data.');
 const t=ev.tactical||{};
 const tacticalReady=finite(t.ballPositionUnit)&&finite(t.currentSecond)&&
  ['midfieldRating'].every(k=>finite(t.homeTeam?.[k])&&finite(t.awayTeam?.[k]))&&
  ['forwardComposure','creativity','transitionSpeed','wingerDribbleRating','substitutesFreshness'].every(k=>finite(t.attackingTeam?.[k]))&&
  ['pressIntensity','lowBlockRating'].every(k=>finite(t.defendingTeam?.[k]))&&
  ['defensiveLineHeight','fullbackDefenseRating','defenderFatigue'].every(k=>finite(t.opponent?.[k]))&&
  Array.isArray(t.teamA?.players)&&Array.isArray(t.teamB?.players);
 if(tactical&&tacticalReady){try{out.tactical=tactical.evaluateTacticalSurprise(t);}catch(e){out.tactical=need('ERROR',e.message);}}
 else out.tactical=need('NEEDS_DATA','Requires source-backed formation/ratings, 5400-grid context, transition and fatigue values, and evidenced player style arrays.');
 const b=ev.background||{};
 const backgroundReady=finite(b.ballPositionUnit)&&finite(b.underdog?.attackerTransitionPacing)&&finite(b.favorite?.defenderErrorTendency)&&
  typeof b.environment?.isHeavyRainOrWind==='boolean'&&finite(b.referee?.whistleFrequencyChaos)&&finite(b.breakThreshold);
 if(background&&backgroundReady){try{out.background=background.simulateMatchBreakScenarios(b);}catch(e){out.background=need('ERROR',e.message);}}
 else out.background=need('NEEDS_DATA','Requires observed pitch-grid, underdog transition, favourite error tendency, weather, referee and threshold inputs.');
 const mainScore=ev.mainModelScore;
 if(unconventional&&mainScore&&finite(mainScore.home)&&finite(mainScore.away)){
  try{out.unconventional=unconventional.generateUnconventionalOutcomes({mainModelScore:mainScore,homeTeam:ev.homeTeam,awayTeam:ev.awayTeam,seed:ev.fixtureId||'ufi',candidateCount:20});}
  catch(e){out.unconventional=need('ERROR',e.message);}
 }else out.unconventional=need('NEEDS_DATA','Requires an actual model scoreline; scenario exploration is not a probability.');
 const sub=ev.subconscious||{};
 const zones=['DEFENSE','MIDFIELD','ATTACK'];
 const subReady=zones.every(z=>['height','composure','footSkill','styleFit'].every(k=>finite(sub.homeSquad?.[z]?.[k])&&finite(sub.awaySquad?.[z]?.[k])));
 if(subconscious&&subReady){try{out.subconscious=subconscious.runPipeline(sub,ev.narrativeConditions||{},!!ev.isHomeFavorite,{finalLimit:12});}
  catch(e){out.subconscious=need('ERROR',e.message);}}
 else out.subconscious=need('NEEDS_DATA','Requires source-backed DEF/MID/ATT squad height, composure, foot skill and style-fit values. No defaults are injected.');
 return out;
}
const playerProfileCache=new Map();
function normalizeSportmonksRows(payload){
 const raw=payload?.data?.data||payload?.data||[];
 if(!Array.isArray(raw))return [];
 return raw.map(x=>{
  const participants=Array.isArray(x.participants)?x.participants:[];
  let home=null,away=null;
  for(const p of participants){const side=String(p?.meta?.location||'').toLowerCase();if(side==='home')home=p.name||p.short_code||null;if(side==='away')away=p.name||p.short_code||null;}
  const venue=x.venue||{};
  return {home,away,kickoff:x.starting_at||null,ending:x.ending_at||x.finished_at||null,
   venue:{lat:hasNumber(venue.latitude)?Number(venue.latitude):NaN,lon:hasNumber(venue.longitude)?Number(venue.longitude):NaN},raw:x};
 }).filter(x=>x.home&&x.away&&x.kickoff);
}
function distanceKm(a,b){
 if(!a||!b||!finite(a.lat)||!finite(a.lon)||!finite(b.lat)||!finite(b.lon))return null;
 const rad=x=>x*Math.PI/180,R=6371,dLat=rad(b.lat-a.lat),dLon=rad(b.lon-a.lon);
 const h=Math.sin(dLat/2)**2+Math.cos(rad(a.lat))*Math.cos(rad(b.lat))*Math.sin(dLon/2)**2;
 return 2*R*Math.asin(Math.sqrt(h));
}
function buildScheduleEvidence(fixture,historyRows){
 const kickoff=Date.parse(fixture.kickoff||fixture.commence_time||'');
 if(!Number.isFinite(kickoff)||!Array.isArray(historyRows))return {};
 const upcomingVenue={lat:hasNumber(fixture.venue?.latitude)?Number(fixture.venue.latitude):NaN,lon:hasNumber(fixture.venue?.longitude)?Number(fixture.venue.longitude):NaN};
 function teamSchedule(team){
  const past=historyRows.filter(row=>{
   const isTeam=String(row.home).toLowerCase()===String(team).toLowerCase()||String(row.away).toLowerCase()===String(team).toLowerCase();
   const t=Date.parse(row.kickoff);return isTeam&&Number.isFinite(t)&&t<kickoff&&t>=kickoff-14*86400000;
  }).sort((a,b)=>Date.parse(b.kickoff)-Date.parse(a.kickoff));
  const last=past[0];let rest=null,travel=null;
  if(last?.ending){const end=Date.parse(last.ending);if(Number.isFinite(end))rest=(kickoff-end)/3600000;}
  if(last)travel=distanceKm(last.venue,upcomingVenue);
  return {last_14_days:past.map(x=>({kickoff:x.kickoff,home:x.home,away:x.away,source:'Sportmonks'})),
   rest_hours:rest,travel_distance_km:travel,extra_time_last_match:last?.raw?.extra_time===true?true:null,
   source:'Sportmonks fixtures range',fetched_at:fixture.timestamps?.fetchedAt||fixture.fetchedAt||null};
 }
 return {home_schedule:teamSchedule(fixture.homeTeam||fixture.home),away_schedule:teamSchedule(fixture.awayTeam||fixture.away)};
}
async function fetchWeatherEvidence(fixture,backend){
 const venue=fixture.venue||{},lat=hasNumber(venue.latitude)?Number(venue.latitude):NaN,lon=hasNumber(venue.longitude)?Number(venue.longitude):NaN;
 const kickoff=fixture.kickoff||fixture.commence_time;
 if(!Number.isFinite(lat)||!Number.isFinite(lon)||!kickoff)return {status:'NEEDS_DATA',reason:'Stadium coordinates or kickoff are missing.'};
 const date=String(kickoff).slice(0,10),hour=new Date(kickoff).getUTCHours();
 try{
  const q=new URLSearchParams({lat:String(lat),lon:String(lon),date,hour:String(hour)});
  const result=await getJSON(backend+'/api/weather?'+q.toString());
  const w=result.weather||{};
  return {status:'FETCHED',source:result.source||'Weather provider',fetched_at:result.fetchedAt||null,
   wind_mph:finite(Number(w.windSpeedKmh))?Number(w.windSpeedKmh)*0.621371:null,
   wind_kmh:w.windSpeedKmh??null,temperature_c:w.temperatureC??null,
   precipitation_mm:w.precipitationMm??null,precipitation_probability_pct:w.precipitationProbabilityPct??null,
   humidity_pct:w.relativeHumidityPct??null,standing_water:null,
   note:result.note||'Weather is a provider forecast/grid estimate, not a pitch sensor.'};
 }catch(e){return {status:'NEEDS_DATA',reason:e.message};}
}
function buildComponentEvidence(fixture,model,selection,evidence,physical){
 const out={},fixtureSource=fixture.sources?.fixture||fixture.providerSources?.[0]||'UFI normalized provider feed';
 const fixtureStamp=fixture.timestamps?.fetchedAt||fixture.fetchedAt||null;
 const modelSource=(model.source||model.source_urls?.[0]||'Football-Data historical results');
 const modelStamp=model.fetched_at||model.fetchedAt||null;
 const marketSource=selection.bookmaker||selection.evidence?.price_source||'Bookmaker odds feed';
 const marketStamp=selection.evidence?.price_timestamp||fixture.timestamps?.fetchedAt||fixture.fetchedAt||null;
 const put=(key,status,source,stamp)=>{if(source&&stamp)out[key]={status,source,fetched_at:stamp};};
 if(fixture.fixtureId||fixture.fixture_id)put('fixture_identity','ASSESSED',fixtureSource,fixtureStamp);
 if(fixture.homeTeam&&fixture.awayTeam)put('team_orientation','ASSESSED',fixtureSource,fixtureStamp);
 if(fixture.competition)put('competition_identity','FETCHED',fixtureSource,fixtureStamp);
 if(fixture.kickoff)put('kickoff_timestamp','ASSESSED',fixtureSource,fixtureStamp);
 if(fixture.venue)put('venue_identity','FETCHED',fixtureSource,fixtureStamp);
 put('source_provider','FETCHED',fixtureSource,fixtureStamp);
 if(fixtureStamp)put('source_freshness','FETCHED',fixtureSource,fixtureStamp);
 if(selection.market)put('market_identity',hasNumber(selection.odds)?'ASSESSED':'ESTIMATED',hasNumber(selection.odds)?marketSource:'UFI model-derived candidate',hasNumber(selection.odds)?marketStamp:modelStamp);
 if(selection.selection)put('selection_identity','ASSESSED',marketSource,marketStamp);
 if(hasNumber(selection.odds))put('decimal_price','FETCHED',marketSource,marketStamp);
 if(selection.bookmaker)put('bookmaker_identity','FETCHED',marketSource,marketStamp);
 if(hasNumber(selection.line))put('market_line','FETCHED',marketSource,marketStamp);
 if(selection.evidence?.price_timestamp)put('price_timestamp','FETCHED',marketSource,selection.evidence.price_timestamp);
 if(model.training_matches)put('historical_sample','FETCHED',modelSource,modelStamp);
 if(model.rate_estimate?.ok&&finite(model.rate_estimate.lambdaHome))put('home_lambda','ASSESSED',modelSource,modelStamp);
 if(model.rate_estimate?.ok&&finite(model.rate_estimate.lambdaAway))put('away_lambda','ASSESSED',modelSource,modelStamp);
 if(model.dixon_coles?.rho!==undefined)put('dixon_coles_rho','ASSESSED',modelSource,modelStamp);
 if((model.models?.xg_dixon_coles_rho_minus_0_10?.score_grid||model.models?.dixon_coles_rho_minus_0_10?.score_grid)?.length===81)put('score_grid','ASSESSED',modelSource,modelStamp);
 if(model.rate_estimate?.leagueHomeMean!==undefined||model.xg_rate_estimate?.leagueHomeXgMean!==undefined)put('base_rate','FETCHED',modelSource,modelStamp);
 if(model.backtest||model.chronological_backtest)put('chronological_validation','FETCHED',modelSource,modelStamp);
 if(physical?.lineups_confirmed)put('official_lineup','FETCHED','Sportmonks lineups (provider-reported; official confirmation flag supplied)',fixtureStamp);
 if(physical?.lineups_confirmed)put('lineup_timestamp','FETCHED','Sportmonks lineups',fixtureStamp);
 if(physical?.home_players?.some(p=>p.position&&/goalkeeper/i.test(p.position))&&physical?.away_players?.some(p=>p.position&&/goalkeeper/i.test(p.position)))put('goalkeeper_identity','FETCHED','Sportmonks player profiles',fixtureStamp);\n if(physical?.home_players?.filter(p=>p.position&&/centre back|center back/i.test(p.position)).length>=2&&physical?.away_players?.filter(p=>p.position&&/centre back|center back/i.test(p.position)).length>=2)put('centre_back_pairing','FETCHED','Sportmonks player profiles',fixtureStamp);
 if(physical?.home_players?.filter(p=>p.height_cm).length>=7)put('home_lineup_heights','FETCHED','Sportmonks player profiles',fixtureStamp);
 if(physical?.away_players?.filter(p=>p.height_cm).length>=7)put('away_lineup_heights','FETCHED','Sportmonks player profiles',fixtureStamp);\n if(physical?.home_players?.some(p=>p.height_cm)&&physical?.away_players?.some(p=>p.height_cm))put('height_cm','FETCHED','Sportmonks player profiles',fixtureStamp);
 if(physical?.formation_home)put('home_formation','FETCHED','Sportmonks formations',fixtureStamp);
 if(physical?.formation_away)put('away_formation','FETCHED','Sportmonks formations',fixtureStamp);
 if(evidence?.weather?.source){
  put('weather_source','FETCHED',evidence.weather.source,evidence.weather.fetched_at||fixtureStamp);
  if(hasNumber(evidence.weather.wind_mph))put('wind_speed','FETCHED',evidence.weather.source,evidence.weather.fetched_at||fixtureStamp);
  if(hasNumber(evidence.weather.temperature_c))put('temperature','FETCHED',evidence.weather.source,evidence.weather.fetched_at||fixtureStamp);
  if(hasNumber(evidence.weather.humidity_pct))put('humidity','FETCHED',evidence.weather.source,evidence.weather.fetched_at||fixtureStamp);
 }
 if(evidence?.referee_assignment?.source)put('referee_assignment','FETCHED',evidence.referee_assignment.source,evidence.referee_assignment.fetched_at||fixtureStamp);
 for(const side of ['home','away']){
  const schedule=evidence[side+'_schedule'];
  if(Array.isArray(schedule?.last_14_days)){
   put(side+'_last_fixture','FETCHED',schedule.source||'Sportmonks fixtures range',schedule.fetched_at||fixtureStamp);
   put(side+'_games_14d','FETCHED',schedule.source||'Sportmonks fixtures range',schedule.fetched_at||fixtureStamp);
  }
  if(hasNumber(schedule?.rest_hours))put(side+'_rest_hours','ASSESSED',schedule.source||'Sportmonks fixture end timestamps',schedule.fetched_at||fixtureStamp);
  if(hasNumber(schedule?.travel_distance_km))put('travel_distance','ESTIMATED',schedule.source||'Sportmonks venue coordinates',schedule.fetched_at||fixtureStamp);
  if(schedule?.extra_time_last_match===true||schedule?.extra_time_last_match===false)put('extra_time_load','FETCHED',schedule.source||'Sportmonks fixture state',schedule.fetched_at||fixtureStamp);
 }
 evidence.component_evidence=out;
 return out;
}
async function buildSportmonksEvidence(fixture,backend,enabled){
 const base={};
 if(!enabled)return {status:'NEEDS_DATA',reason:'Sportmonks player profile endpoint is not configured.'};
 if(fixture.lineupsConfirmed!==true)return {status:'NEEDS_DATA',reason:'Provider lineups are not explicitly marked confirmed; no starting XI is assumed.'};
 if(!Array.isArray(fixture.lineups)||!Array.isArray(fixture.participants))return {status:'NEEDS_DATA',reason:'Confirmed lineups or participant identity mapping are missing.'};
 const sides=new Map();
 for(const p of fixture.participants){const side=String(p?.meta?.location||'').toLowerCase();if(p?.id&&['home','away'].includes(side))sides.set(String(p.id),side);}
 const starters=fixture.lineups.filter(row=>{
  const t=String(row?.type?.name||row?.type?.developer_name||row?.type_name||'').toLowerCase();
  return row?.is_starting===true||row?.starting===true||t.includes('starting xi')||t.includes('starting lineup');
 });
 const grouped={home:[],away:[]};
 for(const row of starters){
  const side=sides.get(String(row.team_id||row.participant_id||''));const id=row.player_id||row.player?.id;
  if(side&&id&&/^\\d+$/.test(String(id)))grouped[side].push({id:String(id),lineup:row});
 }
 if(grouped.home.length<11||grouped.away.length<11)return {status:'NEEDS_DATA',reason:'Sportmonks did not provide 11 explicitly identified starters for both teams.',counts:{home:grouped.home.length,away:grouped.away.length}};
 async function profile(id){
  if(playerProfileCache.has(id))return playerProfileCache.get(id);
  const promise=getJSON(backend+'/api/player?id='+encodeURIComponent(id)).then(x=>{
   const p=x.data?.data||x.data||{};
   return {id,name:p.name||p.display_name||null,height_cm:hasNumber(p.height)?Number(p.height):null,
    position:p.detailed_position?.name||p.position?.name||null,source:'Sportmonks player profile',fetched_at:x.fetchedAt||null};
  });
  playerProfileCache.set(id,promise);
  try{return await promise}catch(e){playerProfileCache.delete(id);throw e;}
 }
 async function allProfiles(rows){
  const out=[];let i=0;
  async function worker(){while(i<rows.length){const row=rows[i++];try{const p=await profile(row.id);out.push({...p,position:p.position||row.lineup.position?.name||row.lineup.position_name||null});}catch(e){out.push({id:row.id,height_cm:null,source_error:e.message});}}}
  await Promise.all(Array.from({length:4},worker));return out;
 }
 const [homePlayers,awayPlayers]=await Promise.all([allProfiles(grouped.home),allProfiles(grouped.away)]);
 const formations=Array.isArray(fixture.formations)?fixture.formations:[];
 const formFor=side=>{
  const participant=fixture.participants.find(p=>String(p?.meta?.location||'').toLowerCase()===side);
  const row=formations.find(x=>String(x.participant_id||x.team_id||'')===String(participant?.id||''));
  return row?.formation?.name||row?.formation_name||row?.formation||null;
 };
 const fh=formFor('home'),fa=formFor('away');
 return {status:'FETCHED',home_players:homePlayers,away_players:awayPlayers,formation_home:fh,formation_away:fa,
  lineups_confirmed:true,lineups_source:'Sportmonks',player_profile_count:homePlayers.length+awayPlayers.length,
  height_coverage:{home:homePlayers.filter(x=>finite(x.height_cm)).length,away:awayPlayers.filter(x=>finite(x.height_cm)).length},
  note:'Only explicitly flagged starting-XI rows were enriched. Missing player heights and jump metrics remain unknown.'};
}
function run400Audit(fixture,selection,prob){
 if(!root.UFI400Audit||typeof root.UFI400Audit.evaluate!=='function')return need('NEEDS_DATA','UFI400Audit browser module is not loaded.');
 const row={label:String(selection.selection||selection.market||''),odd:selection.odds,
  fixtureResolution:{status:'candidate-found',matchId:fixture.fixture_id||fixture.id||null,kickoff:fixture.kickoff||null,orientation:'verified'},
  marketEstimate:finite(prob)?{probability:prob,source:'Dixon-Coles score grid'}:null,
  signalEvidence:selection.evidence||{}};
 try{
  const base=root.UFI400Audit.evaluate(row,null,{});
  const supplied=selection.evidence?.signal_checks||{};
  const allowed=new Set(['FETCHED','ESTIMATED','ASSESSED','FAIL','PENDING','NOT_APPLICABLE','NEEDS_DATA']);
  const checks=(base.checks||[]).map(check=>{
   const exact=supplied[check.id]||supplied[check.name];
   if(!exact||typeof exact!=='object'||!allowed.has(String(exact.status||'')))return check;
   return {...check,status:exact.status,detail:String(exact.detail||check.detail),
    evidenceStatus:['FETCHED','ESTIMATED'].includes(exact.status)?exact.status:check.evidenceStatus,
    source:exact.source||check.source,updatedAt:exact.updatedAt||check.updatedAt};
  });
  const counts={};for(const check of checks)counts[check.status]=(counts[check.status]||0)+1;
  const applicable=checks.length-(counts.NOT_APPLICABLE||0),assessed=counts.ASSESSED||0;
  return {...base,checks,counts,coveragePercent:checks.length?Math.round(100*assessed/checks.length):0,
   applicableCoveragePercent:applicable?Math.round(100*assessed/applicable):0,
   evidenceFetched:checks.filter(x=>x.status==='FETCHED').length,
   evidenceEstimated:checks.filter(x=>x.status==='ESTIMATED').length,
   failures:checks.filter(x=>x.status==='FAIL'),pending:checks.filter(x=>x.status==='PENDING'),
   notApplicable:checks.filter(x=>x.status==='NOT_APPLICABLE'),needsData:checks.filter(x=>x.status==='NEEDS_DATA')};
 }catch(e){return need('ERROR',e.message);}
}
function runCalculator(selections){
 if(!root.UFICalculatorRisk||typeof root.UFICalculatorRisk.evaluateSlip!=='function')return need('NEEDS_DATA','Calculator risk engine is not loaded.');
 try{return root.UFICalculatorRisk.evaluateSlip(selections.map(s=>({selection:s.selection,odds:s.odds})),1)}
 catch(e){return need('ERROR',e.message);}
}
function dateISO(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
function addDays(date,days){const d=new Date(date);d.setDate(d.getDate()+days);return d;}
async function getJSON(url){const r=await fetch(url,{headers:{Accept:'application/json'}});let body;try{body=await r.json()}catch(_){body={}}if(!r.ok)throw new Error('HTTP '+r.status+': '+(body.error||r.statusText));return body;}
async function postJSON(url,payload){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(payload)});let body;try{body=await r.json()}catch(_){body={}}if(!r.ok)throw new Error('HTTP '+r.status+': '+(body.error||r.statusText));return body;}
function rowsFrom(payload){if(Array.isArray(payload))return payload;if(Array.isArray(payload?.data))return payload.data;return [];}
function mapOutcome(name,home,away){
 const n=String(name||'').trim(),v=n.toLowerCase();
 if(v==='draw'||v==='tie'||v==='x')return 'Draw';
 if(v===String(home).toLowerCase())return 'Home';
 if(v===String(away).toLowerCase())return 'Away';
 if(v==='yes'||v==='no')return n;
 if(v==='1x'||v==='12'||v==='x2')return n;
 return n;
}
function marketSelections(fixture){
 const books=Array.isArray(fixture.odds)?fixture.odds:Array.isArray(fixture.bookmakers)?fixture.bookmakers:[];
 const best=new Map();
 for(const book of books){
  const bookmaker=book.title||book.key||book.name||'Unknown bookmaker';
  const markets=Array.isArray(book.markets)?book.markets:[];
  for(const market of markets){
   const key=String(market.key||market.market||'').toLowerCase();
   const outcomes=Array.isArray(market.outcomes)?market.outcomes:[];
   const priced=outcomes.map(o=>({o,price:Number(o.price)})).filter(x=>Number.isFinite(x.price)&&x.price>1);
   const sums=new Map();
   for(const x of priced){
    const point=hasNumber(x.o.point)?Number(x.o.point):'';
    const group=[key,point,bookmaker].join('|');
    sums.set(group,(sums.get(group)||0)+(1/x.price));
   }
   for(const {o,price} of priced){
    const point=!hasNumber(o.point)?null:Number(o.point);
    const rawName=o.name||o.label||o.description||'';
    let marketName=key,selection=mapOutcome(rawName,fixture.homeTeam||fixture.home,fixture.awayTeam||fixture.away),team=o.description||null,side=null,line=Number.isFinite(point)?point:null;
    if(key==='h2h'||key==='h2h_3_way'||key==='moneyline'){marketName='1X2';selection=mapOutcome(rawName,fixture.homeTeam||fixture.home,fixture.awayTeam||fixture.away);}
    else if(key==='totals'||key==='alternate_totals'){marketName='Over Under';selection=String(rawName)+' '+(line===null?'':line); }
    else if(key==='btts'){marketName='BTTS';selection=String(rawName);}
    else if(key==='team_totals'||key==='alternate_team_totals'){marketName='Team Total';team=o.description||null;selection=String(rawName);side=team&&String(team).toLowerCase()===String(fixture.homeTeam||fixture.home).toLowerCase()?'home':team&&String(team).toLowerCase()===String(fixture.awayTeam||fixture.away).toLowerCase()?'away':null;}
    else if(key==='double_chance'){marketName='Double Chance';selection=String(rawName);}
    else if(key==='spreads'||key==='alternate_spreads'){marketName='Asian Handicap';selection=String(rawName);side=team&&String(team).toLowerCase()===String(fixture.homeTeam||fixture.home).toLowerCase()?'home':team&&String(team).toLowerCase()===String(fixture.awayTeam||fixture.away).toLowerCase()?'away':null;}
    const group=[key,line===null?'':line,bookmaker].join('|');
    const invSum=sums.get(group)||0;
    const noVig=invSum>0?(1/price)/invSum:null;
    const evidence={no_vig_probability:noVig,market_key:key,market_line:line,price_source:'The Odds API / SportsGameOdds normalized bookmaker payload',price_timestamp:fixture.timestamps?.providerUpdatedAt||fixture.timestamps?.fetchedAt||fixture.fetchedAt||null};
    const item={market:marketName,selection,team,side,line,odds:price,bookmaker,evidence,_group:group};
    const identity=[key,line===null?'':line,selection,team||''].join('|');
    const old=best.get(identity);
    if(!old||price>old.odds)best.set(identity,item);
   }
  }
 }
 const found=[...best.values()].map(({_group,...x})=>x);
 const hasDC12=found.some(x=>String(x.market).toLowerCase()==='double chance'&&String(x.selection).toUpperCase()==='12');
 const hasTeamMulti=found.some(x=>String(x.market).toLowerCase().includes('multigoals 1 3'));
 if(!hasDC12)found.push({market:'DC12',selection:'12',odds:null,bookmaker:null,evidence:{market_key:'derived_from_score_grid_only'}});
 for(const [team,side] of [[fixture.homeTeam||fixture.home,'home'],[fixture.awayTeam||fixture.away,'away']]){
  if(team&&!hasTeamMulti)found.push({market:'Team Multigoals 1-3',selection:'1–3 goals',team,side,odds:null,bookmaker:null,evidence:{market_key:'derived_from_score_grid_only'}});
 }
 return found;
}
async function runFixture(fixture,backend,playerProfilesEnabled,historyRows){
 const home=fixture.homeTeam||fixture.home,away=fixture.away;
 const kickoff=fixture.kickoff||fixture.commence_time||fixture.starting_at||null;
 const sport=fixture.sport||fixture.sport_key||'';
 const league=LEAGUES[sport]||null;
 const selections=marketSelections(fixture);
 let model={status:'NEEDS_DATA',reason:league?'Model request not completed.':'No supported historical league mapping for this competition.'};
 if(league&&home&&away&&kickoff){
  const qs=new URLSearchParams({home,away,league,seasons:'5',date:String(kickoff).slice(0,10)});
  try{model=await getJSON(backend+'/api/models/score?'+qs.toString());}catch(e){model={status:'NEEDS_DATA',reason:e.message};}
 }
 const mainGrid=model.models?.xg_dixon_coles_rho_minus_0_10?.score_grid||model.models?.dixon_coles_rho_minus_0_10?.score_grid||model.models?.dixon_coles?.score_grid||[];
 let mainModelScore=null;
 if(mainGrid.length){const top=mainGrid.slice().sort((a,b)=>b.p-a.p)[0];mainModelScore={home:top.home,away:top.away};}
 const fixtureInfo={fixture_id:fixture.fixtureId||fixture.id||fixture.matchId||null,home,away,kickoff,competition:fixture.competition||fixture.sport_title||null,sport};
 const engines=runCraineeSuite({fixtureId:fixtureInfo.fixture_id,homeTeam:home,awayTeam:away,mainModelScore,
  chaos:fixture.engineEvidence?.chaos,tactical:fixture.engineEvidence?.tactical,background:fixture.engineEvidence?.background,
  subconscious:fixture.engineEvidence?.subconscious,narrativeConditions:fixture.engineEvidence?.narrativeConditions});
 let anitaResearch=need('NEEDS_DATA','Research worker not run.');
 try{
  const rq=new URLSearchParams({home,away,competition:fixtureInfo.competition||'',date:String(kickoff||'').slice(0,10)});
  anitaResearch=await getJSON(backend+'/api/ai/research-fixture?'+rq.toString());
 }catch(e){anitaResearch={status:'NEEDS_DATA',reason:e.message,verified:false};}
 const evidence={...(fixture.evidence||{})};
 const scheduleEvidence=buildScheduleEvidence(fixture,historyRows);
 Object.assign(evidence,scheduleEvidence);
 const [physicalEvidence,weatherEvidence]=await Promise.all([
  buildSportmonksEvidence(fixture,backend,playerProfilesEnabled),fetchWeatherEvidence(fixture,backend)
 ]);
 if(weatherEvidence.status==='FETCHED')evidence.weather=weatherEvidence;
 if(physicalEvidence.status==='FETCHED'){
  evidence.home_players=physicalEvidence.home_players;
  evidence.away_players=physicalEvidence.away_players;
  evidence.formation_home=physicalEvidence.formation_home;
  evidence.formation_away=physicalEvidence.formation_away;
 }
 // Only lift fields already present in the provider record; no inferred lineup or player attributes.
 if(physicalEvidence.status!=='FETCHED'&&Array.isArray(fixture.lineups)){
  const rows=fixture.lineups.map(x=>x&&typeof x==='object'?x:null).filter(Boolean);
  const homeRows=[],awayRows=[];
  for(const row of rows){
   const player=row.player&&typeof row.player==='object'?row.player:row;
   const team=String(row.team_name||row.team?.name||row.team?.short_code||'').toLowerCase();
   const item={name:player.name||row.player_name||null,position:row.position?.name||row.position_name||null,
    height_cm:Number.isFinite(Number(player.height_cm??player.height))?Number(player.height_cm??player.height):null};
   if(team===String(home).toLowerCase())homeRows.push(item);
   else if(team===String(away).toLowerCase())awayRows.push(item);
  }
  if(homeRows.length)evidence.home_players=homeRows;
  if(awayRows.length)evidence.away_players=awayRows;
 }
 if(fixture.formations&&typeof fixture.formations==='object'){
  evidence.formation_home=fixture.formations.home||null;
  evidence.formation_away=fixture.formations.away||null;
 }
 if(engines.unconventional?.unconventionalShortlist?.length){
  evidence.alternative_scenarios=engines.unconventional.unconventionalShortlist;
  evidence.scenario_engine_ran=true;
 }
 buildComponentEvidence(fixture,model,selections[0]||{},evidence,physicalEvidence.status==='FETCHED'?physicalEvidence:null);
 let audit=null;
 if(selections.length){
  try{audit=await postJSON(backend+'/api/brain/audit',{fixture:fixtureInfo,model,evidence,selections});}
  catch(e){audit={ok:false,error:e.message};}
 }else audit={ok:false,reason:'No bookmaker markets with decimal prices were returned for this fixture.'};
 const audits=selections.map(s=>({selection:s,registry:run400Audit(fixtureInfo,s,marketProbFromModel(model,s,fixtureInfo)),calculator:runCalculator([s])}));
 return {fixture:fixtureInfo,providerSources:fixture.providerSources||fixture.sources||{},playerProfileEvidence:physicalEvidence,weatherEvidence,scheduleEvidence,modelStatus:model.status,modelReason:model.reason||null,
  model,marketCount:selections.length,audit,engines,anitaResearch,400SignalAudits:audits};
}
function marketProbFromModel(model,selection,fixture){
 const grid=model.models?.dixon_coles_rho_minus_0_10?.score_grid||model.models?.dixon_coles?.score_grid||[];
 if(!grid.length)return null;
 const m=String(selection.market||'').toLowerCase(),pick=String(selection.selection||'').toLowerCase(),line=Number(selection.line);
 const sum=grid.reduce((a,x)=>a+(Number(x.p)||0),0)||1;
 let hit;
 if(m==='1x2')hit=(h,a)=>pick==='home'?h>a:pick==='away'?h<a:h===a;
 else if(m==='dc12'||m==='double chance')hit=(h,a)=>pick==='12'||pick==='home or away'?h!==a:pick==='1x'?h>=a:a>=h;
 else if(m==='btts')hit=(h,a)=>pick==='yes'?h>0&&a>0:h===0||a===0;
 else if(m==='over under'&&Number.isFinite(line))hit=(h,a)=>pick.startsWith('over')?h+a>line:h+a<line;
 else if(m==='team multigoals 1-3'||m==='multigoals 1-3'||m==='multi score 1-3')hit=(h,a)=>selection.side==='home'?h>=1&&h<=3:a>=1&&a<=3;
 else if(m==='team total'&&Number.isFinite(line))hit=(h,a)=>selection.side==='home'?(pick.startsWith('over')?h>line:h<line):(pick.startsWith('over')?a>line:a<line);
 else if(m==='under 3.5')hit=(h,a)=>h+a<3.5;
 else if(m==='under 4.5')hit=(h,a)=>h+a<4.5;
 else return null;
 return grid.filter(x=>hit(x.home,x.away)).reduce((a,x)=>a+(Number(x.p)||0),0)/sum;
}
function buildSlip(pool,target=30,low=28,high=32){
 const rows=pool.filter(x=>finite(Number(x.odds))&&Number(x.odds)>1).sort((a,b)=>Number(b.quality||0)-Number(a.quality||0));
 let best=null;const maxLegs=Math.min(12,rows.length);
 function visit(start,chosen,product,fixtures){
  if(chosen.length>0&&product>=low&&product<=high){
   const score=Math.abs(product-target);
   if(!best||score<best.score||(score===best.score&&chosen.length<best.items.length))best={items:chosen.slice(),product,score};
   return;
  }
  if(chosen.length>=maxLegs||product>high)return;
  for(let i=start;i<rows.length;i++){
   const row=rows[i],fid=String(row.fixture?.fixture_id||row.fixture?.home+'|'+row.fixture?.away+'|'+row.fixture?.kickoff);
   if(fixtures.has(fid))continue;
   const next=product*Number(row.odds);if(next>high)continue;
   fixtures.add(fid);chosen.push(row);visit(i+1,chosen,next,fixtures);chosen.pop();fixtures.delete(fid);
  }
 }
 visit(0,[],1,new Set());
 return best?{status:'BUILT',stake_units:1,combined_odds:Number(best.product.toFixed(4)),items:best.items}:null;
}
function buildTwoSlips(results,target=30){
 const candidates=[];
 for(const result of results||[]){
  const fixture=result.fixture||{};
  for(const item of result.audit?.selections||[]){
   if(item.decision!=='REVIEW_ONLY'||!finite(Number(item.odds))||Number(item.odds)<=1)continue;
   candidates.push({fixture,market:item.market,selection:item.selection,team:item.team,bookmaker:item.bookmaker,
    odds:Number(item.odds),model_probability:item.model_probability,expected_value_per_unit:item.expected_value_per_unit,
    quality:Number(item.expected_value_per_unit||0)});
  }
 }
 if(!candidates.length)return {status:'NO_QUALIFYING_SELECTIONS',reason:'No selection passed all nine Pirates layers, market-specific hard gates, 5400 gate, source checks and positive EV.'};
 const a=buildSlip(candidates,target);
 if(!a)return {status:'NO_CLEAN_PRODUCT',reason:'No unpadded Slip A product landed in the permitted 28.00–32.00 window.'};
 const used=new Set(a.items.map(x=>String(x.fixture.fixture_id||x.fixture.home+'|'+x.fixture.away+'|'+x.fixture.kickoff)+'|'+x.market));
 const poolB=candidates.filter(x=>!used.has(String(x.fixture.fixture_id||x.fixture.home+'|'+x.fixture.away+'|'+x.fixture.kickoff)+'|'+x.market));
 const b=buildSlip(poolB,target);
 if(!b)return {status:'ONLY_ONE_CLEAN_SLIP',reason:'Slip A passed the product search, but a second independent clean Slip B could not be formed. No single slip is presented as final.'};
 return {status:'TWO_SLIPS_BUILT',target_combined_odds:target,accepted_range:[28,32],stake_units_each:1,
  slip_a:a,slip_b:b,policy:'Pure multiples only. No padding, no forced leg count. A fixture may recur across A/B only on a different market.'};
}
async function scan(options={}){
 const backend=String(options.backend||DEFAULT_BACKEND).replace(/\/+$/,'');
 const start=options.startDate||dateISO(new Date());
 const end=options.endDate||dateISO(addDays(new Date(start+'T12:00:00'),3));
 let sports=Array.isArray(options.sports)&&options.sports.length?options.sports:null;
 if(!sports){
  try{const catalogue=await getJSON(backend+'/api/sports/catalog');sports=(catalogue.sports||[]).filter(x=>x.active!==false).map(x=>x.key);}
  catch(_){sports=DEFAULT_SPORTS.slice();}
 }
 if(!sports.length)sports=DEFAULT_SPORTS.slice();
 const markets=options.markets||'h2h,spreads,totals,team_totals,btts,draw_no_bet,alternate_totals,alternate_team_totals';
 const batches=[];for(let i=0;i<sports.length;i+=16)batches.push(sports.slice(i,i+16));
 const allRows=[],warnings=[],sources=new Set(),providerRecordCounts={},requestedSports=[];
 let marketFallback=false,firstPayload=null;
 for(const batch of batches){
  const qs=new URLSearchParams({sports:batch.join(','),regions:'uk',markets,from:start+'T00:00:00Z',to:end+'T23:59:59Z',limit:'50'});
  let part;
  try{part=await getJSON(backend+'/api/matches?'+qs.toString());}
  catch(firstError){
   const fallbackQs=new URLSearchParams({sports:batch.join(','),regions:'uk',markets:'h2h',from:start+'T00:00:00Z',to:end+'T23:59:59Z',limit:'50'});
   try{part=await getJSON(backend+'/api/matches?'+fallbackQs.toString());marketFallback=true;warnings.push('Market fallback for '+batch.join(',')+': '+firstError.message);}
   catch(secondError){warnings.push('Provider batch failed for '+batch.join(',')+': '+secondError.message);continue;}
  }
  if(!firstPayload)firstPayload=part;
  allRows.push(...rowsFrom(part));
  (part.sources||[]).forEach(x=>sources.add(x));
  (part.providerWarnings||[]).forEach(x=>warnings.push(x));
  (part.requestedSports||batch).forEach(x=>requestedSports.push(x));
  Object.entries(part.providerRecordCounts||{}).forEach(([k,v])=>providerRecordCounts[k]=(providerRecordCounts[k]||0)+Number(v||0));
 }
 if(!firstPayload||!allRows.length)throw new Error(warnings.join(' | ')||'No configured provider returned fixture records.');
 const deduped=new Map();
 for(const row of allRows){
  const key=[String(row.homeTeam||'').toLowerCase().replace(/\\s+/g,' ').trim(),String(row.awayTeam||'').toLowerCase().replace(/\\s+/g,' ').trim(),String(row.kickoff||'').slice(0,16)].join('|');
  const prior=deduped.get(key);
  if(!prior)deduped.set(key,{...row});
  else{
   prior.odds=[...(Array.isArray(prior.odds)?prior.odds:[]),...(Array.isArray(row.odds)?row.odds:[])];
   prior.providerSources=[...new Set([...(prior.providerSources||[]),...(row.providerSources||[])])];
   prior.sources={...(prior.sources||{}),...(row.sources||{})};
  }
 }
 const payload={...firstPayload,source:'multi-provider-catalogue-scan',sources:[...sources],
  providerRecordCounts,providerWarnings:warnings,requestedSports:[...new Set(requestedSports)],data:[...deduped.values()]};
 const fixtures=rowsFrom(payload).slice(0,Math.min(100,Number(options.maxFixtures)||40));
 let playerProfilesEnabled=false,historyRows=[],historyError=null;
 try{
  const status=await getJSON(backend+'/api/providers/status');playerProfilesEnabled=!!status.providers?.sportmonks?.configured;
  if(playerProfilesEnabled){
   const historyStart=dateISO(addDays(new Date(start+'T12:00:00'),-14));
   const historyPayload=await getJSON(backend+'/api/fixtures/range?'+new URLSearchParams({from:historyStart,to:end}).toString());
   historyRows=normalizeSportmonksRows(historyPayload);
  }
 }catch(e){historyError=e.message;}
 const results=[];let cursor=0;
 async function worker(){while(cursor<fixtures.length){const index=cursor++;const item=fixtures[index];try{results[index]=await runFixture(item,backend,playerProfilesEnabled,historyRows);}catch(e){results[index]={fixture:{home:item.homeTeam,away:item.awayTeam,kickoff:item.kickoff},error:e.message,modelStatus:'NEEDS_DATA'};}}}
 await Promise.all(Array.from({length:Math.min(3,fixtures.length)},worker));
 return {ok:true,source:payload.source,sources:payload.sources,providerRecordCounts:payload.providerRecordCounts,
  providerWarnings:[...(payload.providerWarnings||[]),...(historyError?["Sportmonks schedule enrichment: "+historyError]:[])],marketFallback,requestedSports:payload.requestedSports||sports,
  window:{start,end},fixtureCount:fixtures.length,results,
  summary:{modelReady:results.filter(x=>x.modelStatus==='model_output').length,
   reviewOnly:results.reduce((n,x)=>n+(x.audit?.summary?.review_only||0),0),
   ditch:results.reduce((n,x)=>n+(x.audit?.summary?.ditch||0),0),
   needsData:results.reduce((n,x)=>n+(x.audit?.summary?.needs_data||0),0),
   noValue:results.reduce((n,x)=>n+(x.audit?.summary?.no_value||0),0)},
  slips:buildTwoSlips(results),
  note:'All outputs are evidence-gated. Unsupported leagues, unavailable markets and missing lineup/player/congestion evidence remain NEEDS_DATA.'};
}
function render(result){
 const status=byId('ufiBrainStatus'),out=byId('ufiBrainOutput');
 if(!out)return;
 const summary=result.summary||{};
 if(status)status.textContent='Scan complete: '+result.fixtureCount+' fixtures · '+summary.modelReady+' model-ready · '+summary.reviewOnly+' review-only · '+summary.needsData+' NEEDS_DATA · '+summary.ditch+' ditched.';
 const rows=(result.results||[]).map(x=>{
  const f=x.fixture||{},a=x.audit?.summary||{};
  return '<tr><td>'+escapeHTML(f.kickoff||'—')+'</td><td>'+escapeHTML(f.competition||f.sport||'—')+'</td><td>'+escapeHTML((f.home||'?')+' vs '+(f.away||'?'))+'</td><td>'+escapeHTML(x.modelStatus||'NEEDS_DATA')+'</td><td>'+Number(x.marketCount||0)+'</td><td>'+Number(a.review_only||0)+'</td><td>'+Number(a.ditch||0)+'</td><td>'+Number(a.needs_data||0)+'</td></tr>';
 }).join('');
 const slipStatus=result.slips?.status||'NOT_BUILT';
 out.innerHTML='<div class="metrics compact"><article class="metric"><span>Fixtures</span><strong>'+result.fixtureCount+'</strong></article><article class="metric"><span>Model ready</span><strong>'+summary.modelReady+'</strong></article><article class="metric"><span>Review only</span><strong>'+summary.reviewOnly+'</strong></article><article class="metric"><span>NEEDS_DATA</span><strong>'+summary.needsData+'</strong></article></div><div class="notice '+(slipStatus==='TWO_SLIPS_BUILT'?'success':'warning')+'"><b>Slip builder: '+escapeHTML(slipStatus)+'</b><p>'+escapeHTML(result.slips?.reason||result.slips?.policy||'No final slip is shown unless both independent multiples pass every gate and land naturally in the target range.')+'</p></div><div class="table-wrap"><table><thead><tr><th>Kickoff</th><th>Competition</th><th>Fixture</th><th>Model</th><th>Markets</th><th>Review</th><th>Ditch</th><th>Missing</th></tr></thead><tbody>'+rows+'</tbody></table></div><details><summary>Full audit, Crainee outputs, Anita research, Pirates layers, 100/400 checks and provider warnings</summary><pre>'+escapeHTML(JSON.stringify(result,null,2))+'</pre></details>';
}
function escapeHTML(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function attach(){
 const button=byId('ufiBrainRun');if(!button)return;
 button.addEventListener('click',async()=>{
  button.disabled=true;button.textContent='Scanning providers and models…';
  const status=byId('ufiBrainStatus');if(status)status.textContent='Fetching the four-day fixture window and running model/audit stages. This can take several minutes.';
  try{
   const result=await scan({startDate:byId('ufiBrainStart')?.value||undefined,endDate:byId('ufiBrainEnd')?.value||undefined,maxFixtures:Number(byId('ufiBrainLimit')?.value||40)});
   root.UFI_LAST_FULL_SCAN=result;render(result);
  }catch(e){if(status)status.textContent='Full scan could not complete: '+e.message;if(byId('ufiBrainOutput'))byId('ufiBrainOutput').textContent='No scan result. Check backend availability and provider configuration.';}
  finally{button.disabled=false;button.textContent='Run full UFI four-day audit';}
 });
}
if(typeof document!=='undefined'){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',attach);else attach();}
const api={runCraineeSuite,run400Audit,runCalculator,marketSelections,marketProbFromModel,runFixture,buildSlip,buildTwoSlips,scan,render,DEFAULT_SPORTS,LEAGUES};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
root.UFIFullIntelligence=api;
})(typeof window!=='undefined'?window:globalThis);
