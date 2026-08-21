# FastAPI Browser Contract

This document defines the current HTTP and SSE boundary between the Next.js
browser and the canonical Python game. FastAPI is a stateless adapter. It
hydrates the client-held persisted envelope, calls the same engine path as the
CLI and evals, then returns a typed player-facing view and the next persisted
envelope.

The adapter may translate structured identifiers into display labels. It does
not own gameplay rules, parse meaning from prose, or keep an independent copy
of game state.

## Runtime topology

```text
Next.js browser
  -> PersistedSession from local storage
  -> FastAPI request
  -> hydrate GameState and SeededRng
  -> run_turn(state, action, rng, TurnAgentSet)
  -> typed presentation projections
  -> view plus updated PersistedSession
```

The browser sends the complete `PersistedSession` on view, turn, and cast
requests. The current anonymous POC stores that envelope in browser local
storage. A future account store may replace local storage without changing the
engine boundary.

Development server:

```bash
uv run uvicorn src.api.app:app --reload --port 8000
```

The browser calls FastAPI directly on port 8000 in development. Production
routes `/api/*` to the FastAPI service and removes the `/api` prefix.

## Persisted session

`src/api/persisted.py` owns the storage envelope:

```python
class PersistedSession(BaseModel):
    schema_version: int
    session_id: str
    user_id: str | None
    rng_state: list[Any]
    game_state: dict[str, Any]
    mock_llm: bool
```

`hydrate` validates `game_state` as `GameState` and restores `SeededRng` from
its snapshot. `freeze` captures state and RNG together after a successful turn.
The engine snapshot schema is checked independently inside `game_state`.

## Endpoints

### Health and version

- `GET /healthz` reports process liveness.
- `GET /readyz` reports adapter readiness.
- `GET /version` returns engine schema, API version, and build identifier.

### Create a session

`POST /session/new` accepts:

```json
{
  "archetype": "heartthrob",
  "player_name": "You",
  "player_gender": "man",
  "seed": 42,
  "mock_llm": true
}
```

It creates the deterministic state, applies character creation, runs live
setup agents when real mode is selected, and returns `NewSessionEnvelope`:

```json
{
  "view": {
    "session_id": "...",
    "state": {},
    "available_actions": []
  },
  "persisted": {}
}
```

Setup-agent exhaustion returns `STORY_ENGINE_ERROR`; the adapter does not open
a partially generated live session.

### Load a checkpoint

- `GET /checkpoints` lists bundled and local checkpoints compatible with the
  current engine schema.
- `POST /session/from-checkpoint` accepts a checkpoint name and optional
  `mock_llm`, settles transient zero-action boundaries, assigns a fresh session
  id, and returns the same envelope shape as session creation.

Old-schema or missing checkpoints are not migrated. They are absent from the
loadable list or fail with a specific checkpoint error.

### Rebuild a view

`POST /session/view` accepts `PersistedSession` and returns `SessionResponse`.
It is the refresh and resume path. It does not mutate the envelope.

### Submit a turn

`POST /session/turn` accepts:

```json
{
  "persisted": {},
  "action": {
    "kind": "respond_with",
    "target_id": "chloe",
    "intent_id": "friendly_ask_feelings",
    "option_index": 0,
    "payload": {}
  }
}
```

The response is `TurnResponseEnvelope`: the complete typed turn view and the
new persisted envelope. `available_actions` comes from the engine after the
turn and is the only legal-action authority.

The endpoint creates an explicit mock or live `TurnAgentSet` from the envelope
mode. `run_turn` commits state and RNG atomically. Invalid actions return 400.
Exhausted live-agent contracts return 502 `STORY_ENGINE_ERROR`; state, RNG, and
the caller's persisted envelope remain unchanged.

### Stream a turn

`POST /session/turn/stream` accepts the same envelope and action. It emits SSE
events in this order when present:

1. `turn_start`
2. `dialogue_start`
3. one or more `dialogue_chunk` events
4. `dialogue_end`
5. `state`
6. `options`
7. `ceremony`
8. `response`
9. `turn_end`

The `response` event contains the authoritative `TurnResponseEnvelope`. The
browser saves its persisted value and returns its view to the stage. An error
event ends the stream without a response envelope. Story failures include
`code: "STORY_ENGINE_ERROR"`.

### Cast detail

`POST /session/cast` accepts `PersistedSession` and an NPC id. It returns the
display-safe cast detail for the hydrated state.

## Player-facing session state

`src/api/models.py` owns the response models. `src/api/serializers.py` is the
only engine-to-HTTP adapter. Important fields include:

- structured and display labels for phase, location, and resort;
- player, Heartbreaker, couple, audience, and resort snapshot views;
- the pending pair proposal;
- a typed pending minigame projection;
- projected Daily Recaps;
- the canonical list of legal actions.

### Pending minigame

`pending_challenge` is `MinigameRoundView | MinigameWrapView | null`. `status`
is the discriminator. Each view has an exhaustive `kind` and a matching typed
board payload.

An active round contains round index, count, concise question, narration,
target, answered-round reveals, and its board. A wrap contains classification,
points, audience delta, answered rounds, and its board. Neither shape contains
legal choices. The browser filters `available_actions` for
`challenge_response` and fails closed if an active round has none.

### Daily Recap

`daily_recaps` contains `DailyRecapView` values from
`src/game/presentation/daily_recap.py`. Each recap preserves its historical
resort label. Its items expose only:

- `section`: `your_day` or `while_busy`;
- `speaker_label`;
- second-person `content`;
- `emphasis`: `standard` or `strong`.

Raw memory tags, weights, and recap-disposition mechanics do not cross the
browser boundary.

## Generated TypeScript contract

FastAPI OpenAPI generates `web/lib/openapi-types.ts`. Browser-facing aliases in
`web/lib/types.ts` and `web/lib/minigame/types.ts` refer to those generated
schemas. They do not duplicate the Pydantic minigame or recap shapes by hand.

Regenerate after a response-model change:

```bash
cd web
npm run gen:types
```

Run FastAPI on port 8000 while generating. `make web-contracts` verifies the
checked-in boundary.

## Display translation

`src/api/display.py` translates structured identifiers such as `main`,
`flush_of_hearts`, `heart_throb`, and `pair` into player-facing labels. Free
prose is not rewritten by identifier maps or regex heuristics.

Second-person Daily Recap conversion belongs to its presentation projection,
not to the general display table.

## Agent modes

`PARADISE_MOCK_LLM=1` selects mock mode when a request does not provide an
explicit override. Automated browser checks use mock mode. Live mode uses the
complete live `TurnAgentSet`; it never degrades to mocks after a failed call.

Mock, recorded, and scripted output are explicit development and verification
modes. They are not runtime recovery paths.

## Error model

Non-streaming failures use the shared body:

```json
{
  "detail": {
    "error": {
      "code": "INVALID_ACTION",
      "message": "...",
      "details": {}
    }
  }
}
```

Current domain codes include:

- `VALIDATION_ERROR`
- `INVALID_ACTION`
- `CHECKPOINT_NOT_FOUND`
- `CHECKPOINT_CORRUPT`
- `STORY_ENGINE_ERROR`

Unexpected adapter failures remain server errors and are logged with request
context. The browser displays a recoverable turn error and keeps its last
confirmed persisted envelope.

## Contract verification

The boundary is protected by:

- API model and serializer tests;
- atomic turn and story-error tests;
- minigame and Daily Recap projection tests;
- generated OpenAPI contract checks;
- TypeScript type-check and lint;
- Playwright scene and minigame tests;
- deterministic scenario and checkpoint tests.

The full non-billed repository gate is `make qa`.
