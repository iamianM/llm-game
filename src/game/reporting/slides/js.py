"""JavaScript for the review packet slide deck."""

SLIDE_JS = r"""
(function(){
  const scenes=[...document.querySelectorAll('.scene')];
  const sceneBtns=[...document.querySelectorAll('.scene-btn')];
  const dayPills=[...document.querySelectorAll('.day-pill')];
  const mapHost=document.getElementById('villa-map-host');
  let meta=[];
  try{meta=JSON.parse(document.getElementById('scene-meta').textContent||'[]');}catch(e){}
  let current=0;

  function displayName(n){
    if(!n)return'';
    return String(n).split('_')[0].replace(/^./,c=>c.toUpperCase());
  }

  function renderVillaMap(snapshot){
    if(!mapHost)return;
    if(!snapshot||Object.keys(snapshot).length===0){
      mapHost.innerHTML="<p class='muted small'>No villa map for this scene.</p>";
      return;
    }
    const order=['pool','kitchen','terrace','bedroom','firepit','hideaway'];
    const keys=Object.keys(snapshot).sort((a,b)=>{
      const ia=order.indexOf(a),ib=order.indexOf(b);
      return (ia<0?99:ia)-(ib<0?99:ib);
    });
    const cells=keys.map(loc=>{
      const occ=snapshot[loc]||[];
      if(loc==='hideaway'&&occ.length===0)return'';
      const playerHere=occ.some(o=>String(o).toLowerCase()==='you');
      const names=occ.map(o=>{
        const s=String(o);
        if(s.toLowerCase()==='you')return "<span class='you-marker'>You</span>";
        return displayName(s);
      });
      const cls=playerHere?'map-cell player-here':'map-cell';
      const people=names.length?names.join(', '):"<span class='muted'>—</span>";
      return `<div class='${cls}'><div class='loc-name'>${loc.toUpperCase()}</div><div class='loc-people'>${people}</div></div>`;
    }).join('');
    mapHost.innerHTML=`<div class='villa-map'>${cells}</div>`;
  }

  function highlightDay(day){
    dayPills.forEach(p=>p.classList.toggle('active',String(p.dataset.day)===String(day)));
  }

  function showScene(index){
    if(!scenes.length)return;
    current=Math.max(0,Math.min(index,scenes.length-1));
    scenes.forEach((s,i)=>s.classList.toggle('active',i===current));
    sceneBtns.forEach(b=>{
      b.classList.toggle('active',Number(b.dataset.sceneIndex)===current);
    });
    const m=meta[current];
    if(m){
      highlightDay(m.day);
      renderVillaMap(m.villa_snapshot);
      const activeBtn=document.querySelector(`.scene-btn[data-scene-index='${current}']`);
      if(activeBtn&&activeBtn.scrollIntoView){
        activeBtn.scrollIntoView({block:'nearest',behavior:'smooth'});
      }
      const stage=document.querySelector('.stage');
      if(stage)stage.scrollTop=0;
    }
  }

  sceneBtns.forEach(btn=>{
    btn.addEventListener('click',()=>{
      const idx=Number(btn.dataset.sceneIndex);
      if(!Number.isNaN(idx))showScene(idx);
    });
  });

  dayPills.forEach(pill=>{
    pill.addEventListener('click',()=>{
      const idx=Number(pill.dataset.firstScene);
      if(!Number.isNaN(idx))showScene(idx);
    });
  });

  document.querySelectorAll('.bm-item').forEach(item=>{
    item.addEventListener('click',()=>{
      const idx=Number(item.dataset.sceneIndex);
      if(!Number.isNaN(idx))showScene(idx);
    });
  });

  document.addEventListener('keydown',event=>{
    if(event.target.closest('input,textarea,[contenteditable]'))return;
    if(document.querySelector('dialog[open]'))return;
    if(event.key==='ArrowRight'||event.key==='j')showScene(current+1);
    if(event.key==='ArrowLeft'||event.key==='k')showScene(current-1);
  });

  document.addEventListener('click',event=>{
    const opener=event.target.closest('[data-open-dialog]');
    if(opener){
      const dlg=document.getElementById(opener.dataset.openDialog);
      if(dlg&&typeof dlg.showModal==='function')dlg.showModal();
      else if(dlg)dlg.setAttribute('open','');
      event.preventDefault();
    }
    const closer=event.target.closest('[data-close-dialog]');
    if(closer){
      const dlg=closer.closest('dialog');
      if(dlg)dlg.close();
    }
  });

  document.querySelectorAll('dialog').forEach(d=>{
    d.addEventListener('click',e=>{
      if(e.target===d){const r=d.getBoundingClientRect();const x=e.clientX,y=e.clientY;
        if(x<r.left||x>r.right||y<r.top||y>r.bottom)d.close();
      }
    });
  });

  showScene(0);
})();
"""
