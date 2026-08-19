# Documentation Index

Start here when you need more detail than the project README. The repository
separates current behavior from product design and implementation history so an
old plan cannot accidentally override running code.

## Current Source of Truth

| Question | Document |
| --- | --- |
| What is the project and how do I run it? | [`README.md`](../README.md) |
| What are we improving now? | [`current-plan.md`](current-plan.md) |
| What engineering rules are non-negotiable? | [`ENGINEERING.md`](../ENGINEERING.md) |
| How does deterministic replay and review work? | [`systems/replay-and-review.md`](systems/replay-and-review.md) |
| How are LLM behaviors evaluated? | [`systems/llm-evals.md`](systems/llm-evals.md) |
| How do the browser and API share the engine? | [`systems/browser-and-api.md`](systems/browser-and-api.md) |
| How does scene dialogue work? | [`systems/scene-dialogue.md`](systems/scene-dialogue.md) |
| How do minigames share one harness? | [`systems/minigames.md`](systems/minigames.md) |
| How is current-run knowledge represented? | [`systems/knowledge.md`](systems/knowledge.md) |
| What must pass before merge? | [`systems/qa.md`](systems/qa.md) |
| How do I conduct a structured CLI playtest? | [`workflows/cli-playtesting.md`](workflows/cli-playtesting.md) |

`AGENTS.md` remains the detailed AI-assistant entry point. Current system docs
describe behavior in present tense; source code and tests settle any remaining
ambiguity.

## Design Canon

[`design/`](design/) contains the numbered product and game-system design: game
vision, mechanics, state, conversations, locations, gossip, pacing, social
dynamics, eliminations, and challenges. These documents explain intended game
behavior. They do not override a newer architecture decision or current system
contract.

## Architecture Decisions

[`decisions/`](decisions/) records why the project uses a canonical Python
engine, typed agent boundaries, snapshots and traces, a thin Next.js client,
and validated balance data. When an older design document proposes a different
implementation, the newer accepted decision wins.

## Reference and Research

- [`reference/`](reference/) contains stable vocabulary and naming references.
- [`research/`](research/) contains source analysis, market/reference material,
  and visual research. Research informs the product; it is not a runtime spec.
- [`evals/llm/scenarios/FORMAT.md`](../evals/llm/scenarios/FORMAT.md) is the
  authoring contract for executable golden scenarios.

## History

[`archive/`](archive/) contains build plans, superseded phase specifications,
handoffs, playtest findings, and the chronological build log. These documents
are preserved because they explain how the system evolved. They are never the
first place to look for current behavior.

## Conflict Order

When documentation disagrees, use this order:

1. Running code, schemas, and executable tests.
2. Accepted architecture decisions and `ENGINEERING.md`.
3. Current system docs and `current-plan.md`.
4. Numbered design canon.
5. Research and archived implementation history.

Update the owning system doc in the same change whenever behavior changes.
