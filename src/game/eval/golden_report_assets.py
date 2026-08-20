"""Static assets for the golden eval HTML report."""

from __future__ import annotations


def report_script() -> str:
    """Return small client-side helpers for reviewing the report."""
    return """
<script>
const buttons=[...document.querySelectorAll('[data-filter]')];
const search=document.querySelector('#search');
const sortMode=document.querySelector('#sortMode');
const nav=document.querySelector('.scenario-nav');
const workspace=document.querySelector('.scenario-workspace');
const rank={fail:0,cannot_determine:1,pass:2};
let selectedId=decodeURIComponent(location.hash.replace(/^#/,'')) || document.querySelector('.scenario')?.id;
function ordered(items,mode){
  return items.sort((a,b)=>{
    if(mode==='status') return (rank[a.dataset.status]??9)-(rank[b.dataset.status]??9) || Number(a.dataset.index)-Number(b.dataset.index);
    if(mode==='title') return a.dataset.title.localeCompare(b.dataset.title);
    if(mode==='turns') return Number(b.dataset.turns)-Number(a.dataset.turns) || Number(b.dataset.failures)-Number(a.dataset.failures);
    return Number(a.dataset.index)-Number(b.dataset.index);
  });
}
function applyFilters(){
  const mode=sortMode.value;
  ordered([...document.querySelectorAll('.scenario')],mode).forEach(card=>workspace.appendChild(card));
  ordered([...document.querySelectorAll('.nav-item')],mode).forEach(item=>nav.appendChild(item));
  const active=document.querySelector('[data-filter].active')?.dataset.filter || 'all';
  const query=(search.value || '').toLowerCase();
  const visible=[];
  document.querySelectorAll('.nav-item').forEach(item=>{
    const target=document.querySelector(item.getAttribute('href'));
    const show=target&&(active==='all'||target.dataset.status===active)&&(!query||target.textContent.toLowerCase().includes(query));
    item.hidden=!show;
    if(show) visible.push(target.id);
  });
  if(!visible.includes(selectedId)) selectedId=visible[0];
  selectScenario(selectedId,false);
}
function selectScenario(id,updateHash=true){
  if(!id) return;
  selectedId=id;
  document.querySelectorAll('.scenario').forEach(card=>card.hidden=card.id!==id);
  document.querySelectorAll('.nav-item').forEach(item=>item.classList.toggle('selected',item.getAttribute('href')==='#'+id));
  if(updateHash) history.replaceState(null,'','#'+encodeURIComponent(id));
}
buttons.forEach(button=>button.addEventListener('click',()=>{
  buttons.forEach(other=>other.classList.remove('active'));
  button.classList.add('active');
  applyFilters();
}));
search.addEventListener('input',applyFilters);
sortMode.addEventListener('change',applyFilters);
document.querySelectorAll('.nav-item').forEach(item=>item.addEventListener('click',event=>{
  event.preventDefault();
  selectScenario(item.getAttribute('href').slice(1));
  if(matchMedia('(max-width: 820px)').matches) document.querySelector('.scenario-workspace').scrollIntoView({behavior:'smooth'});
}));
applyFilters();
</script>
"""


def report_css() -> str:
    """Return the editorial, trace-first stylesheet used by the static dashboard."""
    return """
:root{color-scheme:light;--salt:#fffdf1;--paper:#f7f4e7;--panel:#efecdd;--clay:#d9d4c0;--stone:#9b9889;--coal:#282725;--muted:#6d6b61;--pass:#5a6440;--fail:#a13a2a;--warn:#8a7a49;--accent:#caff75}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--coal);font:14px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background-image:radial-gradient(rgba(40,39,37,.035) 1px,transparent 1px);background-size:4px 4px}main{max-width:1500px;margin:auto;padding:24px 30px 72px}h2,h3,p{overflow-wrap:anywhere}h2{margin:0;font:600 30px/1.08 Georgia,"Times New Roman",serif;letter-spacing:-.025em}h3{margin:18px 0 9px;font-size:14px}.eyebrow{margin:0 0 7px;color:var(--muted);font:600 10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.09em;text-transform:uppercase}.hero{display:grid;grid-template-columns:minmax(300px,.9fr) minmax(520px,1.3fr);gap:42px;padding:24px 26px;border:1px solid var(--clay);border-radius:7px;background:rgba(255,253,241,.86)}.lede{max-width:620px;margin:8px 0;color:var(--muted);font-size:14px}.run-summary{display:flex;flex-wrap:wrap;gap:18px;margin-top:18px;font-size:12px}.summary-item{display:inline-flex;align-items:center;gap:6px}.summary-total{color:var(--muted)}.status-dot{display:inline-block;width:7px;height:7px;flex:none;border-radius:50%;background:var(--stone)}.status-dot.pass{background:var(--pass)}.status-dot.fail{background:var(--fail)}.status-dot.cannot_determine{background:var(--warn)}.metrics{display:grid;grid-template-columns:repeat(4,minmax(90px,1fr));align-content:start;border-left:1px solid var(--clay)}.metric{min-width:0;padding:8px 14px}.metric span{display:block;color:var(--muted);font:600 9px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.06em;text-transform:uppercase}.metric b{display:block;margin-top:3px;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.dashboard-shell{display:grid;grid-template-columns:292px minmax(0,1fr);gap:20px;margin-top:18px}.scenario-rail{position:sticky;top:16px;height:calc(100vh - 32px);min-height:520px;overflow:hidden;border:1px solid var(--clay);border-radius:7px;background:rgba(255,253,241,.82)}.toolbar{padding:16px 14px 10px;border-bottom:1px solid var(--clay)}.rail-heading{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px}.rail-heading b{font:600 19px/1.1 Georgia,"Times New Roman",serif}.rail-heading span{color:var(--muted);font-size:10px}button,select,input{font:inherit;color:var(--coal);background:transparent}input[type=search],select{width:100%;border:1px solid var(--clay);border-radius:4px;padding:8px 9px;outline:none}input[type=search]:focus,select:focus{border-color:var(--muted)}.filters{display:flex;gap:16px;margin:10px 0 2px;border-bottom:1px solid var(--clay)}.filters button{padding:6px 0 7px;border:0;border-bottom:2px solid transparent;color:var(--muted);cursor:pointer;font-size:11px}.filters button.active{border-color:var(--coal);color:var(--coal)}.rail-tools{margin-top:9px}.rail-tools select{border:0;padding:3px 0;color:var(--muted);font-size:11px}.scenario-nav{height:calc(100% - 162px);overflow-y:auto;padding:5px 7px 12px}.nav-item{display:flex;align-items:flex-start;gap:10px;padding:10px 9px;color:var(--coal);text-decoration:none;border-bottom:1px solid rgba(155,152,137,.27)}.nav-item:hover{background:rgba(40,39,37,.035)}.nav-item.selected{background:var(--panel);box-shadow:inset 3px 0 var(--coal)}.nav-item .status-dot{margin-top:5px}.nav-copy{min-width:0}.nav-copy b{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.nav-copy small{display:block;margin-top:3px;color:var(--muted);font-size:10px}.scenario-workspace{min-width:0}.scenario{padding:22px 26px 50px;border:1px solid var(--clay);border-radius:7px;background:rgba(255,253,241,.88)}.scenario-head{display:flex;justify-content:space-between;align-items:flex-start;gap:22px;padding-bottom:15px;border-bottom:1px solid var(--clay)}.scenario-head p{max-width:820px;margin:8px 0 0;color:var(--muted)}.scenario-head-tags{display:flex;gap:14px;align-items:center;white-space:nowrap}.mode-label,.status-label{color:var(--muted);font:600 10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.05em;text-transform:uppercase}.status-label{display:inline-flex;align-items:center;gap:6px}.scenario-meta,.pill-row,.trace-metrics{display:flex;gap:18px;align-items:center;flex-wrap:wrap}.scenario-meta{padding:11px 0;border-bottom:1px solid var(--clay);color:var(--muted);font-size:11px}.scenario-meta b{color:var(--coal)}.thread-review{margin:20px 0 8px;padding:15px 0;border-top:2px solid var(--coal);border-bottom:1px solid var(--clay)}.section-heading{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.section-heading h3{margin:0;font:600 20px/1.1 Georgia,"Times New Roman",serif}.thread-check-grid,.checks,.trace-grid{display:block}.golden-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}.thread-check,.check,.trace-card{min-width:0;padding:11px 2px;border-top:1px solid var(--clay)}.contract-card{min-width:0;padding:10px 12px;border-left:2px solid var(--clay);background:rgba(239,236,221,.45)}.thread-check>div,.check>div{display:flex;gap:8px;align-items:center}.thread-check span,.check span{font-size:9px;text-transform:uppercase;letter-spacing:.08em}.thread-check small,.check small{margin-left:auto;color:var(--muted)}.thread-check.pass span,.check.pass span{color:var(--pass)}.thread-check.fail,.check.fail{border-left:3px solid var(--fail);padding-left:10px}.thread-check.fail span,.check.fail span,.trace-error{color:var(--fail)}.thread-check.cannot_determine span,.check.cannot_determine span{color:var(--warn)}.judge-meta{display:grid;justify-items:end;gap:3px;color:var(--muted);font-size:10px}.judge-meta>b{color:var(--coal)}.judge-meta details{text-align:right}.turn{border-top:1px solid var(--clay);padding:10px 0}.turn>summary{display:flex;align-items:center;gap:12px;cursor:pointer;font-weight:650;padding:5px 1px}.turn>summary small{margin-left:auto;color:var(--muted);font-weight:400;min-width:0;overflow:hidden;text-overflow:ellipsis}.turn>section{margin:14px 0 24px;padding-left:18px;border-left:1px solid var(--clay)}.golden{margin:8px 0 0;padding:9px 11px;border-left:3px solid var(--warn);background:rgba(239,236,221,.65)}.fact-card,.dialogue,blockquote,.response-block{max-width:100%;margin:9px 0;padding:12px 14px;border-left:2px solid var(--clay);background:rgba(247,244,231,.75);overflow:auto}.dialogue p{display:grid;grid-template-columns:72px 1fr;gap:12px;margin:8px 0}.dialogue b{font:600 10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.05em;text-transform:uppercase}.muted,.evidence{color:var(--muted);font-size:11px}.compact{margin:8px 0;padding-left:19px}.compact li{margin:4px 0;overflow-wrap:anywhere}table{width:100%;margin-top:8px;border-collapse:collapse}th,td{padding:7px;text-align:left;vertical-align:top;border-bottom:1px solid var(--clay);overflow-wrap:anywhere}th{color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.05em}.trace-card>b{font-size:14px}.trace-card details{margin-top:10px}.trace-card summary,.judge-meta summary{cursor:pointer;color:var(--muted)}.trace-metrics{margin:7px 0;gap:12px}.trace-metrics span,.pill{color:var(--muted);font-size:10px}.pill:not(:last-child)::after{content:" ·"}.reasoning{border-top:1px solid var(--clay);padding-top:9px}.failure-box{margin:12px 0;padding:10px 12px;border-left:3px solid var(--fail);background:#f1e1d9;color:#5a2017}.resort-summary{margin-top:8px}
.nav-item[hidden]{display:none!important}
.thread-rubric{margin-top:8px;border-top:1px solid var(--clay);padding:10px 2px;color:var(--muted);font-size:11px}.thread-rubric summary{cursor:pointer;font-weight:600;color:var(--coal)}.thread-rubric ol{margin:10px 0 0;padding-left:20px}.thread-rubric li{margin:8px 0}.thread-rubric li b{display:block;color:var(--coal);font-size:10px}.thread-rubric li span{display:block;margin-top:2px}
@media(max-width:980px){main{padding:18px}.hero{grid-template-columns:1fr}.metrics{border-left:0;border-top:1px solid var(--clay);padding-top:8px}.dashboard-shell{grid-template-columns:245px minmax(0,1fr)}.section-heading{display:block}.judge-meta{justify-items:start;margin-top:10px}.judge-meta details{text-align:left}}
@media(max-width:820px){main{padding:12px}.hero{padding:18px}.metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.dashboard-shell{grid-template-columns:1fr}.scenario-rail{position:static;height:390px;min-height:0}.scenario{padding:18px}.scenario-head,.turn>summary{display:block}.scenario-head-tags{margin-top:10px}.turn>summary small{display:block;margin:5px 0}.dialogue p{grid-template-columns:1fr}.golden-grid{grid-template-columns:minmax(0,1fr)}}
"""
