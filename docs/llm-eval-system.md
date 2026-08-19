# LLM Eval System

This doc describes the current golden LLM eval system for the game. It adapts
production-agent principles: deterministic scenario setup, typed outputs,
inspectable failures, regression reruns, and human review. The important
findings are:

- Run eval turns through production code, not a mock prompt harness.
- Seed earlier turns from authored goldens so every evaluated turn is isolated and replayable.
- Persist raw inputs, outputs, tool/agent commits, deterministic checks, judge prompts, and model reasoning summaries.
- Treat the judge as a reviewer assistant, not the source of truth.
- Make the human review packet the main artifact.

## System Shape

The eval stack has three layers:

1. **Recorded playthrough evals**
   Keep the existing deterministic trace system as the broad coverage gate. A full trace proves that mechanics, phase movement, replay, and report rendering stay stable.

2. **Agent scenario evals**
   Add focused YAML scenarios for specific agent behaviors. Each scenario runs through the real engine and real agent wrappers, stores every turn artifact, and checks typed outputs before any judge is called.

3. **Judge-assisted review**
   Use an LLM judge only for qualities schemas cannot prove: voice fit, continuity, drama readability, and whether a generated response meaningfully matches the authored golden. Judge results are pass/fail/cannot_determine and always shown beside raw trace evidence.

This works because the game has a single deterministic `run_turn` path, typed
agent outputs, replayable traces, and review packets. The judge does not inspect
game state or decide outcomes. It compares narrative intent against evidence
after deterministic validators have already run.

## Model And Trace Policy

All live game agents should use:

- Model: `gpt-5.4-mini` (defined in `src/game/agents/runtime.py:GAME_AGENT_MODEL`); the judge uses the same model
- Reasoning effort: `high`
- Reasoning summary: `detailed`
- Include: `reasoning.encrypted_content`
- No `max_output_tokens`, no `temperature`, no other request-shape overrides — length and shape come from the prompt and the typed schema

Each live agent call records:

- agent name
- model
- reasoning effort
- retry attempt
- prompt path
- parsed output
- validation error, if a retry was caused by validation
- model reasoning summaries

The trace stores summaries, not hidden chain of thought. These summaries go into the review packet so a human can see why the model thought it was making a choice.

## Scenario Suite

Scenarios live under `evals/llm/scenarios/`. Keep them focused and authored:
one scenario should prove one player-facing contract or one risky agent
boundary. Broad playthrough coverage still belongs to deterministic traces.

### S1: Start Chat With Every Starting NPC

Goal: prove Heartbreaker Voice and Contextual Options work across the launch cast.

Turns:

- Start conversation with Chloe using a friendly intent.
- Start conversation with Maya using a flirty intent.
- Start conversation with Liam using a deep or bromance-eligible intent.
- Start conversation with each remaining opening cast member once trait cards are active in the scenario runner.

Deterministic checks:

- `exchange` exists.
- `player_dialogue` and `npc_dialogue` validate.
- `follow_up_menu` exists unless the action intentionally exits.
- exactly one exit option exists in the menu.
- no hidden heartbreaker names appear in the visible exchange.
- output state hash is replayable.

Judge checks:

- NPC voice matches visible archetype and current relationship.
- Dialogue responds to the selected intent instead of generic flirting.
- Follow-up options are concrete and playable.

Review:

- Open `session.html`.
- Use the conversation scene per NPC.
- Expand `Model reasoning traces`.
- Check whether reasoning summaries line up with the visible state and whether failures cluster by NPC, intent, or prompt.

### S2: Conversation Continuity And Exit

Goal: prove multi-turn conversations stay coherent and end cleanly.

Turns:

- Start a conversation.
- Choose a contextual follow-up.
- Choose one more follow-up.
- Exit softly.

Deterministic checks:

- each chosen intent came from the previous menu.
- conversation exchange count increases only for conversation turns.
- exit closes active conversation.
- curator emits participant memories on close.

Judge checks:

- NPC remembers the immediate prior exchange.
- The exit feels like a social close, not an abrupt system action.
- Memories summarize what happened, not what the model guessed.

### S3: Private Chat, Interruption, And Recovery

Goal: stress the places where agent commits and deterministic social rules meet.

Turns:

- Seed an active NPC-NPC conversation.
- Attempt to pull one NPC for a private chat.
- Cover one success and one rejection via fixed seeds.
- Trigger an interruption while the player is in conversation.
- Accept, defer, and ignore in separate scenario variants.

Deterministic checks:

- private chat chance, roll, and outcome are recorded.
- rejection keeps the original NPC-NPC conversation active.
- success closes or summons through validated engine paths.
- interruption commit validates.
- player response updates active conversation correctly.

Judge checks:

- rejection dialogue does not contradict the failed private chat request.
- interruption reason feels grounded in the current resort state.

### S4: Background Resort Life

Goal: prove the world keeps moving without polluting player-facing memory.

Turns:

- Advance through several player actions with off-screen NPC conversations enabled.
- Force a background conversation start and end.

Deterministic checks:

- Resort Orchestrator commit validates.
- Background Dialogue validates.
- Background Curator emits `kind: background`.
- Player-relevant memory panel excludes background-only memories.
- background activity is still visible in the review packet.

Judge checks:

- background dialogue sounds like the two NPCs, not narrator exposition.
- gossip seeds are plausible when present.

### S5: Ceremony And Ending

Goal: prove resolved events get narrated without the LLM changing outcomes.

Turns:

- Run the Pairing Ceremony.
- Run Heart Out/final vote when the engine supports it in the scenario fixture.

Deterministic checks:

- ceremony events exist before narration.
- Event Narrator output validates.
- narration mentions required participants.
- final state outcome matches deterministic event data.

Judge checks:

- narrator tone feels like reality TV.
- prose describes the resolved event and does not invent a different result.

### S6: Future Mini-Games

Goal: add this when mini-games exist.

Deterministic checks:

- mini-game input choices are legal.
- score/result comes only from engine code.
- narration describes the score without changing it.
- reward or penalty is applied exactly once.

Judge checks:

- narration makes the mini-game legible and dramatic.
- player can tell why the deterministic outcome happened from the UI.

## Check Types

Use deterministic checks whenever possible.

Required deterministic checks:

- typed schema validation
- action availability and selected-action legality
- exact final hash for non-LLM runs
- replay parity for recorded real-agent traces
- required agent output present
- no live agent validation retries for strict goldens
- no unauthorized engine mutation by agents
- expected agent commit shape
- one active conversation invariant
- menu option count and exactly one exit
- curator participant-memory coverage
- ceremony participant mention validation

Use judge checks only for:

- voice
- continuity
- specificity
- narrative faithfulness to a golden
- emotional readability
- whether reasoning summaries reveal a prompt/model misunderstanding

Judge output must be:

- `pass`
- `fail`
- `cannot_determine`

No numeric scoring for now. Numeric judge scores feel precise but are less reviewable.

## Review Packet

Every eval run should produce:

```text
review-packet/
  index.html
  session.html
  playthrough-eval.html
  llm-eval.html
  artifacts/
    session.json
    session-trace.json
    agent-traces.json
    judge-prompts/
```

The packet must answer four review questions:

1. What did the player do?
2. What did the engine decide?
3. What did each agent output?
4. Why did the model think that output was appropriate?

The reviewer should be able to review without reading logs:

- open `index.html`
- open `session.html`
- click a turn or scene
- expand `Why this outcome?`
- expand `Menu offered`
- expand `Memories formed`
- expand `Model reasoning traces`
- compare any judge failure against the raw turn evidence

## Current Scenario Files

The suite currently contains nineteen golden scenarios:

- `opening-ceremony.yaml` checks Event Narrator on a resolved initial coupling.
- `day1-intro-round.yaml` checks the first communal intro beat and pending
  gather state.
- `all-starting-npc-first-chats.yaml` starts and closes a first chat with every
  starting Heartbreaker across pool, kitchen, terrace, and bedroom, with per-NPC
  voice expectations.
- `conversation-continuity-exit.yaml` checks Heartbreaker Voice, Contextual Options,
  Conversation Curator, validation retries, judge checks, and reasoning traces.
- `wheel-exit.yaml` checks the conversation-wheel exit path separately from the
  top-level walk-away action.
- `challenge-result-narration.yaml` checks challenge resolution and narration.
- `producer-flush-announce.yaml` checks Flush of Hearts announcement state and event
  narration.
- `pairing-heart-out.yaml` checks ceremony events around the Pairing Ceremony and Heart Out.
- `player-pair-proposal.yaml` checks a player-driven Heart Swap proposal.
- `npc-proposal-incoming.yaml` checks an NPC proposal as a pending ask, then
  accepts it and verifies the exact couple, relationship, and audience results.
- `npc-proposal-decline.yaml` checks a harsh NPC proposal decline without
  changing couples.
- `final-vote-ending.yaml` checks run-ending outcome narration.
- `private-chat-success.yaml` and `private-chat-rejection.yaml` check both sides of
  pulling an NPC out of a background conversation for a private chat.
- `interruption-accept.yaml`, `interruption-defer.yaml`, and
  `interruption-ignore.yaml` split the three interruption response paths.
- `background-resort-life.yaml` checks Resort Orchestrator, Background Dialogue,
  and background memory isolation.
- `private-suite-night.yaml` checks Paradise Suite state consumption, exact relationship
  deltas, the dedicated private suite event, and privacy narration.

The generated `index.html` is the primary review surface. It intentionally hides
hashes and raw JSON by default, and instead renders scenario goals, authored
goldens, deterministic checks, judge findings, engine results, dialogue,
follow-up menus, ceremony/event output, memories, resort summaries, and model
reasoning traces. Reviewers can filter by status, search across scenario text,
sort scenarios, jump by scenario chip, and expand only failing turns.

Run the deterministic/mock golden pack:

```bash
uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-mock
```

The runner parallelizes by scenario with `min(number_of_scenarios, 8)` workers
by default. Use `--max-workers 1` for a sequential diagnostic run. The CLI,
`run.json`, and HTML report all show the resolved worker count.

Run a live judged scenario with `gpt-5.4-mini`, high reasoning, detailed summaries:

```bash
uv run python -m src.game.cli llm-eval \
  --scenarios evals/llm/scenarios/conversation-continuity-exit.yaml \
  --out review-packet/llm-eval-real-continuity \
  --real-llm \
  --judge
```

Review in this order:

1. Open `review-packet/llm-eval-mock/index.html` to confirm harness and fixtures.
2. Open `review-packet/llm-eval-real-continuity/index.html` for live model behavior.
3. Use the status filter, search box, and sort control to isolate failures or
   a specific NPC/system.
4. For each failing turn, read Checks first, then Actual output, then Model reasoning traces.
5. Open `judge-prompts/*.txt` only when a judge result looks suspicious.

## Why This Is Reliable

This is reliable for this repo because the LLM is downstream of deterministic mechanics. The riskiest failures are not hidden game-state failures; they are typed output failures, continuity failures, or narrative interpretation failures. Those are visible in a trace.

The system does not ask a judge to determine whether the game is correct. The engine and validators do that. The judge only checks whether authored narrative expectations match the actual text after raw evidence is already stored.

Prior production use proved two key implementation details:

- independent golden-seeded turn replay avoids multi-turn flakiness while still exercising production code
- reasoning summaries make model mistakes inspectable without relying on vibes

## Maintenance Rules

- New player-facing systems that cross an agent boundary need at least one
  scenario.
- New action kinds need expected tool/report coverage if they show up in eval
  reports.
- Mini-games should add scenarios only after their deterministic engine contract
  exists.
- Scenarios should use authored goldens for intent, not vague prose like "make
  this good."
- Prefer structural deterministic checks over judge checks.
- Keep judge checks for voice, continuity, specificity, emotional readability,
  and narrative faithfulness.
- When a scenario is no longer accurate, update or delete it in the same change
  that changed the game behavior. Do not support old scenario shapes.
