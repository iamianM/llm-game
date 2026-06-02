# Phase 3 — FastAPI Contract

The HTTP and SSE contract between the Next.js frontend and the Python engine.
The FastAPI server is a *thin adapter*. It does no game logic — every request
calls into existing `src/game/` modules and serializes their output.

**One of its key responsibilities** is translating structured engine identifiers
(`heart_throb`, `flush_of_hearts`, `pair`, `opening`, etc.) into Paradise Hearts
display strings (Heart Throb, Flush of Hearts, Heart Swap, First Spark, etc.)
before sending to the frontend. It must not rewrite free-text prose with
keyword or regex replacement. See `paradise-hearts-glossary.md` for the full
vocabulary and the "Naming reconciliation" section below for the identifier
display table.

**Target:** ~200 lines for `src/api/app.py`, plus Pydantic models in
`src/api/models.py`, plus ~80 lines in `src/api/display.py` for the
translation helpers.

## Server lifecycle

- Dev: `uv run uvicorn src.api.app:app --reload --port 8000`
- Prod: same uvicorn invocation, no `--reload`, behind a reverse proxy
- CORS: allow `http://localhost:3000` in dev; tighten for prod via env
- In-memory session storage: `SESSIONS: dict[str, GameSession]` keyed by UUID
  - `GameSession` holds `GameState`, `Rng`, the agent instances, and a lock
  - LRU eviction at 32 concurrent sessions (MVP — way over MVP capacity)
- LLM mode: env var `PARADISE_MOCK_LLM=1` swaps real agents for mock voices
  (fast/free dev iteration)

## Endpoints

### `POST /session/new`

Creates a new game session.

**Request:**
```json
{
  "archetype": "heartthrob",
  "player_name": "You",
  "player_gender": "man",
  "seed": null
}
```

- `archetype`: one of `"heartthrob" | "class_clown" | "loyal_friend"`
- `player_name`: optional display name; default "You"
- `player_gender`: `"man" | "woman"` (extend later)
- `seed`: optional int; null → server-generated

**Response (201):**
```json
{
  "session_id": "8c2a1d3f-...",
  "state": { ... full SessionState ... },
  "available_actions": [ ... ]
}
```

**Errors:**
- 400 invalid archetype
- 500 engine init failure

### `GET /session/{session_id}`

Snapshot of current state. Used by the frontend on initial mount and on
resume after refresh.

**Response (200):**
```json
{
  "session_id": "8c2a1d3f-...",
  "state": { ... full SessionState ... },
  "available_actions": [ ... ]
}
```

**Errors:**
- 404 session not found

### `POST /session/{session_id}/turn`

Submit a player action. Non-streaming version (used by the UI's
optimistic-locking flow before SSE wiring lands).

**Request:**
```json
{
  "kind": "respond_with",
  "target_id": "chloe",
  "intent_id": "friendly_ask_feelings",
  "option_index": 0,
  "payload": {}
}
```

**Response (200):**
```json
{
  "state": { ... updated SessionState ... },
  "exchange": { ... dialogue ... } | null,
  "available_actions": [ ... ],
  "ceremony_events": [ ... ] | [],
  "audience_delta": -2 | 0 | 3 | null,
  "audience_delta_reason": "they didn't love the gossip" | null,
  "memories_formed": [ ... ] | [],
  "background_activity": [ ... ] | []
}
```

**Errors:**
- 400 invalid action for state
- 404 session not found

### `POST /session/{session_id}/turn/stream`

Submit a player action, get SSE stream back. This is the streamed-typewriter
variant.

**Request:** same as `/turn`.

**Response (200, `text/event-stream`):**

Events emitted in order:

```
event: turn_start
data: {"turn": 8, "phase": "afternoon", "location": "pool"}

event: dialogue_start
data: {"speaker": "chloe", "speaker_name": "Chloe", "mood_before": "playful"}

event: dialogue_chunk
data: {"text": "*smiles* That actu"}

event: dialogue_chunk
data: {"text": "ally feels good "}

event: dialogue_chunk
data: {"text": "coming from you."}

event: dialogue_end
data: {
  "mood_after": "warm",
  "audience_delta": 2,
  "audience_delta_reason": "you stayed loyal",
  "relationship_deltas": {"chloe": {"affection": 3, "trust": 1}}
}

event: state
data: { ... full updated SessionState ... }

event: options
data: { "actions": [ ... ] }

event: ceremony
data: { "kind": "pair_proposal", "narration": "...", "couples": [...] }
// only when a ceremony fires this turn

event: resort_update
data: { "interruptions": [...], "background_starts": [...], ... }
// only when there is background activity

event: turn_end
data: { "state_hash": "abc123" }
```

**SSE format:** each event is `event: <name>\n` + `data: <json>\n\n`. UTF-8.
`id: <int>` for `Last-Event-ID` resume support (Phase 4).

**Errors:** SSE channel emits an `event: error` then closes:
```
event: error
data: {"status": 400, "message": "invalid action for state"}
```

### `GET /session/{session_id}/cast/{npc_id}`

Full popout detail for one NPC. Lazy-loaded when the player opens a cast tile.

**Response (200):**
```json
{
  "id": "chloe",
  "name": "Chloe",
  "gender": "woman",
  "archetype": "sweetheart",
  "mood": "content",
  "location": "flame_deck",
  "backstory": "Twenty-six, primary school teacher from Liverpool. ...",
  "familiarity": 41,
  "relationship": {
    "affection": 43,
    "chemistry": 6,
    "trust": 53,
    "friendship": 7
  },
  "type_on_paper": {
    "physical_type": "warm smiles and kind eyes",
    "personality_type": null,    // gated by familiarity threshold
    "values": null,
    "dealbreakers": null
  },
  "memories": [
    {"subject_id": "marcus", "content": "...", "weight": 5, "source": "direct"},
    ...
  ],
  "coupled_with": "player",
  "eliminated": false
}
```

### `GET /session/{session_id}/couples`

Full couples list with strength scores. Used by the right-rail panel.

**Response (200):**
```json
{
  "couples": [
    {
      "partner_a_id": "player",
      "partner_b_id": "chloe",
      "formed_on_day": 1,
      "formed_via": "opening",
      "strength": 67,
      "rebound": false
    },
    ...
  ],
  "singles": ["jordan_start"]
}
```

### `GET /session/{session_id}/timeline`

Day-by-day timeline of significant events. Used to build the day-recap modals.

**Response (200):**
```json
{
  "days": [
    {
      "day": 1,
      "events": [
        {"kind": "ceremony", "name": "First Spark", "turn": 1, "summary": "..."},
        {"kind": "intros", "summary": "You met 7 Heartbreakers"},
        ...
      ],
      "pulse_board": [
        {"rank": 1, "couple": ["player", "chloe"], "score": 71}
      ],
      "recap_lines": [
        "Maya and Jordan spent the morning by the pool...",
        ...
      ]
    },
    ...
  ]
}
```

### `DELETE /session/{session_id}`

Ends a session. UI calls this when player quits to title.

**Response (204):** no content.

### `GET /healthz` and `GET /readyz`

Standard liveness/readiness probes. `/readyz` checks LLM connectivity if
`PARADISE_MOCK_LLM` is unset.

## Data shapes

Defined as Pydantic models in `src/api/models.py`. The autogenerated
TypeScript types in `web/lib/types.ts` come from FastAPI's `/openapi.json`.

### `SessionState`

```python
class SessionState(BaseModel):
    session_id: str
    schema_version: int
    seed: int
    day: int
    phase: str           # "morning" | "challenge" | "afternoon" | "text" | "evening" | "intros"
    turn_index: int
    location_id: str     # "pool" | "kitchen" | ... | "flush_pool" | ...
    player: PlayerState
    heartbreakers: list[HeartbreakerSummary]      # everyone at a glance
    couples: list[CoupleSummary]
    audience: AudienceState
    pending_pair_proposal: ProposalState | None
    resort: str           # "main" | "flush_of_hearts"  ← engine-side names
    phase_clock: PhaseClock
    outcome: str | None
```

### `HeartbreakerSummary`

```python
class HeartbreakerSummary(BaseModel):
    id: str
    name: str
    gender: str
    archetype: str
    mood: str
    location_id: str
    eliminated: bool
    coupled: bool
    familiarity_with_player: int
```

### `CoupleSummary`

```python
class CoupleSummary(BaseModel):
    partner_a_id: str
    partner_b_id: str
    strength: int
    formed_on_day: int
    formed_via: str
    rebound: bool
```

### `AvailableAction`

```python
class AvailableAction(BaseModel):
    kind: str
    label: str
    target_id: str | None
    intent_id: str | None
    option_index: int | None
    audience_hint: str           # "+" | "-" | ""
    risk: str | None             # "low" | "med" | "high"
    stat_used: str | None
    description: str | None      # optional flavor for popovers
```

### `Exchange`

```python
class Exchange(BaseModel):
    speaker_id: str
    speaker_name: str
    player_dialogue: str
    npc_dialogue: str
    npc_tone: str
    npc_mood_after: str
```

### `AudienceState`

The wire field name stays `public_perception` (engine internal); the UI
labels it **Pulse** in display strings.

```python
class AudienceState(BaseModel):
    public_perception: int    # 0–100 (UI label: "Pulse")
    recent_delta: int | None  # last turn's change, if any
    trend: str                # "rising" | "falling" | "steady"
```

### `Memory`

```python
class Memory(BaseModel):
    holder_id: str
    subject_id: str
    content: str
    emotional_weight: int
    source: str   # "direct" | "witnessed" | "rumor"
    tags: list[str]
    formed_on_turn: int
```

## Naming reconciliation: engine vs. UI

The engine uses structured identifiers (`heart_throb`, `flush_of_hearts`,
`pair`, `opening`, etc.). The UI displays Paradise Hearts terms. The FastAPI
server is responsible for the **display translation**, so the frontend always
sees the correct Paradise Hearts strings. See `src/api/display.py` for the
authoritative implementation.

```python
DISPLAY_NAMES = {
    # Locations and resort state
    "main": "Sunset Bay",                          # resort == "main"
    "flush_of_hearts": "Flush of Hearts",          # resort == "flush_of_hearts"

    # Ceremony event kinds
    "heart_throb": "Heart Throb",
    "pair": "Heart Swap",                          # action kind
    "pairing": "Pairing Ceremony",                 # event kind
    "flush_of_hearts_announce": "Flush of Hearts Announcement",
    "flush_of_hearts_arrival": "Flush of Hearts Arrival",
    "flush_of_hearts_decision": "Flush of Hearts Decision",
    "flush_of_hearts_return_reveal": "Sunset Bay Return",
    "pair_proposal": "Heart Swap Proposal",
    "final_vote": "Finale",

    # Couple formed_via values
    "opening": "First Spark",
    "ceremony": "Pairing Ceremony",
    "proposal": "Heart Swap Proposal",
    "flush_return": "Sunset Bay Return",

    # Status transitions
    "private_suite": "Paradise Suite",
    "elimination": "Heart Out",

    # Phases
    "intros": "Arrivals",
    "morning": "Morning",
    "challenge": "Challenge",
    "afternoon": "Afternoon",
    "text": "Paradise Calls",                  # the "text" phase IS the Paradise Calls beat
    "evening": "Evening",

    # Cast role
    "heartbreaker": "Heartbreaker",

    # Audience
    "public_perception": "Pulse",
    "audience_appeal": "Heart Beats",          # earned currency (Phase 4)
    "audience": "The Audience",

    # Challenges
    "challenges": {
        "compatibility_quiz": "Compatibility Quiz",
        "heart_rate": "Pulse Race",
        "couples_quiz": "The Couples Quiz",
        "kiss_wed_pass": "Kiss Wed Pass",
        "lie_detector": "Lie Detector",
        "final_couples": "Final Couples Challenge",
    },
}
```

`src/api/display.py` (small module) holds the structured identifier display
table and helpers. The frontend code uses the display strings directly; the
engine code stays unchanged until the post-Phase-3 rename PR. Full vocabulary
reference is in `docs/paradise-hearts-glossary.md`; display identifiers here
MUST match it.

## Session storage

In-memory only for MVP:

```python
@dataclass
class GameSession:
    session_id: str
    state: GameState
    rng: SeededRng
    agents: AgentBundle          # one set of agent instances per session
    records: list[dict]          # trace records for the run
    created_at: datetime
    last_accessed: datetime
    lock: asyncio.Lock           # per-session lock — prevent concurrent turns
```

Session lock prevents two browser tabs from racing on the same session.
Eviction policy: 32 concurrent sessions max, LRU evict. Logged as a warning
if eviction happens.

## Mock LLM mode

Set `PARADISE_MOCK_LLM=1` in the FastAPI env to swap real agents for the
existing mock voices in `src/game/agents/mock_*.py`. Useful for:

- Dev iteration without LLM cost
- Playwright tests (deterministic dialogue)
- Codex's screenshot smoke pass
- Fast checkpoint resume validation

Mock mode is the default for all automated tests. Real-LLM is only used in
manual interactive verification (codex's playthroughs in step 14) and in
the final milestone validation.

## Streaming implementation notes

For step 6 (SSE), use FastAPI's `StreamingResponse`:

```python
@app.post("/session/{session_id}/turn/stream")
async def turn_stream(session_id: str, req: TurnRequest):
    session = get_session(session_id)
    async def event_stream():
        async with session.lock:
            async for event in run_turn_streaming(session, req):
                yield format_sse(event)
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

`run_turn_streaming` wraps the existing `run_turn` but yields events as the
LLM responds. The Heartbreaker Voice agent already supports streaming via the
OpenAI streaming API; FastAPI just needs to forward chunks.

For mock LLM, emit chunks with a small sleep between them so the typewriter
still has something to animate during dev iteration.

## Error model

All non-2xx responses share a body shape:

```json
{
  "error": {
    "code": "INVALID_ACTION",
    "message": "Action 'propose_pair' is not available in current state",
    "details": {"state_phase": "intros"}
  }
}
```

Codes:
- `SESSION_NOT_FOUND` (404)
- `INVALID_ACTION` (400)
- `VALIDATION_ERROR` (400) — Pydantic schema mismatch
- `ENGINE_ERROR` (500) — caught engine exception
- `LLM_ERROR` (502) — upstream LLM call failed
- `SESSION_LOCKED` (409) — concurrent turn attempt

## Versioning

`GET /version` returns:

```json
{
  "schema_version": 24,
  "api_version": "0.1.0",
  "build": "2026-05-14"
}
```

UI checks `schema_version` on session resume; if mismatch, force restart.

## Out of scope (Phase 4+)

- Authentication / API keys
- Persistent storage (sessions live only in memory)
- Multiplayer / multiple-session-per-user
- Rate limiting
- Webhook callbacks
- WebSocket (SSE is enough)
