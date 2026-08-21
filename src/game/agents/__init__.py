"""Typed story-agent layer.

Design sources:
- 03-LLM-Architecture.md: Multi-AI System
- 11-Conversation-Flow.md: Single Exchange Generation
- docs/decisions/0016-game-owned-turn-agent-set.md

``TurnAgentSet`` is the canonical turn boundary. Live, mock, recorded, and
scripted modes each provide the complete six-port set; engine callers never
substitute a missing capability or recover a failed live call with mock prose.
"""
