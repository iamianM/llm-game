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
- [Conversation Structure](#conversation-structure)
- [Success Calculation Details](#success-calculation-details)
- [Relationship Application](#relationship-application)
- [Unlocking System](#unlocking-system)
- [Non-Verbal Actions](#non-verbal-actions)
- [Time Management](#time-management)

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

## Conversation Structure & Continuity

### The Two-Tier System

**Tier 1: Intent Selection (Static Menu)**
- Player opens conversation with NPC
- Sees structured menu of intents (Flirt, Go Deep, Banter, etc.)
- Picks category, then specific action
- Clear stat usage shown

**Tier 2: Contextual Follow-ups (Dynamic)**
- After NPC responds, LLM generates 2-4 contextual follow-up options
- Options based on what NPC just said
- Allows natural conversation flow
- Responds to specific dialogue

### Single Exchange Generation

**Player picks intent → LLM generates BOTH sides of exchange:**

```javascript
// Player selects: "Flirt → Compliment her looks"

const exchange = await LLM.generate({
  playerIntent: "flirt_compliment_looks",
  statUsed: "charm",
  context: {
    conversationHistory: previousExchanges,
    npc: chloe,
    location: "pool",
    recentEvents: getRecentEvents()
  }
})

// LLM returns:
{
  playerDialogue: "You look absolutely stunning tonight, by the way.",
  npcDialogue: "Thanks... though I heard you say that to Aisha earlier. 🤨",
  npcTone: "suspicious",
  npcMood: "testing_you",
  tags: ["flirt_attempt", "caught_inconsistency", "trust_test"]
}
```

**Then algorithm processes:**
```javascript
// Calculate success based on tags and stats
const success = calculateSuccess(exchange.tags, player.stats.charm, context)

// Apply mechanical effects
if (success) {
  chloe.relationships.player.affection += 3
  chloe.relationships.player.trust -= 5 // inconsistency penalty
}

// Generate contextual follow-ups
const followUpOptions = await generateContextualOptions(exchange, chloe, player)
```

**Why this works:**
- ✅ Player dialogue and NPC response naturally connect
- ✅ LLM writes realistic back-and-forth
- ✅ Player still chose the INTENT (maintains agency)
- ✅ Algorithm still handles mechanics (success/failure)

### Contextual Follow-up Generation

**After first exchange, LLM generates contextual options:**

```javascript
// Chloe just said: "I heard you say that to Aisha earlier."

const followUpOptions = await LLM.generate({
  prompt: "Generate 3-4 contextual response options",
  npcLastDialogue: "Thanks... though I heard you say that to Aisha earlier.",
  npcMood: "suspicious",
  playerStats: player.stats,
  context: conversationHistory
})

// LLM returns:
{
  options: [
    {
      intent: "deny",
      text: "That's not true, where'd you hear that?",
      statUsed: "charm",
      risk: "high",
      tone: "defensive"
    },
    {
      intent: "deflect_with_humor",
      text: "Jealous already? I like it.",
      statUsed: "banter",
      risk: "medium",
      tone: "playful"
    },
    {
      intent: "honest_vulnerable",
      text: "You're right, I'm sorry. You're the one I want.",
      statUsed: "eq",
      risk: "low",
      tone: "vulnerable"
    },
    {
      intent: "end_conversation",
      text: "Let's talk about this later.",
      statUsed: null,
      risk: "safe",
      tone: "exit"
    }
  ]
}
```

**Player sees:**
```
Chloe: "Thanks... though I heard you say that to Aisha earlier. 🤨"

How do you respond?

┌─────────────────────────────────────────────┐
│ [DENY] "That's not true, where'd you hear  │
│         that?" (Charm, Risky)               │
├─────────────────────────────────────────────┤
│ [DEFLECT] "Jealous already? I like it."     │
│           (Banter, Medium Risk)             │
├─────────────────────────────────────────────┤
│ [BE HONEST] "You're right, I'm sorry.       │
│             You're the one I want."         │
│             (EQ, Vulnerable)                │
├─────────────────────────────────────────────┤
│ [END] Let's talk about this later.          │
└─────────────────────────────────────────────┘
```

### Organic Conversation Endings

**NO HARD CAP - Conversations end naturally**

**Hybrid System:**
1. **Algorithm calculates departure probability** based on objective factors
2. **LLM makes final decision** and generates natural exit (or stays)
3. **Player always has "End conversation" option**

#### Departure Probability Calculation

```javascript
function calculateNPCDepartureChance(conversation, npc, gameState) {
  let departureChance = 0 // 0-100

  // CONVERSATION LENGTH (natural fatigue)
  if (conversation.exchangeCount > 10) departureChance += 30
  if (conversation.exchangeCount > 15) departureChance += 30 // very long

  // CONVERSATION QUALITY
  const recentAffectionGain = getRecentAffectionChange(5) // last 5 exchanges
  if (recentAffectionGain < 0) departureChance += 40 // going badly
  if (recentAffectionGain > 20) departureChance -= 30 // going great, wants to stay

  // ENGAGEMENT
  if (conversation.hasVulnerableMoment) departureChance -= 20 // deep talk, invested
  if (conversation.lastExchangeWasAwkward) departureChance += 25
  if (conversation.topicIsRepetitive) departureChance += 20 // boring

  // EXTERNAL PULLS
  if (gameState.dramaHappeningNearby) departureChance += 20 // distracted
  if (npc.wantsToTalkToSomeoneElse) departureChance += 30
  if (npc.partnerIsWatching && player !== npc.partner) departureChance += 15

  // RELATIONSHIP LEVEL
  if (npc.relationships.player.strength < 40) departureChance += 10 // not that into you
  if (npc.relationships.player.strength > 120) departureChance -= 20 // wants to spend time

  // NPC NEEDS
  if (npc.currentNeeds.includes("talk_to_partner")) departureChance += 25
  if (npc.currentNeeds.includes("alone_time")) departureChance += 15

  return Math.max(0, Math.min(90, departureChance)) // cap at 90% (never guaranteed)
}
```

#### LLM Decides Whether to Leave

```javascript
// Check after each exchange
const departureChance = calculateNPCDepartureChance(conversation, chloe, gameState)

const exchange = await LLM.generate({
  playerIntent: playerChoice.intent,
  context: conversationHistory,
  npc: chloe,
  npcDepartureChance: departureChance, // Pass as context
  instruction: `
    The NPC has a ${departureChance}% likelihood of wanting to end conversation.

    Consider:
    - Is the conversation naturally winding down?
    - Does the NPC have a reason to leave? (other needs, drama elsewhere, bored)
    - Or is the player saying something that hooks them back in?

    Set npcWantsToContinue: true/false accordingly.

    If false, generate natural goodbye with reason.
  `
})

// LLM returns:
{
  playerDialogue: "...",
  npcDialogue: "...",
  npcWantsToContinue: false, // LLM decided to end
  npcDepartureReason: "wants_to_check_on_friend",
  contextualOptions: null // No follow-ups, conversation ends
}
```

#### Natural Exit Examples

**Example 1: Deep Conversation Continues (Low Departure Chance)**

```
Exchange 8:
You: "Do you think we could be that for each other?"
Chloe: "I don't know yet... but I want to find out."

[+10 Affection, +8 Trust, very high engagement]

// Algorithm: departureChance = 5% (going amazing, vulnerable moments)
// LLM: npcWantsToContinue = true
// Chloe stays, wants to keep talking

Contextual Options:
├─ "I'm glad you're giving this a chance." (EQ)
├─ "Can I kiss you?" (Charm, risky)
└─ End conversation
```

**Example 2: Boring Conversation Ends (High Departure Chance)**

```
Exchange 3:
You: "How's your day going?"
Chloe: "Fine, just relaxing by the pool."

[+1 Affection, very boring, repetitive topic]

// Algorithm: departureChance = 65% (boring, low engagement, repetitive)
// LLM: npcWantsToContinue = false

Chloe: "Actually, I should go get ready for tonight's challenge.
       We can catch up later though!"

[Chloe walks toward villa]

[Return to location menu]
```

**Example 3: External Drama Pulls NPC Away**

```
Exchange 6:
You: "I really like spending time with—"

[Marcus and Aisha start arguing loudly nearby]

Chloe: "Oh my god, what's happening? I should check on Aisha,
       she's my best friend here. Rain check?"

// Algorithm: departureChance = 75% (drama nearby, friend needs support)
// LLM: Generated natural reason tied to game state

[Chloe leaves to check on drama]

💡 Drama event triggered: Marcus & Aisha arguing
```

**Example 4: Very Long Conversation - Natural Fatigue**

```
Exchange 18:
You: "And another thing about my ex..."
Chloe: "You know what, we've been talking for ages and I'm getting
       pretty tired. Let's continue this tomorrow? I need to process
       everything you've shared."

// Algorithm: departureChance = 80% (18 exchanges = natural fatigue)
// LLM: Generated natural exit acknowledging conversation length

[Chloe heads to bedroom to rest]
```

### Conversation Flow Summary

```javascript
async function handleConversation(player, npc) {
  const conversationHistory = []
  let exchangeCount = 0

  while (true) {
    // FIRST EXCHANGE: Player picks from static intent menu
    if (exchangeCount === 0) {
      const intent = await showStaticIntentMenu(npc, player)
      // Shows: Flirt, Go Deep, Banter, Supportive, Graft, etc.

      const exchange = await generateExchange(intent, player, npc, conversationHistory)
      conversationHistory.push(exchange)

      displayExchange(exchange)
      applyMechanicalEffects(exchange, player, npc)

      exchangeCount++
    }

    // SUBSEQUENT EXCHANGES: Contextual follow-ups
    else {
      const lastExchange = conversationHistory[conversationHistory.length - 1]

      // Check if NPC wants to leave (hybrid system)
      const departureChance = calculateNPCDepartureChance(
        { exchangeCount, history: conversationHistory },
        npc,
        gameState
      )

      const followUpOptions = await generateContextualOptions(
        lastExchange,
        player,
        npc,
        departureChance
      )

      // LLM might decide NPC leaves
      if (followUpOptions === null || followUpOptions.npcLeft) {
        displayNPCDeparture(followUpOptions.departureDialogue)
        break
      }

      // Show contextual menu to player
      const choice = await showFollowUpMenu(followUpOptions)

      // Player can always choose to leave
      if (choice.intent === "end_conversation") break

      const exchange = await generateExchange(
        choice.intent,
        player,
        npc,
        conversationHistory,
        departureChance
      )

      conversationHistory.push(exchange)
      displayExchange(exchange)
      applyMechanicalEffects(exchange, player, npc)

      // Check if NPC decided to leave after this exchange
      if (!exchange.npcWantsToContinue) {
        displayNPCDeparture(exchange.npcDialogue)
        break
      }

      exchangeCount++
    }
  }

  // Return to location menu
  const totalTime = conversationHistory.reduce((sum, ex) => sum + ex.timeCost, 0)
  advanceTime(totalTime)

  return conversationHistory
}
```

### Why This System Works

**✅ Natural conversation flow**
- No arbitrary hard cap
- Conversations end when they should (boring, external factors, natural fatigue)
- Deep conversations can continue as long as both parties engaged

**✅ Player agency maintained**
- Player always chooses intent (not reading a script)
- Player can end anytime via "End conversation" option
- Clear stat usage shown for each option

**✅ NPC autonomy**
- NPCs feel alive (they have agency to leave)
- Departures feel natural and justified
- External world affects conversations (drama, needs, other NPCs)

**✅ Encourages deep connections**
- Low departure chance when conversation going well
- Game rewards vulnerable, engaging exchanges
- Aligns with game goal: forming genuine relationships

**✅ Prevents exploitation**
- Natural fatigue after very long talks (10-15+ exchanges)
- Boring/repetitive conversations end quickly
- NPCs have other needs and relationships

**✅ Algorithm + LLM balance**
- Algorithm provides structure (objective departure probability)
- LLM adds flavor (natural exit dialogue, contextual awareness)
- Deterministic enough to balance, organic enough to feel real

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

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 06-Location-System.md for spatial gameplay and villa layout

**Note:** For conversation interruptions ("pull for a chat"), group conversations, and movement interceptions, see **09-Social-Dynamics.md**
