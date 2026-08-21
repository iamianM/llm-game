"""Snapshot save/load and state hashing.

Design sources:
- docs/systems/qa.md: Snapshot Contract
- docs/decisions/0008-snapshot-and-trace-architecture.md

Snapshots are the shared restart point for CLI, browser, and tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.game.state.models import SCHEMA_VERSION, GameState

JsonValue = dict[str, object] | list[object] | str | int | float | bool | None
RngSnapshot = list[Any]


def state_hash(payload: JsonValue) -> str:
    """Return a stable hash for a JSON-serializable state payload."""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def state_hash_payload(state: GameState) -> dict[str, object]:
    """Return the mechanical payload used for deterministic state hashes.

    Dialogue prose is intentionally excluded so the same seed and intent
    sequence hashes identically regardless of LLM wording.
    """
    payload = state.model_dump(mode="json")
    # Rolling buffer of recent player spoken lines (used only to vary dialogue
    # openers). Pure LLM-wording prose, so exclude it for the same reason the
    # exchange dialogue below is stripped: same seed + intents must hash alike.
    payload.pop("recent_player_lines", None)
    conversation = payload.get("active_conversation")
    if isinstance(conversation, dict):
        conversation.pop("summary", None)
        exchanges = conversation.get("exchanges")
        if isinstance(exchanges, list):
            for exchange in exchanges:
                if isinstance(exchange, dict):
                    exchange.pop("player_dialogue", None)
                    exchange.pop("npc_dialogue", None)
        _strip_memory_content(conversation.get("gossip_offers"))
    player = payload.get("player")
    if isinstance(player, dict):
        _strip_memory_content(player.get("memories"))
    heartbreakers = payload.get("heartbreakers")
    if isinstance(heartbreakers, list):
        for heartbreaker in heartbreakers:
            if isinstance(heartbreaker, dict):
                _strip_memory_content(heartbreaker.get("memories"))
    npc_conversations = payload.get("npc_conversations")
    if isinstance(npc_conversations, list):
        for conversation in npc_conversations:
            if isinstance(conversation, dict):
                conversation.pop("topic", None)
                exchanges = conversation.get("exchanges")
                if isinstance(exchanges, list):
                    for exchange in exchanges:
                        if isinstance(exchange, dict):
                            exchange.pop("speaker_a_line", None)
                            exchange.pop("speaker_b_line", None)
    recaps = payload.get("daily_recaps")
    if isinstance(recaps, list):
        for recap in recaps:
            if isinstance(recap, dict):
                items = recap.get("items")
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            item.pop("content", None)
    pending_text = payload.get("pending_text")
    if isinstance(pending_text, dict):
        pending_text.pop("body", None)
    return payload


def _strip_memory_content(memories: object) -> None:
    if not isinstance(memories, list):
        return
    for memory in memories:
        if isinstance(memory, dict):
            memory.pop("content", None)
            # Derived from ``content`` (see memory._mentioned_subject_ids), so it
            # inherits the same LLM-wording nondeterminism and must be excluded
            # from the deterministic state hash alongside the prose it came from.
            memory.pop("mentioned_subject_ids", None)


def save_snapshot(path: Path, payload: dict[str, object]) -> None:
    """Write a snapshot payload.

    Placeholder JSON implementation until the SQLite snapshot store is built.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_snapshot(path: Path) -> dict[str, object]:
    """Load a snapshot payload."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"snapshot {path} did not contain a JSON object")
    return payload


def save_named_checkpoint(
    state: GameState,
    name: str,
    trace_records: list[dict[str, object]],
    *,
    seed: int,
    rng_state: RngSnapshot | None = None,
) -> Path:
    """Save a named development checkpoint."""
    path = Path(".game_saves") / "named" / f"{_safe_name(name)}.json"
    _write_checkpoint(path, state, trace_records, seed=seed, checkpoint_name=name, rng_state=rng_state)
    return path


def save_auto_checkpoint(
    state: GameState,
    seed: int,
    trace_records: list[dict[str, object]],
    rng_state: RngSnapshot | None = None,
) -> Path:
    """Save an automatic boundary checkpoint."""
    path = Path(".game_saves") / "auto" / str(seed) / f"day{state.day}_{state.phase.value}.json"
    _write_checkpoint(path, state, trace_records, seed=seed, checkpoint_name=path.stem, rng_state=rng_state)
    return path


def load_checkpoint(
    name_or_path: str | Path,
) -> tuple[GameState, list[dict[str, object]], int, RngSnapshot | None]:
    """Load a named or path-based development checkpoint."""
    path = _checkpoint_path(name_or_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"checkpoint must be a JSON object: {path}")
    state_payload = raw.get("state")
    trace_records = raw.get("trace_records")
    seed = raw.get("seed")
    if not isinstance(state_payload, dict) or not isinstance(trace_records, list) or not isinstance(seed, int):
        raise ValueError(f"checkpoint missing state, trace_records, or seed: {path}")
    rng_state = raw.get("rng_state")
    if rng_state is not None and not isinstance(rng_state, list):
        raise ValueError(f"checkpoint rng_state must be a JSON list: {path}")
    checkpoint_version = state_payload.get("schema_version")
    if checkpoint_version != SCHEMA_VERSION:
        raise ValueError(
            f"checkpoint schema_version {checkpoint_version!r} does not match "
            f"current schema_version {SCHEMA_VERSION}; regenerate the checkpoint"
        )
    records = [record for record in trace_records if isinstance(record, dict)]
    return GameState.model_validate(state_payload), records, seed, rng_state


def _write_checkpoint(
    path: Path,
    state: GameState,
    trace_records: list[dict[str, object]],
    *,
    seed: int,
    checkpoint_name: str,
    rng_state: RngSnapshot | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "name": checkpoint_name,
        "seed": seed,
        "state_hash": state_hash(state_hash_payload(state)),
        "state": state.model_dump(mode="json"),
        "trace_records": trace_records,
    }
    if rng_state is not None:
        payload["rng_state"] = rng_state
    path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _checkpoint_path(name_or_path: str | Path) -> Path:
    path = Path(name_or_path)
    if path.exists():
        return path
    named = Path(".game_saves") / "named" / f"{_safe_name(str(name_or_path))}.json"
    if named.exists():
        return named
    raise FileNotFoundError(f"checkpoint not found: {name_or_path}")


def _safe_name(name: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in name.strip())
    return cleaned.strip("-") or "checkpoint"
