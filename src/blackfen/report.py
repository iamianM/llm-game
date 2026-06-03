"""Static review packet generation for Blackfen Road traces."""

from __future__ import annotations

import html
import json
from pathlib import Path

from src.blackfen.trace import BlackfenTracePackage, load_trace


def write_report_packet(trace_path: Path, out_dir: Path) -> Path:
    """Write a self-contained HTML review packet for a trace."""
    package = load_trace(trace_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "index.html"
    report_path.write_text(_render_html(package, trace_path), encoding="utf-8")
    raw_path = out_dir / "raw-trace.json"
    raw_path.write_text(json.dumps(package.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
    return report_path


def _render_html(package: BlackfenTracePackage, trace_path: Path) -> str:
    turns = "\n".join(_turn_html(turn.turn_index, turn.raw_text, turn.narration, turn.mechanical_result.model_dump(mode="json")) for turn in package.turns)
    notes = "".join(f"<li>{html.escape(note)}</li>" for note in package.review_notes)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blackfen Road Review Packet</title>
  <style>
    body {{ margin: 0; background: #11120f; color: #eee6d8; font-family: ui-sans-serif, system-ui, sans-serif; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 32px; }}
    h1, h2 {{ color: #f4c35f; }}
    .meta, .turn {{ border: 1px solid #514936; border-radius: 8px; background: #191a15; padding: 16px; margin: 16px 0; }}
    code, pre {{ background: #0b0c09; color: #d4e9c1; }}
    pre {{ overflow: auto; padding: 12px; border-radius: 6px; }}
  </style>
</head>
<body>
<main>
  <h1>Blackfen Road Review Packet</h1>
  <section class="meta">
    <p><strong>Trace:</strong> {html.escape(str(trace_path))}</p>
    <p><strong>Seed:</strong> {package.seed} | <strong>Class:</strong> {html.escape(package.class_id)} | <strong>Final hash:</strong> <code>{package.final_hash}</code></p>
    <p><strong>Status:</strong> {package.final_state.status.value} | <strong>Fun score:</strong> {package.fun_score}/100</p>
    <h2>Review Notes</h2>
    <ul>{notes}</ul>
  </section>
  <h2>Turn Transcript</h2>
  {turns}
</main>
</body>
</html>
"""


def _turn_html(index: int, raw_text: str, narration: str, mechanical: dict[str, object]) -> str:
    payload = json.dumps(mechanical, indent=2, sort_keys=True)
    return f"""<article class="turn">
  <h3>Turn {index}: {html.escape(raw_text)}</h3>
  <p>{html.escape(narration)}</p>
  <details>
    <summary>Raw mechanical result</summary>
    <pre>{html.escape(payload)}</pre>
  </details>
</article>"""
