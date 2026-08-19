# Engineering Rules

These rules are non-negotiable for implementation work. They adapt proven
production-agent discipline to this game's deterministic simulation boundary.

## R1. Engine Owns State

The deterministic engine owns `GameState`. Agents may only return typed intent or narration through validated tools. The LLM never mutates `GameState`, writes to disk, or decides success/failure.

## R2. Fail Loud

Invalid LLM output raises. Invalid tool input raises. Invalid content frontmatter raises. Do not silently substitute heuristic results. Traces must show failures.

## R3. One Shape Per Concept

No parallel field names, legacy adapters, or "old format still accepted" paths. When a Pydantic model changes, migrate or regenerate fixtures and delete the old shape in the same change.

## R4. No Dead Or Legacy Code

No commented-out code blocks, `_legacy_*` names, unused compatibility parameters, or "kept for later" functions. If future work needs it, git history has it.

## R5. No Workarounds For Failing Checks

Never bypass checks with `--no-verify`. Avoid bare `# type: ignore` or `# noqa`; if a suppression is truly needed, include a one-line reason.

## R6. No Over-Engineering

Do not add abstractions for hypothetical futures. Prefer a direct implementation until repetition or complexity proves the abstraction is needed.

## R7. No Hardcoded Content Heuristics

Do not add keyword maps, regex filters, or scoring hacks to "fix" LLM content quality. Tighten prompts, schemas, tools, deterministic rules, or structured display identifiers instead.

QA checks must not police prose quality or vocabulary with free-text string matching. Prefer schemas, enums, AST/module metadata, content frontmatter validation, fixture hashes, and cross-reference checks.

## R8. Seeded RNG Only

All gameplay randomness flows through `src/game/state/rng.py`. No `random.random()`, `time.time()`, or `uuid.uuid4()` in deterministic gameplay paths.

## R9. File Size Discipline

Target each `src/game/` module at 300 lines or fewer. Hard cap is 400 lines. Split files before they become expensive to reason about.

## R10. Tests Protect Invariants

Coverage is not a number to chase. Every boundary that protects an invariant needs a test that names the invariant.

## R11. `make qa` Or It Did Not Happen

Do not declare an implementation task done without running the current non-LLM QA gate, or explicitly reporting why it could not run. `make qa` must verify real checks; targets that do not verify real behavior must stay outside the gate until implemented.

## R12. No Backwards-Compatibility Shims During POC

This is not a shipped product yet. Move forward, regenerate fixtures if needed, and delete obsolete paths.

## R13. Keep Public Orientation Separate From Implementation Canon

`README.md` is the public product and portfolio landing page for people who are
new to the repository. It may explain the architecture, CLI, replay, and eval
story well enough to evaluate the project, but it must link to current system
docs for the complete contract. `AGENTS.md` remains the authoritative
engineering entry point for implementation work. Put maintainable system detail
in `ENGINEERING.md`, `FORMAT.md`, `INDEX.md`, ADRs, or current system docs so the
README does not become a second source of truth.

## R14. Git Is User-Owned

Never commit, amend, push, force-push, branch, rebase, or reset without explicit user instruction.

## R15. Stay In The Boundary

Engine = deterministic math and state. `data/balance/` = typed mechanical tuning tables interpreted by engine code. Content = prose and light metadata. Agents = narration from resolved results. Changes that blur these boundaries do not belong in core.

## R16. Architecture Violations Are Regressions

Reject changes that add:

- LLM calls inside `src/game/engine/`
- direct `GameState` mutation inside `src/game/agents/`
- ambient randomness in gameplay paths
- two ways to perform the same mutation
- swallowed LLM/tool/content errors
- fallback narration strings in code
- content frontmatter fields that encode gameplay logic
- free-text string matching checks for docs, content, prompts, or player-facing vocabulary

## R17. Prompts Are Claude-Owned, Codex-Read-Only

Prompt files under `src/game/agents/prompts/` are owned by Claude in this collaboration: Claude may author and edit them directly as part of normal prompt-quality work. Codex may **not** edit prompt wording — it does not soften, shorten, restructure, or "improve" a prompt under any circumstances. When Codex installs a prompt from a build plan, it installs verbatim; if Codex believes a prompt is wrong, it flags the problem and proposes an edit for Claude (or the user) to make, and never rewrites it itself.

For Codex, prompt drift is a content-quality heuristic in the same family as R7 and gets the same answer: the prompt is the heuristic; edits go through Claude. For Claude, editing the prompt *is* the sanctioned response to bad output — tighten the prompt rather than adding a code-side string-matching workaround.

## R18. No Arbitrary Limits On Agent I/O

Agent request kwargs are limited to model, instructions, input, text/text_format, and the shared `reasoning_request_kwargs()` block. No `max_output_tokens`. No `temperature`. No `top_p`, `presence_penalty`, or other sampling overrides. Trust the model defaults and the prompt.

Length, sentence count, option count, and word count are conveyed through the prompt and the typed schema. They are not enforced in validators that reject otherwise-valid output. The only validation a reject path may enforce is the structural agent boundary: enum values, schema shape, participant mention, third-person body language, no-leaked-engine-state, etc.

Likewise, do not slice agent input or output with arbitrary `[:N]` / `[-N:]` caps. If the model needs to focus on recent context, say so in the prompt. The conversation engine already retains the last `MAX_RETAINED_EXCHANGES`; downstream agents see what the engine retained, not a second arbitrary truncation on top.

This rule exists because: capping tokens prevents the model from finishing its work; setting temperature defeats reasoning effort; truncating context starves the agent of information that the engine already decided was relevant; rejecting output by length forces retries that waste tokens and never make the output better.
