"""Tests for daily recap creation."""

from __future__ import annotations

from src.game.engine.daily_recap import append_daily_recap_if_needed
from src.game.engine.memory import add_memory, create_memory
from src.game.state.models import new_game


def test_daily_recap_appends_once_per_completed_day() -> None:
    state = new_game(1)
    memory = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=3,
        weight=8,
        tags=["spark"],
        content="Chloe remembered a resort-defining moment.",
    )
    add_memory(state, memory)
    state.day = 2

    first = append_daily_recap_if_needed(state, 1)
    second = append_daily_recap_if_needed(state, 1)

    assert first is not None
    assert second is None
    assert [recap.day for recap in state.daily_recaps] == [1]
    assert state.daily_recaps[0].items[0].content == memory.content


def test_daily_recap_waits_until_day_rolls_forward() -> None:
    state = new_game(1)

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is None
    assert state.daily_recaps == []


def test_daily_recap_rewrites_the_player_label_to_second_person() -> None:
    state = new_game(1)
    memory = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=3,
        weight=8,
        tags=["warmth"],
        content="I appreciated the player checking in, and the player's calm steadied me.",
    )
    add_memory(state, memory)
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    surfaced = recap.items[0].content
    assert "the player" not in surfaced
    assert surfaced == "I appreciated you checking in, and your calm steadied me."
    # The underlying memory keeps its name-agnostic phrasing.
    assert "the player" in state.heartbreakers[0].memories[-1].content


def test_daily_recap_diversifies_across_storylines() -> None:
    # A hot Heart-Throb pair can spawn many distinct memories in one day (both
    # principals' versions + the couple announcement). Without a diversity pass
    # they sweep all five slots and bury the player's own quieter beat. The
    # recap should survey several storylines first, so the lower-weight player
    # memory still surfaces alongside the dominant pair.
    state = new_game(1)
    for turn, (holder, subject) in enumerate(
        [("maya", "marcus"), ("marcus", "maya")] * 3
    ):
        add_memory(
            state,
            create_memory(
                holder_id=holder,
                subject_id=subject,
                source="direct",
                day=1,
                turn=turn,
                weight=8,
                tags=["peer_attraction"],
                content=f"{holder} and {subject} drifted closer — moment {turn}.",
            ),
        )
    player_beat = "I liked the quiet way Chloe checked in on me."
    add_memory(
        state,
        create_memory(
            holder_id="player",
            subject_id="chloe",
            source="direct",
            day=1,
            turn=9,
            weight=5,  # lower weight than the pair — would rank 7th without diversity
            tags=["felt_seen"],
            content=player_beat,
        ),
    )
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    assert len(recap.items) == 5
    # The player's quieter beat survives despite six higher-weight pair memories.
    assert any(item.content == player_beat for item in recap.items)
    # The maya/marcus pair no longer monopolises every slot.
    pair_cards = [item for item in recap.items if {item.holder_id, item.subject_id} == {"maya", "marcus"}]
    assert len(pair_cards) <= 4


def test_daily_recap_collapses_identical_witnessed_content() -> None:
    # A witnessed event is stored once per holder with the exact same wording.
    # The recap must surface it once, not fill every slot. (Uses a non-ceremony
    # gossip tag so the dedupe — not the ceremony filter — is what collapses it.)
    state = new_game(1)
    shared = "Sunset Bay buzzed about a dramatic exit."
    for holder in ["player", *[heartbreaker.id for heartbreaker in state.heartbreakers[:5]]]:
        add_memory(
            state,
            create_memory(
                holder_id=holder,
                subject_id="resort",
                source="witnessed",
                day=1,
                turn=2,
                weight=6,
                tags=["gossip"],
                content=shared,
            ),
        )
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    matching = [item for item in recap.items if item.content == shared]
    assert len(matching) == 1


def test_daily_recap_drops_every_ceremony_tagged_memory() -> None:
    # ``remember_ceremony_events`` stamps every procedural resort announcement
    # with the ``"ceremony"`` tag (flame_deck gathers, eliminations, challenges,
    # Flush of Hearts text, pairings). Matching that single tag must drop them
    # all — including event kinds with no dedicated denylist entry — so leaked
    # cast ids ("jordan_start leaves") and stage labels never reach the player.
    state = new_game(1)
    ceremony_lines = [
        ("elimination", "Heart Out: jordan_start leaves Sunset Bay."),
        ("flush_of_hearts_arrival", "Flush of Hearts begins: you are sent to the Flush resort."),
        ("pairing", "The Pairing Ceremony locks in the next couples."),
    ]
    for kind, content in ceremony_lines:
        add_memory(
            state,
            create_memory(
                holder_id="player",
                subject_id="resort",
                source="witnessed",
                day=1,
                turn=2,
                weight=7,
                tags=[kind, "ceremony"],
                content=content,
            ),
        )
    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="player",
            source="direct",
            day=1,
            turn=3,
            weight=6,
            tags=["spark"],
            content="Chloe softened every time you walked past.",
        ),
    )
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    contents = [item.content for item in recap.items]
    assert contents == ["Chloe softened every time you walked past."]
    assert not any("jordan_start" in c or "Heart Out" in c for c in contents)


def test_daily_recap_drops_internal_caught_unprepared_markers() -> None:
    # ``caught_unprepared`` quiz reactions are internal, tag-only markers phrased
    # in a bare first person ("...about my age...") that read as orphaned in a
    # player-facing digest. They must not surface even though they carry no
    # ceremony tag.
    state = new_game(1)
    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="player",
            source="direct",
            day=1,
            turn=2,
            weight=4,
            tags=["caught_unprepared", "compatibility_quiz", "age"],
            content="The player guessed wrong about my age in the Compatibility Quiz.",
        ),
    )
    add_memory(
        state,
        create_memory(
            holder_id="maya",
            subject_id="player",
            source="direct",
            day=1,
            turn=3,
            weight=5,
            tags=["banter"],
            content="Maya laughed the hardest at your joke by the pool.",
        ),
    )
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    contents = [item.content for item in recap.items]
    assert contents == ["Maya laughed the hardest at your joke by the pool."]


def test_daily_recap_rewrites_bare_player_label_to_second_person() -> None:
    # Some engine-authored memories use a bare "Player"/"the player" subject
    # label; the player-facing recap must address them directly in both forms.
    state = new_game(1)
    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="player",
            source="direct",
            day=1,
            turn=2,
            weight=6,
            tags=["spark"],
            content="Player leaned in, and the player's smile gave it away.",
        ),
    )
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    assert recap.items[0].content == "You leaned in, and your smile gave it away."


def test_daily_recap_drops_procedural_flame_deck_announcements() -> None:
    # Stage directions ("called to the flame_deck") and producer-text events carry
    # internal labels and are things the player saw directly — not whispers.
    state = new_game(1)
    procedural = [
        ("gather_scheduled", "Everyone is called to the flame_deck for a Pairing Ceremony."),
        ("producer_text", "Pairing Ceremony text: Heartbreakers, choose wisely."),
        ("challenge", "The Couples Quiz tested Banter and is still pending."),
    ]
    for kind, content in procedural:
        add_memory(
            state,
            create_memory(
                holder_id="player",
                subject_id="resort",
                source="witnessed",
                day=1,
                turn=2,
                weight=5,
                tags=[kind, "ceremony"],
                content=content,
            ),
        )
    # One genuine whisper should still come through.
    add_memory(
        state,
        create_memory(
            holder_id="chloe",
            subject_id="player",
            source="direct",
            day=1,
            turn=3,
            weight=7,
            tags=["spark"],
            content="Chloe kept glancing your way all evening.",
        ),
    )
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    contents = [item.content for item in recap.items]
    assert contents == ["Chloe kept glancing your way all evening."]
    assert not any("flame_deck" in c or "text:" in c.lower() for c in contents)


def test_daily_recap_capitalizes_sentence_initial_player_label() -> None:
    state = new_game(1)
    memory = create_memory(
        holder_id="chloe",
        subject_id="player",
        source="direct",
        day=1,
        turn=4,
        weight=7,
        tags=["honesty"],
        content="The player's honesty surprised me. The player owned it.",
    )
    add_memory(state, memory)
    state.day = 2

    recap = append_daily_recap_if_needed(state, 1)

    assert recap is not None
    assert recap.items[0].content == "Your honesty surprised me. You owned it."
