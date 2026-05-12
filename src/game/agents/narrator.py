"""Narrator agent construction and narration calls.

Design sources:
- 03-LLM-Architecture.md: Dialogue Writing, Event Narration
- 11-Conversation-Flow.md: single exchange generation and continuity

Implementation rule:
The Narrator receives resolved mechanical results and visible context. It does
not mutate game state or decide outcomes.
"""
