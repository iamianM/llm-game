"""Inline CSS for the editorial review packet."""

STYLISH_CSS = """
:root{--bg:#f5f1eb;--card:#fff;--border:#d8cfbd;--drama:#a4341a;--warm:#5b7c4f;--cool:#3a5a73;--win:#1f6a3e;--ink:#29231d;--muted:#6f665a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.55 Charter,Georgia,serif}
a{color:var(--drama)}code{font-size:12px}.shell{max-width:1480px;margin:0 auto;padding:28px}
.hero{border-bottom:3px solid var(--drama);padding:24px 0 18px;margin-bottom:22px}.hero h1{font:800 42px/1 Inter,-apple-system,BlinkMacSystemFont,sans-serif;margin:0}.hero p{max-width:900px;color:var(--muted)}
.layout{display:grid;grid-template-columns:170px minmax(0,1fr)280px;gap:20px;align-items:start}.left,.right{position:sticky;top:16px}
.panel,.card,.turn{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:16px;box-shadow:0 1px 0 rgba(0,0,0,.03)}
.day-nav a,.pill{display:block;border:1px solid var(--border);border-radius:999px;padding:6px 10px;margin:6px 0;background:#fff;text-decoration:none;font:700 13px Inter,sans-serif}
.turn{margin:0 0 16px}.turn summary{cursor:pointer;font:800 22px/1.25 Inter,sans-serif}.meta{color:var(--muted);font-size:14px}.success{color:var(--win)}.miss{color:var(--drama)}
.dialogue p{margin:.5rem 0}.speaker{font:800 12px Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--cool)}
.math details{border-left:4px solid var(--cool);padding-left:12px}.pull-attempt{border-left:4px solid #d8793f}.interruption{border-left:4px solid #6b3fa0}.memory{border-left:4px solid var(--warm)}.hideaway{border-left:4px solid #b36b83;background:#fff9fb}
.couple{margin:10px 0;padding:10px;border:1px solid var(--border);border-radius:8px}.couple.player{border-color:var(--drama);box-shadow:inset 3px 0 0 var(--drama)}.bar-bg{height:10px;background:#eee4d7;border-radius:999px;overflow:hidden}.bar{display:block;height:10px;background:var(--warm)}
svg{max-width:100%;height:auto}.viz{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px}table{border-collapse:collapse;width:100%}th,td{border:1px solid var(--border);padding:8px;text-align:left}
@media(max-width:700px){.shell{padding:16px}.layout{display:block}.left,.right{position:static;margin-bottom:14px}.viz{grid-template-columns:1fr}.hero h1{font-size:30px}}
"""
