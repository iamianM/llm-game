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
question: Can the AI do this behavior in plain language?
category: conversation           # conversation / social_dynamics /
                                 # pairing_and_endings / special_events / challenges
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
    spark: 5
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
live_resort_life: false           # set false unless the scenario is testing
                                 # Resort Orchestrator + Background Dialogue
judge_context:                   # short bullets the judge sees as fixed facts
  - This is a Day 3 flame_deck beat; pairing is decided in-engine.
thread_check:                    # required single holistic scenario verdict
  id: thread_acceptance
  severity: blocking
  criteria:                     # rubric dimensions, not separate verdicts
    - id: conversation_arc
      criteria: >
        Across the complete thread, each exchange builds on the prior beat and
        the ending resolves the conversation without changing engine outcomes.
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
    golden:
      criteria: >
        One or two sentences describing what matters in the result. The judge
        applies this semantically; it does not require identical prose.
      calls:                            # ordered reviewed agent results
        - agent: heartbreaker_voice
          output_type: Exchange
          output:                      # same shape as the actual parsed result
            player_dialogue: How are you actually feeling this morning?
            npc_dialogue: Honestly, a little more wobbly than I am letting on.
            npc_tone: vulnerable
            npc_mood_after: content
        - agent: contextual_options
          output_type: ContextualBespoke
          output:
            options:
              - {label: Go deeper, category: deep, risk: medium}
              - {label: End on a good note, category: exit, risk: safe}
    checks:                               # deterministic checks (see below)
      - exchange_valid
      - follow_up_menu_valid
      - conversation_active
      - agent_traces_present
      - no_agent_validation_retries
```

## Deterministic checks

Add any of these to a turn's `checks:` list. The check looks at structured
fields the engine + agents produce; it never policies prose for length or
vocabulary (per ENGINEERING.md R7 and R18).

These checks protect exact contracts that the thread judge should not guess.
The hosted dashboard collapses passing checks into one summary. It opens failed
checks so a reviewer can read the reason and evidence.

- **Universal (always runs, even if not listed):**
  - `engine_state_invariants_preserved` — schema/seed/player identity are
    unchanged, eliminated Heartbreakers stay eliminated, couples only move
    under an action that legitimately changes couples.

- **Conversation contract:**
  - `mechanical_success` — the authored beat is explicitly a successful interaction.
  - `exchange_valid` — Heartbreaker Voice output validates (hidden-cast guard,
    tone enum, gossip-subject allowance).
  - `follow_up_menu_valid` — menu schema + exit invariant + enum values.
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
  - `challenge_cleared` — a resolved challenge no longer owns the playable
    surface after its wrap turn.
  - `flush_active` — Flush of Hearts is active.
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
  - `private_suite_consumed:<partner_id>` — Private Suite state, couple flag, player
    location, partner location, used day, and deltas-applied flag all match.
  - `visible_targets_include:id1,id2,...` — listed NPCs are at the player's
    location and not eliminated.

- **Private chat mechanics:**
  - `private_chat_recorded` — a private chat attempt was rolled this turn.
  - `private_chat_succeeded` / `private_chat_rejected` — the attempt resolved as expected.
  - `npc_conversation_still_active` — after a rejected private chat, the original
    NPC-NPC conversation persists.
  - `npc_conversation_closed` — after a successful private chat, the original NPC-NPC
    conversation was removed and an engine-owned `private_chat_success` closure was recorded.
  - `private_chat_rejection_witness_memory` — rejected private chats leave a witnessed memory
    tagged to the target.

- **Background resort life:**
  - `resort_update_committed` — orchestrator returned a typed update.
  - `background_kind_isolated` — background curator batches never write a
    `source=direct` memory with `holder_id=player`.

- **Live-only metadata (auto-pass in mock):**
  - `agent_traces_present` — at least one trace captured.
  - `no_agent_validation_retries` — no agent had to retry its commit.

## Thread check

Every scenario defines exactly one `thread_check:` at scenario scope. After the
complete trace artifact is written, one judge call receives the scenario goal,
judge context, every action, each structured golden, every engine record, all
ordered actual agent outputs, and the complete acceptance rubric. It returns one holistic `pass`,
`fail`, or `cannot_determine` verdict for the scenario.

Golden calls lock the expected agent order, output contract, and a reviewed
example result. Natural-language fields are semantic references, not exact
string snapshots. Rubric criteria describe qualities schemas cannot prove across a sequence:
voice consistency, emotional continuity, narrative arc, specificity, and
faithfulness to the semantic targets and engine-owned outcomes. Use deterministic turn
checks for shape, contracts, and game state. Never add per-turn semantic judge
checks or multiple thread verdicts.

The single thread check is blocking. A `fail` or `cannot_determine` affects
scenario status.

## Running

```bash
# fast, free, deterministic mock mode
make llm-eval-mock

# live agents (GPT-5.6 Luna role profiles) — slow and billed
make llm-eval-real

# add the judge for voice / continuity / faithfulness
make llm-eval-real-judge

# or call the CLI directly
uv run python -m src.game.cli llm-eval \
  --scenarios evals/llm/scenarios/private-chat-rejection.yaml \
  --out review-packet/single-private-chat \
  --real-llm --judge \
  --max-workers 1
```

The command writes three outputs. `index.html` is the full local review packet.
`artifacts/run.json` is the raw run. `showcase.json` is an allowlisted public
projection without prompts, model inputs, response IDs, hashes, or local paths.
The projection keeps structured goldens, safe structured output for each agent,
evaluation reasons, model profiles, latency, model-provided reasoning summaries,
token usage, and a dated price snapshot. It excludes prompts, model inputs,
response IDs, hashes, and hidden reasoning. `showcase.json` stores game-agent,
judge, per-call, and total cost estimates. The browser reads those estimates;
it does not use a separate pricing table.
The CLI and report show the worker count; default is
`min(number_of_scenarios, 8)`, and `--max-workers 1` gives a sequential run.

## When to add a scenario

- New agent or new agent contract.
- New action kind reachable from the player menu.
- New ceremony type or new format twist.
- A real playtest surfaced a beat that broke — lock the fix in here.
- A whole-thread check would catch a visible regression that pure schema cannot.

Do not add a scenario just to bump coverage. Each scenario costs real LLM
spend in `--real-llm` mode; the bar is "would a regression here be visible
to the player."
