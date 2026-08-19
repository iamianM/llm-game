"""Static assets for the golden eval HTML report."""

from __future__ import annotations


def report_script() -> str:
    """Return small client-side helpers for reviewing the report."""
    return """
<script>
const buttons=[...document.querySelectorAll('[data-filter]')];
const search=document.querySelector('#search');
const sortMode=document.querySelector('#sortMode');
const main=document.querySelector('main');
const nav=document.querySelector('.scenario-nav');
const rank={fail:0,cannot_determine:1,pass:2};
function ordered(items,mode){
  return items.sort((a,b)=>{
    if(mode==='status') return (rank[a.dataset.status]??9)-(rank[b.dataset.status]??9) || Number(a.dataset.index)-Number(b.dataset.index);
    if(mode==='title') return a.dataset.title.localeCompare(b.dataset.title);
    if(mode==='turns') return Number(b.dataset.turns)-Number(a.dataset.turns) || Number(b.dataset.failures)-Number(a.dataset.failures);
    return Number(a.dataset.index)-Number(b.dataset.index);
  });
}
function sortScenarios(){
  const mode=sortMode.value;
  ordered([...document.querySelectorAll('.scenario')],mode).forEach(card=>main.appendChild(card));
  ordered([...document.querySelectorAll('.nav-item')],mode).forEach(item=>nav.appendChild(item));
}
function applyFilters(){
  sortScenarios();
  const active=document.querySelector('[data-filter].active')?.dataset.filter || 'all';
  const query=(search.value || '').toLowerCase();
  document.querySelectorAll('.scenario').forEach(card=>{
    const statusOk=active==='all' || card.dataset.status===active;
    const textOk=!query || card.textContent.toLowerCase().includes(query);
    card.hidden=!(statusOk && textOk);
  });
  document.querySelectorAll('.nav-item').forEach(item=>{
    const statusOk=active==='all' || item.dataset.status===active;
    const target=document.querySelector(item.getAttribute('href'));
    item.hidden=!statusOk || (target && target.hidden);
  });
}
buttons.forEach(button=>button.addEventListener('click',()=>{
  buttons.forEach(other=>other.classList.remove('active'));
  button.classList.add('active');
  applyFilters();
}));
search.addEventListener('input', applyFilters);
sortMode.addEventListener('change', applyFilters);
document.querySelector('#collapseAll').addEventListener('click',()=>{
  document.querySelectorAll('details.turn').forEach(item=>item.open=false);
});
document.querySelector('#expandFailures').addEventListener('click',()=>{
  document.querySelectorAll('details.turn').forEach(item=>item.open=item.dataset.status==='fail');
});
</script>
"""


def report_css() -> str:
    """Return the report stylesheet."""
    return """
:root{color-scheme:light;--bg:#f6f2ea;--ink:#25221d;--muted:#6b6258;--line:#d8cfc0;--card:#fffdf9;--pass:#137447;--fail:#a7352a;--warn:#8c6400;--accent:#7b3f98}
*{box-sizing:border-box}html,body{max-width:100%;overflow-x:hidden}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}main{width:100%;max-width:1240px;margin:0 auto;padding:28px}main>*,section,details,summary{min-width:0}h1{margin:0 0 18px;font-size:28px}h2{margin:0 0 8px;font-size:24px;overflow-wrap:anywhere}h3{margin:18px 0 8px;font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}p{line-height:1.45;overflow-wrap:anywhere}.hero,.toolbar,.scenario,.scenario-nav{max-width:100%;background:var(--card);border:1px solid var(--line);border-radius:10px}.hero{display:grid;grid-template-columns:1.2fr 1fr;gap:20px;padding:22px;margin-bottom:14px}.hero>*,.toolbar>*,.scenario>*{min-width:0}.eyebrow{margin:0 0 4px;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em}.lede{max-width:760px;color:var(--muted);overflow-wrap:anywhere}.metrics{display:grid;grid-template-columns:repeat(2,minmax(120px,1fr));gap:8px;min-width:0}.metric{min-width:0;border:1px solid var(--line);border-radius:8px;padding:10px;background:#fff}.metric span{display:block;color:var(--muted);font-size:12px}.metric b{font-size:24px}.metric.pass b{color:var(--pass)}.metric.fail b{color:var(--fail)}.toolbar{position:sticky;top:0;z-index:2;display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;padding:12px;margin:14px 0}.filters{display:flex;gap:6px;flex-wrap:wrap;min-width:0}button,select{border:1px solid var(--line);background:#fff;border-radius:7px;padding:7px 10px;cursor:pointer;max-width:100%}input[type=search]{width:100%;min-width:0;border:1px solid var(--line);border-radius:7px;padding:9px 10px}button.active{background:var(--ink);color:#fff}.scenario-nav{display:flex;gap:8px;overflow:auto;padding:10px;margin-bottom:14px}.nav-item{white-space:nowrap;color:var(--ink);text-decoration:none;border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 8px;display:flex;gap:8px;align-items:center}.scenario{padding:18px;margin:16px 0}.scenario-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}.scenario-head>.badge{flex:0 0 auto}.scenario-meta,.pill-row{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;min-width:0}.scenario-meta span,.badge,.pill{border:1px solid var(--line);border-radius:999px;padding:4px 8px;background:#fff;color:var(--muted);font-size:12px;max-width:100%;overflow:hidden;text-overflow:ellipsis}.badge.pass{color:var(--pass);border-color:#a5d6bd}.badge.fail{color:var(--fail);border-color:#e3aaa4}.badge.cannot_determine{color:var(--warn);border-color:#d9c58a}.badge.mode-mock{color:var(--muted);background:#f0ece4;border-color:#cdc6b8}.badge.mode-real{color:#fff;background:var(--accent);border-color:var(--accent)}.scenario-head-tags{display:flex;gap:6px;align-items:center;flex-wrap:wrap;flex:0 0 auto}.failure-box{border-left:4px solid var(--fail);background:#fff4f2;padding:10px 12px;margin:12px 0}.turn{border-top:1px solid var(--line);padding:10px 0}.turn summary{cursor:pointer;display:flex;align-items:center;gap:10px;font-weight:700}.turn summary small{margin-left:auto;color:var(--muted);font-weight:400;min-width:0;overflow:hidden;text-overflow:ellipsis}.golden{background:#f8f5ff;border-left:4px solid var(--accent);padding:10px 12px}.checks,.trace-grid,.golden-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:8px;min-width:0}.check,.trace-card,.contract-card{min-width:0;border:1px solid var(--line);border-radius:8px;background:#fff;padding:10px}.check span{font-size:12px;text-transform:uppercase}.check.pass span{color:var(--pass)}.check.fail{border-color:#e3aaa4}.check.fail span,.trace-error{color:var(--fail)}.check.cannot_determine span{color:var(--warn)}.evidence{color:var(--muted);font-size:13px}.fact-card,.dialogue,blockquote{max-width:100%;border:1px solid var(--line);border-radius:8px;background:#fff;padding:12px;margin:10px 0;overflow:auto}.dialogue p{display:grid;grid-template-columns:80px 1fr;gap:12px;margin:8px 0}.muted{color:var(--muted);font-size:13px}.compact{margin:8px 0;padding-left:20px}.compact li{margin:4px 0;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;margin-top:8px}th,td{border-bottom:1px solid var(--line);padding:7px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{color:var(--muted);font-size:12px}.trace-card p{font-size:13px}.response-block{max-width:100%;background:#fbfaf7;border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:8px;overflow:auto}.response-block p{margin:6px 0}.resort-summary{margin-top:8px}@media(max-width:820px){main{padding:16px}.hero,.toolbar{grid-template-columns:1fr}.turn summary{display:block}.turn summary small{display:block;margin:4px 0 0}.dialogue p{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.checks,.trace-grid,.golden-grid{grid-template-columns:minmax(0,1fr)}}@media(max-width:520px){main{padding:14px}.hero,.scenario{padding:16px}.metrics{grid-template-columns:1fr}.scenario-head{display:block}.toolbar{position:static}.scenario-meta span{white-space:normal}.filters button,.filters select{flex:1 1 auto}}
"""
