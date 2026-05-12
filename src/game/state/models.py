"""Pydantic models for canonical game state.

Design sources:
- 04-State-Management.md: Islander State, Player State, Villa State
- 02-Core-Mechanics.md: Player stats and relationship stats

Implementation rule:
The browser may render a filtered view of these models, but it does not own
canonical game state.
"""
