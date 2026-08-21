# 0017 - Daily Recap Facts And Projection

Date: 2026-08-21

## Context

The Daily Recap currently mixes the player's own memories with off-screen whispers under the heading "While you were busy." Snapshots store too little context to project a historical recap without consulting current state, while the HTTP, CLI, report, and browser adapters each rebuild names, resort labels, or reader voice.

## Decision

Persist canonical Daily Recap facts, including the day, resort identity, holder identifiers, content, and recap classification. A game-owned projection module turns those facts into one typed player-facing view for every adapter.

The memory or memory batch receives one required recap disposition when it is committed: `none`, `your_day`, or `while_busy`. The engine assigns it from explicit event or batch context. Agents do not author it. Later consumers do not infer it from tags, holder identifiers, or prose.

The projected Daily Recap has two sections. "Your day" contains the player's notable choices, conversations, and consequences. "While you were busy" contains off-screen Heartbreaker storylines that reached the player as whispers.

Snapshots retain canonical name-agnostic content. The projection converts references to "the player" into second person once. Deterministic recap structure, including the day, resort identity, classification, holder, and subject, affects the state hash. Prose and display labels do not affect the state hash.

A recap contains at most five items total. Selection reserves at least one item for each nonempty visible section, ranks candidates by engine-owned emotional weight and storyline diversity, and then displays selected items chronologically inside each section.

Each projected item exposes only its section, speaker label, second-person content, and `standard` or `strong` emphasis. Raw tags and emotional-weight values remain internal. The API, CLI, reports, and browser consume this same projection instead of deriving their own view.

The recap worktree owns disposition assignment, canonical selection, projection, and recap UI. Its targeted checks cover model validation, selection, snapshots, serialization, CLI output, and browser rendering. The integration owner connects shared session and generated-type files, then runs the full `make qa` gate. No billed live-model check is required.

The persisted shape increments the snapshot schema version. Checked-in fixtures are regenerated. Older local saves, checkpoints, and traces fail with a clear version mismatch; no legacy reader or compatibility shim is added.

## Consequences

- Historical recaps retain their original resort context.
- Browser, CLI, and report adapters stop rebuilding recap meaning.
- Snapshot fixtures and hashes require intentional regeneration if the persisted shape changes.
- The projection must expose presentation-safe emphasis instead of leaking internal tags or raw weights.
- Existing mixed-recap tests must assert the two classifications.
- Owning state, recap, browser-contract, and current-plan docs must describe the verified behavior in present tense after implementation.
