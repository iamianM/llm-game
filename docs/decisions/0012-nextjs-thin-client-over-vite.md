# 0012. Next.js Thin Client Over Vite

## Status

Accepted. Supersedes `0002-vite-over-nextjs.md`.

## Context

The early implementation plan chose Vite to keep the browser layer minimal after the Python engine became canonical. The project has since shipped a Next.js client under `web/` and a FastAPI adapter under `src/api/`, with Vercel configuration for both services.

## Decision

Use Next.js as the browser shell for the POC. Next.js remains UI-only: it renders state, owns client-side UX concerns, and posts actions to FastAPI. Gameplay state, action validation, deterministic rules, replay, and LLM agent orchestration remain in Python.

Do not add Next.js API routes for gameplay logic. If deployment needs a platform adapter, it must call the same FastAPI/Python engine surface used by CLI and tests.

## Consequences

- `web/` is the canonical browser client.
- Browser checks should use the existing Next.js scripts.
- Older docs that say Vite is current are stale unless they are discussing historical context.
- Engine/API/browser parity remains the invariant; framework choice does not move game logic into TypeScript.
