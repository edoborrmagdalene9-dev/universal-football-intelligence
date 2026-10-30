(function(){
'use strict';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let lastReport=null;
function status(message,kind){const el=$('historical1x2Status');if(el){el.className='notice'+(kind?' '+kind:'');el.textContent=message;}}
function parseRows(raw){
 const lines=raw.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
 return lines.map((line,index)=>{
  const p=line.split('|').map(x=>x.trim());
  if(p.length!==5)throw Error('Line '+(index+1)+': use exactly five fields separated by |.');
  const [date,competition,home_team,away_team,selection]=p;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('Line '+(index+1)+': date must be YYYY-MM-DD.');
  if(!competition||!home_team||!away_team||!selection)throw Error('Line '+(index+1)+': all five fields are required.');
  return {date,competition,home_team,away_team,selection};
 });
}
function render(report){
 const target=$('historical1x2Output');if(!target)return;
 const rows=report.picks||[];
 target.innerHTML='<p><b>'+rows.length+' fixtures screened</b> · '+Number(report.dataset_matches_loaded||0).toLocaleString()+' historical results · Data cutoff: '+esc(report.historical_data_cutoff||'unknown')+'</p>'+
 '<div class="table-wrap"><table><thead><tr><th>Fixture</th><th>Pick</th><th>Historical H/D/A baseline</th><th>Pick probability</th><th>Screen</th><th>Evidence</th></tr></thead><tbody>'+
 rows.map(r=>'<tr><td>'+esc(r.home_team)+' vs '+esc(r.away_team)+'<br><small>'+esc(r.date)+' · '+esc(r.competition)+'</small></td><td>'+esc(r.selection)+'</td><td>H '+(100*r.p_home_baseline).toFixed(1)+'% / D '+(100*r.p_draw_baseline).toFixed(1)+'% / A '+(100*r.p_away_baseline).toFixed(1)+'%</td><td>'+(100*r.selected_probability_baseline).toFixed(1)+'%</td><td><b>'+esc(r.screen)+'</b></td><td>'+esc(r.reason)+'<br><small>Home history: '+r.home_team_historical_matches+' · Away venue history: '+r.away_team_historical_away_matches+' · Model cutoff: '+esc(r.model_data_cutoff||'unknown')+'</small></td></tr>').join('')+
 '</tbody></table></div><p class="muted">'+esc(report.method)+'</p><p class="amber">Historical frequency is not a calibrated forecast or a guaranteed spoiler detector. Do not auto-remove a selection from this screen alone. Cross-check current fixtures, team news, odds and independent model evidence.</p>';
}
async function run(){
 const button=$('runHistorical1x2');if(!button)return;
 let picks;
 try{picks=parseRows($('historical1x2Input').value);if(!picks.length)throw Error('Enter at least one fixture.');}
 catch(e){status(e.message,'error');return;}
 button.disabled=true;status('Running historical audit. The first request may download and cache the results archive.','warning');
 try{
  const apiOrigin=location.hostname.endsWith('github.io')?'https://universal-football-intelligence.onrender.com':'';
  const response=await fetch(apiOrigin+'/api/slip/historical-audit',{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify({picks})});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok||!payload.ok)throw Error(payload.error||('Historical audit returned HTTP '+response.status));
  lastReport=payload.report;render(lastReport);
  $('exportHistorical1x2').disabled=false;
  status('Completed: '+lastReport.picks_audited+' picks screened. Dataset cutoff '+lastReport.historical_data_cutoff+'.','good');
 }catch(e){status('Historical audit did not run: '+e.message+'. If this page is hosted on GitHub Pages, open the Render app; if the server reports missing pandas/pyarrow, install the requirements listed in the deployment note. Your existing slip data was not changed.','error');}
 finally{button.disabled=false;}
}
function exportReport(){if(!lastReport)return;const blob=new Blob([JSON.stringify(lastReport,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='ufi-historical-1x2-audit.json';a.click();URL.revokeObjectURL(url);}
document.addEventListener('DOMContentLoaded',()=>{$('runHistorical1x2')?.addEventListener('click',run);$('exportHistorical1x2')?.addEventListener('click',exportReport);});
})();