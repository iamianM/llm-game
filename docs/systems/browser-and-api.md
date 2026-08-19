# Browser and API

The browser is a presentation client over the canonical Python game. It does
not calculate gameplay results or maintain a second version of game truth.

## Request Path

Next.js renders character creation, the resort scene, dialogue, choices,
minigames, ceremonies, and state feedback. Gameplay actions are posted to the
FastAPI adapter, which validates the request and calls the same application and
engine path used by the CLI and scenario runner.

```text
Next.js UI -> FastAPI request -> run_turn -> TurnResult -> API display model -> UI
```

SSE carries streamed turn events where progressive presentation is useful.
Zustand stores presentation concerns such as selected panels and animation
state, never canonical relationships, phase movement, or legal actions.

## Shared Action Vocabulary

`ActionKind` in `src/game/engine/actions.py` is canonical. The API exposes legal
actions derived from engine state; the browser renders those actions and sends
their typed identifiers back. A gameplay action must not exist only in React or
only in the CLI.

Focused Playwright action-contract tests protect this mapping. They are part of
`make qa` through `make web-contracts`.

## Display Boundary

The API translates internal state into a player-visible display model. Hidden
preferences, exact private NPC state, and other engine-only truth stay hidden.
The browser can explain visible relationship and audience consequences without
receiving authority to calculate them.

## Current Presentation

The browser uses a scene-based visual-novel stage. Player and NPC cutouts,
speaker-anchored dialogue, contextual choices, narration, and embedded challenge
spectacles render one engine result at a time. See
[`scene-dialogue.md`](scene-dialogue.md) for that presentation contract and
[`minigames.md`](minigames.md) for the shared challenge harness.

## Development

Run the API and browser separately:

```bash
uv run python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

```bash
cd web
npm run dev
```

The default local/browser mode uses deterministic mock agents. A real model is
opt-in and does not change engine ownership.

## Verification

```bash
make web-check
make web-contracts
```

Browser acceptance also requires manual inspection of the relevant desktop and
mobile scene when a change is visual. Static type checks and action contracts
cannot establish that dialogue, choices, or consequences are legible.
