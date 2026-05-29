"""Cast grid, popout dialogs, and villa map for the slide deck right rail."""

from __future__ import annotations

from typing import Any

from src.game.reporting.html_base import escape

# Deterministic avatar palette per islander id (or display name)
PALETTE = [
    "#b9502f", "#5b7c4f", "#c8932a", "#6b3fa0",
    "#3d6f8e", "#a93826", "#2d6a3f", "#8b6a17",
    "#7a4b1f", "#3f6b6a",
]


def avatar_color(key: str) -> str:
    """Pick a deterministic color for a name or id."""
    if not key:
        return PALETTE[0]
    return PALETTE[sum(ord(c) for c in key.lower()) % len(PALETTE)]


def initials(name: str) -> str:
    """Two-character initials for the avatar."""
    parts = name.replace("_", " ").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[1][0]).upper()


def avatar_svg(name: str, *, size: int = 30) -> str:
    """Render an inline avatar as styled HTML, deterministic by name."""
    color = avatar_color(name)
    return (
        f"<span class='avatar' style='background:{color};width:{size}px;height:{size}px;font-size:{max(9, size // 3)}px'>"
        f"{escape(initials(name))}</span>"
    )


def display_name(name: str) -> str:
    """Strip suffixes like _ht from cast ids for display."""
    if not isinstance(name, str):
        return str(name)
    return name.split("_")[0].title()


def render_villa_map(snapshot: dict[str, Any]) -> str:
    """Render the 4-location villa map for the right rail."""
    if not isinstance(snapshot, dict) or not snapshot:
        return "<p class='muted small'>No villa map for this scene.</p>"
    cells: list[str] = []
    # Stable display order
    order = ["pool", "kitchen", "terrace", "bedroom", "firepit", "hideaway"]
    keys = sorted(snapshot.keys(), key=lambda k: (order.index(k) if k in order else 99, k))
    for loc in keys:
        occupants = snapshot.get(loc)
        if not isinstance(occupants, list):
            continue
        if loc in {"hideaway"} and not occupants:
            continue  # skip empty hideaway clutter
        names: list[str] = []
        player_here = False
        for occ in occupants:
            occ_str = str(occ)
            if occ_str.lower() == "you":
                player_here = True
                names.append("<span class='you-marker'>You</span>")
            else:
                names.append(escape(display_name(occ_str)))
        cls = "map-cell player-here" if player_here else "map-cell"
        people = ", ".join(names) if names else "<span class='muted'>—</span>"
        cells.append(
            f"<div class='{cls}'><div class='loc-name'>{escape(loc.title())}</div>"
            f"<div class='loc-people'>{people}</div></div>"
        )
    return f"<div class='villa-map'>{''.join(cells)}</div>"


def collect_cast(records: list[dict[str, Any]], final_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract a deterministic ordered cast roster from final_state or trace fallback."""
    cast: list[dict[str, Any]] = []
    seen: set[str] = set()
    # Prefer final_state islanders for full data
    if isinstance(final_state, dict):
        islanders = final_state.get("islanders")
        if isinstance(islanders, list):
            for isl in islanders:
                if not isinstance(isl, dict):
                    continue
                npc_id = str(isl.get("id") or "")
                if not npc_id or npc_id in seen:
                    continue
                seen.add(npc_id)
                cast.append(_cast_record_from_state(isl, final_state))
            if cast:
                return cast
    # Fallback: pull names from the last villa_snapshot in records
    for record in reversed(records):
        snap = record.get("villa_snapshot") if isinstance(record, dict) else None
        if not isinstance(snap, dict):
            continue
        for occupants in snap.values():
            if not isinstance(occupants, list):
                continue
            for occ in occupants:
                occ_str = str(occ)
                if occ_str.lower() == "you" or occ_str in seen:
                    continue
                seen.add(occ_str)
                cast.append({
                    "id": occ_str,
                    "name": display_name(occ_str),
                    "location": "",
                    "mood": "",
                    "archetype": "",
                    "backstory": "",
                    "eliminated": False,
                    "relationship": {},
                })
        if cast:
            break
    return cast


def _cast_record_from_state(islander: dict[str, Any], final_state: dict[str, Any]) -> dict[str, Any]:
    npc_id = str(islander.get("id") or "")
    name = str(islander.get("name") or display_name(npc_id))
    location = str(islander.get("location_id") or "")
    mood = str(islander.get("mood") or "")
    archetype = str(islander.get("archetype") or "")
    backstory = str(islander.get("backstory") or "")
    eliminated = bool(islander.get("eliminated"))
    relationship = islander.get("relationship") if isinstance(islander.get("relationship"), dict) else {}
    return {
        "id": npc_id,
        "name": name,
        "location": location,
        "mood": mood,
        "archetype": archetype,
        "backstory": backstory,
        "eliminated": eliminated,
        "relationship": relationship,
        "gender": str(islander.get("gender") or ""),
        "memories": islander.get("memories") if isinstance(islander.get("memories"), list) else [],
        "familiarity": islander.get("familiarity_with_player", 0),
        "type_on_paper": islander.get("type_on_paper") if isinstance(islander.get("type_on_paper"), dict) else {},
        "public_perception": islander.get("public_perception", 0),
    }


def render_cast_grid(cast: list[dict[str, Any]], partner_id: str | None) -> str:
    """Sticky right-rail cast grid showing 8 islanders."""
    if not cast:
        return "<p class='muted small'>Cast roster unavailable.</p>"
    cards: list[str] = []
    for c in cast:
        if c.get("eliminated"):
            continue
        npc_id = c["id"]
        name = c["name"]
        loc = c.get("location") or ""
        cls = "cast-card your-partner" if partner_id and npc_id == partner_id else "cast-card"
        loc_label = f"<div class='cast-loc'>{escape(display_name(loc)) if loc else ''}</div>" if loc else ""
        cards.append(
            f"<button class='{cls}' data-open-dialog='cast-{escape(npc_id)}'>"
            f"{avatar_svg(name)}<div class='cast-info'><div class='cast-name'>{escape(name)}</div>{loc_label}</div></button>"
        )
    return f"<div class='cast-grid'>{''.join(cards)}</div>"


def render_cast_popouts(cast: list[dict[str, Any]], records: list[dict[str, Any]]) -> str:
    """Render all NPC popout dialogs once globally."""
    # Build memory index: subject_id -> list of (holder, content, weight, tags)
    npc_memories = _collect_memories_per_npc(records)
    dialogs: list[str] = []
    for c in cast:
        npc_id = c["id"]
        dialogs.append(_npc_popout(c, npc_memories.get(npc_id, [])))
    return "".join(dialogs)


def _npc_popout(c: dict[str, Any], own_memories: list[dict[str, Any]]) -> str:
    name = c["name"]
    npc_id = c["id"]
    archetype = c.get("archetype") or ""
    backstory = c.get("backstory") or ""
    mood = c.get("mood") or ""
    location = c.get("location") or ""
    familiarity = c.get("familiarity", 0)
    rel = c.get("relationship") if isinstance(c.get("relationship"), dict) else {}
    type_on_paper = c.get("type_on_paper") if isinstance(c.get("type_on_paper"), dict) else {}
    sub_parts: list[str] = []
    if archetype:
        sub_parts.append(escape(archetype.title()))
    if mood:
        sub_parts.append(f"mood: {escape(mood)}")
    if location:
        sub_parts.append(f"at {escape(display_name(location))}")
    sub = " · ".join(sub_parts)
    backstory_block = (
        f"<section><h4>Backstory</h4><p>{escape(backstory)}</p></section>" if backstory else ""
    )
    rel_block = _relationship_block(rel)
    type_block = _type_on_paper_block(type_on_paper, familiarity)
    mem_block = _memory_popout_block(own_memories, npc_id)
    return (
        f"<dialog id='cast-{escape(npc_id)}'>"
        f"<div class='dialog-head'>{avatar_svg(name, size=44)}"
        f"<div><h3>{escape(name)}</h3><div class='sub'>{sub}</div></div>"
        f"<button class='dialog-close' data-close-dialog aria-label='Close'>×</button></div>"
        f"<div class='dialog-body'>"
        f"{backstory_block}{rel_block}{type_block}{mem_block}"
        f"</div></dialog>"
    )


def _relationship_block(rel: dict[str, Any]) -> str:
    if not rel:
        return ""
    rows: list[str] = []
    for key in ("affection", "chemistry", "trust", "friendship"):
        val = rel.get(key)
        if not isinstance(val, (int, float)):
            continue
        pct = max(0, min(100, int(val)))
        fill_class = "rel-fill"
        if key == "trust":
            fill_class += " cool"
        elif key == "friendship":
            fill_class += " weak"
        rows.append(
            f"<div class='rel-row'><div class='rel-label'>{escape(key)}</div>"
            f"<div class='rel-bar'><div class='{fill_class}' style='width:{pct}%'></div></div></div>"
        )
    if not rows:
        return ""
    return f"<section><h4>How they feel about you</h4>{''.join(rows)}</section>"


def _type_on_paper_block(top: dict[str, Any], familiarity: int) -> str:
    if not top:
        return ""
    thresholds = {"physical_type": 25, "personality_type": 50, "values": 75, "dealbreakers": 100}
    items: list[str] = []
    for field, threshold in thresholds.items():
        val = top.get(field)
        revealed = isinstance(familiarity, (int, float)) and familiarity >= threshold
        label = field.replace("_", " ").title()
        if revealed and val:
            if isinstance(val, list):
                display = ", ".join(escape(str(v)) for v in val)
            else:
                display = escape(str(val))
            items.append(f"<div><b>{escape(label)}:</b> {display}</div>")
        else:
            items.append(f"<div class='muted'><b>{escape(label)}:</b> ???</div>")
    fam_pct = max(0, min(100, int(familiarity or 0)))
    return (
        f"<section><h4>Type on paper · familiarity {fam_pct}/100</h4>"
        f"<div class='rel-bar' style='margin-bottom:8px'><div class='rel-fill' style='width:{fam_pct}%'></div></div>"
        f"<div class='small'>{''.join(items)}</div></section>"
    )


def _memory_popout_block(memories: list[dict[str, Any]], own_id: str) -> str:
    if not memories:
        return ""
    # Show the most recent 6
    items: list[str] = []
    for m in memories[-6:]:
        if not isinstance(m, dict):
            continue
        subject = display_name(str(m.get("subject_id") or ""))
        content = str(m.get("content") or "")
        if not content:
            continue
        weight = m.get("emotional_weight", "")
        source = str(m.get("source") or "direct")
        tags = m.get("tags") if isinstance(m.get("tags"), list) else []
        tag_html = "".join(f"<span class='mem-tag'>{escape(str(t))}</span>" for t in tags[:4])
        items.append(
            f"<div class='memory'>"
            f"<div class='mem-meta'>About {escape(subject)} · weight {escape(weight)} · {escape(source)}</div>"
            f"<div class='mem-content'>{escape(content)}</div>"
            f"<div class='mem-tags'>{tag_html}</div></div>"
        )
    if not items:
        return ""
    return f"<section><h4>What {escape(display_name(own_id))} remembers</h4><div class='memory-list'>{''.join(items)}</div></section>"


def _collect_memories_per_npc(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Walk the trace, collect curator memories indexed by holder."""
    result: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        commits = record.get("agent_commits") if isinstance(record, dict) else None
        if not isinstance(commits, dict):
            continue
        batches = commits.get("curator_batches")
        if not isinstance(batches, list):
            continue
        for batch in batches:
            if not isinstance(batch, dict):
                continue
            memories = batch.get("memories")
            if not isinstance(memories, list):
                continue
            for m in memories:
                if not isinstance(m, dict):
                    continue
                holder = str(m.get("holder_id") or "")
                if not holder:
                    continue
                result.setdefault(holder, []).append(m)
    return result


def player_partner_id(final_state: dict[str, Any] | None) -> str | None:
    """Find the player's current partner id from final state."""
    if not isinstance(final_state, dict):
        return None
    couples = final_state.get("couples")
    if not isinstance(couples, list):
        return None
    for couple in couples:
        if not isinstance(couple, dict):
            continue
        a = couple.get("partner_a_id")
        b = couple.get("partner_b_id")
        if a == "player":
            return str(b) if b else None
        if b == "player":
            return str(a) if a else None
    return None


def render_couples_panel(
    final_state: dict[str, Any] | None,
    cast: list[dict[str, Any]],
) -> str:
    """Render the right-rail couples panel from final state."""
    if not isinstance(final_state, dict):
        return "<p class='muted small'>No couples data.</p>"
    couples = final_state.get("couples")
    if not isinstance(couples, list) or not couples:
        return "<p class='muted small'>No couples formed.</p>"
    name_lookup: dict[str, str] = {}
    for c in cast:
        name_lookup[c["id"]] = c.get("name", display_name(c["id"]))
    player_name = "You"
    rows: list[str] = []
    for couple in couples:
        if not isinstance(couple, dict):
            continue
        a_id = str(couple.get("partner_a_id") or "")
        b_id = str(couple.get("partner_b_id") or "")
        if not a_id or not b_id:
            continue
        is_player = a_id == "player" or b_id == "player"
        a_name = player_name if a_id == "player" else name_lookup.get(a_id, display_name(a_id))
        b_name = player_name if b_id == "player" else name_lookup.get(b_id, display_name(b_id))
        a_avatar = avatar_svg("you" if a_id == "player" else a_name, size=22)
        b_avatar = avatar_svg("you" if b_id == "player" else b_name, size=22)
        strength = couple.get("strength")
        strength_html = (
            f"<span class='couple-strength'>{int(strength)}</span>"
            if isinstance(strength, (int, float)) else ""
        )
        cls = "couple-row player-couple" if is_player else "couple-row"
        rows.append(
            f"<div class='{cls}'>{a_avatar}<span class='couple-amp'>&</span>{b_avatar}"
            f"<span class='couple-names'>{escape(a_name)} & {escape(b_name)}</span>"
            f"{strength_html}</div>"
        )
    if not rows:
        return "<p class='muted small'>No couples formed.</p>"
    return f"<div class='couples-list'>{''.join(rows)}</div>"
