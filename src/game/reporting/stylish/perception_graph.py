"""SVG public perception graph."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.game.reporting.html_base import escape


def perception_graph_svg(records: list[dict[str, Any]]) -> str:
    """Render a tiny SVG line graph from audience snapshots."""
    series: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for record in records:
        snapshot = record.get("audience_snapshot")
        if not isinstance(snapshot, dict):
            continue
        day = snapshot.get("day")
        if not isinstance(day, int):
            continue
        for entry in snapshot.get("entries", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("score"), int):
                continue
            key = " & ".join(str(part) for part in entry.get("couple", []))
            series[key].append((day, int(entry["score"])))
    if not series:
        return "<section class='panel'><h2>Public Perception</h2><p class='meta'>No audience snapshots.</p></section>"
    width, height = 420, 180
    lines = []
    labels = []
    for index, (label, points) in enumerate(sorted(series.items())):
        color = ["#a4341a", "#5b7c4f", "#3a5a73", "#8c5a7a"][index % 4]
        coords = " ".join(f"{_x(day, width)},{_y(score, height)}" for day, score in points)
        lines.append(f"<polyline fill='none' stroke='{color}' stroke-width='3' points='{coords}'/>")
        labels.append(f"<li><span style='color:{color}'>■</span> {escape(label)}</li>")
    axes = "<line x1='30' y1='10' x2='30' y2='150' stroke='#d8cfbd'/><line x1='30' y1='150' x2='400' y2='150' stroke='#d8cfbd'/>"
    return (
        "<section class='panel'><h2>Public Perception</h2>"
        f"<svg viewBox='0 0 {width} {height}'>{axes}{''.join(lines)}</svg>"
        f"<ul>{''.join(labels)}</ul></section>"
    )


def _x(day: int, width: int) -> int:
    return 30 + int(((max(1, min(8, day)) - 1) / 7) * (width - 60))


def _y(score: int, height: int) -> int:
    return 150 - int((max(0, min(100, score)) / 100) * (height - 40))
