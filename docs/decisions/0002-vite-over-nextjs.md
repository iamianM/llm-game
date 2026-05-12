# 0002 - Vite Over Next.js For The Browser Client

Date: 2026-05-11

## Context

Next.js made sense when API routes and the Vercel AI SDK were expected to own game logic and LLM calls. With a Python engine and FastAPI backend, the browser is a thin visual novel client that renders state, submits actions, and animates narration.

## Decision

Use Vite + React + TypeScript + Tailwind for the browser client.

## Consequences

- The browser app lives under `web/`.
- Zustand is allowed for UI state only: selected menus, panels, animation timing, optimistic UI, and local view preferences.
- Canonical game state is fetched from the Python backend and persisted by the engine.
- Server-side rendering, Next.js API routes, and the Vercel AI SDK are out of scope for the POC.
