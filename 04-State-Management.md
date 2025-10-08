# State Management

*Data structures and schemas that power the game*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Overview](#overview)
- [Islander State](#islander-state)
- [Player State](#player-state)
- [Villa State](#villa-state)
- [Relationship State](#relationship-state)
- [Event State](#event-state)
- [Knowledge State](#knowledge-state)
- [State Transitions](#state-transitions)
- [Persistence Strategy](#persistence-strategy)

---

## Overview

### State Management Approach

**Library:** Zustand

**Why Zustand:**
- Simple, unopinionated
- Perfect for complex game state
- Easy to persist to localStorage
- No boilerplate
- TypeScript-friendly

**Architecture:**

```javascript
// Single store with slices
const useGameStore = create((set, get) => ({
  // Villa slice
  villa: { /* villa state */ },

  // Islanders slice
  islanders: { /* all Islander objects */ },

  // Player slice
  player: { /* player state */ },

  // Events slice
  events: { /* scheduled and recent events */ },

  // Actions
  updateRelationship: (islanderId, changes) => { /* ... */ },
  simulateNPCBehavior: () => { /* ... */ },
  advanceDay: () => { /* ... */ }
}))
```

### State Persistence

**Save to localStorage after:**
- Each day completes
- Player leaves the game
- Major events (recoupling, dumping)

**Don't save:**
- During active conversations
- During transitions
- While LLM is generating

**Save format:**
```javascript
{
  version: "0.2",
  timestamp: 1633024800000,
  currentDay: 5,
  currentPhase: "afternoon",
  islanders: [...],
  player: {...},
  villa: {...}
}
```

---

## Islander State

Complete state for each NPC Islander:

```typescript
interface Islander {
  // IDENTITY (generated once, never changes)
  id: string                    // "chloe_001"
  name: string                  // "Chloe"
  age: number                   // 24
  gender: "male" | "female"     // For coupling logic
  occupation: string            // "Marketing Manager"
  hometown: string              // "Manchester"

  appearance: {
    description: string         // LLM-generated paragraph
    hairColor: string          // "Blonde, long and wavy"
    eyeColor: string           // "Blue"
    height: string             // "5'6\""
    build: string              // "Athletic, toned"
    style: string              // "Casual chic, loves sundresses"
    spriteSet: string          // "blonde_athletic_01" (links to art assets)
  }

  // PERSONALITY (Big 5 + Attachment, never changes)
  personality: {
    openness: number            // 0-10
    conscientiousness: number   // 0-10
    extraversion: number        // 0-10
    agreeableness: number       // 0-10
    neuroticism: number         // 0-10
  }

  attachmentStyle: "secure" | "anxious" | "avoidant" | "fearful"

  // TYPE ON PAPER (hidden preferences, never changes)
  preferences: {
    physicalType: string        // "Tall, athletic, dark features"
    personalityType: string     // "Funny, confident, ambitious"
    values: string[]            // ["loyalty", "adventure", "honesty"]
    dealbreakers: string[]      // ["arrogance", "laziness"]
  }

  // BACKSTORY (never changes)
  backstory: string             // 3-4 sentences from LLM
  secret: string                // Hidden insecurity/past
  chatUpLine: string            // What they say when entering
  strategy: string              // Why they're on Love Island

  // CURRENT STATE (changes constantly)
  currentMood: "happy" | "flirty" | "upset" | "anxious" | "angry" | "content"
  currentLocation: LocationId   // "pool" | "gym" | "kitchen" etc.
  currentActivity: string       // "sunbathing" | "working_out" | "chatting"
  coupledWith: string | null    // Islander ID or null

  // STATS (0-10, can increase during run)
  stats: {
    charm: number               // Romantic appeal
    banter: number              // Humor and wit
    graft: number               // Pursuit ability
    loyalty: number             // Faithfulness
    emotional_intelligence: number // Reading emotions
    physical: number            // Athletic ability

    // Derived stats (calculated from personality)
    attractiveness: number      // Base attraction level
    humor: number               // Comedy ability
    charisma: number            // Social influence
    confidence: number          // Self-assurance
  }

  // RELATIONSHIPS (with every other Islander including player)
  relationships: {
    [islanderId: string]: {
      affection: number         // 0-100
      chemistry: number         // 0-100
      trust: number             // 0-100
      friendship: number        // 0-100
      animosity: number         // 0-100
      familiarity: number       // 0-100

      // Metadata
      daysMet: number           // How long they've known each other
      lastInteraction: number   // Day of last interaction
      interactionCount: number  // Total interactions
    }
  }

  // KNOWLEDGE (what they know about villa drama)
  knowledge: Array<{
    fact: string                // "Marcus kissed Sophie last night"
    source: "witnessed" | "gossip" | "told_directly"
    sourceIslander: string | null  // Who told them (if gossip)
    timestamp: {
      day: number
      phase: string
    }
    participants: string[]      // Islander IDs involved
    juiciness: number           // 0-100, how dramatic is this?
    willingnessToShare: number  // 0-100, likelihood of sharing
    sharedWith: string[]        // Islander IDs they've told
  }>

  // AI BEHAVIOR (influences autonomous actions)
  goals: {
    primary: "find_love" | "win_game" | "have_fun" | "cause_drama"
    secondary: "make_friends" | "win_challenges" | "stay_safe"
    willingToPlayGame: number   // 1-10, strategic vs genuine
  }

  // SOCIAL GRAPH (updated by AI behavior system)
  interests: string[]           // Islander IDs they're romantically interested in
  threats: string[]             // Islander IDs they see as competition
  allies: string[]              // Islander IDs they're aligned with

  // METADATA
  enteredVilla: number          // Day number
  isBombshell: boolean          // Entered mid-run
  isOriginal: boolean           // Started at Day 0
  dumpedOnDay: number | null    // If eliminated
}
```

### Example Islander Object

```javascript
const chloe = {
  id: "chloe_001",
  name: "Chloe",
  age: 24,
  gender: "female",
  occupation: "Marketing Manager",
  hometown: "Manchester",

  appearance: {
    description: "Blonde and athletic with an infectious smile. Loves to dress casually chic - often in sundresses. Radiates warmth and approachability.",
    hairColor: "Blonde, long and wavy",
    eyeColor: "Blue",
    height: "5'6\"",
    build: "Athletic, toned",
    style: "Casual chic, sundresses",
    spriteSet: "blonde_athletic_01"
  },

  personality: {
    openness: 7,
    conscientiousness: 6,
    extraversion: 9,
    agreeableness: 8,
    neuroticism: 4
  },

  attachmentStyle: "secure",

  preferences: {
    physicalType: "Tall, athletic, good smile",
    personalityType: "Funny, genuine, confident",
    values: ["loyalty", "humor", "adventure"],
    dealbreakers: ["arrogance", "game-playing", "dishonesty"]
  },

  backstory: "Grew up in a big family, always the social butterfly. Worked her way up in marketing through charm and hard work. Previous relationships ended because she felt her partners weren't matching her energy and enthusiasm for life.",

  secret: "Worries she's too much for people. Fears being alone despite being surrounded by friends.",

  chatUpLine: "Hope you're all ready for some good vibes and maybe a bit of trouble!",

  strategy: "Find genuine connection while having fun. Not here to play games.",

  currentMood: "happy",
  currentLocation: "pool",
  currentActivity: "sunbathing",
  coupledWith: "player",

  stats: {
    charm: 8,
    banter: 7,
    graft: 6,
    loyalty: 8,
    emotional_intelligence: 7,
    physical: 7,
    attractiveness: 8,
    humor: 7,
    charisma: 9,
    confidence: 8
  },

  relationships: {
    "player": {
      affection: 65,
      chemistry: 58,
      trust: 72,
      friendship: 55,
      animosity: 0,
      familiarity: 45,
      daysMet: 3,
      lastInteraction: 5,
      interactionCount: 12
    },
    "marcus": {
      affection: 15,
      chemistry: 30,
      trust: 50,
      friendship: 60,
      animosity: 0,
      familiarity: 40,
      daysMet: 5,
      lastInteraction: 4,
      interactionCount: 8
    }
    // ... all other Islanders
  },

  knowledge: [
    {
      fact: "Marcus kissed Aisha on the terrace",
      source: "witnessed",
      sourceIslander: null,
      timestamp: { day: 4, phase: "evening" },
      participants: ["marcus", "aisha"],
      juiciness: 80,
      willingnessToShare: 75,
      sharedWith: ["player", "liam"]
    }
  ],

  goals: {
    primary: "find_love",
    secondary: "have_fun",
    willingToPlayGame: 3
  },

  interests: ["player"],
  threats: [],
  allies: ["liam", "emma"],

  enteredVilla: 0,
  isBombshell: false,
  isOriginal: true,
  dumpedOnDay: null
}
```

---

## Player State

```typescript
interface Player {
  id: "player"  // Always "player"

  // PLAYER IDENTITY (set at run start)
  name: string              // Player-entered name
  gender: "male" | "female"

  // STATS (0-10, grow during run)
  stats: {
    charm: number
    banter: number
    graft: number
    loyalty: number
    emotional_intelligence: number
    physical: number
  }

  // CURRENT STATE
  currentLocation: LocationId
  currentActivity: string
  coupledWith: string | null  // Islander ID
  mood: string

  // PUBLIC PERCEPTION (0-100)
  publicPerception: number    // Simulated audience opinion

  // RELATIONSHIPS (same as Islander.relationships)
  relationships: {
    [islanderId: string]: {
      affection: number
      chemistry: number
      trust: number
      friendship: number
      animosity: number
      familiarity: number
      daysMet: number
      lastInteraction: number
      interactionCount: number
    }
  }

  // KNOWLEDGE (what player has learned)
  knowledge: Array<{
    fact: string
    source: "conversation" | "gossip" | "witnessed"
    sourceIslander: string | null
    day: number
    reliability: "confirmed" | "rumor" | "uncertain"
  }>

  // UNLOCKS (for this run)
  unlockedInteractions: string[]  // ["kiss", "hideaway_access", etc.]
  unlockedLocations: string[]     // ["terrace", "hideaway"]

  // ACTIVE BUFFS (temporary bonuses)
  activeBuffs: Array<{
    type: string                    // "challenge_winner", "date_bonus", etc.
    effect: string                  // "+10% to all interactions"
    duration: "until_next_challenge" | "end_of_day" | number
    appliedDay: number
  }>

  // PLAYER HISTORY (for this run)
  totalInteractions: number
  successfulFlirts: number
  failedFlirts: number
  deepConversations: number
  dramaEvents: number             // How much drama they've caused
  challengesWon: number

  // META (across all runs)
  audienceAppeal: number          // Total AP earned (persists across runs)
  completedRuns: number
  achievements: string[]
  unlockedArchetypes: string[]
  permanentPerks: string[]
}
```

### Player Starting State

```javascript
const newPlayer = {
  id: "player",
  name: "", // Set during character creation
  gender: "female", // Player choice

  stats: {
    charm: 5,
    banter: 5,
    graft: 5,
    loyalty: 5,
    emotional_intelligence: 5,
    physical: 5
  },

  currentLocation: "bedroom", // Start here
  currentActivity: "entering_villa",
  coupledWith: null, // Single at start
  mood: "excited",

  publicPerception: 50, // Neutral

  relationships: {}, // Filled as they meet Islanders

  knowledge: [],

  unlockedInteractions: [
    "friendly",
    "banter",
    "ask_about"
  ], // Basic interactions

  unlockedLocations: [
    "pool",
    "gym",
    "kitchen",
    "bedroom",
    "beach"
  ], // Terrace/hideaway locked

  activeBuffs: [],

  totalInteractions: 0,
  successfulFlirts: 0,
  failedFlirts: 0,
  deepConversations: 0,
  dramaEvents: 0,
  challengesWon: 0,

  // Meta (loaded from saved data)
  audienceAppeal: 0,
  completedRuns: 0,
  achievements: [],
  unlockedArchetypes: ["default"],
  permanentPerks: []
}
```

---

## Villa State

Global state for the villa:

```typescript
interface VillaState {
  // TIME
  currentDay: number          // 1-20
  currentPhase: "morning" | "challenge" | "afternoon" | "evening"
  timeRemaining: number       // Minutes left in current phase

  // LOCATIONS
  locations: {
    [locationId: string]: {
      name: string
      capacity: number
      islandersPresent: string[]  // Islander IDs
      activities: string[]         // Available activities
      privacy: "public" | "semi-private" | "private"
      requiresInvitation: boolean
      requiresUnlock: string | null  // "challenge_winner", etc.
    }
  }

  // COUPLES (current pairings)
  couples: Array<{
    islander1: string
    islander2: string
    formedDay: number
    strength: number  // 0-100, calculated
  }>

  singles: string[]  // Islander IDs who are uncoupled

  // RECENT EVENTS (last 3 days)
  recentEvents: Array<{
    type: "argument" | "kiss" | "confession" | "betrayal" | "coupling"
    participants: string[]
    location: string
    day: number
    phase: string
    witnessed_by: string[]
    description: string
  }>

  // SCHEDULED EVENTS (upcoming)
  scheduledEvents: Array<{
    type: "recoupling" | "dumping" | "bombshell" | "challenge" | "date" | "twist"
    day: number
    phase: string
    participants: string[] | null  // Pre-selected or null (TBD)
    metadata: any  // Event-specific data
  }>

  // VILLA METRICS (for Producer AI)
  metrics: {
    averageCoupleStrength: number
    dramaLevel: number              // 0-100
    daysSinceLastBombshell: number
    daysSinceLastRecoupling: number
    daysSinceLastDumping: number
    totalActiveRomances: number
    totalActiveRivalries: number
  }

  // AUDIENCE STATE (simulated)
  audienceFavorites: string[]       // Top 3 Islander IDs
  audienceLeastFavorite: string[]   // Bottom 3
  audienceVotesAvailable: boolean   // Is there an active public vote?

  // RUN METADATA
  runStartTime: number              // Timestamp
  seed: string                      // Random seed for this run
  difficulty: "casual" | "normal" | "dramatic"
}
```

### Example Villa State

```javascript
const villaState = {
  currentDay: 5,
  currentPhase: "morning",
  timeRemaining: 90, // minutes

  locations: {
    pool: {
      name: "Pool Area",
      capacity: 6,
      islandersPresent: ["chloe", "marcus", "sophie", "player"],
      activities: ["swim", "sunbathe", "lounge", "chat"],
      privacy: "public",
      requiresInvitation: false,
      requiresUnlock: null
    },
    gym: {
      name: "Gym",
      capacity: 4,
      islandersPresent: ["liam"],
      activities: ["workout", "cardio", "weights"],
      privacy: "semi-private",
      requiresInvitation: false,
      requiresUnlock: null
    },
    terrace: {
      name: "Terrace",
      capacity: 2,
      islandersPresent: [],
      activities: ["stargaze", "deep_talk", "romantic_moment"],
      privacy: "private",
      requiresInvitation: true,
      requiresUnlock: null
    },
    hideaway: {
      name: "The Hideaway",
      capacity: 2,
      islandersPresent: [],
      activities: ["overnight_stay"],
      privacy: "private",
      requiresInvitation: true,
      requiresUnlock: "challenge_winner"
    }
  },

  couples: [
    {
      islander1: "player",
      islander2: "chloe",
      formedDay: 2,
      strength: 68
    },
    {
      islander1: "marcus",
      islander2: "sophie",
      formedDay: 0,
      strength: 45
    },
    {
      islander1: "liam",
      islander2: "emma",
      formedDay: 1,
      strength: 72
    }
  ],

  singles: ["aisha", "tom"],

  recentEvents: [
    {
      type: "kiss",
      participants: ["player", "chloe"],
      location: "terrace",
      day: 3,
      phase: "evening",
      witnessed_by: [],
      description: "First kiss on the terrace under the stars"
    },
    {
      type: "argument",
      participants: ["marcus", "sophie"],
      location: "bedroom",
      day: 4,
      phase: "evening",
      witnessed_by: ["liam", "chloe"],
      description: "Marcus and Sophie argued about trust"
    }
  ],

  scheduledEvents: [
    {
      type: "challenge",
      day: 5,
      phase: "challenge",
      participants: null,
      metadata: {
        challengeType: "compatibility_quiz",
        prize: "date_for_two"
      }
    },
    {
      type: "recoupling",
      day: 7,
      phase: "evening",
      participants: null,
      metadata: {
        format: "girls_choose"
      }
    }
  ],

  metrics: {
    averageCoupleStrength: 62,
    dramaLevel: 45,
    daysSinceLastBombshell: 1, // Aisha just arrived
    daysSinceLastRecoupling: 5,
    daysSinceLastDumping: 5,
    totalActiveRomances: 5,
    totalActiveRivalries: 1
  },

  audienceFavorites: ["liam", "chloe", "player"],
  audienceLeastFavorite: ["marcus"],
  audienceVotesAvailable: false,

  runStartTime: 1633024800000,
  seed: "abc123def456",
  difficulty: "normal"
}
```

---

## Relationship State

Relationships are stored in both Islander and Player objects, but here's the detailed schema:

```typescript
interface Relationship {
  // CORE STATS (0-100)
  affection: number         // Romantic liking
  chemistry: number         // Physical attraction
  trust: number             // Security and faith
  friendship: number        // Platonic bond
  animosity: number         // Negative feelings
  familiarity: number       // How well they know each other

  // HISTORY
  daysMet: number           // How long they've known each other
  lastInteraction: number   // Day number
  interactionCount: number  // Total interactions

  // INTERACTION LOG (last 5)
  recentInteractions: Array<{
    day: number
    type: string            // "flirt", "deep", "friendly", etc.
    success: boolean
    changes: {              // What changed
      affection: number
      chemistry: number
      trust: number
      // ...
    }
  }>

  // MILESTONES
  milestones: Array<{
    type: "first_kiss" | "first_date" | "coupled" | "confession" | "betrayal"
    day: number
    description: string
  }>

  // FLAGS
  hasKissed: boolean
  hasCoupled: boolean
  hasBetrayed: boolean
  inActiveDrama: boolean
}
```

### Relationship Calculation Helpers

```javascript
// Calculate overall couple strength
function getCoupleStrength(relationship) {
  return (
    relationship.affection * 0.4 +
    relationship.trust * 0.4 +
    relationship.chemistry * 0.2
  )
}

// Check if relationship is romantic
function isRomanticRelationship(relationship) {
  return (
    relationship.affection > 40 ||
    relationship.chemistry > 50
  )
}

// Check if relationship is hostile
function isHostileRelationship(relationship) {
  return relationship.animosity > 50
}

// Predict if NPC would accept coupling
function wouldAcceptCoupling(npc, player) {
  const rel = npc.relationships.player

  const score = (
    rel.affection * 0.5 +
    rel.chemistry * 0.3 +
    rel.trust * 0.2
  )

  return score > 50
}
```

---

## Event State

```typescript
interface Event {
  id: string
  type: "recoupling" | "dumping" | "bombshell" | "challenge" | "date" | "twist"
  day: number
  phase: string

  // PARTICIPANTS
  participants: string[]  // Islander IDs

  // EVENT-SPECIFIC DATA
  metadata: {
    // For recouplings
    format?: "boys_choose" | "girls_choose" | "public_vote"
    choices?: Array<{
      chooser: string
      chosen: string
      previousPartner: string | null
    }>

    // For challenges
    challengeType?: string
    winner?: string
    prize?: string

    // For bombshells
    bombshellId?: string
    targetCouple?: string

    // For dates
    dateLocation?: string
    dateActivity?: string
  }

  // OUTCOMES
  outcomes: Array<{
    type: "coupled" | "dumped" | "won" | "unlocked"
    affectedIslanders: string[]
    description: string
  }>

  // DRAMA GENERATED
  dramaScore: number  // 0-100
  witnessedBy: string[]
}
```

---

## Knowledge State

How information propagates through the villa:

```typescript
interface KnowledgeFact {
  id: string
  fact: string              // "Marcus kissed Aisha"

  // PARTICIPANTS
  participants: string[]     // ["marcus", "aisha"]

  // SOURCE
  originalSource: "witnessed" | "confession" | "caught"
  originalWitnesses: string[]  // Who saw it happen

  // PROPAGATION
  knownBy: Array<{
    islanderId: string
    learnedFrom: string | null  // null if witnessed
    day: number
    willingToShare: number      // 0-100
    hasSharedWith: string[]
  }>

  // METADATA
  timestamp: {
    day: number
    phase: string
  }
  location: string
  juiciness: number          // 0-100, how dramatic
  isSecret: boolean          // Should this be hidden?
  reliability: number        // 0-100, how accurate
}
```

### Knowledge Propagation Example

```javascript
// Marcus kisses Aisha (player witnesses)
const event = {
  id: "kiss_marcus_aisha_day4",
  fact: "Marcus kissed Aisha on the terrace",
  participants: ["marcus", "aisha"],
  originalSource: "witnessed",
  originalWitnesses: ["player"],

  knownBy: [
    {
      islanderId: "player",
      learnedFrom: null, // witnessed directly
      day: 4,
      willingToShare: 80, // likely to gossip
      hasSharedWith: []
    }
  ],

  timestamp: { day: 4, phase: "evening" },
  location: "terrace",
  juiciness: 85, // very dramatic
  isSecret: false,
  reliability: 100 // player saw it directly
}

// Player tells Liam
// → Add to Liam's knowledge
event.knownBy.push({
  islanderId: "liam",
  learnedFrom: "player",
  day: 5,
  willingToShare: 90, // Liam loves gossip
  hasSharedWith: []
})

// Update player's record
const playerKnowledge = event.knownBy.find(k => k.islanderId === "player")
playerKnowledge.hasSharedWith.push("liam")

// Liam tells Chloe
// → Add to Chloe's knowledge
event.knownBy.push({
  islanderId: "chloe",
  learnedFrom: "liam",
  day: 5,
  willingToShare: 75,
  hasSharedWith: []
})

// Now 3 Islanders know, gossip is spreading
```

---

## State Transitions

### Day Transition

```javascript
function advanceDay() {
  // 1. Increment day
  villaState.currentDay++
  villaState.currentPhase = "morning"
  villaState.timeRemaining = 90

  // 2. Update metrics
  villaState.metrics.daysSinceLastBombshell++
  villaState.metrics.daysSinceLastRecoupling++

  // 3. Apply daily relationship decay
  applyRelationshipDecay()

  // 4. Update NPC moods
  updateAllMoods()

  // 5. Check for scheduled events
  executeScheduledEvents()

  // 6. Producer AI decides new events
  const newEvent = await getProducerDecision(villaState)
  if (newEvent) {
    scheduleEvent(newEvent)
  }

  // 7. Save state
  saveToLocalStorage()
}
```

### Phase Transition

```javascript
function advancePhase() {
  const phases = ["morning", "challenge", "afternoon", "evening"]
  const currentIndex = phases.indexOf(villaState.currentPhase)
  const nextPhase = phases[(currentIndex + 1) % 4]

  // If wrapping around, advance day instead
  if (nextPhase === "morning") {
    return advanceDay()
  }

  villaState.currentPhase = nextPhase
  villaState.timeRemaining = getPhaseTimeLimit(nextPhase)

  // Simulate NPC behavior during transition
  simulateAllNPCBehavior()

  // Update locations
  redistributeIslanders()
}
```

### Relationship Decay

```javascript
function applyRelationshipDecay() {
  for (let islander of allIslanders) {
    for (let [targetId, rel] of Object.entries(islander.relationships)) {
      // Skip if they just interacted
      if (rel.lastInteraction === villaState.currentDay - 1) continue

      // Decay rates
      const daysSinceInteraction = villaState.currentDay - rel.lastInteraction

      if (daysSinceInteraction >= 2) {
        rel.affection -= 1
        rel.chemistry -= 1
      }

      if (daysSinceInteraction >= 3) {
        rel.trust -= 2
      }

      // Clamp to 0
      rel.affection = Math.max(0, rel.affection)
      rel.chemistry = Math.max(0, rel.chemistry)
      rel.trust = Math.max(0, rel.trust)
    }
  }
}
```

---

## Persistence Strategy

### What to Save

```javascript
const saveState = {
  version: "0.2",
  timestamp: Date.now(),

  // Core state
  villa: villaState,
  player: player,
  islanders: allIslanders,

  // Derived state (can be recalculated, but save for convenience)
  couples: villaState.couples,
  knowledge: allKnowledgeFacts,

  // Run metadata
  seed: villaState.seed,
  difficulty: villaState.difficulty,
  startTime: villaState.runStartTime
}
```

### When to Save

```javascript
// Auto-save triggers
const AUTOSAVE_TRIGGERS = [
  "day_complete",
  "phase_complete",
  "major_event",
  "player_exit"
]

function autoSave(trigger) {
  if (AUTOSAVE_TRIGGERS.includes(trigger)) {
    saveToLocalStorage(getGameState())
  }
}
```

### Load Strategy

```javascript
function loadGame() {
  const saved = loadFromLocalStorage()

  if (!saved) {
    return null // No save found
  }

  // Validate version
  if (saved.version !== CURRENT_VERSION) {
    return migrateOldSave(saved)
  }

  // Restore state
  restoreVillaState(saved.villa)
  restorePlayer(saved.player)
  restoreIslanders(saved.islanders)

  return saved
}
```

---

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 05-Interaction-System.md for how these states are modified through gameplay
