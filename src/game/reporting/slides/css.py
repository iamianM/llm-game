"""CSS for the review packet slide deck."""

SLIDE_CSS = """
:root{
  --bg:#faf6ef;--card:#ffffff;--card-alt:#fffaf2;
  --ink:#2a2620;--muted:#786a58;--faint:#a99887;
  --line:#e3d8c5;--line-strong:#cdbfa6;
  --accent:#b9502f;--accent-soft:#f6dccf;
  --sage:#5b7c4f;--gold:#c8932a;
  --good:#2d6a3f;--bad:#a93826;
  --shadow:0 4px 14px rgba(60,40,15,.06);
  --shadow-lg:0 16px 48px rgba(60,40,15,.12);
  --radius:10px;--radius-lg:14px;
  --font-display:'Charter','Iowan Old Style','Georgia',serif;
  --font-body:'Inter',-apple-system,'Segoe UI',system-ui,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font-family:var(--font-body);font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased}
button{font-family:inherit;font-size:inherit;color:inherit}
h1,h2,h3,h4{font-family:var(--font-display);font-weight:600;letter-spacing:-.01em;margin:0}
h1{font-size:22px}h2{font-size:24px;line-height:1.25}h3{font-size:16px}h4{font-size:14px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
p{margin:.4em 0}
.muted{color:var(--muted)}.faint{color:var(--faint)}.small{font-size:13px}
.shell{min-height:100vh;display:grid;grid-template-rows:auto 1fr}

.run-header{background:linear-gradient(180deg,#fff 0%,#fffaf2 100%);border-bottom:1px solid var(--line);padding:8px 20px;position:sticky;top:0;z-index:10;box-shadow:var(--shadow)}
.run-title{display:flex;align-items:center;gap:12px;flex-wrap:wrap;min-height:32px}
.run-title h1{margin:0;font-size:18px}
.run-meta{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;gap:6px;padding:2px 9px;border-radius:999px;font-size:12px;background:var(--card-alt);border:1px solid var(--line);color:var(--ink)}
.badge.outcome-won_as_couple{background:#e7f1e8;border-color:#9fc6a7;color:var(--good)}
.badge.outcome-eliminated{background:#f7e2dd;border-color:#d7a597;color:var(--bad)}
.badge.outcome-runner_up_couple{background:#fdf2d6;border-color:#dfc26a;color:#8b6a17}
.about-btn{background:transparent;border:1px solid var(--line);padding:2px 10px;border-radius:999px;cursor:pointer;font-size:12px;color:var(--muted)}
.about-btn:hover{background:var(--card-alt);color:var(--ink)}
.day-strip{display:flex;gap:4px;padding:0 20px 6px;background:#fff;border-bottom:1px solid var(--line);overflow-x:auto;scrollbar-width:thin;position:sticky;top:48px;z-index:9}
.day-pill{flex-shrink:0;background:transparent;border:1px solid var(--line);padding:5px 11px;border-radius:999px;cursor:pointer;font-size:12px;color:var(--muted);transition:all .15s}
.day-pill:hover{background:var(--card-alt);color:var(--ink)}
.day-pill.active{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
.day-pill .day-count{font-size:10px;opacity:.7;margin-left:3px}

.layout{display:grid;grid-template-columns:240px minmax(0,1fr) 320px;gap:0;min-height:calc(100vh - 82px)}
.scene-nav{background:#fffaf2;border-right:1px solid var(--line);padding:14px 12px;overflow-y:auto;position:sticky;top:82px;align-self:start;max-height:calc(100vh - 82px)}
.scene-nav h4{margin-bottom:10px}
.day-section{margin-bottom:14px}
.day-section-head{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);padding:6px 10px;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center}
.day-section-head .count{font-size:10px;color:var(--faint)}
.scene-list{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:3px}
.scene-btn{width:100%;text-align:left;background:transparent;border:0;padding:7px 10px;border-radius:7px;cursor:pointer;display:flex;align-items:center;gap:8px;color:var(--ink);transition:background .12s}
.scene-btn:hover{background:rgba(185,80,47,.06)}
.scene-btn.active{background:var(--accent-soft);color:var(--ink);font-weight:600}
.scene-btn .icon{font-size:13px;width:16px;text-align:center;flex-shrink:0}
.scene-btn .label{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}
.scene-btn .time{font-size:10px;color:var(--muted);flex-shrink:0;font-variant-numeric:tabular-nums}
.scene-btn.active .time{color:var(--ink);opacity:.7}

.stage{padding:20px 28px;overflow-y:auto;max-height:calc(100vh - 82px)}
.scene{display:none;animation:fadein .25s ease}
.scene.active{display:block}
@keyframes fadein{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

.scene-header{display:flex;align-items:baseline;justify-content:space-between;gap:12px;margin-bottom:18px;padding-bottom:14px;border-bottom:1px solid var(--line)}
.scene-header .title-row{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.scene-kind-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:6px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
.scene-kind-conversation{background:#e7f1e8;color:var(--good)}
.scene-kind-ceremony{background:#fdf2d6;color:#8b6a17}
.scene-kind-challenge{background:#e8e0f3;color:#5e3f9e}
.scene-kind-gather{background:#fde6dc;color:var(--accent)}
.scene-kind-background{background:#eee9df;color:var(--muted)}
.scene-kind-movement{background:#eee9df;color:var(--muted)}
.scene-kind-day_boundary{background:#dfe9d9;color:var(--sage)}
.scene-kind-turn{background:#eee9df;color:var(--muted)}
.scene-meta{color:var(--muted);font-size:13px;margin:0;display:flex;gap:8px;align-items:center;flex-wrap:wrap}

.turn-pill{display:inline-flex;align-items:center;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:1px 7px;font-size:10px;font-variant-numeric:tabular-nums;color:var(--muted);font-weight:600;letter-spacing:.03em}
.turn-pill .clock{color:var(--ink)}
.turn-pill .cost{color:var(--accent);font-weight:500}
.turn-range{display:inline-block;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:0 7px;font-size:11px;color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
.clock-pill{display:inline-flex;align-items:center;gap:4px;background:var(--card);border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:11px;font-variant-numeric:tabular-nums;color:var(--ink)}

.chat{margin-top:14px;display:flex;flex-direction:column;gap:16px}
.exchange{display:flex;flex-direction:column;gap:6px;padding-bottom:8px;border-bottom:1px dashed var(--line)}
.exchange:last-child{border-bottom:0}
.exchange-header{display:flex;justify-content:flex-start;gap:8px;font-size:11px;color:var(--muted);align-items:center}
.bubble{max-width:80%;padding:10px 14px;border-radius:14px;font-size:14.5px;line-height:1.5}
.bubble.player{align-self:flex-end;background:var(--accent);color:#fff;border-bottom-right-radius:4px}
.bubble.npc{align-self:flex-start;background:var(--card);border:1px solid var(--line);border-bottom-left-radius:4px;box-shadow:var(--shadow)}
.bubble.npc .npc-tag{font-size:12px;font-weight:600;color:var(--accent);margin-bottom:4px}
.exchange-outcome{align-self:flex-start;margin-top:2px;font-size:12px;color:var(--muted);display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.outcome-pill{padding:2px 8px;border-radius:6px;background:var(--card-alt);border:1px solid var(--line);font-size:11px}
.outcome-pill.success{background:#e7f1e8;border-color:#9fc6a7;color:var(--good)}
.outcome-pill.miss{background:#f7e2dd;border-color:#d7a597;color:var(--bad)}
.outcome-pill.delta{background:#fff;border-color:var(--gold);color:#8b6a17;font-weight:600}
.intent-pill{padding:2px 8px;border-radius:6px;background:var(--accent-soft);border:1px solid var(--accent);font-size:11px;color:var(--ink)}

.inline-detail{margin-top:6px}
.inline-detail summary{cursor:pointer;font-size:11px;color:var(--muted);padding:3px 0;font-weight:500;list-style:none;display:inline-block}
.inline-detail summary::-webkit-details-marker{display:none}
.inline-detail summary:before{content:'▸ ';color:var(--accent);font-size:10px}
.inline-detail[open] summary:before{content:'▾ '}
.inline-detail summary:hover{color:var(--ink)}
.inline-body{padding:8px 12px;background:var(--card-alt);border:1px solid var(--line);border-radius:8px;font-size:12.5px;margin-top:4px;line-height:1.55}
.inline-body code{font-size:11px;background:var(--card);padding:1px 4px;border-radius:3px}
.mech-line{margin:3px 0}
.mech-line + .mech-line{margin-top:6px;padding-top:6px;border-top:1px solid var(--line)}
.rationale-line{color:var(--ink)}
.mem-summary{margin-bottom:8px;padding:6px 9px;background:var(--card);border-left:3px solid var(--sage);border-radius:4px;font-size:12.5px}
.mem-row{padding:6px 0;border-bottom:1px solid var(--line)}
.mem-row:last-child{border-bottom:0}
.mem-row .mem-meta{font-size:11px;color:var(--muted);margin-bottom:2px}
.mem-row .mem-content{font-size:12.5px;color:var(--ink)}

.inset{margin:8px 0;padding:8px 12px;border-radius:8px;font-size:12.5px}
.interruption-inset{background:#f3e8f8;border:1px solid #c8a8d4;color:#5e3f9e}
.interruption-inset .inset-tag{font-size:10px;text-transform:uppercase;letter-spacing:.06em;background:#c8a8d4;color:#fff;padding:1px 7px;border-radius:4px;margin-right:6px;font-weight:600}

.bg-detail summary{color:var(--muted);font-style:italic}
.bg-batch{padding:8px 0;border-bottom:1px solid var(--line)}
.bg-batch:last-child{border-bottom:0}
.bg-batch-head{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;margin-bottom:4px}
.mem-src.witnessed{display:inline-block;padding:0 6px;border-radius:4px;background:var(--card);border:1px solid var(--line);color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.04em;margin-left:4px}

.ceremony-feature{background:linear-gradient(180deg,#fff 0%,var(--card-alt) 100%);border:1px solid var(--line-strong);border-radius:var(--radius-lg);padding:28px 32px;margin:14px 0 18px;text-align:center;box-shadow:var(--shadow-lg)}
.ceremony-feature .label{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);font-weight:600;margin-bottom:12px}
.ceremony-feature .prose{font-family:var(--font-display);font-size:19px;line-height:1.5;color:var(--ink);max-width:60ch;margin:0 auto}
.ceremony-feature .ceremony-events{margin-top:14px;display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--muted);text-align:left;max-width:60ch;margin-left:auto;margin-right:auto}
.ceremony-feature .ceremony-event{padding:2px 0}
.ceremony-feature.finale{background:linear-gradient(135deg,#fff8e1 0%,#fde6dc 100%);border-color:var(--gold);padding:44px 36px}
.ceremony-feature.finale .label{color:var(--gold);font-size:14px;letter-spacing:.15em}
.ceremony-feature.finale .prose{font-size:22px}

.challenge-feature{background:linear-gradient(135deg,#fff 0%,#f7f0e6 100%);border:1px solid var(--line-strong);border-radius:var(--radius-lg);padding:20px 24px;margin:14px 0 18px}
.challenge-feature .label{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#5e3f9e;font-weight:600}
.challenge-feature .name{font-family:var(--font-display);font-size:20px;margin:6px 0 10px;display:flex;align-items:baseline;gap:10px}
.challenge-feature .summary{font-size:14px;color:var(--ink);margin-bottom:8px}

.recap-feature{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:18px 22px;margin:12px 0;border-left:4px solid var(--sage)}
.recap-feature h3{margin-bottom:10px}
.recap-feature .recap-item{padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}
.recap-feature .recap-item:last-child{border-bottom:0}

.bg-vignette{background:var(--card-alt);border:1px solid var(--line);border-radius:var(--radius);padding:12px 16px;margin:10px 0}
.bg-vignette .where{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px}
.bg-vignette .line{font-style:italic;color:var(--ink);font-size:14px;line-height:1.55;margin:4px 0}
.bg-vignette .who{font-size:12px;color:var(--muted);margin-bottom:4px}

.right-rail{background:var(--card-alt);border-left:1px solid var(--line);padding:14px 14px;overflow-y:auto;position:sticky;top:82px;align-self:start;max-height:calc(100vh - 82px)}
.right-rail section{margin-bottom:22px}
.right-rail h4{margin-bottom:10px}

.couples-list{display:flex;flex-direction:column;gap:6px}
.couple-row{display:flex;align-items:center;gap:6px;padding:6px 8px;background:var(--card);border:1px solid var(--line);border-radius:7px;font-size:12px}
.couple-row.player-couple{border-color:var(--accent);background:var(--accent-soft)}
.couple-row .avatar{width:22px;height:22px;font-size:9px}
.couple-row .couple-amp{color:var(--muted);font-size:10px}
.couple-row .couple-names{flex:1;line-height:1.2}
.couple-row .couple-strength{font-size:10px;color:var(--muted);font-variant-numeric:tabular-nums}

.villa-map{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.map-cell{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px;min-height:54px;display:flex;flex-direction:column;gap:3px}
.map-cell.player-here{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent-soft)}
.map-cell .loc-name{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:600}
.map-cell .loc-people{font-size:12px;color:var(--ink);line-height:1.35}
.map-cell .you-marker{color:var(--accent);font-weight:600}

.cast-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.cast-card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px;cursor:pointer;display:flex;align-items:center;gap:8px;transition:all .12s;text-align:left}
.cast-card:hover{border-color:var(--accent);background:#fff}
.cast-card.your-partner{border-color:var(--accent);background:var(--accent-soft)}
.avatar{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;color:#fff;font-size:11px;font-weight:700;flex-shrink:0}
.cast-card .cast-info{flex:1;min-width:0}
.cast-card .cast-name{font-size:13px;font-weight:600;line-height:1.2;color:var(--ink)}
.cast-card .cast-loc{font-size:10px;color:var(--muted);line-height:1.2}

.bookmarks-list{display:flex;flex-direction:column;gap:6px}
.bm-group summary{cursor:pointer;font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;padding:4px 0;list-style:none}
.bm-group summary::-webkit-details-marker{display:none}
.bm-group summary:before{content:'▸';color:var(--accent);margin-right:6px;font-size:10px}
.bm-group[open] summary:before{content:'▾'}
.bm-item{display:flex;align-items:flex-start;gap:6px;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:7px 9px;cursor:pointer;font-size:12px;line-height:1.35;text-align:left;width:100%;margin-top:4px}
.bm-item:hover{border-color:var(--accent)}
.bm-item .bm-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;margin-top:5px}
.bm-event .bm-dot{background:#6b3fa0}
.bm-highlight .bm-dot{background:var(--good)}
.bm-anomaly .bm-dot{background:#d97917}
.bm-error .bm-dot{background:var(--bad)}
.bm-note .bm-dot{background:var(--accent)}
.bm-regression .bm-dot{background:var(--bad)}
.bm-smell .bm-dot{background:var(--gold)}
.bm-item .bm-title{flex:1;color:var(--ink)}

dialog{border:0;border-radius:var(--radius-lg);background:var(--card);color:var(--ink);padding:0;max-width:520px;width:90vw;box-shadow:0 24px 80px rgba(0,0,0,.28)}
dialog::backdrop{background:rgba(40,30,20,.45)}
.dialog-head{padding:18px 22px 12px;border-bottom:1px solid var(--line);display:flex;align-items:flex-start;gap:14px}
.dialog-head .avatar{width:44px;height:44px;font-size:14px}
.dialog-head h3{margin-bottom:2px;font-size:20px}
.dialog-head .sub{color:var(--muted);font-size:13px}
.dialog-close{margin-left:auto;background:transparent;border:0;cursor:pointer;font-size:20px;color:var(--muted);line-height:1}
.dialog-close:hover{color:var(--ink)}
.dialog-body{padding:18px 22px;max-height:60vh;overflow-y:auto}
.dialog-body section{margin-bottom:16px}
.dialog-body section:last-child{margin-bottom:0}
.dialog-body h4{margin-bottom:8px;font-size:11px}

.rel-row{display:grid;grid-template-columns:88px 1fr;align-items:center;gap:10px;font-size:12px;margin:4px 0}
.rel-label{color:var(--muted);text-transform:capitalize}
.rel-bar{height:8px;background:var(--card-alt);border-radius:4px;overflow:hidden;border:1px solid var(--line)}
.rel-fill{height:100%;background:var(--accent);transition:width .2s}
.rel-fill.cool{background:var(--sage)}
.rel-fill.weak{background:var(--gold)}

.memory-list{display:flex;flex-direction:column;gap:8px}
.memory{background:var(--card-alt);border:1px solid var(--line);border-radius:8px;padding:10px 12px;font-size:13px;line-height:1.5}
.memory .mem-meta{font-size:11px;color:var(--muted);margin-bottom:4px}
.memory .mem-content{font-style:italic;color:var(--ink)}
.memory .mem-tags{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px}
.memory .mem-tag{font-size:10px;background:var(--card);border:1px solid var(--line);border-radius:4px;padding:1px 6px;color:var(--muted)}

@media(max-width:1200px){.layout{grid-template-columns:220px minmax(0,1fr) 280px}}
@media(max-width:1000px){.layout{grid-template-columns:1fr;grid-template-rows:auto 1fr auto}.scene-nav,.right-rail{position:static;max-height:none;border:0;border-bottom:1px solid var(--line)}.scene-nav,.right-rail{padding:12px 16px}}
"""
