# Current Plan

This is the live planning surface for Paradise Hearts. It describes what should
improve next, not everything already built. Shipped behavior belongs in the
owning document under [`docs/systems/`](systems/); completed implementation
plans belong in [`docs/archive/`](archive/).

## Current Product Shape

The playable POC has one canonical Python engine shared by the CLI, FastAPI,
browser, deterministic scenarios, replay, and golden LLM evals. It includes the
season loop, scene-based browser dialogue, current-run knowledge, autonomous
resort life, ceremonies, special events, and all six minigames.

The next milestone is not another broad subsystem. It is a stronger, more
legible Day 1 through Day 3 vertical slice, improved through real play and eval
evidence.

## Planning Cycle

For each meaningful change:

1. Start with a concrete play problem, eval failure, or missing review signal.
2. Implement the smallest complete slice across every affected surface.
3. Protect deterministic behavior with tests or a scripted scenario.
4. Add or update a golden scenario when an agent affects a player-facing beat.
5. Inspect the relevant browser state or static review packet.
6. Update the owning system doc in present tense.
7. Remove the item from this plan after it ships.

An active item should identify its player value, affected surfaces, evidence,
and acceptance signal. If it cannot name its evidence, it is still design work.

## Now

### Real Eval Review and Failure-Driven Fixes

**Problem:** The eval harness is established; its product value now depends on
using live results to find specific failures in voice, continuity, option
quality, narration, and faithfulness.

**Smallest slice:** Run the full live judged pack, inspect the HTML packet, and
fix only the highest-signal failures. Convert each repeatable failure into a
scenario check, schema constraint, or deterministic test before changing the
responsible boundary.

**Evidence:** `make llm-eval-real-judge`, the generated packet, focused tests,
and a clean mock pack. If a live key is unavailable, harness changes can ship
only with clearly stated mock-only evidence.

### GPT-5.6 Prompt Simplification (Claude-Owned)

**Problem:** The shipped model profiles now use GPT-5.6 Luna, but several
prompts still reflect older-model scaffolding: repeated constraints, large
positive/negative example sets, and two contradictory in-world vocabulary
lines that identify "Flush of Hearts" and then prohibit the same phrase.

**Smallest slice:** Claude simplifies one prompt family at a time, beginning
with Heartbreaker Voice, Event Narrator, Contextual Options, Conversation
Curator, and NPC Greeter. Keep schemas, engine boundaries, and the context
builders unchanged. State each instruction once, remove repeated examples only
after the corresponding thread scenario exists, and correct the vocabulary
rule to require "Flush of Hearts" while prohibiting the external franchise term.

**Evidence:** Run the focused whole-thread scenario at the shipped reasoning
effort and one adjacent effort, compare pass/fail findings, validation retries,
latency, and tokens in the dashboard, then run the full mock pack. Prompt files
remain Claude-owned under `ENGINEERING.md` R17.

### Day 1 Through Day 3 Browser Polish

**Problem:** The engine exposes more social context than a first-time browser
player can always interpret.

**Smallest slice:** Play from character creation through opening coupling,
first chats, interruptions and pulls, the first challenge, ceremony warning,
and the Day 3 pairing ceremony. Fix confusing, unreachable, or poorly staged
moments without expanding the season design.

**Evidence:** focused Playwright contracts, desktop and mobile visual review,
the matching deterministic action path, and a review packet where state
consequences need explanation.

### Audience Feedback Clarity

**Problem:** Audience ranking affects the run, but a player can miss why public
perception changed.

**Smallest slice:** Add concise post-action signals and trend language derived
from engine results. Keep hidden scoring and private NPC state hidden.

**Evidence:** deterministic audience tests, API/browser contract coverage, and
visual review showing that the consequence is legible without raw JSON.

### Review Packet Signal

**Problem:** Replay and branch comparison exist, but packet density can slow
down review of the decision that actually caused a divergence.

**Smallest slice:** Improve filtering or consequence summaries only where a
real playtest shows that two checkpoint branches are hard to compare.

**Evidence:** one before/after branch comparison from the same checkpoint and a
focused rendering test.

### Social Event Broadcasts

**Problem:** Group events can use more of the existing knowledge, memory,
gossip, and audience substrate to feel like reality television rather than
isolated encounters.

**Smallest slice:** Choose one recurring event and let the deterministic engine
select its participants and stakes; agents write only the resulting social
texture.

**Evidence:** deterministic participant/stake tests, one authored golden
scenario, and a browser or review-packet walkthrough.

## Later

- Meta-progression, reunion flow, permanent perks, and cross-run unlocks.
- Persistent knowledge across runs.
- Custom player and cast authoring.
- Production hosting concerns: authentication, telemetry, durable storage, and
  model cost controls.
- Additional animation, sound, mobile polish, and venue art after the first
  three days are consistently readable.

## Parked for the POC

- LiveKit or realtime voice.
- LLM-driven mechanics.
- Next.js gameplay API routes.
- Heavy database architecture.
- Save-scumming as a supported player loop.
- Alternate reality-show formats.
- A general-purpose game engine.

## Documentation Rules

- Use current system docs for shipped behavior.
- Use this file only for active and intentionally deferred work.
- Update [`systems/qa.md`](systems/qa.md) when the completion gate, trace
  contract, or test layering changes.
- Update [`systems/llm-evals.md`](systems/llm-evals.md) or the
  [scenario format](../evals/llm/scenarios/FORMAT.md) when eval authoring,
  reporting, or judge policy changes.
- Update [`contract-map.yaml`](contract-map.yaml) when source ownership changes.
- Treat archived plans as history. Do not add compatibility code to preserve
  superseded instructions.
