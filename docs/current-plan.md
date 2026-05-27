# Current Plan

This is the live planning surface for the game. It is not a completion ledger.
When a feature finishes, remove it from this plan and update the owning system
doc so the repo describes the game as it is.

Use this file to answer:

- What are we trying to improve next?
- What is intentionally deferred?
- What evidence makes a feature ready to merge?
- Which docs need to change with the implementation?

Historical build plans under `docs/build-plan-*.md` and the chronological
`docs/build-log.md` are useful context, but they are not the active roadmap.

## Current Product Shape

The game is a playable POC hardening toward a stronger first vertical slice.
The Python engine is canonical. The CLI, FastAPI adapter, browser client,
scenario fixtures, traces, review packets, and LLM evals must all exercise the
same engine path.

Current pillars:

- Deterministic social-sim engine with seeded RNG and typed state.
- Typed agent layer for dialogue, narration, options, summaries, background
  villa life, gossip context, and trait generation.
- Thin browser client over FastAPI.
- CLI for interactive play, persisted sessions, checkpoints, branch comparison,
  replay, review notes, deterministic verification, and golden LLM evals.
- Static review packets for human inspection.
- Mock golden evals in `make qa`; live-agent and judge evals are opt-in.

The game should feel like a reality dating show first. Systems should create
legible romantic tension, social consequences, and player-readable choices.
The LLM should make resolved moments feel alive; it should not decide math,
eligibility, votes, phase movement, or rewards.

## Planning Cycle

Use a short cycle for every meaningful feature:

1. Start from a real play problem, eval failure, or missing player-facing loop.
2. Write the smallest feature slice that would make the experience better.
3. Identify the owning engine, agent, browser, CLI, content, and docs surfaces.
4. Add deterministic tests for mechanics and a golden scenario when agent
   behavior or reviewability matters.
5. Update system docs in present tense as part of the PR.
6. Generate or inspect the relevant review packet when the feature is
   player-facing.
7. Remove the item from this plan after the owning docs describe the shipped
   behavior.

Do not keep completed checklists here. Git history and the build log preserve
how something landed; the system docs should preserve what is true now.

## Work Item Shape

Each active item should be small enough to review and should name its evidence.

Recommended fields:

- **Problem:** the player/developer pain being fixed.
- **Player value:** why the game gets better.
- **Smallest slice:** the narrow implementation that proves the direction.
- **Surfaces:** engine, agents, CLI, browser, content, docs.
- **Eval:** deterministic tests, scenario fixture, golden LLM eval, real review
  packet, or manual browser play.
- **Acceptance:** what a reviewer should be able to see without trusting vibes.

If an item cannot name its eval evidence, it is probably still design work.

## Now

### Real Eval Review And Failure-Driven Fixes

**Problem:** The golden LLM eval system exists, but its value comes from using it
to find model and prompt failures in real runs.

**Player value:** Dialogue, options, ceremonies, interruptions, and endings get
better based on inspectable failures rather than taste-only discussion.

**Smallest slice:** Run the full real judged scenario pack, review failures in
the HTML packet, and convert the highest-signal failures into direct prompt,
schema, engine, or scenario fixes.

**Surfaces:** `evals/llm/scenarios/`, `src/game/eval/`,
`src/game/agents/`, `src/game/agents/prompts/`, and review packet rendering.

**Eval:** `make llm-eval-real-judge` when an OpenAI key is available; otherwise
mock eval plus report inspection for harness changes.

**Acceptance:** The reviewer can open `review-packet/llm-eval-real-judge/index.html`,
filter to failing scenarios, compare authored golden intent to actual output,
read reasoning summaries, and understand why each fix was made.

### Browser Loop Polish For Day 1 Through Day 3

**Problem:** The browser is the player-facing surface, but the engine has added
many systems faster than the UI can make them legible.

**Player value:** The first three days should be playable without needing the
CLI or raw traces to understand what happened.

**Smallest slice:** Review the browser through character creation, opening
coupling, first chats, interruption/pull moments, challenge, recoupling warning,
and Day-3 recoupling. Fix only the confusing or unreachable surfaces. Includes
wiring the round-based Compatibility Quiz view that the API now exposes
(`pending_challenge.stem`, `round_index`, `round_count`, `choices[]` with
`{choice_id, round_index}` payloads).

**Surfaces:** `web/`, `src/api/`, CLI/browser shared action vocabulary, and
`docs/phase3-ui-spec.md`.

**Eval:** `make web-check`, `make web-contracts`, targeted Playwright coverage,
and a review packet for the same action path when useful.

**Acceptance:** Every legal engine action in the covered path is reachable in
the browser, the player can tell why the villa state changed, and no important
result is visible only in raw JSON.

### Remaining Five Minigames

Build after the Compatibility Quiz proves the shared harness. Each reuses the
same Question Bank, deterministic scoring contract, narration payload, surface
checklist, and three-layer eval policy from
[minigame-system.md](minigame-system.md). One PR per minigame. Order:

1. The Couples Quiz — [minigames/couples-quiz.md](minigames/couples-quiz.md)
   (validates two-sided rounds).
2. Lie Detector — [minigames/lie-detector.md](minigames/lie-detector.md)
   (adds the truth/lie axis and event-history lookups).
3. Pulse Race — [minigames/heart-rate.md](minigames/heart-rate.md)
   (validates reveal-only minigames with one reaction round).
4. Kiss Wed Pass — [minigames/snog-marry-pie.md](minigames/snog-marry-pie.md)
   (validates constrained-allocation choice sets).
5. Final Couples Challenge — [minigames/final-couples.md](minigames/final-couples.md)
   (validates cross-minigame aggregation feeding the final vote).

If the Compatibility Quiz exposes a harness change, fix the harness first and
update [minigame-system.md](minigame-system.md) before the next minigame
starts.

### Social Event Broadcasts

Use known facts, memories, gossip seeds, and audience pressure to make group
events feel like reality TV scenes. The engine should choose participants and
stakes; agents should write the social texture after the deterministic result.

### Audience Feedback Clarity

Audience ranking exists, but the player needs better feedback about why public
perception moved. Add concise post-action chips, trend language, and report
visibility without exposing hidden math.

### Eval Coverage For New Gameplay

Every mini-game, major ceremony, ending path, and new agent behavior should get
a scenario that shows authored golden intent, actual tools/output, deterministic
checks, judge results when useful, and model reasoning summaries.

### Review Packet Comparison

Branch comparison exists for checkpoints. Improve it only where real play shows
reviewers cannot quickly compare consequences across two choices.

## Later

### Meta-Progression

Audience Appeal, reunion flow, permanent perks, unlocks, and cross-run strategy
belong after the core single-season loop is fun and legible.

### Persistent Knowledge Across Runs

Keep current-run knowledge deterministic for now. Cross-run memory should wait
until meta-progression has a clear player value and storage contract.

### Custom Player And Cast Authoring

Player customization UI, custom cast JSON, and broader procedural cast controls
are valuable, but they should not distract from making the default cast loop
excellent.

### Deployment And Production Operations

Hosting, auth, telemetry, production persistence, and cost controls matter after
the browser loop and eval discipline are stable.

### Presentation Polish

Animation, sound, mobile polish, richer avatars, and venue art should support a
working loop. They are not substitutes for readable social consequences.

## Parked For The POC

- LiveKit or realtime voice.
- LLM-driven mechanics.
- Next.js API routes for gameplay logic.
- Heavy database architecture.
- Save-scumming as a supported player loop.
- Alternate reality-show formats.
- A general game engine.

## Documentation Rules

Use present tense for shipped behavior. Avoid "done" sections, completion
tables, and old acceptance checklists as the main source of truth.

When implementation changes behavior:

- Update the owning system doc.
- Update `AGENTS.md` only if navigation, stack, commands, or project posture
  changed.
- Update `docs/qa-strategy.md` only if the gate, trace contract, or test layer
  changed.
- Update `docs/llm-eval-system.md` or `evals/llm/scenarios/FORMAT.md` when
  scenario authoring, report review, judge policy, or eval coverage changes.
- Update `docs/contract-map.yaml` when a new source area needs a doc owner.

When a historical build-plan detail conflicts with present docs, present docs
win. Do not add compatibility shims to preserve old plans.
