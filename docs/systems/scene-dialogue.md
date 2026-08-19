# Scene Dialogue

The browser presents conversations as staged visual-novel scenes rather than a
dashboard. This document describes the current presentation contract; the
original implementation handoff is preserved under `docs/archive/handoffs/`.

## Scene Grammar

- The player's selected cutout remains present in the scene.
- NPC cutouts occupy stable stage positions and move as focus changes.
- Dialogue is anchored to the current speaker.
- Narration uses a distinct presentation from spoken dialogue.
- Contextual choices appear near the player and submit canonical engine action
  identifiers.
- Minigames reuse the same stage and mount their challenge spectacle inside it.

The scene may animate or rearrange presentation, but it does not infer legal
actions or mutate canonical state.

## Input Contracts

The stage renders API display data derived from `TurnResult`: visible cast,
speaker, dialogue or narration, available actions, pending challenge state, and
the relationship/audience feedback allowed for the player. Engine identifiers
remain stable beneath player-facing labels.

## Responsive Behavior

Desktop and mobile share the same information priority: speaker and scene first,
then readable dialogue, then reachable choices. Responsive layouts may change
positions but must not hide a legal action or require raw JSON to understand a
turn.

## Verification

Scene changes require TypeScript/lint checks, focused Playwright coverage for
the affected action path, and visual inspection at representative desktop and
mobile sizes. Golden screenshots are evidence for stable checkpoints, not a
substitute for checking motion and interaction.

Related contracts:

- [`intent-tree-dialogue.md`](intent-tree-dialogue.md) defines the conversational choice hierarchy.
- [`browser-and-api.md`](browser-and-api.md) defines engine/UI ownership.
- [`minigames.md`](minigames.md) defines the embedded challenge harness.
