"""Interaction outcome calculation and relationship deltas.

Design sources:
- 02-Core-Mechanics.md: Interaction Success Formula, Relationship Stats
- 05-Interaction-System.md: Success Calculation Details, Relationship Application

Implementation rule:
All math lives here or in nearby deterministic engine modules. The Narrator
receives the resolved result; it never calculates outcomes.
"""
