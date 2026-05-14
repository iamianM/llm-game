"""Tests for recorded playthrough feature evaluation."""

from __future__ import annotations

from src.game.eval.playthrough import evaluate_trace


def test_playthrough_report_has_twenty_nine_assertions() -> None:
    """The L7 report exposes the planned feature checklist plus H1 run checks."""
    report = evaluate_trace(_complete_package())

    assert len(report.assertions) == 29


def test_playthrough_report_passes_complete_trace() -> None:
    """A trace with all major systems represented passes the checklist."""
    report = evaluate_trace(_complete_package())

    assert report.failed == 0
    assert report.passed == 29


def test_playthrough_report_flags_missing_pull_failure() -> None:
    """The pull failure assertion fails loudly when no miss is recorded."""
    package = _complete_package()
    for record in package["records"]:
        pull = record.get("mechanical_result", {}).get("pull_attempt")
        if isinstance(pull, dict):
            pull["success"] = True

    report = evaluate_trace(package)

    failure = next(assertion for assertion in report.assertions if assertion.id == "pull_failure")
    assert failure.passed is False
    assert report.failed == 1


def test_playthrough_report_counts_memory_holders() -> None:
    """Memory coverage checks all major NPC holders."""
    package = _complete_package()
    package["records"][1]["agent_commits"]["curator_batches"] = []

    report = evaluate_trace(package)

    failure = next(assertion for assertion in report.assertions if assertion.id == "memory_coverage")
    assert failure.passed is False
    assert "memory counts" in failure.detail


def test_playthrough_report_tracks_interesting_turns() -> None:
    """Interesting turns are deduplicated and sorted for dashboard links."""
    report = evaluate_trace(_complete_package())

    assert report.interesting_turns == sorted(set(report.interesting_turns))
    assert 4 in report.interesting_turns


def test_playthrough_report_flags_stalled_day_progression() -> None:
    package = _complete_package()
    package["final_state"]["outcome"] = None
    package["final_state"]["day"] = 2
    for record in package["records"]:
        record["day"] = 2

    report = evaluate_trace(package)

    failure = next(assertion for assertion in report.assertions if assertion.id == "day_progression_reasonable")
    assert failure.passed is False


def _complete_package():
    memories = [
        {"holder_id": holder, "subject_id": "player", "content": "x", "source": "direct"}
        for holder in ("chloe", "maya", "liam")
        for _ in range(3)
    ]
    return {
        "records": [
            _record(1, "start_conversation", chance=55),
            _record(
                2,
                "respond_with",
                intent_id="end_softly",
                chance=80,
                curator_memories=memories,
                background_dialogues=1,
            ),
            _record(3, "end_conversation", chance=None),
            _record(
                4,
                "start_conversation",
                chance=42,
                pull={"target_id": "chloe", "success": False, "chance": 42, "roll": 88},
            ),
            _record(
                5,
                "respond_with",
                intent_id="accept_interruption",
                chance=70,
                interruption={"interrupter_id": "maya", "reason": "jealous", "urgency": "insistent"},
            ),
            _record(6, "respond_with", intent_id="ask_gossip:mem1", chance=52),
            _record(7, "start_conversation", chance=75, arrival_roll=True, summon=True),
            _record(8, "respond_with", intent_id="ignore_interruption", chance=None, audience=True, arrival_roll=True),
            _record(9, "advance_phase", challenge=True),
            _record(10, "advance_phase", challenge=True),
            _record(11, "advance_phase", challenge=True),
            _record(12, "advance_phase", challenge=True),
            _record(13, "hideaway", challenge=True, couple_strength=74),
            _record(14, "advance_phase", producer_text=True, group_date=True),
            _record(15, "advance_phase", producer_text=True),
            _record(16, "advance_phase", producer_text=True, steal=True),
            _record(17, "advance_phase", villa="casa_amor", casa={"started_on_day": 4}),
            _record(
                18,
                "casa_decision",
                chance=None,
                casa={
                    "started_on_day": 4,
                    "player_decision": "return_with_new",
                    "partners_swapped": True,
                    "player_perception_before": 50,
                    "player_perception_after": 38,
                },
                ceremony_events=[{"kind": "casa_amor_decision"}],
            ),
            _record(
                19,
                "advance_phase",
                casa={
                    "started_on_day": 4,
                    "player_decision": "return_with_new",
                    "partners_swapped": True,
                    "player_perception_before": 50,
                    "player_perception_after": 38,
                },
                ceremony_events=[{"kind": "casa_amor_return_reveal"}],
            ),
            _record(20, "start_conversation", chance=55, auto_advance=True),
        ],
        "final_state": {
            "day": 6,
            "outcome": "won_as_couple",
            "islanders": [{"id": "chloe", "familiarity_with_player": 50}],
        },
    }


def _record(
    turn: int,
    kind: str,
    *,
    intent_id: str | None = None,
    chance: int | None = 70,
    pull: dict[str, object] | None = None,
    interruption: dict[str, object] | None = None,
    curator_memories: list[dict[str, object]] | None = None,
    background_dialogues: int = 0,
    audience: bool = False,
    challenge: bool = False,
    producer_text: bool = False,
    group_date: bool = False,
    couple_strength: int | None = 50,
    steal: bool = False,
    villa: str = "main",
    casa: dict[str, object] | None = None,
    ceremony_events: list[dict[str, object]] | None = None,
    auto_advance: bool = False,
    arrival_roll: bool = False,
    summon: bool = False,
) -> dict[str, object]:
    action: dict[str, object] = {"kind": kind}
    if intent_id is not None:
        action["intent_id"] = intent_id
    result: dict[str, object] = {
        "action": action,
        "success": chance is None or chance >= 50,
        "relationship_deltas": {},
    }
    if chance is not None:
        result["success_chance"] = chance
        result["roll"] = 10
        result["chance_breakdown"] = {
            "compatibility_bonus": 4 if turn == 1 else 0,
        }
    if pull is not None:
        result["pull_attempt"] = pull
    curator_batches = []
    if curator_memories is not None:
        curator_batches.append({"memories": curator_memories})
    return {
        "turn": turn,
        "day": ((turn - 1) // 4) + 1,
        "phase": ["morning", "challenge", "afternoon", "text", "evening"][turn % 5],
        "villa": villa,
        "auto_advance": auto_advance,
        "action": action,
        "arrival_rolls": [
            {
                "arriving_npc_id": "maya",
                "target_id": "chloe",
                "interruption_chance": 55,
                "interruption_roll": 40,
                "interruption_hit": True,
                "pull_chance": 35,
                "pull_roll": 20,
                "pull_hit": True,
            }
        ]
        if arrival_roll
        else [],
        "mechanical_result": result,
        "audience_snapshot": (
            {"day": 1, "entries": [{"rank": 1, "couple": ["player", "chloe"], "score": 74, "is_player_couple": True}]}
            if audience
            else None
        ),
        "challenge": (
            {"id": f"challenge-{turn}", "kind": "compatibility_quiz", "stat_tested": "eq", "result": "success"}
            if challenge
            else None
        ),
        "producer_text": (
            {"id": f"text-{turn}", "kind": "welcome", "body": "I've got a text."}
            if producer_text
            else None
        ),
        "group_date": (
            {"id": "group-date", "participants": ["player", "chloe", "maya"], "location": "terrace", "day": 3}
            if group_date
            else None
        ),
        "couple_strength": couple_strength,
        "hideaway": (
            {"used_on_day": 5, "partner_id": "chloe", "deltas_applied": True}
            if kind == "hideaway"
            else {"used_on_day": None, "partner_id": None, "deltas_applied": False}
        ),
        "casa_amor": casa,
        "ceremony_events": ceremony_events
        if ceremony_events is not None
        else ([{"kind": "steal_attempt", "message": "Steal attempt fails."}] if steal else ([{"kind": "bombshell"}] if turn == 6 else [])),
        "agent_commits": {
            "villa_update": _villa_update(interruption=interruption, summon=summon),
            "curator_batches": curator_batches,
            "background_dialogues": [{} for _ in range(background_dialogues)],
        },
    }


def _villa_update(
    *,
    interruption: dict[str, object] | None,
    summon: bool,
) -> dict[str, object]:
    return {
        "npc_interruptions": [interruption] if interruption is not None else [],
        "npc_summoned_elsewhere": [
            {
                "npc_id": "chloe",
                "from_conversation_id": "player_active",
                "reason": "chemistry_partner_arrived",
                "target_location": "kitchen",
            }
        ]
        if summon
        else [],
    }
