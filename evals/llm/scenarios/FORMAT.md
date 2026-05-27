# Golden Scenario Format

Every YAML in this directory is one scenario for the golden LLM eval. The
runner loads each file into a [`GoldenEvalScenario`](../../../src/game/eval/golden_models.py)
and runs every turn through the production [`run_turn`](../../../src/game/engine/turn.py)
path — same engine the CLI and FastAPI session loop call. There is no
parallel "eval engine."

Adding a scenario is the way to lock in expected behavior for a beat (a new
agent, a new ceremony, a new format twist). Every feature that touches an
agent boundary or a player-facing beat should ship with a scenario here.

## Top-level fields

```yaml
id: short-kebab-case             # filename without .yaml
title: Human Readable Title
goal: One-sentence "what this scenario locks in"
seed: 1234                       # SeededRng root; pick one and stick with it

# Optional scenario setup (everything below is engine-canonical state)
character_creation:              # if omitted, the player has only defaults
  archetype_id: heartthrob       # heartthrob / class_clown / loyal_friend
  gender: man                    # man / woman
  stats:                         # must sum to exactly 30
    charm: 9
    banter: 6
    eq: 5
    graft: 5
    loyalty: 5
initial_day: 3                   # 1..6
initial_phase: evening           # morning / afternoon / evening / intros / text / event
initial_phase_budget_minutes: 240
initial_location: pool
initial_relationships:           # per-NPC tweaks on top of defaults
  chloe: {affection: 45, trust: 25}
initial_couples:                 # full Couple list; replaces any defaults
  - {partner_a_id: player, partner_b_id: chloe, formed_on_day: 1}
initial_npc_conversations:       # seed an off-screen NPC-NPC chat
  - id: npcconv_maya_liam_pool
    participants: [maya, liam]
    location_id: pool
    topic: Maya and Liam comparing notes on the early couples
    started_on_turn: 0
    status: active
live_villa_life: false           # set false unless the scenario is testing
                                 # Villa Orchestrator + Background Dialogue
judge_context:                   # short bullets the judge sees as fixed facts
  - This is a Day 3 firepit beat; recoupling is decided in-engine.
```

## Turn list

```yaml
turns:
  - id: short-kebab-case
    arrange_player_location: pool         # optional per-turn move
    arrange_npc_locations:                # optional per-turn moves
      chloe: pool
    action:
      kind: start_conversation            # any ActionKind value
      target_id: chloe
      intent_id: friendly_ask_feelings
      option_index: null
    golden: >
      One or two sentences of what a great response looks like, in voice.
      Include an imagined sample line. Goldens are guidance for the judge,
      not exact wording the model must reproduce.
    checks:                               # deterministic checks (see below)
      - exchange_valid
      - follow_up_menu_valid
      - exactly_one_exit
      - conversation_active
      - agent_traces_present
      - no_agent_validation_retries
    judge_checks:                         # optional LLM judge checks
      - id: voice_fit
        criteria: >
          Chloe sounds warm, sincere, gently vulnerable. Fail if she is
          chaotic or sounds like a different archetype.
```

## Deterministic checks

Add any of these to a turn's `checks:` list. The check looks at structured
fields the engine + agents produce; it never policies prose for length or
vocabulary (per ENGINEERING.md R7 and R18).

- **Universal (always runs, even if not listed):**
  - `engine_state_invariants_preserved` — schema/seed/player identity are
    unchanged, eliminated Heartbreakers stay eliminated, couples only move
    under an action that legitimately changes couples.

- **Conversation contract:**
  - `exchange_valid` — Islander Voice output validates (hidden-cast guard,
    tone enum, gossip-subject allowance).
  - `follow_up_menu_valid` — menu schema + exit invariant + enum values.
  - `exactly_one_exit` — exactly one exit-category option.
  - `conversation_active` / `conversation_closed` — state matches the turn's
    action intent.
  - `active_conversation_target_is:<id>` — exact active-conversation target,
    useful for interruption resolution paths.
  - `curator_memories` — close-turn writes both player and target memories
    (or for non-close turns, the action's participants).

- **Event narration:**
  - `event_narration_valid` — every named ceremony participant appears in
    the prose.
  - `event_narration_present` — prose exists.
  - `ceremony_events_present` — at least one ceremony event was recorded.
  - `ceremony_event_present:<kind>` — a specific event kind was recorded.

- **Engine state:**
  - `pending_gather_waiting` — `state.pending_gather` is set.
  - `challenge_resolved` — pending challenge has a result.
  - `casa_active` — Flush of Hearts is active.
  - `run_outcome_present` — final outcome is set.
  - `location_is:<id>` — player location matches.
  - `relationship_delta:<target>:<field>:<amount>` — exact mechanical
    relationship delta, such as `relationship_delta:liam:affection:-4`.
  - `forced_movement_present:<actor>:<kind>` — a deterministic movement side
    effect was recorded.
  - `pending_npc_proposal_from:<id>` — an NPC proposal is pending from the
    named proposer.
  - `pending_npc_proposal_cleared` — the pending NPC proposal was consumed by
    a response action.
  - `proposal_outcome_is:<accepted|rejected>` — proposal outcome matches the
    expected response.
  - `couple_present:<first>:<second>` — the named pair exists in `state.couples`.
  - `audience_delta:<amount>` — the action applied the exact public perception
    delta.
  - `hideaway_consumed:<partner_id>` — Hideaway state, couple flag, player
    location, partner location, used day, and deltas-applied flag all match.
  - `visible_targets_include:id1,id2,...` — listed NPCs are at the player's
    location and not eliminated.

- **Pull mechanics:**
  - `pull_recorded` — a pull attempt was rolled this turn.
  - `pull_succeeded` / `pull_rejected` — the attempt resolved as expected.
  - `npc_conversation_still_active` — after a rejected pull, the original
    NPC-NPC conversation persists.
  - `npc_conversation_closed` — after a successful pull, the original NPC-NPC
    conversation was removed.
  - `pull_rejection_witness_memory` — rejected pulls leave a witnessed memory
    tagged to the target.

- **Background villa life:**
  - `villa_update_committed` — orchestrator returned a typed update.
  - `background_kind_isolated` — background curator batches never write a
    `source=direct` memory with `holder_id=player`.

- **Live-only metadata (auto-pass in mock):**
  - `agent_traces_present` — at least one trace captured.
  - `no_agent_validation_retries` — no agent had to retry its commit.

## Judge checks

`judge_checks:` is a list of `{id, criteria}` items. The judge sees the
scenario goal, judge context, golden, prior-turn records, this turn's
record (engine result + agent outputs + traces), and the criteria. It
returns one of `pass`, `fail`, `cannot_determine` per check.

Only use judge checks for qualities schemas cannot prove: voice fit,
emotional continuity, faithfulness to the golden, beat specificity. Use
deterministic checks for shape, contract, and engine state.

## Running

```bash
# fast, free, deterministic mock mode
make llm-eval-mock

# live agents (gpt-5.4-mini, high reasoning) — slow and billed
make llm-eval-real

# add the judge for voice / continuity / faithfulness
make llm-eval-real-judge

# or call the CLI directly
uv run python -m src.game.cli llm-eval \
  --scenarios evals/llm/scenarios/pull-rejection.yaml \
  --out review-packet/single-pull \
  --real-llm --judge \
  --max-workers 1
```

The output is `review-packet/.../index.html`. The report has a scenario
filter, search, sort, an LLM-mode badge per scenario, and per-turn details
including the golden, the actual agent output, model reasoning summaries,
and judge findings. The CLI and report show the worker count; default is
`min(number_of_scenarios, 8)`, and `--max-workers 1` gives a sequential run.

## When to add a scenario

- New agent or new agent contract.
- New action kind reachable from the player menu.
- New ceremony type or new format twist.
- A real playtest surfaced a beat that broke — lock the fix in here.
- A judge check would catch a regression that pure schema cannot.

Do not add a scenario just to bump coverage. Each scenario costs real LLM
spend in `--real-llm` mode; the bar is "would a regression here be visible
to the player."
