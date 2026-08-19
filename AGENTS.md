# Paradise Hearts — AI Assistant Guide

*Engineering entry point for a visual novel roguelite dating game powered by AI*

**IMPORTANT**: This is the authoritative implementation entry point. The root
`README.md` is a concise public product overview and must not duplicate or
override engineering canon.

---

## Project Overview

**Working Title**: "Paradise Hearts"

**Core Concept**: A visual novel roguelite dating sim that combines the structure of reality dating shows with procedurally generated narrative powered by a Large Language Model (LLM).

**The Innovation**: The LLM acts as a dynamic Game Master, generating unique contestants, dialogue, drama, and events for every playthrough. No two summers of love are ever the same.

**Current Phase**: Playable POC hardening - the deterministic Python engine, CLI, FastAPI adapter, and Next.js browser client exist and must stay in parity.

**Tech Stack**: See detailed breakdown below

---

## Tech Stack

**Philosophy**: Optimize for a playable, reproducible POC. The game is a deterministic social simulation first and an LLM-narrated visual novel second. The browser and CLI must use the same engine.

### Current Implementation Direction

The previous Vercel AI SDK plan has been superseded. The current browser implementation uses Next.js as a thin client while the Python engine remains canonical. See `docs/decisions/` for superseding ADRs when older ADRs disagree.

**Backend / Engine**: Python 3.11+
- Canonical game state, rules, seeded RNG, NPC simulation, action validation, phase progression, and persistence
- Pydantic v2 for every state, action, content, and agent contract
- FastAPI for HTTP and SSE
- JSON snapshots/traces for local saves and deterministic replay during the POC

**LLM Integration**: Python agents
- OpenAI Responses structured output behind typed Python agent wrappers
- Heartbreaker Voice, Contextual Options, Event Narrator, Conversation Curator, Resort Orchestrator, and Background Dialogue agents
- Prompts live under `src/game/agents/prompts/` and are user-owned per `ENGINEERING.md` R17
- The LLM never calculates success, relationship deltas, eliminations, votes, or phase movement

**Frontend**: Next.js + React + TypeScript
- Thin visual novel client that renders state and posts actions to FastAPI
- Tailwind CSS for styling
- Zustand only for UI state such as selected menus, animation timing, and local panel state
- Canonical game state lives in Python, not in the browser

**CLI**: Python argparse
- First-class development interface
- `play` for interactive local runs
- `verify-script` for deterministic seed/action script checks
- `play --replay` for recorded trace replay
- Debug/trace output should start as flags before becoming separate commands

**Testing**: pytest
- Pure engine tests with no LLM calls
- Scenario/golden-run tests using fixed seeds and action scripts
- Mock-LLM mode for most agent-adjacent tests
- Golden LLM evals through the production `run_turn` path, with optional live-agent and judge-assisted review packets

### Architecture

```
CLI or Browser
  -> FastAPI / direct Python call
  -> Game engine validates available actions
  -> Seeded RNG + deterministic rules calculate MechanicalResult
  -> Agent layer writes dialogue, event prose, options, and recorded resort commits
  -> Engine persists state and trace
  -> UI renders visible state, narration, and next actions
```

### Runtime Content Strategy

The current design docs are design canon, not runtime input. Runtime-loaded content should be small, structured markdown with frontmatter:

```
content/
  archetypes/   # narrator-relevant personality and casting flavor
  locations/    # prose mood + light metadata
  events/       # event beats only; mechanics stay in code
  challenges/   # challenge flavor only; scoring stays in code or typed balance data
```

Typed mechanical balance data is separate from runtime flavor content:

```
data/
  balance/      # deterministic tuning tables interpreted by Python engine code
```

Rule of thumb:

- Math, branching, state changes, and unlock logic live in Python engine code.
- Tunable mechanical tables may live in `data/balance/` only when they are Pydantic-validated and interpreted by engine code.
- Flavor, tone, display copy, and narrator snippets live in markdown.
- `content_lint` validates frontmatter references against engine enums and Pydantic models.

### What We're Not Using For The POC

- **Next.js API routes for gameplay** - The Python engine owns game logic; Next.js is UI-only.
- **Vercel AI SDK** - LLM calls live behind Python agents.
- **LiveKit** - Voice/realtime is a future layer, not core gameplay.
- **Game engines** - DOM-based visual novel UI is enough.
- **Complex database** - SQLite is enough for local saves and replay.
- **LLM-driven mechanics** - The LLM narrates resolved outcomes; code owns numbers.

### Current Implementation Snapshot

The repo is past the first playable milestone. The current POC has:

1. A deterministic Python engine with seeded RNG, typed state, action validation, phase clocks, couples, proposals, interruptions, private chats, Paradise Suite, Flush of Hearts, challenges, final vote, knowledge/fact state, background resort life, and review bookmarks.
2. A typed Python agent layer for Heartbreaker Voice, Contextual Options, Event Narrator, Conversation Curator, Resort Orchestrator, Background Dialogue, Contextual Gossip, and Trait Generator.
3. A CLI that supports interactive play, deterministic verification, persisted playtest sessions, checkpoints, trace replay, review notes, report packets, and golden LLM evals.
4. A FastAPI adapter and Next.js browser client that stay thin over the Python engine.
5. Static review packets for playthroughs and golden eval reports.
6. Mock, deterministic, and opt-in live LLM gates for different kinds of confidence.

Current active planning lives in [docs/current-plan.md](docs/current-plan.md). Finished systems should be documented as present-tense behavior in their owning system docs, not preserved as completed checklist items.

---

## Engineering And QA

Read [ENGINEERING.md](ENGINEERING.md) before making code changes. Those rules are non-negotiable and adapt the useful discipline from the steno runtime: no dead code, no legacy shims, no silent fallbacks, no workaround suppressions, no over-engineering, seeded RNG only, and strict engine/content/agent boundaries.

Read [docs/qa-strategy.md](docs/qa-strategy.md) before adding tests or declaring implementation work done.

### Self-QA Before Marking Done

Before an AI assistant says an implementation task is done, run:

```bash
make qa
```

`make qa` is the non-LLM gate:

1. `make lint`
2. `make type-check`
3. `make content-lint`
4. `make test`
5. `make smoke`
6. `make determinism`
7. `make llm-eval-mock` — golden scenarios through `run_turn` in mock mode (see [docs/llm-eval-system.md](docs/llm-eval-system.md))
8. `make web-check`
9. `make web-contracts`

If the gate cannot run, report the exact blocker. Do not replace the gate with "looks right."

Use `make test-llm` only for opt-in agent quality tests. LLM tests are excluded from the default QA gate.

Opt-in live agent checks (slow and billed) live behind:

- `make llm-eval-real` — golden scenarios with live OpenAI agents.
- `make llm-eval-real-judge` — adds the LLM judge for voice-fit / continuity / faithfulness.

Every feature that touches an agent boundary or a player-facing beat should ship with a scenario under `evals/llm/scenarios/` — see [docs/llm-eval-system.md](docs/llm-eval-system.md) and [evals/llm/scenarios/FORMAT.md](evals/llm/scenarios/FORMAT.md).

### CLI And Makefile Split

The CLI is the program surface. The Makefile is a shortcut layer.

- Real operations live under `uv run python -m src.game.cli ...`.
- Make targets wrap CLI commands or common test commands.
- Make targets should not duplicate business logic.
- AI assistants should prefer explicit CLI commands when debugging.

Current CLI surface:

```bash
uv run python -m src.game.cli play
uv run python -m src.game.cli play-session ...
uv run python -m src.game.cli review ...
uv run python -m src.game.cli verify-script --actions tests/scenarios/fixtures/day1-happy-path.yaml
uv run python -m src.game.cli play --replay .game_traces/<trace>.json
uv run python -m src.game.cli verify --all
uv run python -m src.game.cli verify --playthrough .game_traces/<trace>.json
uv run python -m src.game.cli snapshot inspect <file>
uv run python -m src.game.cli snapshot hash <file>
uv run python -m src.game.cli content lint
uv run python -m src.game.cli trace inspect <file>
uv run python -m src.game.cli report packet --trace .game_traces/<trace>.json --out review-packet
uv run python -m src.game.cli report compare --checkpoint <checkpoint> --trace-a <trace-a> --trace-b <trace-b> --out <html-path>
uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-mock
uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-real --real-llm --judge
```

### Action Vocabulary

`ActionKind` in `src/game/engine/actions.py` is the canonical action vocabulary. Browser buttons, CLI menu items, scenario YAML, traces, and tests must all use the same action kinds.

Adding an action starts in the engine, then flows to CLI/browser rendering and optional content flavor. Do not add browser-only or CLI-only gameplay actions.

### Snapshots, Scripts, And Traces

Snapshots and action scripts are first-class debugging tools:

- local saves live under `.game_saves/`
- local traces live under `.game_traces/`
- checked-in snapshot fixtures live under `fixtures/snapshots/`
- checked-in action scripts live under `tests/scenarios/fixtures/`

The CLI, browser, and tests must be able to start from the same snapshot and produce the same state hash after the same action script.

Current interactive CLI slash commands:

- `/state` prints the visible state.
- `/background` prints recent background resort activity.
- `/checkpoint <name>` saves a named checkpoint for branch testing.
- `/hash` prints the deterministic state hash.
- `/help` prints the available commands.
- `/quit` exits the session.

Checkpoint resume and branch comparison are CLI commands rather than in-session slash commands:

```bash
uv run python -m src.game.cli play --from-checkpoint <checkpoint> --branch-name <name>
uv run python -m src.game.cli play-session resume --name <name> --from-checkpoint <checkpoint>
uv run python -m src.game.cli report compare --checkpoint <checkpoint> --trace-a <trace-a> --trace-b <trace-b> --out <html-path>
```

---

## Documentation Philosophy

This repo follows a **high-context-efficiency** approach optimized for AI-assisted development.

### The Rules

**File Structure:**
- **README.md is the public front door; AGENTS.md is implementation canon**
- **One file = one complete system** - No fragmentation across multiple files
- **Design docs are canon; implementation rules live in ENGINEERING.md**
- **Runtime content is structured markdown; mechanics live in Python**
- **Each file should be 300-800 lines** - If smaller, it probably belongs in another file
- **Use ## headers heavily** - For AI navigation via `rg`

**When to Create a New File:**
- ✅ When a system is **fully designed** (not "we might do X or Y")
- ✅ When a section in AGENTS.md exceeds ~500 lines
- ✅ When a topic needs **independent iteration** (e.g., balance will change frequently)
- ✅ When an AI would need to reference it **independently** (e.g., "how do challenges work?")
- ✅ When it is implementation infrastructure named in an ADR or QA strategy

**File Naming Convention:**
- `01-Game-Vision.md` - Always first, the "why" and philosophy
- `02-Core-Mechanics.md` - The fundamental gameplay systems
- `03-XX.md` - Major systems in order of importance/dependency
- `docs/decisions/NNNN-title.md` - ADRs for implementation decisions
- `FORMAT.md` - Format notes inside fixture/content folders
- `INDEX.md` - Index files inside documentation folders

### Reference Model

This repo follows the same philosophy as the **Pachinko Pop** design vault:
- Clear system boundaries
- AI-optimized navigation
- Consolidation over fragmentation
- Template-driven extensibility

Location: `/home/azureuser/pachinko-pop-docs`

---

## Current Game Design

### Format Decision

**Top Contenders:**
1. **Paradise Hearts** (9/10) - Most dynamic, best roguelite structure
2. **The Bachelor** (9/10) - Clear weekly elimination structure
3. **Love Is Blind** (8/10) - Strong narrative depth, two-act structure

**Format Locked**: **Paradise Hearts** (reality-dating-show format)

**Why the Reality-Dating-Show Format Works Best:**
- Daily cycle creates tight roguelite loop
- Constantly shifting social landscape = high replayability
- Player has maximum agency (can swap partners, form alliances)
- Multiple relationship stats tracked simultaneously
- Clear failure states (being Heart Out)

**Future Question**: Unlockable alternate formats can be revisited after the primary Paradise Hearts loop is playable.

---

### Core Mechanics (Rough Draft)

#### Player Stats (Your "Heartbreaker Vibe")

**Charm** - Natural charisma and romantic appeal
- Influences first impressions
- Key for romantic moments

**Banter** - Wit and humor
- Crucial for group settings
- Wins certain challenges

**Spark** - Active pursuit and flirtation
- Core Paradise Hearts concept
- Unlocks forward dialogue options
- Determines how aggressively you pursue partners

**Loyalty** - Faithfulness and commitment
- Makes partners feel secure
- Low loyalty opens options with new Heart Throbs
- Constant tug-of-war mechanic

#### Relationship Stats (The "Resort Graph")

**Couple Strength** (0-100)
- Primary score with current partner
- Combines Affection + Trust
- Main defense against being "stolen"

**Chemistry** (0-100, per Heartbreaker)
- Latent attraction score with every other contestant
- High chemistry with non-partner = drama potential
- LLM uses this to generate flirtatious options

**Friendship** (0-100, per Heartbreaker)
- Critical for survival
- Friends give advice, defend you, might save you in votes

**Public Perception** (0-100)
- Simulated "audience" score
- Rises with loyalty, humor, genuine moments
- Falls with "cooled on" behavior
- Determines fate in public votes

---

### The Daily Loop (Core Gameplay)

Each day is a turn, consisting of 5 phases:

1. **Morning Chat** - Informal conversations, debrief drama, reinforce friendships
2. **Daily Challenge** - Stat-based mini-game (Banter, Charm, Spark, Physical)
3. **Afternoon Socializing** - Free time to make strategic moves
4. **"Paradise Calls!"** - AI Producer introduces dramatic event
5. **Evening Event** - Pairing Ceremony or elimination

**Run Length**: 6 in-game weeks maximum

**Objective**: End as a popular couple and win the final public vote

---

### The LLM System

#### The AI Producer

The LLM analyzes resort state and makes dramatic interventions:
- Introduces Heart Throbs when couples are too stable
- Forces dates between people who just argued
- Triggers Pairing Ceremonies at strategic moments
- Simulates "America's vote" based on player behavior

#### Dynamic Generation

**Procedural Heartbreakers** - Each run generates new contestants with:
- Personality archetype ("The Joker," "The Sweetheart," "The Alpha")
- Physical description
- Secret insecurity
- Personal "Type on Paper" (hidden preferences)

**AI Contestant Behavior** - Other Heartbreakers actively:
- Build their own relationship scores
- Form alliances
- Sabotage rivals with high animosity
- Make strategic pairing decisions

#### The Tagging & Scoring System

This is the bridge between LLM and game engine.

**How It Works:**

1. **LLM generates dialogue options with metadata tags**
   ```json
   {
     "option_text": "That's a beautiful dream. What made you fall in love with history?",
     "tags": ["Sincerity", "Engaged", "Listener", "Matches_Preference"]
   }
   ```

2. **Player selects an option**

3. **Game engine reads tags and calculates score**
   - `"Sincerity"` tag → Check player's Sincerity stat → Success
   - `"Engaged"` tag → Standard positive interaction → +3 Affection
   - `"Listener"` tag → High-value for trust → +2 Trust
   - `"Matches_Preference"` tag → Aligns with Heartbreaker's hidden type → +5 Affection (BONUS!)

4. **Result added to context for next LLM call**
   - LLM remembers this positive moment
   - Future dialogue references it

**Key Insight**: The LLM doesn't do math (it's bad at it). It provides qualitative analysis via tags, and the game engine does the numerical calculations.

---

### Mid-Run Enhancements

Temporary boons earned during a season:

**Producer's Notes** - Weekly random advantage (choose 1 of 3):
- **Gossip Tip-Off** - Learn someone's plan to sabotage you
- **The Date Rose** - Immunity for one week
- **Secret Advantage** - "Steal 5 minutes" token for cocktail party
- **Extra Time** - Bonus alone-time with the lead

**Challenge Rewards**:
- One-on-one dates
- Safety from elimination
- Advantages at Sunset Bay

---

### Meta-Progression (The Roguelite "Lite")

**When You're Eliminated**: Run ends, but you gain **Heart Beats**

**Earn Heart Beats Based On**:
- Days survived
- Pulse score
- Memorable moments created
- Drama generated

**Spend Heart Beats at "The Reunion Show"**:

**Casting Tapes** (Starting Archetypes):
- *The Heart Throb* - Start with +3 Charm
- *The Class Clown* - Start with +3 Banter, higher initial Pulse
- *The Loyal Friend* - Start with +3 Loyalty, stronger initial friendships

**Social Skills** (Permanent Perks):
- *Teflon* (300 Heart Beats) - 25% less damage from rumors
- *Expert Sparker* (400 Heart Beats) - Spark actions 50% more effective
- *Gossip Proof* (300 Heart Beats) - Rumors about you 25% less effective
- *Insider Info* (400 Heart Beats) - Learn one of lead's hidden "Type on Paper" traits
- *Challenge Beast* (500 Heart Beats) - Small bonus in all daily challenges

**Content Unlocks**:
- *The Paradise Suite* - Unlock private night with partner (huge Couple Strength boost)
- *Flush of Hearts* - Ultimate mid-game twist (Heartbreakers separated, new temptations)

---

## Implementation Roadmap

The active roadmap lives in [docs/current-plan.md](docs/current-plan.md). Keep `AGENTS.md` as the entry point and orientation layer, not the backlog.

### Build Order

1. Make the current playable loop easier to evaluate and improve from real play.
2. Keep CLI, FastAPI, browser, scenarios, traces, and review packets on the same engine path.
3. Build new gameplay only when it can be protected by deterministic tests, scenario fixtures, and, when agent behavior matters, golden LLM evals.
4. When a feature lands, update the owning system doc so it describes present behavior. Do not leave completed phase checklists as the main source of truth.

Historical build plans under `docs/build-plan-*.md` are useful implementation archaeology, but they are not the current roadmap. Use them for context, then check `docs/current-plan.md`, `ENGINEERING.md`, `docs/qa-strategy.md`, and the relevant system docs before changing code.

### Documentation Rules Going Forward

- `README.md` is the concise public product and portfolio landing page.
- `AGENTS.md` is the authoritative implementation entry point.
- `CLAUDE.md` is a pointer for compatibility only.
- Existing numbered design docs remain design canon unless a newer ADR, build log entry, or phase doc explicitly supersedes them.
- Implementation decisions live in `docs/decisions/`.
- Runtime markdown under `content/` carries flavor and light metadata, not mechanics.
- Contract-sensitive modules cite the design docs they implement in module docstrings or in `docs/contract-map.yaml`.

---

## AI Assistant Instructions

### Your Role

**Implement confirmed work decisively** - The implementation direction is set by the ADRs, `ENGINEERING.md`, and this file. When the user asks for a concrete change, make it and verify it.

**Keep scope tight** - Do not add features, agents, content, or abstractions beyond the current milestone.

**Git is user-owned** - Never commit, amend, push, force-push, branch, rebase, or reset unless the user explicitly asks. When the user does ask, keep commits small and logical, delete or ignore scratch artifacts first, run the relevant verification before committing, and push only after the repo is in a known-good state.

**Use the shared engine path** - CLI, tests, and browser routes must call the same engine functions.

---

### Implementation Workflow

1. Read `ENGINEERING.md`, relevant ADRs, and the module docstrings.
2. Make the smallest complete change that satisfies the request.
3. Add or update tests that protect the contract touched by the change.
4. Run `make qa`, or report the exact blocker.
5. Keep the worktree clean: do not leave review packets, throwaway screenshots, server logs, or temporary playtest transcripts untracked.
6. Summarize changed files and verification honestly.

---

### When User Asks to "Flesh Out X"

1. **Ask clarifying questions first**
   - What aspect are you most uncertain about?
   - What constraints do you have?
   - What's the priority?

2. **Present design options**
   - Show 2-3 different approaches
   - Explain pros/cons of each
   - Reference similar games/systems

3. **After decisions are made, ask:**
   - "Should this stay in AGENTS.md or become its own file?"
   - Only create a new file if:
     - System is complete and substantial (300+ lines)
     - Will be referenced independently
     - Won't change dramatically

---

### How to Help Grow This Repo

**Suggest File Creation When**:
- A section in AGENTS.md hits ~500 lines
- A system is fully designed and won't change
- The topic needs independent iteration
- The file is implementation infrastructure named in an ADR, QA strategy, or current milestone

**Keep in AGENTS.md When**:
- User is flip-flopping on design
- System is still in "rough draft" phase
- Content is < 300 lines
- It's an "Open Question"

**Use Pachinko Pop Repo as Reference**:
- Location: `/home/azureuser/pachinko-pop-docs`
- Similar structure and philosophy
- Good model for file organization
- But don't force the same structure—adapt to this game's needs

---

## Quick Reference

### Key Innovations

**1. LLM-as-Game-Master**
- Procedurally generates contestants with full personalities
- Acts as AI Producer creating drama
- Writes dynamic dialogue and events
- No two runs are ever the same

**2. Reality TV Roguelite Loop**
- Structured daily cycle (Morning → Challenge → Socializing → Drama → Event)
- Clear failure states (elimination = permadeath)
- Meta-progression (Heart Beats unlock permanent perks)
- High replayability through procedural generation

**3. Dynamic Social Graph**
- Track relationships with every Heartbreaker simultaneously
- AI contestants have their own strategies and goals
- Emergent drama from competing interests
- Player agency in pairing, alliances, rivalries

---

### Inspiration Games

**Monster Prom** - Roguelite dating sim structure
- Proves the run-based loop works for social games
- Stat-building and random events
- Multiplayer competitive dating

**Paradise Hearts The Game** - Format and structure
- Has the reality TV loop
- But not procedural or roguelite

**AI Dungeon** - LLM-powered narrative
- Pioneered LLM-as-game-master
- Shows potential for dynamic storytelling

**Hades** - Relationship meta-progression
- Demonstrates how relationship-building across runs creates attachment
- Slow-burn character development through repeated attempts

---

### Why This Combination Works

**Never Been Done**: No game combines:
1. Bachelor/reality-dating-show structure
2. Roguelite run-based gameplay
3. LLM-powered procedural narrative

**Each Component is Proven**:
- Reality-dating-show structure = proven entertainment format
- Roguelite dating sim = Monster Prom shows it works
- LLM narrative = AI Dungeon demonstrates the tech

**The "All-Star" Concept**: Takes the best of each and creates something new.

---

## Current Status

**Phase:** Playable POC hardening. The repo has a deterministic game engine, CLI, FastAPI adapter, browser client, review packets, and a golden LLM eval system. The current work is making the loop better through real play, stronger evals, and focused feature slices.

**Product direction:**
- **Genre:** Social sandbox with seasonal runs, not a punishing hardcore roguelite.
- **Format:** Paradise Hearts-style Sunset Bay structure.
- **Target run length:** 2-3 hours, roughly 15-20 key days once the full game is built.
- **Target audience:** Casual-friendly, drama-forward, emotionally legible, and low on opaque failure.
- **LLM role:** Personality, dialogue, narration, summaries, and authored-feeling texture. The LLM does not own mechanics.
- **Engine role:** State, RNG, action legality, relationship deltas, votes, eliminations, phase movement, and rewards.
- **Interaction model:** Static intent/action surface plus dynamic contextual follow-ups.
- **Information model:** The player sees the Sunset Bay map, relationship/audience signals, known facts, and memories; hidden truth remains engine-side.
- **Testing model:** Deterministic tests protect mechanics; golden LLM evals protect agent behavior and reviewability.

**Current documentation model:**

| Need | Read |
|------|------|
| Entry point and engineering posture | `AGENTS.md` |
| Non-negotiable rules | `ENGINEERING.md` |
| Active priorities and planning cycle | `docs/current-plan.md` |
| QA gates and trace strategy | `docs/qa-strategy.md` |
| LLM eval system | `docs/llm-eval-system.md` and `evals/llm/scenarios/FORMAT.md` |
| Design canon | `00-Game-Start-And-Setup.md` through `12-Challenges-And-Events.md`, plus `Love-Island-Reference.md` |
| Implementation decisions | `docs/decisions/` |
| Browser/API contract | `docs/phase3-fastapi-contract.md`, `docs/phase3-ui-spec.md`, `docs/phase3-acceptance-and-testing.md` |
| Historical build context | `docs/build-plan-*.md`, `docs/build-log.md`, and `docs/engine-issues-from-h11-review.md` |

---

## Finding Information

**High-level questions:**
- "What is this game?" - `AGENTS.md` (this file)
- "What are we working on now?" - `docs/current-plan.md`
- "How does Paradise Hearts actually work?" - `Love-Island-Reference.md`
- "Why the reality-dating-show format?" - `01-Game-Vision.md`
- "What's the tech stack?" - `AGENTS.md` ## Tech Stack
- "What engineering rules apply?" - `ENGINEERING.md`
- "What checks and tests matter?" - `docs/qa-strategy.md`
- "How do LLM evals work?" - `docs/llm-eval-system.md`
- "Why Python/Next.js/agent split?" - `docs/decisions/`

**System-specific questions:**

| Question | Read This | Key Section |
|----------|-----------|-------------|
| "How does the show work?" | Love-Island-Reference.md | ## The Rules of the Game |
| "What do fans love/hate?" | Love-Island-Reference.md | ## What Fans Love/Hate |
| "How does character creation work?" | 00-Game-Start-And-Setup.md | ## The Setup Flow |
| "What are the archetypes?" | 00-Game-Start-And-Setup.md | ## Archetype Selection |
| "How do I allocate stats?" | 00-Game-Start-And-Setup.md | ## Stat Allocation |
| "How do rerolls work?" | 00-Game-Start-And-Setup.md | ## The Reroll System |
| "What is meta-progression?" | 00-Game-Start-And-Setup.md | ## Meta-Progression |
| "How do stats work?" | 02-Core-Mechanics.md | ## Player Stats, ## Relationship Stats |
| "How does success calculation work?" | 02-Core-Mechanics.md | ## Interaction Success Formula |
| "How does the LLM work?" | 03-LLM-Architecture.md | ## The Multi-AI System |
| "When to use code vs LLM?" | 03-LLM-Architecture.md | ## Algorithm vs LLM Boundaries |
| "What are the data structures?" | 04-State-Management.md | ## Heartbreaker State, ## Resort State |
| "How do conversations work?" | 05-Interaction-System.md | ## The Interaction Flow |
| "What's the menu system?" | 05-Interaction-System.md | ## Hybrid Menu System |
| "How do contextual follow-ups work?" | 05-Interaction-System.md | ## Conversation Structure & Continuity |
| "When do conversations end?" | 05-Interaction-System.md | ## Organic Conversation Endings |
| "Does the LLM generate player dialogue?" | 05-Interaction-System.md | ## Single Exchange Generation |
| "How do locations work?" | 06-Location-System.md | ## Sunset Bay Locations |
| "What actions are available?" | 06-Location-System.md | ## Location-Specific Actions |
| "How does gossip work?" | 07-Gossip-And-Information.md | ## The Gossip System |
| "What can the player see?" | 07-Gossip-And-Information.md | ## Information Architecture |
| "What's the daily structure?" | 08-Daily-Loop.md | ## The Four Phases |
| "How long is a run?" | 08-Daily-Loop.md | ## Run Length and Pacing |
| "What are social events?" | 08-Daily-Loop.md | ## Social Events |
| "How do interruptions work?" | 09-Social-Dynamics.md | ## Conversation Interruptions |
| "What are group conversations?" | 09-Social-Dynamics.md | ## Group Conversations |
| "How does private chat work?" | 09-Social-Dynamics.md | ## The Private Chat System |
| "How does the Producer AI work?" | 10-Elimination-System.md | ## The Producer AI System |
| "What are the Pairing Ceremony rules?" | 10-Elimination-System.md | ## Pairing Ceremonies |
| "How do challenges work?" | 12-Challenges-And-Events.md | ## Challenge System |
| "What social events exist?" | 12-Challenges-And-Events.md | ## Social Events (Round-Table Sharing) |
| "When do Heart Throbs arrive?" | 10-Elimination-System.md | ## Heart Throb System |
| "How does Flush of Hearts work?" | 12-Challenges-And-Events.md | ## Flush of Hearts |
| "How do votes and eliminations work?" | 10-Elimination-System.md | ## Voting and Eliminations |
| "How does audience ranking work?" | 10-Elimination-System.md | ## Audience/Pulse System |

**Use `rg` to find specific topics:**
```bash
# Find all mentions of chemistry
rg -n "chemistry" *.md

# Find where relationship thresholds are defined
rg -n "threshold" 05-Interaction-System.md

# Find personality system details
rg -n "Big 5" 03-LLM-Architecture.md
```

---

*This is the main entry point for understanding and developing the Paradise Hearts LLM-powered social sandbox game. Use it for orientation, then use the owning system doc and `docs/current-plan.md` for current implementation work.*
