# LLM-Powered Love Island Roguelite - AI Assistant Guide

*Documentation entry point for a visual novel roguelite dating game powered by AI*

**IMPORTANT**: This is the ONLY entry point file. Never create a README.md file.

---

## 🎯 Project Overview

**Working Title**: "Isle of Echoes" (or TBD)

**Core Concept**: A visual novel roguelite dating sim that combines the structure of reality TV shows like *Love Island* with procedurally generated narrative powered by a Large Language Model (LLM).

**The Innovation**: The LLM acts as a dynamic Game Master, generating unique contestants, dialogue, drama, and events for every playthrough. No two "summers of love" are ever the same.

**Current Phase**: Early concept/brainstorming - no implementation yet

**Tech Stack**: See detailed breakdown below

---

## 🛠️ Tech Stack

**Philosophy**: Optimize for **speed to playable POC**. We're building a text-based visual novel with LLM integration, not a physics game. The stack prioritizes rapid iteration and proven tools.

### Core Stack

**Framework**: **Next.js 14+** (App Router)
- Server components for LLM calls (keeps API keys secure)
- API routes for game logic
- Built-in optimization (image loading, code splitting)
- Vercel deployment ready

**LLM Integration**: **Vercel AI SDK**
- Provider-agnostic (OpenAI, Anthropic, Gemini)
- Streaming support (text appears as generated)
- React hooks: `useChat()`, `useCompletion()`
- Structured output (JSON mode for Islander generation)
- Tool calling (for our tagging system)

**State Management**: **Zustand**
- Simple, un-opinionated
- Perfect for complex game state (relationship graphs, villa state)
- Easy to persist to localStorage
- No boilerplate like Redux

**Styling**: **Tailwind CSS**
- Utility-first, fast to prototype
- Built-in animations (fade, slide)
- Responsive by default
- Works perfectly with Next.js

**UI Components**: **Headless UI**
- Accessible modals, transitions
- Pairs perfectly with Tailwind
- No styling opinions

**Typewriter Effect**: **react-type-animation**
- Tiny (2kb), performant
- Essential for visual novel feel
- Simple API

### What We're NOT Using (And Why)

❌ **LiveKit** - Too complex for POC (add voice later if needed)
❌ **Framer Motion** - Overkill; CSS transitions are enough
❌ **PixiJS / Canvas** - Not needed for text-based UI
❌ **Game engines** (Ren'Py, Unity, etc.) - Too rigid for LLM integration
❌ **Complex database** - Start with localStorage, add PostgreSQL later

### Visual Novel Specific Libraries

**For POC:**
```json
{
  "core": ["next", "react", "react-dom"],
  "llm": ["ai", "@ai-sdk/openai", "@ai-sdk/anthropic"],
  "state": ["zustand"],
  "styling": ["tailwindcss", "@headlessui/react"],
  "effects": ["react-type-animation"]
}
```

**For Polish (Post-POC):**
- **Howler.js** - Background music, sound effects
- **@vercel/postgres** or **Prisma** - Persistent save system
- **Sharp** (via Next.js) - Character portrait optimization

### Architecture

```
Client (Browser)
  ↓
Next.js Frontend (React Components)
  ↓
Zustand (Game State: relationships, villa status, player stats)
  ↓
Next.js API Routes (Server-side)
  ↓
Vercel AI SDK
  ↓
LLM Provider (OpenAI GPT-4 / Anthropic Claude)
  ↓
Response → Update State → Render UI
```

### Visual Novel Layout Pattern

Classic VN structure, all DOM-based (no canvas):

```tsx
<VillaScene>
  <Background src="/villa-pool.jpg" />       {/* Next.js Image */}
  <CharacterSprites>
    <Character position="left" sprite={player} />
    <Character position="right" sprite={chloe} expression="happy" />
  </CharacterSprites>
  <DialogueBox>
    <NameTag>Chloe</NameTag>
    <TypewriterText>{currentDialogue}</TypewriterText>
    {showChoices && <ChoiceButtons options={aiGeneratedChoices} />}
  </DialogueBox>
</VillaScene>
```

### LLM Integration Pattern

**Example: Generating an Islander**

```typescript
// app/api/generate-islander/route.ts
import { generateObject } from 'ai'
import { openai } from '@ai-sdk/openai'
import { z } from 'zod'

export async function POST(req: Request) {
  const { archetype } = await req.json()

  const islander = await generateObject({
    model: openai('gpt-4'),
    schema: z.object({
      name: z.string(),
      age: z.number(),
      occupation: z.string(),
      personality: z.string(),
      type_on_paper: z.object({
        values_humor: z.number(),
        values_loyalty: z.number(),
        dislikes_drama: z.number()
      }),
      secret: z.string()
    }),
    prompt: `Generate a Love Island contestant. Archetype: ${archetype}`
  })

  return Response.json(islander.object)
}
```

**Example: Dialogue with Tagging System**

```typescript
// app/api/dialogue/route.ts
import { generateObject } from 'ai'
import { openai } from '@ai-sdk/openai'

export async function POST(req: Request) {
  const { context, playerStats } = await req.json()

  const response = await generateObject({
    model: openai('gpt-4'),
    schema: z.object({
      dialogue: z.string(),
      options: z.array(z.object({
        text: z.string(),
        tags: z.array(z.string()), // ["Charm", "Flirty", "Risky"]
        stat_used: z.enum(["Charm", "Banter", "Graft", "Loyalty"])
      }))
    }),
    system: `You are the AI producer. Generate dialogue and tag options.`,
    prompt: `Context: ${JSON.stringify(context)}`
  })

  return Response.json(response.object)
}
```

### Asset Strategy

**Character Portraits**:
- AI-generated (Midjourney/DALL-E) or placeholder stock photos
- Multiple expressions per character (happy, sad, angry, flirty)
- Store in `/public/characters/`

**Backgrounds**:
- AI-generated villa locations (pool, bedroom, kitchen, terrace)
- Store in `/public/backgrounds/`

**Audio** (Post-POC):
- Royalty-free background music
- UI sound effects (click, notification)

### Deployment

**Platform**: **Vercel**
- Free tier sufficient for POC
- Automatic deployments from git
- Edge functions for fast API routes
- Environment variables for API keys

**Environment Variables**:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Development Workflow

```bash
# Local development
npm run dev

# Type checking
npm run type-check

# Build for production
npm run build

# Deploy to Vercel
git push origin main  # Auto-deploys
```

### Performance Targets

**For POC** (not production-level yet):
- ✅ LLM response streaming (text appears immediately)
- ✅ Dialogue appears in <2 seconds
- ✅ Islander generation in <5 seconds
- ✅ No frame drops during transitions
- ⚠️ Cost monitoring (LLM API costs can add up during testing)

### Cost Considerations

**LLM API Costs** (approximate):
- GPT-4: ~$0.03 per 1K tokens (input), ~$0.06 per 1K tokens (output)
- Claude 3.5 Sonnet: ~$0.003 per 1K tokens (much cheaper)

**POC Budget Estimate**:
- 100 test runs × ~10K tokens per run = ~$50-100 total
- Use Claude for dialogue (cheaper), GPT-4 for complex generation

### Future Considerations (Post-POC)

**If adding voice (LiveKit)**:
- Add `@livekit/components-react`
- Separate voice-enabled routes
- Much higher costs (~$0.10-0.50 per minute of voice)

**If going local LLM**:
- Replace Vercel AI SDK provider
- Use Ollama or llama.cpp
- Requires more powerful hardware
- No API costs but slower generation

---

## 📚 Documentation Philosophy

This repo follows a **high-context-efficiency** approach optimized for AI-assisted development.

### The Rules

**File Structure:**
- **CLAUDE.md is the ONLY entry point** - Never create README.md
- **One file = one complete system** - No fragmentation across multiple files
- **Don't create files until systems are defined** - It's OK to keep everything in CLAUDE.md initially
- **Aim for ~10-15 numbered files eventually** - Not 50+ fragments
- **Each file should be 300-800 lines** - If smaller, it probably belongs in another file
- **Use ## headers heavily** - For AI navigation via grep

**When to Create a New File:**
- ✅ When a system is **fully designed** (not "we might do X or Y")
- ✅ When a section in CLAUDE.md exceeds ~500 lines
- ✅ When a topic needs **independent iteration** (e.g., balance will change frequently)
- ✅ When an AI would need to reference it **independently** (e.g., "how do challenges work?")

**File Naming Convention:**
- `01-Game-Vision.md` - Always first, the "why" and philosophy
- `02-Core-Mechanics.md` - The fundamental gameplay systems
- `03-XX.md` - Major systems in order of importance/dependency
- `Templates/` - For extensible content types (events, challenges, archetypes)
- `SETUP-CHECKLIST.md` - Pre-implementation action items

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

**Current Lean**: **Love Island**

**Why Love Island Works Best:**
- Daily cycle creates tight roguelite loop
- Constantly shifting social landscape = high replayability
- Player has maximum agency (can switch partners, form alliances)
- Multiple relationship stats tracked simultaneously
- Clear failure states (being "dumped from the island")

**Open Question**: Single format or unlockable variants?

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

## 🗺️ Roadmap for Documentation Growth

### Phase 1: Concept Solidification (CURRENT PHASE)

**Open Questions to Resolve**:
- [ ] Commit to primary format (Love Island vs. alternatives)
- [ ] Define exact stat formulas and scaling
- [ ] Decide on dialogue interaction model:
  - Pure choice-based (3-4 LLM-generated options)?
  - Text input for key moments ("confessionals")?
  - Hybrid approach?
- [ ] Choose LLM approach:
  - Cloud API (GPT-4, Claude, Gemini)?
  - Local model (Llama, Mistral)?
  - Hybrid (local for simple, API for complex)?
- [ ] Determine number of AI Islanders per run
- [ ] Design challenge variety and mechanics
- [ ] Map out entire 6-week run structure

**Keep Everything in CLAUDE.md Until These Are Answered**

---

### Phase 2: First File Creation

**Create files only when systems are fully designed:**

**01-Game-Vision.md** - Create when:
- Format is locked in
- You can articulate the "why" behind core innovations
- Design pillars are clear

**02-Core-Mechanics.md** - Create when:
- All stats are defined with formulas
- Scoring system is locked
- Relationship graph is mapped

**03-Daily-Loop.md** - Create when:
- All 5 phases are detailed
- Turn structure is finalized
- Week-to-week progression is mapped

**04-LLM-Integration.md** - Create when:
- Prompt architecture is designed
- Tagging system is formalized
- Context management strategy is clear
- API choice is made

**05-Islander-AI-System.md** - Create when:
- Personality archetypes are defined
- AI decision-making logic is mapped
- "Type on Paper" system is complete

**06-Meta-Progression.md** - Create when:
- All unlocks are designed
- Progression curve is balanced
- AP economy is defined

---

### Phase 3: Implementation Prep

**When Ready to Code:**

**Templates/** folder:
- `Event-Template.md` - Format for villa events
- `Challenge-Template.md` - Format for challenge types
- `Islander-Archetype-Template.md` - Format for personality types

**SETUP-CHECKLIST.md**:
- LLM API setup
- Dev environment
- Testing framework
- State management architecture

**Implementation-Roadmap.md**:
- Week-by-week development plan
- Critical path (what must work first)
- Testing strategy for LLM consistency

---

### Future Files (Don't Create Until Needed)

- `Challenges-and-Events.md` - Catalog of all challenge types and villa events
- `Economy-and-Balance.md` - Stat scaling, difficulty curves, vote simulation
- `Alternative-Formats.md` - Love Is Blind, Bachelor, Are You The One variants
- `Testing-Strategy.md` - LLM consistency testing, edge cases, metrics
- `UI-UX.md` - Screen flow, visual style, text presentation

---

## 🤝 AI Assistant Instructions

### Your Role

**Brainstorm and Discuss FIRST** - Never implement without confirmation

**Never Create Files Prematurely** - If a system isn't fleshed out, keep it in CLAUDE.md

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
   - "Should this stay in CLAUDE.md or become its own file?"
   - Only create a new file if:
     - System is complete and substantial (300+ lines)
     - Will be referenced independently
     - Won't change dramatically

---

### How to Help Grow This Repo

**Suggest File Creation When**:
- A section in CLAUDE.md hits ~500 lines
- A system is fully designed and won't change
- The topic needs independent iteration

**Keep in CLAUDE.md When**:
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

## 📊 Document Version

**Version**: 0.1 (Initial Brainstorm)
**Status**: Concept phase - no files created yet
**Last Updated**: 2025-01-08

**Major Changes**:
- Initial CLAUDE.md creation
- Documented core game concept from brainstorm session
- Established documentation philosophy
- Defined roadmap for future file creation

---

## 🔍 Finding Information

**Since everything is currently in this file:**

Use Obsidian search or grep:
```bash
# Find player stats
grep -n "Player Stats" CLAUDE.md

# Find LLM tagging system
grep -n "Tagging & Scoring" CLAUDE.md

# Find meta-progression
grep -n "Meta-Progression" CLAUDE.md
```

**As files are created**, update this section with a reference table like:

| Question | Read This | Section |
|----------|-----------|---------|
| "How does LLM scoring work?" | 04-LLM-Integration.md | ## Tagging & Scoring System |
| "What are player stats?" | 02-Core-Mechanics.md | ## Player Stats |

---

*This is the main entry point for understanding and developing the LLM-powered Love Island roguelite. All current knowledge about the game is contained in this file. As systems are finalized, they will be extracted into numbered documentation files following the philosophy outlined above.*
