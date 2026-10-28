/* Additive UI for the Crainee Unconventional Outcome Engine. */
(function(){
 'use strict';
 function init(){
  if(!window.CraineeUnconventionalOutcomeEngine||!document.querySelector('#navigation')||!document.querySelector('.main')) return;
  const nav=document.querySelector('#navigation'), main=document.querySelector('.main');
  if(document.getElementById('view-unconventional')) return;
  const button=document.createElement('button');button.className='nav-item';button.dataset.view='unconventional';button.innerHTML='<span>✦</span> Unconventional outcomes';nav.appendChild(button);
  const view=document.createElement('section');view.className='view';view.id='view-unconventional';
  view.innerHTML=`<div class="page-heading"><div><div class="eyebrow">CHALLENGE THE FAVOURITE MODEL</div><h1>Unconventional Outcome Engine</h1><p class="muted">Explore alternate exact-score realities without bookmaker odds controlling candidate generation.</p></div></div>
  <div class="panel"><div class="form-grid">
  <label>Home team<input id="ucoHome" value="Home" maxlength="80"></label><label>Away team<input id="ucoAway" value="Away" maxlength="80"></label>
  <label>Main model home goals<input id="ucoMainHome" type="number" min="0" max="15" value="2"></label><label>Main model away goals<input id="ucoMainAway" type="number" min="0" max="15" value="1"></label>
  <label>Candidate count<input id="ucoCount" type="number" min="4" max="40" value="12"></label><label>Maximum goals explored<input id="ucoMax" type="number" min="2" max="10" value="5"></label>
  <label>Random seed<input id="ucoSeed" value="ufi-experiment-001" maxlength="128"></label></div>
  <p class="muted">Optional conventional scores, one per line (home-away format). Kept separate.</p><textarea id="ucoConventional" rows="3" placeholder="2-1&#10;1-1"></textarea>
  <div class="actions"><button class="button primary" id="ucoGenerate">Generate unconventional shortlist</button><button class="button ghost" id="ucoRandomSeed">New random seed</button></div>
  <div id="ucoStatus" class="notice" role="status"></div><div id="ucoResults"></div></div>
  <div class="panel"><h2>Alternate realities</h2><p>Early underdog goal · Red-card disruption · Favourite dominates but blanks · Clinical underdog · Open chaotic match · Late equaliser.</p><p class="muted">Exploration scores are not probabilities. Unexpected candidates are possibilities, not evidence-supported likelihoods.</p></div>`;
  main.appendChild(view);
  function activate(){document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v===view));document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active',b===button));window.scrollTo(0,0);}
  button.addEventListener('click',activate);
  function run(){
   const status=document.getElementById('ucoStatus'),out=document.getElementById('ucoResults');
   try{
    const conventional=(document.getElementById('ucoConventional').value||'').split(/\n+/).map(s=>s.trim()).filter(Boolean).map(s=>{const m=s.match(/^(\d{1,2})\s*[-:]\s*(\d{1,2})$/);if(!m)throw Error('Use home-away format, e.g. 2-1');return {home:+m[1],away:+m[2]};});
    const r=window.CraineeUnconventionalOutcomeEngine.generateUnconventionalOutcomes({seed:document.getElementById('ucoSeed').value,homeTeam:document.getElementById('ucoHome').value,awayTeam:document.getElementById('ucoAway').value,mainModelScore:{home:Number(document.getElementById('ucoMainHome').value),away:Number(document.getElementById('ucoMainAway').value)},candidateCount:Number(document.getElementById('ucoCount').value),maxGoals:Number(document.getElementById('ucoMax').value),conventionalShortlist:conventional});
    status.textContent='Seed: '+r.seed+' · Seed hash: '+r.seedHash+' · Same seed reproduces this experiment.';
    const rows=r.unconventionalShortlist.map(s=>'<tr><td>'+s.rank+'</td><td><strong>'+s.score+'</strong></td><td>'+s.scenarioLabel+'</td><td>'+s.explorationScore+'</td><td>Explored possibility; probability not estimated</td></tr>').join('');
    const refs=r.conventionalShortlist.map(s=>'<li>'+s.score+' — conventional reference; probability not recomputed</li>').join('');
    out.innerHTML='<h2>Unconventional shortlist</h2><div class="table-wrap"><table><thead><tr><th>#</th><th>Exact score</th><th>Scenario</th><th>Exploration score</th><th>Status</th></tr></thead><tbody>'+rows+'</tbody></table></div><h3>Conventional shortlist</h3><ul>'+refs+'</ul><details><summary>Method and limitations</summary><p>'+r.method+'</p><ul>'+r.limitations.map(x=>'<li>'+x+'</li>').join('')+'</ul></details>';
   }catch(e){status.textContent='Could not generate: '+e.message;out.textContent='';}
  }
  document.getElementById('ucoGenerate').addEventListener('click',run);
  document.getElementById('ucoRandomSeed').addEventListener('click',()=>{document.getElementById('ucoSeed').value='ufi-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,9);run();});
  run();
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
