"""Deterministic state hash helpers for Blackfen Road."""

from __future__ import annotations

import hashlib
import json

from src.blackfen.models import GameState


def state_hash(state: GameState) -> str:
    """Return a stable hash of the deterministic state payload."""
    payload = state.model_dump(mode="json", exclude={"turns"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]
