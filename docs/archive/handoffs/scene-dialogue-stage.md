# Scene Dialogue Presentation

This document describes the browser's current visual-novel presentation
contract. The Python engine remains canonical. The scene layer plans and plays
typed response data; it does not infer mechanics or invent player dialogue.

Decision source: `docs/decisions/0015-deep-scene-and-minigame-presentation.md`.

## Responsibilities

The presentation stack has four boundaries:

1. `GameStage` owns transport state, turn submission, feature overlays, and
   integration adapters.
2. `SceneDirector` is a pure planner. It turns one typed transition into a
   deterministic `ScenePlan`.
3. `useScenePlayback` owns ephemeral playback state such as the active beat,
   tap advancement, timer advancement, and replay suppression.
4. `SceneDialogueStage` renders the active frame, beat, action lane, and
   optional module-owned slot.

The minigame module composes through a narrow presentation port. Scene code
does not switch on minigame kinds or interpret board payloads.

## Presentation transition

Every plan consumes one of three typed transitions:

```ts
type PresentationTransition =
  | { kind: "baseline"; state: SessionState; actions: AvailableAction[] }
  | {
      kind: "pending";
      previous: SessionState;
      state: SessionState;
      actions: AvailableAction[];
      selectedAction: AvailableAction;
      stream: { speakerId: string | null; speakerName: string | null; text: string };
    }
  | { kind: "resolved"; previous: SessionState; response: TurnResponse };
```

Baseline renders the current playable state without replaying historical
feature screens. Pending presents the in-flight stream against the last
confirmed state. Resolved presents the authoritative turn response and any new
features.

The selected action label is never treated as the player's spoken line. Only
`exchange.player_dialogue` can produce a player speech beat.

## ScenePlan

The pure planner returns:

```ts
type ScenePlan<TSlot> = {
  id: string;
  locationId: string;
  segments: SceneSegment<TSlot>[];
  frames: SceneFrame[];
  actionLanes: ActionLanes;
  features: SceneFeature[];
};
```

A segment groups ordered beats with an optional deep-module slot. Frames are
planned one-for-one with beats. A mismatched count is an invariant failure.

Plan ids are stable across the pending and resolved forms of the same turn.
Beat identities use segment id, semantic beat identity, and occurrence. When a
streamed beat has already been consumed, the resolved plan continues after it
instead of replaying it.

## Beat order

For an ordinary resolved turn, presentation follows this order when the data
exists:

1. camera setup;
2. player dialogue;
3. Heartbreaker dialogue;
4. connection feedback;
5. Pulse feedback;
6. event narration or minigame segment;
7. feature overlays;
8. legal actions.

The planner omits absent beats. It does not create filler narration.

Intro turns keep the same scene grammar but focus the next Heartbreaker at the
Flame Deck and use the legal `introduce_to` actions for that target.

## Action lanes

Every legal `AvailableAction` appears in exactly one lane:

- `character`: per-Heartbreaker actions such as starting a conversation;
- `move`: location changes;
- `fan`: responses, ceremony choices, challenge choices, and other immediate
  actions.

Character and move lanes are used only outside conversations and minigames.
When a minigame is active, all legal challenge actions stay in the fan lane.

The planner verifies an exact partition by object identity and count. Dropped
or duplicated actions throw. Labels and UI heuristics never create additional
gameplay actions.

## Cast framing

`CharacterLayer` receives a planned `SceneFrame`. It does not decide who should
be visible.

The frame planner:

- keeps the player staged;
- keeps the focused Heartbreaker staged;
- includes present, non-eliminated Heartbreakers;
- uses the Flame Deck cast during intros;
- supports focused poses and camera-relative positions;
- stages at most seven Heartbreakers;
- moves any remaining present cast into one compact group panel.

The player remains visible during dialogue and minigames. `ChoiceFan` stays
anchored to the action surface rather than replacing the cast.

## Playback

`useScenePlayback` flattens segments into stable playback items. It advances:

- on tap for speech and narrator beats;
- automatically for camera, reaction, connection, and delta beats;
- only by submitting an action for a `choice_fan` beat.

If a streaming bubble is still typing, the first tap reveals it. A later tap
advances. Updating a plan with the same id preserves the last completed beat
when that identity still exists.

The playback adapter reports settled features once per plan. `GameStage`
deduplicates feature ids before queueing overlays.

## Feature overlays

Ceremonies and Daily Recaps sit above the scene because they are full feature
beats rather than persistent boards.

For a resolved turn, the planner queues supported ceremony events in engine
order, then appends only Daily Recaps added by that turn. A baseline plan never
replays recaps already present in loaded state.

Current feature event families include:

- Pairing Ceremony and partner changes;
- Heart Out;
- pair proposals;
- Paradise Suite;
- Flush of Hearts arrival, decision, and return;
- final vote.

The Daily Recap consumes the typed projection from the API. It renders “Your
day” and “While you were busy” separately and uses the recap's historical
resort label.

## Minigame composition

`MINIGAME_SCENE_PRESENTATION` implements
`MinigamePresentationPort<MinigamePresentation>`. It reads the typed pending
minigame view and the transition's legal actions, then delegates interpretation
to `presentMinigame`.

The resulting segment contains:

- a `minigame_board` camera beat;
- optional typed narration;
- a `choice_fan` beat for an active round;
- a compact board slot rendered by `MinigameInsert`.

The slot owns title, kicker, round label, progress, concise question, and the
per-kind board. Scene code owns camera, playback, cast, and action timing.

The six board renderers are exhaustive:

- Compatibility Quiz answer reveal;
- Pulse Race recorded readings;
- Couples Quiz answer alignment;
- Lie Detector recorded verdict and needle value;
- Kiss Wed Pass allocations;
- Final Couples facet scores and tally.

`available_actions` is the sole choice authority. An active round with no legal
`challenge_response` action fails closed. Board state cannot add or relabel a
choice.

The former large centered challenge card is not part of this architecture. It
blocked the cast and clipped on mobile. Compact inserts preserve the useful
board concept without restoring that layout.

## Browser data boundary

The stage reads only typed player-facing fields:

| Need | Source |
|---|---|
| Location and display label | `SessionState.location_id`, `location_label` |
| Cast and location membership | `SessionState.heartbreakers` |
| Player identity | `SessionState.player` |
| Conversation focus | `active_conversation_target_id` |
| Dialogue | `TurnResponse.exchange` |
| Event narration | `TurnResponse.event_narration` |
| Connection and Pulse feedback | `connection_shift`, `audience_delta` |
| Legal actions | `available_actions` |
| Minigame board | typed `pending_challenge` projection |
| Feature screens | `ceremony_events`, projected `daily_recaps` |

The stage does not read persisted engine state, raw memory weights, minigame
truth fields, or agent traces.

## Files and ownership

| Area | Files |
|---|---|
| Pure scene planning | `web/components/scene/SceneDirector.ts` |
| Scene contracts | `web/lib/scene/presentation.ts`, `web/lib/scene/types.ts` |
| Playback | `web/components/scene/useScenePlayback.ts` |
| Stage rendering | `web/components/scene/SceneDialogueStage.tsx` |
| Cast rendering | `web/components/scene/CharacterLayer.tsx` |
| Positions | `web/lib/scene/positions.ts` |
| Minigame interpretation | `web/lib/minigame/presentation.ts` |
| Minigame scene adapter | `web/lib/minigame/scene-port.ts` |
| Minigame boards | `web/components/minigame/` |
| Integration and features | `web/components/stage/GameStage.tsx` |

Do not move engine rules into these files. If the renderer needs a missing
truthful value, add it to the Python presentation projection and regenerate
OpenAPI types.

## Verification

The scene contract is protected by deterministic planner and playback tests.
Important invariants include:

- same transition, same plan;
- every action routed exactly once;
- pending action labels never become dialogue;
- pending and resolved plans share consumed stream identities;
- ceremony order is preserved;
- only newly added recaps are queued;
- baseline load suppresses historical recap playback;
- focused cast members stay staged when the cast overflows;
- minigames compose through the port without scene interpretation.

The minigame contract adds table-driven coverage for all six renderer kinds,
choice authority, fail-closed active rounds, and mismatched board kinds.

Run the relevant browser checks:

```bash
cd web
npm run type-check
npm run lint
npx playwright test tests/scene-presentation.spec.ts tests/e2e/minigame-presentation.spec.ts
```

The repository acceptance gate remains `make qa`.

## Extension rules

When adding a new scene beat:

1. extend the `SceneBeat` union;
2. give it a stable playback identity;
3. plan its frame behavior;
4. define tap or timer advancement;
5. add a planner and playback invariant test.

When changing minigame presentation:

1. change the Pydantic projection first;
2. regenerate OpenAPI types;
3. update the exhaustive browser interpreter and renderer;
4. keep legal choices in `available_actions`;
5. verify mobile and desktop layouts.

When adding a feature overlay, update the feature event allowlist and test its
order relative to existing ceremonies and Daily Recaps.
