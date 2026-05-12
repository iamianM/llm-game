# LLM-Powered Love Island Roguelite - AI Assistant Guide

*Documentation entry point for a visual novel roguelite dating game powered by AI*

**IMPORTANT**: This is the ONLY entry point file. Never create a README.md file.

---

## 🎯 Project Overview

**Working Title**: "Isle of Echoes" (or TBD)

**Core Concept**: A visual novel roguelite dating sim that combines the structure of reality TV shows like *Love Island* with procedurally generated narrative powered by a Large Language Model (LLM).

**The Innovation**: The LLM acts as a dynamic Game Master, generating unique contestants, dialogue, drama, and events for every playthrough. No two "summers of love" are ever the same.

**Current Phase**: Implementation planning and scaffolding - build the deterministic Python CLI loop first

**Tech Stack**: See detailed breakdown below

---

## Tech Stack

**Philosophy**: Optimize for a playable, reproducible POC. The game is a deterministic social simulation first and an LLM-narrated visual novel second. The browser and CLI must use the same engine.

### Current Implementation Direction

The previous Next.js/Vercel AI SDK plan has been superseded. See `docs/decisions/` for the reasoning behind the current direction.

**Backend / Engine**: Python 3.11+
- Canonical game state, rules, seeded RNG, NPC simulation, action validation, phase progression, and persistence
- Pydantic v2 for every state, action, content, and agent contract
- FastAPI for HTTP once the CLI loop works
- SQLite for local saves and deterministic replay

**LLM Integration**: Python agents
- `openai-agents` style tool-gated calls, following the useful patterns from `C:\Users\Mcian\projects\steno-livekit-agent`
- One v0 Narrator agent: `MechanicalResult + visible context -> narration`
- No Director, Producer, or Curator agent until the deterministic loop is playable
- The LLM never calculates success, relationship deltas, eliminations, votes, or phase movement

**Frontend**: Vite + React + TypeScript
- Thin visual novel client that renders state and posts actions to FastAPI
- Tailwind CSS for styling
- Zustand only for UI state such as selected menus, animation timing, and local panel state
- Canonical game state lives in Python, not in the browser

**CLI**: Python argparse
- First-class development interface
- `play` for interactive local runs
- `replay` for deterministic seed/action replays
- Debug/trace output should start as flags before becoming separate commands

**Testing**: pytest
- Pure engine tests with no LLM calls
- Scenario/golden-run tests using fixed seeds and action scripts
- Mock-LLM mode for most agent-adjacent tests
- Later: judge-based narration quality tests

### Architecture

```
CLI or Browser
  -> FastAPI / direct Python call
  -> Game engine validates available actions
  -> Seeded RNG + deterministic rules calculate MechanicalResult
  -> Narrator agent writes prose from the resolved result
  -> Engine persists state and trace
  -> UI renders visible state, narration, and next actions
```

### Runtime Content Strategy

The current design docs are design canon, not runtime input. Runtime-loaded content should be small, structured markdown with frontmatter:

```
content/
  archetypes/   # narrator-relevant personality and casting flavor
  locations/    # prose mood + light metadata
  actions/      # optional prose flavor only; mechanics stay in code
  events/       # event beats only; mechanics stay in code
  challenges/   # challenge flavor only; scoring stays in code
```

Rule of thumb:

- Math, branching, state changes, and unlock logic live in Python.
- Flavor, tone, display copy, and narrator snippets live in markdown.
- `content_lint` validates frontmatter references against engine enums and Pydantic models.

### What We're Not Using For The POC

- **Next.js API routes** - The Python engine owns game logic.
- **Vercel AI SDK** - LLM calls live behind Python agents.
- **LiveKit** - Voice/realtime is a future layer, not core gameplay.
- **Game engines** - DOM-based visual novel UI is enough.
- **Complex database** - SQLite is enough for local saves and replay.
- **LLM-driven mechanics** - The LLM narrates resolved outcomes; code owns numbers.

### First Playable Milestone

1. `GameState`, seeded RNG, one location, three NPCs
2. `available_actions()` returns a small set of actions
3. `apply_action()` returns deterministic `MechanicalResult`
4. CLI plays through one day and can replay from seed
5. Narrator agent converts `MechanicalResult` to prose
6. FastAPI and Vite UI call the same engine

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

`make smoke` and `make determinism` are intentionally outside `make qa` until Phase A creates real replay fixtures and expected hashes. Add them back to `qa` once they verify real behavior.

If the gate cannot run, report the exact blocker. Do not replace the gate with "looks right."

Use `make test-llm` only for opt-in Narrator quality tests. LLM tests are excluded from the default QA gate and must remain cost-capped.

### CLI And Makefile Split

The CLI is the program surface. The Makefile is a shortcut layer.

- Real operations live under `python -m src.game.cli ...`.
- Make targets wrap CLI commands or common test commands.
- Make targets should not duplicate business logic.
- AI assistants should prefer explicit CLI commands when debugging.

Current planned CLI surface:

```bash
python -m src.game.cli play
python -m src.game.cli replay
python -m src.game.cli verify --all
python -m src.game.cli snapshot inspect <file>
python -m src.game.cli snapshot hash <file>
python -m src.game.cli content lint
python -m src.game.cli scenario run <file>
python -m src.game.cli trace inspect <file>
python -m src.game.cli simulate --seeds 1000
python -m src.game.cli codegen --out web/src/types/generated.ts
```

### Action Vocabulary

`ActionKind` in `src/game/engine/actions.py` is the canonical action vocabulary. Browser buttons, CLI menu items, scenario YAML, traces, and tests must all use the same action kinds.

Adding an action starts in the engine, then flows to CLI/browser rendering and optional content flavor. Do not add browser-only or CLI-only gameplay actions.

### Snapshots, Scripts, And Traces

Snapshots and action scripts are first-class debugging tools:

- local saves live under `.game_saves/`
- local traces live under `.game_traces/`
- checked-in snapshot fixtures live under `fixtures/snapshots/`
- checked-in action scripts live under `scripts/fixtures/`

The CLI, browser, and tests must be able to start from the same snapshot and produce the same state hash after the same action script.

Planned in-session debug commands for CLI and browser dev mode:

- `/save <name>`
- `/load <name>`
- `/record <name>`
- `/stop`
- `/state`
- `/state --debug`
- `/trace`
- `/hash`
- `/help`

---

## 📚 Documentation Philosophy

This repo follows a **high-context-efficiency** approach optimized for AI-assisted development.

### The Rules

**File Structure:**
- **AGENTS.md is the ONLY entry point** - Never create README.md
- **One file = one complete system** - No fragmentation across multiple files
- **Design docs are canon; implementation rules live in ENGINEERING.md**
- **Runtime content is structured markdown; mechanics live in Python**
- **Each file should be 300-800 lines** - If smaller, it probably belongs in another file
- **Use ## headers heavily** - For AI navigation via grep

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

## 🎮 Current Game Design

### Format Decision

**Top Contenders:**
1. **Love Island** (9/10) - Most dynamic, best roguelite structure
2. **The Bachelor** (9/10) - Clear weekly elimination structure
3. **Love Is Blind** (8/10) - Strong narrative depth, two-act structure

**Format Locked**: **Love Island**

**Why Love Island Works Best:**
- Daily cycle creates tight roguelite loop
- Constantly shifting social landscape = high replayability
- Player has maximum agency (can switch partners, form alliances)
- Multiple relationship stats tracked simultaneously
- Clear failure states (being "dumped from the island")

**Future Question**: Unlockable alternate formats can be revisited after the primary Love Island loop is playable.

---

### Core Mechanics (Rough Draft)

#### Player Stats (Your "Islander Vibe")

**Charm** - Natural charisma and romantic appeal
- Influences first impressions
- Key for romantic moments

**Banter** - Wit and humor
- Crucial for group settings
- Wins certain challenges

**Graft** - Active pursuit and flirtation
- Core *Love Island* concept
- Unlocks forward dialogue options
- Determines how aggressively you pursue partners

**Loyalty** - Faithfulness and commitment
- Makes partners feel secure
- Low loyalty opens options with new bombshells
- Constant tug-of-war mechanic

#### Relationship Stats (The "Villa Graph")

**Couple Strength** (0-100)
- Primary score with current partner
- Combines Affection + Trust
- Main defense against being "stolen"

**Chemistry** (0-100, per Islander)
- Latent attraction score with every other contestant
- High chemistry with non-partner = drama potential
- LLM uses this to generate flirtatious options

**Friendship** (0-100, per Islander)
- Critical for survival
- Friends give advice, defend you, might save you in votes

**Public Perception** (0-100)
- Simulated "audience" score
- Rises with loyalty, humor, genuine moments
- Falls with "snakey" behavior
- Determines fate in public votes

---

### The Daily Loop (Core Gameplay)

Each day is a turn, consisting of 5 phases:

1. **Morning Chat** - Informal conversations, debrief drama, reinforce friendships
2. **Daily Challenge** - Stat-based mini-game (Banter, Charm, Graft, Physical)
3. **Afternoon Socializing** - Free time to make strategic moves
4. **"I'VE GOT A TEXT!"** - AI Producer introduces dramatic event
5. **Evening Event** - Recoupling or elimination ceremony

**Run Length**: 6 in-game weeks maximum

**Objective**: End as a popular couple and win the final public vote

---

### The LLM System

#### The AI Producer

The LLM analyzes villa state and makes dramatic interventions:
- Introduces bombshells when couples are too stable
- Forces dates between people who just argued
- Triggers recouplings at strategic moments
- Simulates "America's vote" based on player behavior

#### Dynamic Generation

**Procedural Islanders** - Each run generates new contestants with:
- Personality archetype ("The Joker," "The Sweetheart," "The Alpha")
- Physical description
- Secret insecurity
- Personal "Type on Paper" (hidden preferences)

**AI Contestant Behavior** - Other Islanders actively:
- Build their own relationship scores
- Form alliances
- Sabotage rivals with high animosity
- Make strategic coupling decisions

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
   - `"Matches_Preference"` tag → Aligns with Islander's hidden type → +5 Affection (BONUS!)

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
- Advantages in the villa

---

### Meta-Progression (The Roguelite "Lite")

**When You're Eliminated**: Run ends, but you gain **Audience Appeal (AP)**

**Earn AP Based On**:
- Days survived
- Public Perception score
- Memorable moments created
- Drama generated

**Spend AP at "The Reunion Show"**:

**Casting Tapes** (Starting Archetypes):
- *The Heartthrob* - Start with +3 Charm
- *The Class Clown* - Start with +3 Banter, higher initial Public Perception
- *The Loyal Friend* - Start with +3 Loyalty, stronger initial friendships

**Social Skills** (Permanent Perks):
- *Teflon* (300 AP) - 25% less damage from rumors
- *Expert Grafter* (400 AP) - Graft actions 50% more effective
- *Gossip Proof* (300 AP) - Rumors about you 25% less effective
- *Insider Info* (400 AP) - Learn one of lead's hidden "Type on Paper" traits
- *Challenge Beast* (500 AP) - Small bonus in all daily challenges

**Content Unlocks**:
- *The Hideaway* - Unlock private night with partner (huge Couple Strength boost)
- *Casa Amor* - Ultimate mid-game twist (boys/girls separated, new temptations)

---

## 🗺️ Implementation Roadmap

The design vault is no longer in concept-solidification mode. The current priority is a tiny, deterministic, replayable CLI loop before any large content authoring or browser work.

### Build Order

1. **Engine spine**
   - Implement `src/game/state/rng.py`
   - Define minimal `GameState`, `PlayerAction`, `MechanicalResult`, and `TurnResult`
   - Make every random outcome reproducible from seed + action script

2. **One playable day**
   - One location
   - Three NPCs
   - A small action set: talk, flirt, listen, leave, advance phase
   - Deterministic relationship deltas and phase movement

3. **CLI first**
   - `play` runs an interactive local session
   - `replay` reproduces a run from seed + action log
   - Debug output shows rolls, deltas, and current state

4. **Tests before agents**
   - Pure engine tests with no LLM calls
   - Golden scenario tests for fixed seeds
   - Smoke tests for content loading once real content exists

5. **Narrator second**
   - Add the single v0 Narrator agent after the deterministic loop works
   - The Narrator receives `MechanicalResult` and visible context only
   - Mock narration remains the default for tests

6. **Browser last**
   - Add the Vite client under `web/`
   - It renders visible state and submits actions to FastAPI
   - Zustand remains UI-only

### Documentation Rules Going Forward

- `AGENTS.md` is the only entry point.
- `CLAUDE.md` is a pointer for compatibility only.
- Existing numbered design docs remain design canon.
- Implementation decisions live in `docs/decisions/`.
- Runtime markdown under `content/` carries flavor and light metadata, not mechanics.
- Code modules cite the design docs they implement in module docstrings.
- `UI-UX.md` - Screen flow, visual style, text presentation

---

## 🤝 AI Assistant Instructions

### Your Role

**Brainstorm and Discuss FIRST** - Never implement without confirmation

**Never Create Files Prematurely** - If a system isn't fleshed out, keep it in AGENTS.md

**Never Auto-Commit** - User handles all git operations

**Suggest Structure, Don't Impose It** - Adapt to user preferences

---

### Discussion-First Workflow

1. **Discuss First**: Present options, design ideas, and tradeoffs
2. **User Confirms**: Wait for user to approve approach
3. **Then Implement**: Make changes only after confirmation
4. **Iterate**: Repeat if refinement needed

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

## 🎯 Quick Reference

### Key Innovations

**1. LLM-as-Game-Master**
- Procedurally generates contestants with full personalities
- Acts as AI Producer creating drama
- Writes dynamic dialogue and events
- No two runs are ever the same

**2. Reality TV Roguelite Loop**
- Structured daily cycle (Morning → Challenge → Socializing → Drama → Event)
- Clear failure states (elimination = permadeath)
- Meta-progression (Audience Appeal unlocks permanent perks)
- High replayability through procedural generation

**3. Dynamic Social Graph**
- Track relationships with every Islander simultaneously
- AI contestants have their own strategies and goals
- Emergent drama from competing interests
- Player agency in coupling, alliances, rivalries

---

### Inspiration Games

**Monster Prom** - Roguelite dating sim structure
- Proves the run-based loop works for social games
- Stat-building and random events
- Multiplayer competitive dating

**Love Island The Game** - Format and structure
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
1. Bachelor/Love Island structure
2. Roguelite run-based gameplay
3. LLM-powered procedural narrative

**Each Component is Proven**:
- Love Island structure = proven entertainment format
- Roguelite dating sim = Monster Prom shows it works
- LLM narrative = AI Dungeon demonstrates the tech

**The "All-Star" Concept**: Takes the best of each and creates something new.

---

## 🎯 Current Status: Core Systems Defined

**Phase:** Implementation scaffolding started. Core systems are designed; next build target is the deterministic Python CLI loop.

**What's Been Decided:**
- ✅ **Genre:** Social Sandbox with Seasonal Runs (NOT hardcore roguelite)
- ✅ **Format:** Love Island structure (locked in)
- ✅ **Run length:** 2-3 hours (15-20 key days, not full 42)
- ✅ **Target audience:** General/women, casual-friendly, low failure tolerance
- ✅ **LLM role:** Narrative flavor and personality, NOT game mechanics
- ✅ **Core philosophy:** Algorithm calculates outcomes, LLM writes dialogue
- ✅ **Interaction model:** Two-tier hybrid (static intent menu → dynamic contextual follow-ups)
- ✅ **Conversation system:** LLM generates both player dialogue and NPC response in single call
- ✅ **Conversation endings:** Organic (hybrid algorithm + LLM decides when NPC leaves, no hard cap)
- ✅ **Islander count:** 8 Islanders (4 couples), peak at 14-16 with bombshells/Casa Amor
- ✅ **Personality system:** Big 5 OCEAN + Attachment Styles + Type on Paper
- ✅ **Information architecture:** Hybrid visibility (map shown, dialogue hidden)
- ✅ **Location system:** Discrete locations with context-specific actions
- ✅ **No save scumming:** Choices locked in
- ✅ **Stats:** 5 fixed stats (Charm, Banter, EQ, Graft, Loyalty) set at character creation (3-9 range, 30 points)
- ✅ **Stat gating:** Advanced options locked behind stat thresholds (e.g., Graft 5 = Bold category)
- ✅ **Social events:** Round-table sharing events (6 types) replace free days
- ✅ **Setup flow:** Archetype selection → stat allocation → character card examination → reroll system
- ✅ **Challenges:** All non-interactive (algorithm-based), no physical challenges
- ✅ **Audience meter:** Visible individual (1-8) and couple (1-4) rankings with trajectory arrows

**Documentation Structure:**

| File | Contents | Lines | Status |
|------|----------|-------|--------|
| **Love-Island-Reference.md** | Complete show breakdown, what works/doesn't | ~800 | ✅ Reference |
| **00-Game-Start-And-Setup.md** | Character creation, archetypes, stats, rerolls, meta-progression | ~900 | ✅ Complete |
| **01-Game-Vision.md** | Genre, philosophy, inspiration, why this works | ~450 | ✅ Complete |
| **02-Core-Mechanics.md** | Stats (fixed 3-9), relationships, interactions, formulas | ~1115 | ✅ Complete |
| **03-LLM-Architecture.md** | Multi-AI system, code vs LLM separation | ~750 | ✅ Complete |
| **04-State-Management.md** | Data structures, schemas, state flow | ~800 | ✅ Complete |
| **05-Interaction-System.md** | Conversation system, contextual follow-ups, organic endings | ~1508 | ✅ Complete |
| **06-Location-System.md** | Villa layout, actions, spatial gameplay | ~600 | ✅ Complete |
| **07-Gossip-And-Information.md** | Knowledge systems, information architecture | ~650 | ✅ Complete |
| **08-Daily-Loop.md** | Run structure, pacing, social events | ~1090 | ✅ Complete |
| **09-Social-Dynamics.md** | Interruptions, group chats, pulls for chat | ~750 | ✅ Complete |
| **10-Elimination-System.md** | Producer AI, recouplings, voting, bombshells, weekly flow | ~1269 | ✅ Complete |
| **11-Conversation-Flow.md** | Contextual follow-ups, organic endings, two-tier system | ~800 | ✅ Complete |
| **12-Challenges-And-Events.md** | Challenges, social events, Casa Amor, special events | ~1110 | ✅ Complete |
| **ENGINEERING.md** | Non-negotiable implementation rules | ~100 | ✅ Active |
| **docs/qa-strategy.md** | QA layers, snapshots, traces, and parity plan | ~100 | ✅ Active |
| **docs/decisions/** | ADRs for implementation choices and architecture tradeoffs | 11 files | ✅ Active |

---

## 🔍 Finding Information

**High-level questions:**
- "What is this game?" → **AGENTS.md** (this file)
- "How does Love Island actually work?" → **Love-Island-Reference.md**
- "Why Love Island?" → **01-Game-Vision.md**
- "What's the tech stack?" → **AGENTS.md** ## Tech Stack
- "What engineering rules apply?" → **ENGINEERING.md**
- "What checks and tests matter?" → **docs/qa-strategy.md**
- "Why Python/Vite/one Narrator?" → **docs/decisions/**

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
| "What are the data structures?" | 04-State-Management.md | ## Islander State, ## Villa State |
| "How do conversations work?" | 05-Interaction-System.md | ## The Interaction Flow |
| "What's the menu system?" | 05-Interaction-System.md | ## Hybrid Menu System |
| "How do contextual follow-ups work?" | 05-Interaction-System.md | ## Conversation Structure & Continuity |
| "When do conversations end?" | 05-Interaction-System.md | ## Organic Conversation Endings |
| "Does the LLM generate player dialogue?" | 05-Interaction-System.md | ## Single Exchange Generation |
| "How do locations work?" | 06-Location-System.md | ## Villa Locations |
| "What actions are available?" | 06-Location-System.md | ## Location-Specific Actions |
| "How does gossip work?" | 07-Gossip-And-Information.md | ## The Gossip System |
| "What can the player see?" | 07-Gossip-And-Information.md | ## Information Architecture |
| "What's the daily structure?" | 08-Daily-Loop.md | ## The Four Phases |
| "How long is a run?" | 08-Daily-Loop.md | ## Run Length and Pacing |
| "What are social events?" | 08-Daily-Loop.md | ## Social Events |
| "How do interruptions work?" | 09-Social-Dynamics.md | ## Conversation Interruptions |
| "What are group conversations?" | 09-Social-Dynamics.md | ## Group Conversations |
| "How does pulling for a chat work?" | 09-Social-Dynamics.md | ## The Pull System |
| "How does the Producer AI work?" | 10-Elimination-System.md | ## The Producer AI System |
| "What are the recoupling rules?" | 10-Elimination-System.md | ## Recoupling Ceremonies |
| "How do challenges work?" | 12-Challenges-And-Events.md | ## Challenge System |
| "What social events exist?" | 12-Challenges-And-Events.md | ## Social Events (Round-Table Sharing) |
| "When do bombshells arrive?" | 10-Elimination-System.md | ## Bombshell System |
| "How does Casa Amor work?" | 12-Challenges-And-Events.md | ## Casa Amor |
| "How do votes and eliminations work?" | 10-Elimination-System.md | ## Voting and Eliminations |
| "How does audience ranking work?" | 10-Elimination-System.md | ## Audience/Public Perception System |

**Use grep to find specific topics:**
```bash
# Find all mentions of chemistry
grep -rn "chemistry" *.md

# Find where relationship thresholds are defined
grep -n "threshold" 05-Interaction-System.md

# Find personality system details
grep -n "Big 5" 03-LLM-Architecture.md
```

---

*This is the main entry point for understanding and developing the LLM-powered Love Island social sandbox game. Core systems are now fully documented in 10 comprehensive files plus Love Island reference. Ready for implementation planning.*
