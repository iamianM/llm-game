"""Tests for review HTML surfaces."""

from __future__ import annotations

from src.game.eval.playthrough import evaluate_trace
from src.game.reporting.eval_dashboard import playthrough_eval_page
from src.game.reporting.html import session_page


def test_session_page_renders_math_villa_memories_pull_and_interruption() -> None:
    """Enhanced session HTML exposes the G8 review details."""
    html = session_page("Session", [_record()])

    assert "Success math" in html
    assert "Villa snapshot" in html
    assert "Pull attempt" in html
    assert "NPC interruption" in html
    assert "Memories formed this turn" in html
    assert "id='turn-1'" in html


def test_playthrough_eval_page_links_to_session_turns() -> None:
    """Eval dashboard links assertion evidence back to session turn cards."""
    report = evaluate_trace({"records": [_record()]})

    html = playthrough_eval_page(report)

    assert "Playthrough Eval" in html
    assert "Open session.html" in html
    assert "Turn 1" in html
    assert "href='session.html#turn-1'" in html


def _record() -> dict[str, object]:
    return {
        "turn": 1,
        "day": 1,
        "phase": "morning",
        "location": "pool",
        "visible_state": "Chloe: affection 10",
        "villa_snapshot": {"pool": ["you", "Chloe"], "terrace": ["Maya"]},
        "action": {"kind": "respond_with", "intent_id": "end_softly"},
        "mechanical_result": {
            "action": {"kind": "respond_with", "intent_id": "end_softly"},
            "success": True,
            "roll": 40,
            "success_chance": 80,
            "relationship_deltas": {"chloe": {"trust": 1}},
            "tags": ["end_softly", "safe"],
            "pull_attempt": {
                "target_id": "chloe",
                "started_from_location": "pool",
                "success": False,
                "chance": 45,
                "roll": 90,
                "blocked_conversation_id": "npcconv_1",
                "deflection_line": "I am busy right now.",
            },
        },
        "exchange": None,
        "event_narration": None,
        "follow_up_menu": None,
        "ceremony_events": [],
        "agent_commits": {
            "villa_update": {
                "npc_movements": [],
                "conversation_starts": [],
                "conversation_continues": [],
                "conversation_ends": [],
                "npc_interruptions": [
                    {"interrupter_id": "maya", "reason": "jealous", "urgency": "insistent"}
                ],
            },
            "background_dialogues": [],
            "curator_batches": [
                {
                    "memories": [
                        {
                            "holder_id": "chloe",
                            "subject_id": "player",
                            "content": "The player left gently.",
                            "emotional_weight": 4,
                            "tags": ["exit"],
                        }
                    ]
                }
            ],
        },
        "output_hash": "abc123",
    }
