# Engineering Rules

These rules are non-negotiable for implementation work. They adapt the discipline from `C:\Users\Mcian\projects\steno-livekit-agent` to this game.

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

## R13. No README.md

`AGENTS.md` is the entry point. Use `ENGINEERING.md`, `FORMAT.md`, `INDEX.md`, ADRs, or numbered design docs for other documentation.

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

## R17. Prompts Are User-Owned

Prompt files under `src/game/agents/prompts/` are authored and edited only by the user (Claude in this collaboration drafts them; the user approves). When a build plan installs a prompt, it installs verbatim. Codex does not soften, shorten, restructure, or "improve" prompt wording without an explicit user request.

If a prompt produces bad output, the response is to flag the problem and propose an edit — not to silently rewrite the prompt. Prompt drift is a content-quality heuristic in the same family as R7 and gets the same answer: the prompt is the heuristic; edits go through the prompt owner.
