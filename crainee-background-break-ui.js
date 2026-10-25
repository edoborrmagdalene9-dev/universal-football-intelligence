/* Additive UI integration for match-break simulator. */
(function(){
 'use strict';
 function init(){
  if(!window.CraineeBackgroundBreakEngine||!document.querySelector('#navigation')||!document.querySelector('.main')||document.getElementById('view-backgroundbreak'))return;
  const nav=document.querySelector('#navigation'),main=document.querySelector('.main');
  const btn=document.createElement('button');btn.className='nav-item';btn.dataset.view='backgroundbreak';btn.innerHTML='<span>⚡</span> Match-break simulator';nav.appendChild(btn);
  const view=document.createElement('section');view.className='view';view.id='view-backgroundbreak';
  view.innerHTML=`<div class="page-heading"><div><div class="eyebrow">STRUCTURAL FRACTURE SCENARIOS</div><h1>Match-Can-Break-This-Way Simulator</h1><p class="muted">Explore hypothetical match fractures and score shifts. Signals are not calibrated probabilities.</p></div></div>
  <div class="panel"><div class="form-grid">
  <label>Ball position (0–5400)<input id="mbGrid" type="number" min="0" max="5400" value="2700"></label>
  <label>Favourite defender error tendency (1–10)<input id="mbError" type="number" min="1" max="10" value="7"></label>
  <label>Underdog transition pacing (1–10)<input id="mbPace" type="number" min="1" max="10" value="8"></label>
  <label>Referee whistle disruption (0.5–2.5)<input id="mbWhistle" type="number" min="0.5" max="2.5" step="0.1" value="1.2"></label>
  <label>Break threshold<input id="mbThreshold" type="number" min="0.1" max="20" step="0.1" value="2"></label></div>
  <label class="check-row"><input id="mbHead" type="checkbox"> Simulate underdog scoring first</label>
  <label class="check-row"><input id="mbWeather" type="checkbox"> Heavy rain or wind</label>
  <div class="actions"><button class="button primary" id="mbRun">Simulate match-break scenarios</button></div><div id="mbStatus" class="notice" role="status"></div><div id="mbResult"></div></div>`;
  main.appendChild(view);
  btn.addEventListener('click',()=>{document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v===view));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b===btn));window.scrollTo(0,0);});
  document.getElementById('mbRun').addEventListener('click',()=>{
   const status=document.getElementById('mbStatus'),out=document.getElementById('mbResult');
   try{
    const r=window.CraineeBackgroundBreakEngine.simulateMatchBreakScenarios({ballPositionUnit:Number(document.getElementById('mbGrid').value),underdogScoredFirst:document.getElementById('mbHead').checked,favorite:{defenderErrorTendency:Number(document.getElementById('mbError').value)},underdog:{attackerTransitionPacing:Number(document.getElementById('mbPace').value)},environment:{isHeavyRainOrWind:document.getElementById('mbWeather').checked},referee:{whistleFrequencyChaos:Number(document.getElementById('mbWhistle').value)},breakThreshold:Number(document.getElementById('mbThreshold').value)});
    status.textContent=r.simulationStatus+' · Rupture index: '+r.ruptureIndex+' · Confidence: not estimated';
    out.innerHTML='<h2>Explored score candidates</h2><ul>'+r.exactScoreExploration.map(x=>'<li><strong>'+x.score+'</strong> — '+x.label+'</li>').join('')+'</ul><h3>Scenario signals</h3><ul>'+r.scenarioPaths.map(x=>'<li>'+(x.active?'Active signal: ':'Not active: ')+x.label+' — '+x.description+'</li>').join('')+'</ul><p class="muted">'+r.interpretation+'</p><details><summary>Limitations</summary><ul>'+r.limitations.map(x=>'<li>'+x+'</li>').join('')+'</ul></details>';
   }catch(e){status.textContent='Could not simulate: '+e.message;out.textContent='';}
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
