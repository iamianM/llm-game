"""Snapshot save/load and state hashing.

Design sources:
- docs/qa-strategy.md: Snapshot Contract
- docs/decisions/0008-snapshot-and-trace-architecture.md

Snapshots are the shared restart point for CLI, browser, and tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.game.state.models import GameState

JsonValue = dict[str, object] | list[object] | str | int | float | bool | None


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
    conversation = payload.get("active_conversation")
    if isinstance(conversation, dict):
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
    islanders = payload.get("islanders")
    if isinstance(islanders, list):
        for islander in islanders:
            if isinstance(islander, dict):
                _strip_memory_content(islander.get("memories"))
    return payload


def _strip_memory_content(memories: object) -> None:
    if not isinstance(memories, list):
        return
    for memory in memories:
        if isinstance(memory, dict):
            memory.pop("content", None)


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
