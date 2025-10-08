# Interaction System

*How conversations and player actions work*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Core Philosophy](#core-philosophy)
- [The Sims Comparison](#the-sims-comparison)
- [Hybrid Menu System](#hybrid-menu-system)
- [The Interaction Flow](#the-interaction-flow)
- [Success Calculation Details](#success-calculation-details)
- [Relationship Application](#relationship-application)
- [Unlocking System](#unlocking-system)
- [Non-Verbal Actions](#non-verbal-actions)
- [Time Management](#time-management)

**Note:** For multi-exchange conversations, contextual follow-ups, and organic conversation endings, see **11-Conversation-Flow.md**

---

## Core Philosophy

### Intent-Based, Not Dialogue-Based

**Player selects INTENT, LLM generates DIALOGUE**

**NOT this (pure visual novel):**
```
[Choice 1] "Honestly? I'm here to find genuine love. I'm tired of the games."
[Choice 2] "I mean, who wouldn't want a summer in a villa? But yeah, hoping to meet someone."
[Choice 3] "I just wanted the Instagram followers." (Joke)
```
Problems: Slow, reading-heavy, can't scan quickly

**YES this (Sims-style + LLM flavor):**
```
Talk to Chloe

Friendly:
→ Ask how she's feeling
→ Chat about the villa
→ Compliment her personality

Flirty: 💕
→ Compliment her looks
→ Playful teasing
→ Intimate eye contact
```
Benefits: Fast, strategic, scannable

**Then LLM writes the actual exchange:**
```
You lean in with a playful smile. "You look absolutely stunning today."

Chloe blushes. "Stop it, I haven't even done my makeup yet!" She's smiling though. You can tell she likes the attention.

✨ Charm check: SUCCESS
💕 Chemistry +5, Affection +3
```

**Best of both worlds:**
- Sims speed and strategy
- LLM personality and uniqueness
- Visual novel narrative flavor

---

## The Sims Comparison

### How The Sims Does Social Interactions

**1. Context-Based Menus**

When you click on a Sim:
```
Friendly:
→ Chat
→ Joke
→ Hug
→ Ask About Day

Funny:
→ Tell Joke
→ Perform
→ Prank

Romance: (locked until relationship ≥20)
→ Flirt
→ Compliment Appearance
→ First Kiss (locked until relationship ≥40)

Mean:
→ Insult
→ Fight
→ Argue
```

**2. Unlocking Through Relationship Levels**

- Relationship 0-20: Only Friendly and Funny
- Relationship 20-40: Romance unlocks
- Relationship 40-60: Physical romance (kiss)
- Relationship 60+: Intimate actions

**3. Context Adds Special Options**

- Near pool → "Invite to Swim"
- While in pool → "Splash" or "Swim Together"
- On couch → "Sit Together" or "Cuddle" (if romantic)
- In bedroom → "WooHoo" (if relationship high enough)

**4. Success Calculation**

Sims uses:
- Compatibility score (traits)
- Current mood (both Sims)
- Relationship level
- RNG with weighted probability

Example:
```
Tell Joke action:
- Base chance: 60%
- Funny trait: +20%
- Target has Playful mood: +10%
- Relationship 50: +10%
= 100% success (capped at 95%)
```

**5. Outcomes**

Success:
- Relationship +5
- Both Sims get mood boost
- Sometimes unlocks new interactions

Failure:
- Relationship -3
- Embarrassed moodlet
- Slight mood penalty

**6. Autonomous Behavior**

NPCs choose from same menu:
- Weighted by traits (Romantic Sims flirt more)
- Filtered by relationship (won't kiss strangers)
- Some randomness (prevents repetition)

### What We Take From The Sims

✅ **Category-based interaction menus**
- Clean, organized, easy to scan
- Player learns the system quickly

✅ **Relationship thresholds unlock actions**
- Clear progression
- Feels earned
- Strategic depth

✅ **Context-specific options**
- Location matters
- Actions feel appropriate
- Variety without overwhelming

✅ **Success probability (not guaranteed)**
- Risk/reward
- Personality matters
- Strategic choice

✅ **Mood system**
- Affects interaction success
- Adds realism
- Creates dynamic situations

### What We Improve

❌ **Sims has weak gossip** → We have robust knowledge propagation

❌ **Sims has infinite time** → We have time pressure (strategic choices)

❌ **Sims has generic dialogue** → We have LLM-generated unique responses

❌ **Sims has no clear goals** → We have win conditions and structure

❌ **Sims NPCs are passive** → Our NPCs have goals and strategies

---

## Hybrid Menu System

### Three-Tier Menu Structure

**Tier 1: Always Available (Core Categories)**

These are ALWAYS visible (unless locked by relationship):

```javascript
const coreMenu = {
  friendly: {
    icon: "💬",
    unlocked: true, // always
    options: [
      "Ask how they're feeling",
      "Chat about the villa",
      "Compliment their personality"
    ]
  },

  flirty: {
    icon: "💕",
    unlocked: relationship.affection >= 20,
    options: [
      "Compliment their looks",
      "Playful teasing",
      "Intimate eye contact"
    ]
  },

  deep: {
    icon: "🗨️",
    unlocked: relationship.affection >= 40,
    options: [
      "Ask about their life back home",
      "Share your feelings",
      "Discuss your connection"
    ]
  },

  banter: {
    icon: "😄",
    unlocked: true,
    options: [
      "Tell a joke",
      "Playful roasting",
      "Funny story"
    ]
  }
}
```

**Tier 2: Contextual Options (Dynamic)**

Added by code based on current situation:

```javascript
const contextualOptions = []

// If they seem upset
if (target.mood === "upset") {
  contextualOptions.push({
    category: "supportive",
    icon: "🤗",
    option: "Comfort them",
    statUsed: "emotional_intelligence"
  })
}

// If there's drama involving them
if (recentDramaInvolves(target)) {
  contextualOptions.push({
    category: "address_drama",
    icon: "⚠️",
    option: `"Are you okay after that situation with ${otherPerson}?"`,
    statUsed: "emotional_intelligence"
  })
}

// If player is coupled with someone else (risky)
if (player.coupledWith && player.coupledWith !== target.id) {
  contextualOptions.push({
    category: "graft",
    icon: "🔥",
    option: "Pull them for a private chat (risky)",
    statUsed: "graft",
    warning: "Your partner might find out"
  })
}
```

**Tier 3: LLM-Suggested Options (Optional Enhancement)**

For extra depth, LLM can suggest 1-2 unique options:

```javascript
// LLM call (cheap, happens once when opening menu)
const llmSuggestions = await generateContextualOptions({
  character: target,
  recentEvents: getRecentEvents(target),
  relationship: relationship
})

// Returns:
[
  {
    text: "Ask about her conversation with Marcus earlier",
    category: "gossip",
    statUsed: "emotional_intelligence"
  }
]
```

**Final Combined Menu:**

```
Talk to Chloe

Friendly: 💬
→ Ask how she's feeling
→ Chat about the villa
→ Compliment her personality

Flirty: 💕
→ Compliment her looks
→ Playful teasing
→ Intimate eye contact

Deep: 🗨️
→ Ask about her life back home
→ Share your feelings
→ Discuss your connection

Banter: 😄
→ Tell a joke
→ Playful roasting

⚡ Contextual:
→ "You seem worried. Want to talk?" (EI check)
→ "I noticed you talking to Aisha..." (Gossip)

Activities:
→ Invite to swim together
→ Suggest working out later
```

### Menu Display Logic

```javascript
function buildInteractionMenu(target, player, context) {
  const menu = {
    categories: [],
    contextual: [],
    activities: []
  }

  // 1. ADD CORE CATEGORIES (if unlocked)

  if (true) { // always available
    menu.categories.push({
      name: "Friendly",
      icon: "💬",
      options: getFriendlyOptions(target, player)
    })
  }

  if (target.relationships.player.affection >= 20) {
    menu.categories.push({
      name: "Flirty",
      icon: "💕",
      options: getFlirtyOptions(target, player)
    })
  }

  if (target.relationships.player.affection >= 40) {
    menu.categories.push({
      name: "Deep",
      icon: "🗨️",
      options: getDeepOptions(target, player)
    })
  }

  if (true) {
    menu.categories.push({
      name: "Banter",
      icon: "😄",
      options: getBanterOptions(target, player)
    })
  }

  // 2. ADD CONTEXTUAL OPTIONS

  menu.contextual = getContextualOptions(target, player, context)

  // 3. ADD LOCATION-SPECIFIC ACTIVITIES

  menu.activities = getAvailableActivities(player.currentLocation, target)

  // 4. ADD GOSSIP (if available)

  const gossip = getAvailableGossip(target, player)
  if (gossip.length > 0) {
    menu.categories.push({
      name: "Gossip",
      icon: "🗨️",
      options: gossip.map(g => `Ask about ${g.subject}`)
    })
  }

  return menu
}
```

---

## The Interaction Flow

**Step-by-step walkthrough of a single interaction:**

### Step 1: Player Initiates

Player selects "Talk to Chloe" from location view.

```javascript
function initiateConversation(targetId) {
  const target = getIslanderById(targetId)

  // Check if target is available
  if (target.currentLocation !== player.currentLocation) {
    return error("They're not here")
  }

  if (target.currentActivity === "in_conversation") {
    return error("They're talking to someone else")
  }

  // Open conversation UI
  openConversationUI(target)
}
```

### Step 2: Display Menu

Game builds and shows interaction menu:

```javascript
const menu = buildInteractionMenu(chloe, player, context)

// Displays:
// Talk to Chloe
// [Friendly] [Flirty] [Deep] [Banter] [Activities]
```

### Step 3: Player Selects Option

Player clicks "Flirty → Compliment her looks"

```javascript
const action = {
  type: "flirt",
  category: "flirty",
  specificOption: "compliment_looks",
  statUsed: "charm",
  target: chloe
}
```

### Step 4: Code Calculates Success

```javascript
// Algorithm determines outcome BEFORE calling LLM
const successChance = calculateInteractionSuccess(action, chloe, player, context)
// Returns: 72%

const roll = random(1, 100)
const success = roll <= 72 // true or false

// In this case: roll = 45, success = true
```

### Step 5: Code Applies Mechanical Changes

```javascript
if (success) {
  // Update relationships (instant, no LLM needed)
  chloe.relationships.player.chemistry += 5
  chloe.relationships.player.affection += 3
  chloe.relationships.player.familiarity += 1

  // Check side effects
  if (player.coupledWith && player.coupledWith !== "chloe") {
    // Risk of being caught
    checkIfCaughtFlirting(player, chloe)
  }

  // Update player stats (small chance to grow)
  if (random(100) < 10) {
    player.stats.charm += 0.1
  }
}
```

### Step 6: LLM Generates Dialogue

Now (and ONLY now) we call the LLM:

```javascript
const prompt = buildDialoguePrompt({
  character: chloe,
  action: "player_complimented_looks",
  outcome: success ? "positive" : "rejected",
  context: {
    location: "pool",
    mood: "flirty",
    relationship: chloe.relationships.player,
    recentHistory: getRecentHistory(chloe, player, 3)
  }
})

const dialogue = await generateDialogue(prompt)

// Returns:
// "Chloe blushes and bites her lip. \"You're going to give me a big head with all these compliments.\" She glances toward Aisha across the pool, then back to you. \"I'm glad we're solid though.\""
```

### Step 7: Display Result

```javascript
showInteractionResult({
  dialogue: dialogue,
  success: true,
  changes: {
    chemistry: +5,
    affection: +3,
    familiarity: +1
  },
  timeCost: 20, // minutes
  newRelationshipLevel: calculateRelationshipLevel(chloe.relationships.player)
})
```

**Player sees:**
```
You lean in with a playful smile. "You look absolutely stunning today."

Chloe blushes and bites her lip. "You're going to give me a big head with all these compliments."

She glances toward Aisha across the pool, then back to you. "I'm glad we're solid though."

✨ Charm check: SUCCESS
💕 Chemistry +5, Affection +3

Relationship with Chloe: 65 → 73 (Strong Connection)
⏰ 20 minutes passed
```

### Step 8: Player Chooses Next Action

```
Continue conversation?
→ Keep talking (choose another option)
→ Suggest an activity together
→ End conversation

Time remaining this phase: 70 minutes
```

**Total time: ~2-3 seconds (mostly LLM call)**

---

## Success Calculation Details

### Full Algorithm (Expanded)

```javascript
function calculateInteractionSuccess(action, target, player, context) {
  let chance = 50 // base

  // 1. PLAYER STAT BONUS (0-50)
  if (action.statUsed) {
    const statValue = player.stats[action.statUsed] // 0-10
    const bonus = statValue * 5
    chance += bonus
  }

  // 2. RELATIONSHIP BONUS (0-50)
  const affection = target.relationships.player.affection
  const relationshipBonus = affection / 2
  chance += relationshipBonus

  // 3. COMPATIBILITY (Big 5 based) (-20 to +20)
  const compatibility = calculateCompatibility(player, target)
  chance += compatibility

  // 4. MOOD MODIFIER (-30 to +30)
  const moodTable = {
    happy: { friendly: +10, flirty: +10, banter: +15, deep: 0 },
    flirty: { friendly: 0, flirty: +20, banter: +5, deep: +5 },
    upset: { friendly: +5, flirty: -20, banter: -15, deep: +15 },
    anxious: { friendly: +10, flirty: -10, banter: -5, deep: +10 },
    angry: { friendly: -15, flirty: -25, banter: -10, deep: -10 },
    content: { friendly: +5, flirty: +5, banter: +5, deep: +5 }
  }
  const moodMod = moodTable[target.currentMood]?.[action.category] || 0
  chance += moodMod

  // 5. CONTEXT BONUSES

  // Location appropriateness
  if (action.preferredLocation === player.currentLocation) {
    chance += 10
  }

  // Privacy (romantic actions need privacy)
  if (action.needsPrivacy) {
    const privacyBonus = context.location.privacy === "private" ? 15 :
                         context.location.privacy === "semi-private" ? 5 : -10
    chance += privacyBonus
  }

  // Time of day
  if (action.category === "deep" && context.phase === "evening") {
    chance += 10 // evenings better for deep talks
  }

  // 6. PENALTIES

  // Target is coupled with someone else
  if (target.coupledWith && target.coupledWith !== player.id) {
    if (action.category === "flirty") {
      chance -= 20 // they're loyal
    }
  }

  // Player is coupled with someone else (public)
  if (player.coupledWith && player.coupledWith !== target.id) {
    if (action.category === "flirty") {
      const publicPenalty = context.location.privacy === "public" ? -30 : -15
      chance += publicPenalty
    }
  }

  // High animosity
  if (target.relationships.player.animosity > 50) {
    const animosityPenalty = target.relationships.player.animosity / 2
    chance -= animosityPenalty
  }

  // Recently failed same action (spam protection)
  if (hasRecentlyFailed(action.category, target, 2)) { // within 2 exchanges
    chance -= 15
  }

  // 7. PERSONALITY MODIFIERS

  // Extraversion affects group interactions
  if (context.othersPresent > 2) {
    const extraversionMod = (target.personality.extraversion - 5) * 3
    chance += extraversionMod // -15 to +15
  }

  // Openness affects deep conversations
  if (action.category === "deep") {
    const opennessMod = (target.personality.openness - 5) * 4
    chance += opennessMod // -20 to +20
  }

  // Neuroticism makes trust harder
  if (action.builds === "trust") {
    const neuroticismPenalty = target.personality.neuroticism - 5
    chance -= neuroticismPenalty * 2 // -10 to +10
  }

  // Agreeableness helps all positive interactions
  const agreeablenessMod = (target.personality.agreeableness - 5)
  chance += agreeablenessMod // -5 to +5

  // Attachment style affects romantic actions
  if (action.category === "flirty" || action.category === "deep") {
    switch (target.attachmentStyle) {
      case "secure":
        chance += 5 // easier
        break
      case "anxious":
        chance += 10 // loves attention
        break
      case "avoidant":
        if (affection > 70) {
          chance -= 15 // pulls away when close
        }
        break
      case "fearful":
        // Unpredictable
        chance += random(-10, 10)
        break
    }
  }

  // 8. PREFERENCE MATCHING
  const preferenceBonus = checkPreferenceMatch(player, target)
  chance += preferenceBonus // 0-20

  // 9. CLAMP TO VALID RANGE
  const final = Math.max(10, Math.min(95, chance))

  return final
}
```

### Preference Matching

```javascript
function checkPreferenceMatch(player, target) {
  let bonus = 0

  // Physical type (if discovered)
  if (target.preferences.physicalTypeRevealed) {
    if (playerMatchesPhysicalType(player, target.preferences.physicalType)) {
      bonus += 10
    }
  }

  // Personality type
  if (target.preferences.personalityTypeRevealed) {
    // Check if player has high relevant stats
    if (target.preferences.personalityType.includes("funny")) {
      bonus += player.stats.banter >= 7 ? 5 : 0
    }
    if (target.preferences.personalityType.includes("confident")) {
      bonus += player.stats.charm >= 7 ? 5 : 0
    }
    if (target.preferences.personalityType.includes("loyal")) {
      bonus += player.stats.loyalty >= 7 ? 5 : 0
    }
  }

  // Values alignment
  const sharedValues = countSharedValues(player.demonstratedValues, target.preferences.values)
  bonus += sharedValues * 2 // 0-6

  // Dealbreakers (MAJOR PENALTY)
  if (playerHasDealbreaker(player, target.preferences.dealbreakers)) {
    bonus -= 15
  }

  return bonus
}
```

---

## Relationship Application

### Change Patterns by Action Type

```javascript
const relationshipChanges = {
  friendly: {
    success: { friendship: +4, affection: +2, familiarity: +2 },
    failure: { friendship: -1, familiarity: +1 }
  },

  flirty: {
    success: { chemistry: +5, affection: +3, familiarity: +1 },
    failure: { chemistry: -3, affection: -1, animosity: +1 }
  },

  deep: {
    success: { trust: +5, affection: +3, familiarity: +6 },
    failure: { trust: -2, animosity: +1 }
  },

  banter: {
    success: { friendship: +5, affection: +2 },
    failure: { friendship: -2, animosity: +1 }
  },

  graft: {
    success: { chemistry: +7, affection: +5, familiarity: +2 },
    failure: { animosity: +4, chemistry: -2 }
  },

  reassure: {
    success: { trust: +7, affection: +3 },
    failure: { trust: -3, animosity: +2 }
  }
}
```

### Application with Multipliers

```javascript
function applyRelationshipChange(action, target, success) {
  const baseChanges = relationshipChanges[action.category][success ? "success" : "failure"]
  const finalChanges = { ...baseChanges }

  // Personality multipliers (success only)
  if (success) {
    if (target.personality.agreeableness > 7) {
      finalChanges.affection *= 1.2
      finalChanges.friendship *= 1.2
    }

    if (target.personality.extraversion > 7 && action.isPublic) {
      finalChanges.affection *= 1.15
    }

    if (target.personality.neuroticism > 7) {
      finalChanges.trust *= 0.8 // harder to build trust
    }
  } else {
    // Failure multipliers
    if (target.personality.neuroticism > 7) {
      finalChanges.animosity *= 1.5 // takes it harder
    }
  }

  // Apply changes
  for (let [stat, change] of Object.entries(finalChanges)) {
    const current = target.relationships.player[stat]
    const newValue = Math.max(0, Math.min(100, current + change))
    target.relationships.player[stat] = newValue
  }

  // Record interaction
  recordInteraction(target, action, success, finalChanges)

  return finalChanges
}
```

---

## Unlocking System

### Relationship Tier Unlocks

```javascript
const unlockTiers = {
  0: {
    name: "Stranger",
    unlocks: ["friendly", "banter", "ask_about"]
  },

  20: {
    name: "Acquaintance",
    unlocks: ["flirty_light", "suggest_activity", "gossip_light"]
  },

  40: {
    name: "Friend/Interest",
    unlocks: ["deep", "private_chat", "ask_to_couple"]
  },

  60: {
    name: "Close/Romantic",
    unlocks: ["kiss", "cuddle", "define_relationship", "hideaway_invite"]
  },

  80: {
    name: "Strong Couple",
    unlocks: ["confession", "future_planning", "hideaway_overnight"]
  }
}

function getUnlockedActions(target, player) {
  const affection = target.relationships.player.affection
  const unlocked = []

  for (let [threshold, tier] of Object.entries(unlockTiers)) {
    if (affection >= parseInt(threshold)) {
      unlocked.push(...tier.unlocks)
    }
  }

  return unlocked
}
```

### Context Unlocks

```javascript
function getContextUnlockedActions(target, player, context) {
  const unlocked = []

  // Location-based
  if (context.location.id === "pool" && bothAtPool(player, target)) {
    unlocked.push("swim_together", "splash_playfully")
  }

  // Mood-based
  if (target.mood === "upset") {
    unlocked.push("comfort")
  }

  // Drama-based
  if (recentDramaInvolves(target)) {
    unlocked.push("address_drama")
  }

  // Coupled-based
  if (player.coupledWith === target.id) {
    unlocked.push("reassure", "couple_strategy")
  }

  return unlocked
}
```

---

## Non-Verbal Actions

### Activity System

Activities are special interactions that change state:

```javascript
const activities = {
  swim_together: {
    name: "Swim together",
    location: "pool",
    duration: 30,
    participants: 2,
    effects: {
      chemistry: +4,
      friendship: +3,
      mood: "happy"
    },
    animation: "swim_together",
    description: "You both dive into the pool and spend time swimming and splashing around."
  },

  workout_together: {
    name: "Work out together",
    location: "gym",
    duration: 35,
    participants: 2,
    effects: {
      friendship: +5,
      physical: +0.1 // stat increase
    },
    animation: "workout",
    description: "You spot each other during weights and push each other to go harder."
  },

  stargaze: {
    name: "Stargaze together",
    location: "terrace",
    duration: 25,
    participants: 2,
    requiresRelationship: 40,
    effects: {
      affection: +6,
      trust: +4,
      chemistry: +3,
      mood: "romantic"
    },
    animation: "stargaze",
    description: "You lie back and watch the stars together, talking about your dreams."
  }
}
```

### Activity Flow

```javascript
function startActivity(activityId, target) {
  const activity = activities[activityId]

  // 1. Check requirements
  if (activity.location !== player.currentLocation) {
    return error("Wrong location")
  }

  if (activity.requiresRelationship) {
    if (target.relationships.player.affection < activity.requiresRelationship) {
      return error("Relationship not high enough")
    }
  }

  // 2. Enter activity state
  player.currentActivity = activityId
  target.currentActivity = activityId

  // 3. Generate LLM narration
  const narration = await generateActivityNarration(activity, target)

  // 4. Show activity in progress
  showActivityScreen({
    activity: activity,
    narration: narration,
    duration: activity.duration
  })

  // 5. While in activity, show sub-menu
  const subMenu = getActivitySubMenu(activityId, target)
  // e.g., while swimming: "Splash her", "Swim closer", "Race", "Get out"

  return { activity, narration, subMenu }
}
```

### Activity Sub-Actions

While in an activity:

```
You're swimming with Chloe

→ Splash her playfully (Banter check)
→ Swim closer (Flirty, Charm check)
→ Challenge her to race (Physical check)
→ Deep conversation while floating
→ Get out of pool (end activity)
```

Each sub-action uses normal success calculation.

---

## Time Management

### Time Costs

Every action has a time cost:

```javascript
const timeCosts = {
  // Conversations
  friendly: 15,
  flirty: 20,
  deep: 25,
  banter: 15,
  gossip: 20,

  // Activities
  swim_together: 30,
  workout: 35,
  private_chat: 25,
  stargaze: 25,

  // Movement
  change_location: 5,
  invite_someone: 10
}
```

### Phase Time Budgets

```javascript
const phaseBudgets = {
  morning: 90,      // minutes
  challenge: 60,    // fixed event
  afternoon: 90,
  evening: 0        // story-driven, no limit
}
```

### Time Pressure Creates Strategy

**Morning phase: 90 minutes**

Possible actions:
- Talk to Chloe (20 min)
- Talk to Liam (20 min)
- Talk to new bombshell Aisha (20 min)
- Work out with Marcus (35 min)
- Move around villa (5 min each)

**Can't do everything. Must choose.**

**Example morning:**
```
Start: 90 min remaining

Talk to Chloe (partner, need to reassure): -20 min
→ 70 min remaining

Talk to Liam (friend, might have gossip): -20 min
→ 50 min remaining

Talk to Aisha (new bombshell, competitor): -20 min
→ 30 min remaining

Talk to Marcus (rival, causing drama): -20 min
→ 10 min remaining

Not enough time to work out or talk to anyone else.

Phase ends.
```

**Strategic questions:**
- Do I prioritize my partner or explore new options?
- Do I gather gossip or avoid drama?
- Do I confront rivals or ignore them?

**Time creates meaningful choice.**

---

**Version:** 1.1
**Status:** ✅ Complete
**Last Updated:** 2025-10-08

**Related Files:**
- **11-Conversation-Flow.md** - Multi-exchange conversations, contextual follow-ups, organic endings
- **06-Location-System.md** - Spatial gameplay and villa layout
- **09-Social-Dynamics.md** - Conversation interruptions, "pull for a chat", group conversations
