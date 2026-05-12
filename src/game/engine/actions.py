"""Available action generation and action validation.

Design sources:
- 05-Interaction-System.md: Hybrid Menu System, Interaction Flow
- 06-Location-System.md: Location-specific actions

Implementation rule:
Action mechanics live in Python. Optional markdown content may provide
narrator-facing flavor, but it must not decide whether an action is valid.
"""

from __future__ import annotations

from enum import StrEnum


class ActionKind(StrEnum):
    """Canonical action vocabulary shared by engine, CLI, browser, and tests."""

    TALK = "talk"
    FLIRT = "flirt"
    LISTEN = "listen"
    LEAVE = "leave"
    ADVANCE_PHASE = "advance_phase"
