# 0015 - Deep Scene And Minigame Presentation

Date: 2026-08-21

## Context

Scene presentation policy is spread across `GameStage`, `SceneDialogueStage`, `SceneDirector`, and `CharacterLayer`. The browser also rebuilds the pending minigame shape in several places. The old `ChallengeSpectacle` was removed from the live scene after it blocked the cast and clipped on mobile, but the unused implementation and stale handoff remained.

## Decision

Use one pure scene presentation module to produce a complete deterministic scene plan. The plan owns scene sequencing, cast staging, action lanes, focus, location, and the order of feature screens. A small React playback adapter owns timers, tap advancement, and other ephemeral playback state. `GameStage` remains the transport and feature-screen render adapter.

The module consumes one typed presentation transition. A pending stream is one mutable presentation segment. The resolved turn extends or replaces that segment without replaying consumed beats. The selected intent label is not player dialogue.

Pairing Ceremonies, couple reveals, Heart Out, Heart Throb arrivals, Flush returns, finales, and the Daily Recap use feature screens. Challenges and Paradise Calls remain in the scene. One turn presents output in this order:

1. Player line and Heartbreaker reply
2. Connection and Pulse feedback
3. In-scene event or minigame wrap
4. Feature screens in engine order
5. Daily Recap
6. Legal actions

When more than seven Heartbreakers share a scene, the player and focused Heartbreaker remain in the foreground. A compact group panel represents the rest of the present cast.

Use a separate deep minigame presentation module behind the scene seam. A typed, display-safe Pydantic projection defines the browser-facing minigame data. The minigame module supplies compact per-kind board inserts for all six minigames. `available_actions` remains the only authority for legal choices. Delete the dead `ChallengeSpectacle` implementation instead of restoring the large persistent board.

The minigame projection uses a discriminated `round` or `wrap` status and an exhaustive six-value minigame kind. Compact boards display only typed reveal values derived from engine truth. The browser does not synthesize displayed mechanics.

Engine minigame state carries narration and the concise question as separate typed fields. No serializer or browser renderer extracts a question from prose. The six compact board contracts are:

- Compatibility Quiz shows the concise question, answer, and reaction reveal.
- Couples Quiz shows partner answers and their alignment reveal.
- Pulse Race shows engine-owned BPM or rank values.
- Lie Detector drives its needle and verdict from the engine truth result.
- Kiss, Wed, Pass shows the engine-owned allocation cards.
- Final Couples shows facet scores and the final tally.

The projection schema and renderer registry are exhaustive. An unknown or unimplemented minigame kind fails validation or compilation instead of falling back to a generic challenge card.

Acceptance requires direct scene-planner tests, projection and serializer tests, and table-driven browser coverage for all six minigames. Browser checks cover a 390 by 700 viewport and a desktop viewport. Checkpoint-backed flows exercise the major feature-screen and minigame families. Targeted checks run in each isolated worktree; the full `make qa` gate runs after controlled integration. No billed live-model check is part of this deterministic presentation refactor.

## Consequences

- Renderers stop interpreting raw engine state.
- Scene and minigame planning gain direct deterministic test seams.
- The six minigames must have exhaustive presentation coverage.
- Shared connector files require a controlled integration pass after parallel module work.
- The scene handoff and current plan must be updated to match the playtested compact-board decision.
- Owning system docs, the browser contract, minigame documentation, and contract map must describe the verified behavior in present tense after implementation. Stale spectacle references and future checklists must be removed while this ADR remains as decision history.
