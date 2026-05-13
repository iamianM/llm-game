"""SVG memory web visualization."""

from __future__ import annotations

import math
from typing import Any

from src.game.reporting.html_base import escape
from src.game.reporting.stylish.avatars import avatar_svg


def memory_web_svg(records: list[dict[str, Any]]) -> str:
    """Render holder -> subject memory edges for meaningful memories."""
    memories = _memories(records)
    actors = sorted({item["holder_id"] for item in memories} | {item["subject_id"] for item in memories})
    if not memories or not actors:
        return "<section class='panel'><h2>Memory Web</h2><p class='meta'>No high-weight memories yet.</p></section>"
    width, height = 420, 260
    positions = _positions(actors, width, height)
    edges = []
    for memory in memories:
        source = memory["holder_id"]
        target = memory["subject_id"]
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        style = _edge_style(memory.get("source", "direct"))
        weight = max(1, min(6, int(memory.get("emotional_weight", 4)) // 2))
        edges.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke-width='{weight}' {style}/>")
    nodes = []
    for actor in actors:
        x, y = positions[actor]
        nodes.append(f"<g transform='translate({x - 16},{y - 16})'>{avatar_svg(actor, actor.title())}</g>")
        nodes.append(f"<text x='{x}' y='{y + 30}' text-anchor='middle' font-size='11'>{escape(actor)}</text>")
    return (
        "<section class='panel'><h2>Memory Web</h2>"
        f"<svg viewBox='0 0 {width} {height}'>{''.join(edges)}{''.join(nodes)}</svg></section>"
    )


def _memories(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        commits = record.get("agent_commits")
        if not isinstance(commits, dict):
            continue
        for batch in commits.get("curator_batches", []):
            if not isinstance(batch, dict):
                continue
            for memory in batch.get("memories", []):
                if isinstance(memory, dict) and int(memory.get("emotional_weight", 0)) >= 4:
                    rows.append(memory)
    return rows[:40]


def _positions(actors: list[str], width: int, height: int) -> dict[str, tuple[int, int]]:
    radius = min(width, height) // 2 - 46
    center = (width // 2, height // 2)
    positions = {}
    for index, actor in enumerate(actors):
        angle = (math.tau * index) / max(1, len(actors))
        positions[actor] = (center[0] + int(math.cos(angle) * radius), center[1] + int(math.sin(angle) * radius))
    return positions


def _edge_style(source: object) -> str:
    if source == "witnessed":
        return "stroke='#3a5a73' stroke-dasharray='6 4'"
    if source == "told_by":
        return "stroke='#8c5a7a' stroke-dasharray='2 5'"
    return "stroke='#5b7c4f'"
