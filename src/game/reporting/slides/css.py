"""CSS for the slide-based review packet."""

SLIDE_CSS = """
:root{--bg:#f6f1e9;--ink:#211d19;--muted:#766a5d;--card:#fffaf2;--line:#dbcdbb;--accent:#b9502f;--good:#17633a;--bad:#9b2d20}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}
.review-shell{height:100vh;display:grid;grid-template-rows:auto 1fr;background:var(--bg)}
.topbar{display:flex;gap:18px;align-items:center;padding:12px 18px;border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:4}
.topbar h1{font-size:18px;margin:0;white-space:nowrap}.timeline{display:flex;gap:6px;overflow:auto;flex:1}
.timeline button,.bookmark-strip button,.nav button{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 10px;cursor:pointer}
.timeline button.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.deck-layout{display:grid;grid-template-columns:minmax(0,1fr) 300px;height:100%;overflow:hidden}
.slides{position:relative;overflow:hidden;padding:22px}.slide{display:none;height:100%;overflow:auto}.slide.active{display:block}
.scene-card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:24px;min-height:calc(100vh - 140px);box-shadow:0 8px 24px rgba(50,30,10,.08)}
.scene-card h2{margin:0 0 8px;font-size:26px}.scene-meta{color:var(--muted);margin-bottom:18px}
.record-block{border-top:1px solid var(--line);padding:14px 0}.record-block:first-of-type{border-top:0}
.pill{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 8px;margin:2px;background:#fff}
.success{color:var(--good)}.miss{color:var(--bad)}.dialogue{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px;margin:8px 0}
.side-panel{border-left:1px solid var(--line);background:#fff;overflow:auto;padding:16px}.side-panel h3{margin:0 0 12px}
.state-card{border:1px solid var(--line);border-radius:8px;padding:10px;margin-bottom:10px;background:#fffaf2}.nav{display:flex;gap:10px;margin-top:14px}
.cast-button{display:block;width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:8px;padding:8px;margin:6px 0;cursor:pointer}
dialog{border:1px solid var(--line);border-radius:12px;max-width:520px;background:#fffaf2;color:var(--ink);box-shadow:0 20px 80px rgba(0,0,0,.25)}
dialog::backdrop{background:rgba(35,25,15,.35)}.dialog-close{float:right;border:0;background:var(--accent);color:#fff;border-radius:999px;padding:4px 10px;cursor:pointer}
.bookmark-strip{display:flex;gap:6px;overflow:auto}.bookmark-strip button{border-radius:6px}.bookmark-event{border-color:#6b3fa0}.bookmark-anomaly{border-color:#9b2d20}.bookmark-highlight{border-color:#17633a}
details{margin:8px 0}summary{cursor:pointer;font-weight:700}code{font-size:12px}.hidden{display:none}
@media(max-width:900px){.deck-layout{grid-template-columns:1fr}.side-panel{display:none}.topbar{align-items:flex-start;flex-direction:column}.slides{padding:12px}}
"""
