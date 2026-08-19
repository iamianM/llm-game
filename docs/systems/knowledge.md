# Knowledge and Memory

Paradise Hearts distinguishes canonical facts from what each participant knows.
That separation lets gossip, quizzes, dialogue continuity, and misunderstandings
use the same deterministic substrate without exposing hidden truth to the
player or delegating memory to an LLM.

## Canonical Truth and Belief

The engine owns event facts and participant knowledge. A fact can describe a
choice, statement, relationship beat, challenge answer, or resort event. Its
visibility and subject determine who can know it. Agents receive a bounded,
typed view of relevant facts and memories; they do not query arbitrary history
or invent mechanical truth.

## How Knowledge Enters the Game

- Deterministic actions and events emit canonical facts.
- Conversation curation records durable memories from completed exchanges.
- Background resort commits add off-screen social events through a typed agent
  boundary and deterministic engine application.
- Gossip reveals or transfers eligible information according to engine rules.
- Minigames read the shared question bank and event history rather than keeping
  a separate trivia state.

## Player Visibility

The player sees known facts, surfaced memories, relationship signals, and
appropriate gossip. Hidden preferences and private knowledge remain engine-side
until a deterministic reveal makes them visible. Reports and traces may expose
more diagnostic detail than the player UI; that is a review surface, not the
game's information model.

## Agent Boundary

Agents may summarize, phrase, or select from the context the engine provides.
They may not create a relationship change, retroactively alter a fact, or decide
who learned something. Typed commits make any requested addition inspectable
before the engine accepts it.

## Current Consumers

Current-run knowledge supports conversation continuity, contextual options,
gossip, background dialogue, preference reveals, social events, and all six
minigames. Cross-run memory is intentionally deferred until meta-progression has
a clear player contract.
