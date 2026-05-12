# 0001 - Python Engine Over TypeScript API Routes

Date: 2026-05-11

## Context

The original technical plan centered on Next.js API routes and the Vercel AI SDK. After reviewing the reusable infrastructure in `C:\Users\Mcian\projects\steno-livekit-agent`, the stronger path is to reuse its architectural patterns: a deterministic runtime, Pydantic contracts, tool-gated LLM calls, traces, CLI-first development, and scenario testing.

This game also needs seeded replay, simulation runs, and engine tests that run without spending LLM tokens.

## Decision

Build the canonical game engine in Python.

The browser UI and CLI both call the same Python engine. The frontend is a client, not the owner of game mechanics.

## Consequences

- Game state, rules, RNG, action validation, NPC simulation, and persistence live in `src/game/`.
- The web app talks to Python through FastAPI.
- LLM calls use Python agent infrastructure, not the Vercel AI SDK.
- TypeScript remains useful in the browser client, but it does not own canonical game state.
- The existing design docs stay as design canon; implementation modules cite them in docstrings and tests.
