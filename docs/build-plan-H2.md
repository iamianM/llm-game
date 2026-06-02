# Build Plan: Phase H2 — Daily Challenges + Producer Texts

> Historical build plan. This file is kept for implementation context only.
> Current planning lives in [current-plan.md](current-plan.md).

After H1, the run has a beginning (character creation) and an end (final vote). H2 fills the middle. The `CHALLENGE` phase fires actual challenges with mechanical outcomes and dramatic narration. The `TEXT` phase fires producer texts that announce dates, twists, and heart_throbs. Every phase becomes something the player reacts to, not a clock tick.

**Design sources:** [12-Challenges-And-Events.md](../12-Challenges-And-Events.md), [08-Daily-Loop.md § The Four Phases](../08-Daily-Loop.md), [10-Elimination-System.md § Producer AI](../10-Elimination-System.md).

**Operating contract:** See [build-plan-H-index.md](build-plan-H-index.md).

---

## Architectural Decisions

### Challenges system

A challenge is an algorithmic, stat-based mini-event that fires automatically when the day clock reaches the `CHALLENGE` phase. The challenge's mechanical outcome is computed by code (no LLM); the Event Narrator writes the dramatic narration of the result.

Each challenge is content-authored as a markdown file under `content/challenges/`. Frontmatter declares the challenge's kind, the day(s) it can fire on, the stats it tests, the success/failure outcomes, and any narrative beats. Code matches the challenge to the current day via a deterministic schedule.

Six initial challenges, one per day:

| Day | Challenge | Stat | Outcome on success | Outcome on failure |
|---|---|---|---|---|
| 1 | **Compatibility Quiz** | EQ | Couple strength +5 with partner, public perception +3 | Couple strength +0, public perception -1, slight tension |
| 2 | **Heart Rate Challenge** | Charm | Chemistry +6 with partner, public perception +4 | Chemistry +1, public perception -2, mild humiliation |
| 3 | **The Couples Quiz** | Banter + Player relationship knowledge | Friendship +5 across cast, public perception +5 | Friendship -2 with partner, public perception -3 |
| 4 | **Lie Detector** | Loyalty | Trust +6 with partner, public perception +4 | Trust -6 with partner, public perception -3, drama incoming |
| 5 | **Kiss Wed Pass** | Banter | Chemistry +3 with chosen kiss target, public perception +2 | Friendship -3 with whoever you passed on, public perception -1 |
| 6 | **Final Couple's Challenge** | combined Charm + Banter | Couple strength +10 with partner, public perception +6 | Couple strength +2, public perception -2 |

Each challenge type has its own resolution function in `engine/challenges.py`. The scheduling table `DAILY_CHALLENGE_SCHEDULE = {1: "compatibility_quiz", 2: "heart_rate", ...}` is a module-level constant. Validation rejects challenges that reference unknown stats.

When the player enters CHALLENGE phase: the engine resolves the challenge, applies deltas, generates an `Event Narrator` call with the challenge result. The CLI/HTML renders the challenge card prominently.

### Player choice within challenges

Some challenges require a player choice mid-event (e.g. Kiss Wed Pass: pick three heartbreakers by name). These present a quick menu, **not the conversation wheel** — it's a simple list selection. The chosen option becomes part of the recorded action stream.

New action kind: `CHALLENGE_RESPONSE` with `choice: str` field. Only valid when a challenge is in-flight. Engine validation rejects it otherwise.

### Producer Texts

A producer text is a brief announcement in the `TEXT` phase that triggers a scheduled event the next phase or day. Each text is content-authored as a markdown file under `content/producer_texts/`. Frontmatter declares the kind, the trigger conditions, and the consequence event.

Six initial producer text kinds:

| Kind | Day | Effect |
|---|---|---|
| `welcome` | 1 | Sets resort tone; no mechanical effect |
| `group_date_invite` | 2 | Three player+heartbreaker pairs get a group date the next morning |
| `coupling_warning` | 3 | Tells the heartbreakers Pairing Ceremony is tonight (sets mood: anxious for some) |
| `heart_throb_arrival_tease` | 4 (just before heart_throb) | Announces Aisha's imminent arrival, raises tension |
| `flush_of_hearts_announce` | After H5: day 4 | Triggers Flush of Hearts flow |
| `final_vote_announce` | 6 | "Tonight, the public vote opens" — sets the stakes |

Texts are scheduled deterministically by day in `engine/producer_events.py`. The Event Narrator writes the actual text-to-screen prose.

When a producer text fires, the next applicable phase may have a special pre-amble (e.g. group date intent menu appears on the morning after `group_date_invite`).

### Group dates as a new conversation flavor

Group date is a special conversation type where two NPCs are present, not just one. The wheel options behave similarly but exchanges reference both NPCs. The Heartbreaker Voice context includes both participants. Memories are created for both NPCs (direct), plus any bystander at the location.

For H2, group dates are limited to fixed pairings (player + 2 NPCs in different scenarios). The Producer Event scheduler decides which NPCs and writes the pairing into the conversation start.

### State extensions

```python
class Challenge(BaseModel):
    id: str                                            # e.g. "compatibility_quiz"
    day: int
    kind: str
    participants: list[str]                            # ids of all involved
    player_choice: str | None                          # for choice-based challenges
    result: Literal["success", "failure"] | None
    deltas: dict[str, RelationshipDelta]              # per-target deltas

class ProducerText(BaseModel):
    id: str
    day: int
    phase: Phase                                       # always TEXT
    kind: str
    body: str                                          # LLM-narrated prose
    triggers: list[str]                                # scheduled event ids

class GroupDate(BaseModel):
    id: str
    participants: list[str]
    location: Location
    day: int
    pending: bool
```

`GameState` gains: `pending_challenge: Challenge | None`, `pending_text: ProducerText | None`, `pending_group_date: GroupDate | None`. Bump `SCHEMA_VERSION`.

`state_hash_payload` hash-includes everything except LLM-authored prose (`Challenge.deltas` are hashed; `ProducerText.body` is not).

---

## Changes by file

### New files

| File | Purpose |
|---|---|
| `src/game/engine/challenges.py` | Challenge resolution functions per kind, scheduling table |
| `src/game/engine/producer_events.py` | Producer text scheduler, group date setup |
| `content/challenges/compatibility_quiz.md` | Challenge definition |
| `content/challenges/heart_rate.md` | Challenge definition |
| `content/challenges/couples_quiz.md` | Challenge definition |
| `content/challenges/lie_detector.md` | Challenge definition |
| `content/challenges/kiss_wed_pass.md` | Challenge definition |
| `content/challenges/final_couples.md` | Challenge definition |
| `content/producer_texts/welcome.md` | Text content + frontmatter |
| `content/producer_texts/group_date_invite.md` | Text content + frontmatter |
| `content/producer_texts/coupling_warning.md` | Text content + frontmatter |
| `content/producer_texts/heart_throb_arrival_tease.md` | Text content + frontmatter |
| `content/producer_texts/final_vote_announce.md` | Text content + frontmatter |
| `tests/engine/test_challenges.py` | Per-challenge unit tests |
| `tests/engine/test_producer_events.py` | Producer text scheduling tests |
| `tests/scenarios/fixtures/challenge-day1.yaml` | Scenario: compatibility quiz fires |
| `tests/scenarios/fixtures/producer-text-day2.yaml` | Scenario: producer text fires |

### Files changed

- [`src/game/state/models.py`](../src/game/state/models.py): Add `Challenge`, `ProducerText`, `GroupDate`. Add `pending_*` fields to `GameState`. Bump `SCHEMA_VERSION`.
- [`src/game/engine/actions.py`](../src/game/engine/actions.py): Add `CHALLENGE_RESPONSE` action kind. Add it to `available_actions` only when `state.pending_challenge` requires player input.
- [`src/game/engine/turn.py`](../src/game/engine/turn.py): On phase advance to `CHALLENGE`, set `state.pending_challenge = schedule_challenge(state.day)`. On phase advance to `TEXT`, set `state.pending_text = schedule_text(state.day, state)`. Handle `CHALLENGE_RESPONSE` action.
- [`src/game/engine/phases.py`](../src/game/engine/phases.py): No structural change; phases stay the same. Phase transitions trigger the new event setups.
- [`src/game/agents/event_narrator.py`](../src/game/agents/event_narrator.py): Accepts new event kinds: `challenge`, `producer_text`, `group_date_announce`. Same prompt; the context just expands. No prompt change.
- [`src/game/cli/commands/play.py`](../src/game/cli/commands/play.py): When `state.pending_challenge` requires choice, show the choice menu (not the wheel). When `state.pending_text` is set, display the producer text prominently.
- [`src/game/cli/commands/play_render.py`](../src/game/cli/commands/play_render.py): New blocks for challenge card, producer text card.
- [`src/game/reporting/html_blocks.py`](../src/game/reporting/html_blocks.py): New HTML blocks for challenge_result, producer_text, group_date.
- [`src/game/eval/playthrough.py`](../src/game/eval/playthrough.py): Add `assert_challenge_fired_each_day` (six challenges across six days), `assert_at_least_three_producer_texts`, `assert_group_date_observed`.
- [`src/game/content/lint.py`](../src/game/content/lint.py): Validate `content/challenges/` — six files matching the scheduled kinds; each has required frontmatter (`id`, `day`, `kind`, `stat_tested`, `success_deltas`, `failure_deltas`). Validate `content/producer_texts/` — required frontmatter (`id`, `day`, `kind`).
- [`src/game/content/models.py`](../src/game/content/models.py): Add `ChallengeContent`, `ProducerTextContent`.
- [`src/game/content/loader.py`](../src/game/content/loader.py): Load both new content directories.

---

## Acceptance criteria

- [ ] `make qa` green.
- [ ] `make test-llm` green.
- [ ] `make play` shows a challenge each day during the CHALLENGE phase. The player sees the challenge name, the stat tested, and either the result (algorithmic challenges) or a choice menu (Kiss Wed Pass).
- [ ] Producer texts fire in the TEXT phase on days 1, 2, 3, 4, and 6 at minimum.
- [ ] A group date setup leads to a special two-NPC conversation flavor the next morning.
- [ ] Each challenge applies correct relationship deltas (positive on success, varied on failure) per the table.
- [ ] Public perception meaningfully fluctuates from challenge results.
- [ ] Scenario fixture `challenge-day1.yaml` replays to a known hash showing the Compatibility Quiz fired and applied deltas.
- [ ] Scenario fixture `producer-text-day2.yaml` replays with the group date invite triggering a group conversation on day 3 morning.
- [ ] `verify --playthrough` includes three new assertions:
  - `assert_challenge_fired_each_day` — at least 5/6 days have a challenge in the trace.
  - `assert_at_least_three_producer_texts` — three or more producer text records.
  - `assert_group_date_observed` — one group date conversation appears.

---

## Tests

### Engine unit tests (non-LLM)

- `tests/engine/test_challenges.py`:
  - `test_compatibility_quiz_success_applies_couple_strength_bonus`
  - `test_compatibility_quiz_failure_applies_tension`
  - `test_heart_rate_uses_charm`
  - `test_couples_quiz_failure_drops_friendship`
  - `test_lie_detector_high_loyalty_succeeds`
  - `test_lie_detector_low_loyalty_breaks_trust`
  - `test_kiss_wed_pass_choice_required`
  - `test_kiss_wed_pass_cooled on_heartbreaker_loses_friendship`
  - `test_final_couples_challenge_combines_stats`
  - `test_schedule_challenge_returns_correct_kind_per_day`
  - `test_challenge_emits_ceremony_event_for_narration`
- `tests/engine/test_producer_events.py`:
  - `test_welcome_text_fires_day_1`
  - `test_group_date_invite_creates_pending_group_date`
  - `test_coupling_warning_text_on_day_3`
  - `test_heart_throb_arrival_tease_precedes_aisha`
  - `test_final_vote_announce_text_day_6`
  - `test_producer_text_does_not_fire_off_schedule`

### Scenario fixtures (mock LLM)

- `tests/scenarios/fixtures/challenge-day1.yaml`: locked hash after the day-1 challenge completes successfully.
- `tests/scenarios/fixtures/producer-text-day2.yaml`: locked hash after the day-2 group date invite triggers a day-3 group conversation.

### LLM tests (opt-in)

- None required. Event Narrator already handles new event kinds via its existing prompt.

---

## Evals (new playthrough assertions)

- `assert_challenge_fired_each_day` — at least 5 of 6 days have a challenge in the trace (one off-day permitted for off-schedule fixtures).
- `assert_at_least_three_producer_texts` — total producer_text events in trace ≥ 3.
- `assert_group_date_observed` — at least one conversation has more than one NPC participant.

Aggregate stats added: `challenges_completed`, `challenges_succeeded`, `producer_texts_fired`, `group_dates_held`.

---

## Anti-goals

- ❌ No live LLM in challenge resolution math. Challenges are algorithmic. The Event Narrator writes prose, not outcomes.
- ❌ No "Producer AI" that dynamically schedules events. Producer texts use a fixed schedule. Dynamic scheduling stays deferred.
- ❌ No procedural challenge generation. The six challenges are content-authored. New kinds require an ADR and a new content file.
- ❌ No challenge skipping. Every day fires its scheduled challenge (or a fallback if the player is eliminated).
- ❌ No prompt edits without user direction (R17).

---

## Done checklist for Codex

- [ ] Read [build-plan-H-index.md](build-plan-H-index.md) pre-flight checklist
- [ ] Re-read [12-Challenges-And-Events.md](../12-Challenges-And-Events.md), [08-Daily-Loop.md](../08-Daily-Loop.md)
- [ ] Add `Challenge`, `ProducerText`, `GroupDate` Pydantic models
- [ ] Add `CHALLENGE_RESPONSE` action kind
- [ ] Bump `SCHEMA_VERSION`
- [ ] Author the 6 challenge content files
- [ ] Author the 5 producer text content files
- [ ] Write `engine/challenges.py` with resolution functions and schedule
- [ ] Write `engine/producer_events.py` with text scheduling and group date setup
- [ ] Wire phase transitions in `engine/turn.py`
- [ ] Update `content/lint.py`, `content/models.py`, `content/loader.py`
- [ ] Update CLI rendering for challenge cards and producer texts
- [ ] Add HTML blocks for challenge results and producer texts
- [ ] Regenerate scenario fixtures
- [ ] Write unit tests for challenges and producer events
- [ ] Add scenario fixtures `challenge-day1.yaml` and `producer-text-day2.yaml`
- [ ] Extend `eval/playthrough.py` with three new assertions
- [ ] Run `make qa`; fix root causes
- [ ] Run `make test-llm`
- [ ] Append to `docs/build-log.md`
- [ ] Commit: `Phase H2: daily challenges and producer texts`
