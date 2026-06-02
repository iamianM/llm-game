# Build Plan H — Make It a Real Game

> Historical build-plan index. This file is kept for implementation context
> only. Current planning lives in [current-plan.md](current-plan.md).

This is the index for the H-series of build plans. Each H phase has its own plan doc with full implementation detail, acceptance criteria, and evals. Codex executes them in the order below.

The H series exists because v0 ships an engine, not a game. H makes it a game: it has a start (character creation), a middle (daily challenges and producer events), a climax (Flush of Hearts or Pairing Ceremony drama), and an ending (the public vote). The engine systems built in F and G become the *substrate* for actual gameplay.

---

## Phase order and dependencies

| Phase | Title | Plan | Depends on |
|---|---|---|---|
| **G9** | Repo cleanup (completed) | committed | — |
| **H1** | Win Condition + Character Creation | [build-plan-H1.md](build-plan-H1.md) | G9 |
| **H2** | Daily Challenges + Producer Texts | [build-plan-H2.md](build-plan-H2.md) | H1 |
| **H3** | NPC Personality Depth | [build-plan-H3.md](build-plan-H3.md) | H1 |
| **H4** | Paradise Suite + Couple Strength | [build-plan-H4.md](build-plan-H4.md) | H1, H2 |
| **H5** | Flush of Hearts | [build-plan-H5.md](build-plan-H5.md) | H1–H4 |
| **H6** | Stylish HTML Report | [build-plan-H6.md](build-plan-H6.md) | H1, H2 |
| **H7** | AI Self-Play Validation | [build-plan-H7.md](build-plan-H7.md) | H1, H2 |

**Sequencing rules.**

- H1 ships first, always. Nothing else matters without a win condition.
- H2 and H3 can run in either order after H1. H2 fills phase content; H3 deepens social math. Doing H2 first gives the player more variety to react to.
- H4 needs H1 (couple ranking) and H2 (text phase events).
- H5 (Flush of Hearts) is the biggest content drop and needs all the engine hooks from H1–H4.
- H6 (stylish report) waits until H1+H2 have produced enough content to render meaningfully.
- H7 (AI autopilot) waits until H1 (a goal to optimize toward) and H2 (variety to react to).

A reasonable shipping order: G9 → H1 → H2 → H3 → H4 → H6 → H7 → H5. Flush of Hearts is the dessert; the other phases produce the meal first.

---

## Per-phase pre-flight checklist

Codex follows this before starting any H phase:

- [ ] Read [`ENGINEERING.md`](../ENGINEERING.md)
- [ ] Read [`AGENTS.md`](../AGENTS.md)
- [ ] Read this index doc
- [ ] Read the phase plan doc fully
- [ ] Re-read the design docs cited by the phase
- [ ] Re-read the previous phase's `docs/build-log.md` entry

## Per-phase commit checklist

Before declaring a phase committed:

- [ ] All "Changes" items in the plan have landed
- [ ] All new tests in the plan exist and pass
- [ ] `make qa` green (including `make smoke`, `make determinism`, content lint, type-check)
- [ ] `make test-llm` green if the phase touched any prompts or new agents
- [ ] All acceptance criteria in the plan are checked off
- [ ] No prompt files edited without explicit user direction (R17)
- [ ] Build log appended with a structured entry (files added, files changed, tests added, QA result, scenario fixture name if any)
- [ ] One git commit per phase, message format `Phase H<N>: <one-line summary>`
- [ ] New CLI subcommands wired into `src/game/cli/__main__.py`
- [ ] `SCHEMA_VERSION` bumped if any Pydantic state model changed; scenario fixtures regenerated (R12)
- [ ] No dead code, no `--no-verify`, no bare `# type: ignore` (R4, R5)
- [ ] No new agent calls outside the four established surfaces (Heartbreaker Voice, Contextual Options, Event Narrator, Resort Orchestrator, Background Dialogue, Conversation Curator) without an ADR

## Per-phase evaluation checklist

Each phase that adds a new player-facing system extends [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py) with one or more new assertions. Each phase's plan lists them. After the phase commits, a real-LLM session should be recorded and `verify --playthrough` should pass the new assertions in addition to the existing 11.

By H7 completion the eval suite should be at ~20+ assertions covering every player-facing system.

---

## Repo structure target after Phase H

```
llm-game/
├── 00-Game-Start-And-Setup.md       (design canon, unchanged)
├── 01-Game-Vision.md                 ...
├── 02–12-*.md                        ...
├── AGENTS.md
├── CLAUDE.md
├── ENGINEERING.md
├── Makefile
├── pyproject.toml
├── uv.lock
├── content/
│   ├── archetypes/                   (3 NPC archetypes, expandable)
│   ├── locations/                    (4 locations + Flush of Hearts)
│   ├── intents.yaml                  (intent catalog with risk-by-category)
│   ├── challenges/                   (H2)
│   │   ├── compatibility_quiz.md
│   │   ├── heart_rate.md
│   │   ├── couples_quiz.md
│   │   ├── lie_detector.md
│   │   ├── kiss_wed_pass.md
│   │   └── final_couples.md
│   ├── producer_texts/               (H2)
│   │   ├── welcome.md
│   │   ├── group_date.md
│   │   ├── flush_of_hearts_announce.md
│   │   └── ...
│   ├── player_archetypes/            (H1)
│   │   ├── heartthrob.md
│   │   ├── class_clown.md
│   │   └── loyal_friend.md
│   └── private_suite.md                   (H4)
├── docs/
│   ├── build-plan-A2-E.md            (historical)
│   ├── build-plan-F.md               (historical)
│   ├── build-plan-G.md               (historical)
│   ├── build-plan-G8.md              (historical)
│   ├── build-plan-H-index.md         (this doc)
│   ├── build-plan-H1.md
│   ├── build-plan-H2.md
│   ├── build-plan-H3.md
│   ├── build-plan-H4.md
│   ├── build-plan-H5.md
│   ├── build-plan-H6.md
│   ├── build-plan-H7.md
│   ├── build-log.md
│   ├── qa-strategy.md
│   └── decisions/                    (ADRs)
├── fixtures/
│   └── snapshots/                    (checked-in snapshots for tests)
├── src/
│   └── game/
│       ├── agents/
│       │   ├── prompts/              (all prompts, user-owned per R17)
│       │   ├── background_dialogue.py
│       │   ├── contextual_options.py
│       │   ├── conversation_curator.py
│       │   ├── event_narrator.py
│       │   ├── heartbreaker_voice.py
│       │   ├── player_autopilot.py   (H7)
│       │   ├── resort_orchestrator.py
│       │   └── __init__.py
│       ├── api/                      (FastAPI; unchanged through H)
│       ├── cli/
│       │   ├── commands/
│       │   │   ├── content.py
│       │   │   ├── play.py           (H1: adds character creation flow)
│       │   │   ├── play_render.py
│       │   │   ├── report.py
│       │   │   ├── snapshot.py
│       │   │   ├── trace.py
│       │   │   ├── verify.py
│       │   │   └── verify_script.py
│       │   └── __main__.py
│       ├── content/
│       │   ├── lint.py               (extended each phase)
│       │   ├── loader.py
│       │   └── models.py             (extended each phase)
│       ├── engine/
│       │   ├── actions.py
│       │   ├── ceremonies.py
│       │   ├── challenges.py         (H2)
│       │   ├── chance.py
│       │   ├── character_creation.py (H1)
│       │   ├── conversation.py
│       │   ├── compatibility.py      (H3)
│       │   ├── couples.py            (H4)
│       │   ├── final_vote.py         (H1)
│       │   ├── followups.py
│       │   ├── gossip.py
│       │   ├── private_suite.py           (H4)
│       │   ├── interruptions.py
│       │   ├── memory.py
│       │   ├── perception.py
│       │   ├── phases.py
│       │   ├── producer_events.py    (H2)
│       │   ├── private_chat.py
│       │   ├── recorded_agents.py
│       │   ├── results.py
│       │   ├── rules.py
│       │   ├── scenario.py
│       │   ├── state_access.py
│       │   ├── turn.py
│       │   └── resort.py
│       ├── eval/
│       │   ├── playthrough.py        (extended each phase)
│       │   └── __init__.py
│       ├── reporting/
│       │   ├── balance.py
│       │   ├── eval_dashboard.py
│       │   ├── html_base.py
│       │   ├── html_blocks.py
│       │   ├── html.py
│       │   ├── stylish/              (H6)
│       │   │   ├── css.py
│       │   │   ├── timeline.py
│       │   │   ├── avatars.py
│       │   │   └── perception_graph.py
│       │   └── memory_web.py         (H6)
│       └── state/
│           ├── models.py             (extended each phase)
│           ├── persistence.py
│           ├── rng.py
│           ├── snapshot.py
│           └── trace.py
└── tests/
    ├── agents/
    │   ├── test_background_dialogue.py
    │   ├── test_conversation_curator.py
    │   ├── test_event_narrator.py
    │   ├── test_heartbreaker_voice.py
    │   ├── test_heartbreaker_voice_private_chat_rejected.py
    │   ├── test_player_autopilot.py        (H7)
    │   ├── test_resort_orchestrator.py
    │   └── test_resort_orchestrator_interruptions.py
    ├── cli/
    │   └── test_play.py                    (H1 adds character creation tests)
    ├── engine/
    │   ├── test_actions.py
    │   ├── test_ceremonies.py
    │   ├── test_challenges.py              (H2)
    │   ├── test_character_creation.py      (H1)
    │   ├── test_compatibility.py           (H3)
    │   ├── test_conversation.py
    │   ├── test_couples.py                 (H4)
    │   ├── test_final_vote.py              (H1)
    │   ├── test_gossip.py
    │   ├── test_private_suite.py                (H4)
    │   ├── test_intents.py
    │   ├── test_interruptions.py
    │   ├── test_memory.py
    │   ├── test_models.py
    │   ├── test_phases.py
    │   ├── test_producer_events.py         (H2)
    │   ├── test_private_chat.py
    │   ├── test_rng.py
    │   ├── test_rules.py
    │   ├── test_turn.py
    │   └── test_resort.py
    ├── eval/
    │   └── test_playthrough.py             (extended each phase)
    ├── reporting/
    │   ├── test_html.py
    │   └── test_stylish.py                 (H6)
    └── scenarios/
        ├── fixtures/
        │   ├── flush-of-hearts-arrive.yaml        (H5)
        │   ├── flush-of-hearts-return.yaml        (H5)
        │   ├── challenge-day1.yaml          (H2)
        │   ├── character-creation.yaml      (H1)
        │   ├── conversation-multi-exchange.yaml
        │   ├── day1-flirt-mixed.yaml
        │   ├── day1-full-stats.yaml
        │   ├── day1-happy-path.yaml
        │   ├── day1-low-stats.yaml
        │   ├── day6-final-vote.yaml         (H1)
        │   ├── day6-full-run.yaml
        │   ├── elimination-day5.yaml
        │   ├── private-suite-night.yaml          (H4)
        │   ├── producer-text-day2.yaml      (H2)
        │   ├── pairing-day3.yaml
        │   └── type-on-paper-reveal.yaml    (H3)
        └── test_runner.py
```

---

## Definition of done for Phase H overall

Phase H is complete when:

1. All seven phases (H1–H7) committed with `make qa` green.
2. `docs/build-log.md` has an entry per phase.
3. A real-LLM 6-day session can be recorded via `make play --record FILE` from a fresh character through the final vote ceremony, with a defined outcome.
4. `verify --playthrough` passes at least 18 of 20+ assertions on that real-LLM session.
5. The stylish HTML report (H6) renders that session with avatars, day timeline, couple status, and perception graph.
6. An autopilot trace (H7) exists alongside the manual trace, and both pass the same eval suite.
7. The user reviews both packets and confirms the game holds together.

After H, Phase I or J is the decision point: deploy (Vite UI + hosting), expand (more cast, more challenges, procedural NPCs, meta-progression), or polish (sound, animations, mobile).
