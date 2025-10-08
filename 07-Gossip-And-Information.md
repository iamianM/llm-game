# Gossip and Information Systems

*Knowledge architecture, information flow, and the fog of war*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Information Architecture](#information-architecture)
- [What the Player Sees](#what-the-player-sees)
- [Knowledge System](#knowledge-system)
- [The Gossip System](#the-gossip-system)
- [Gossip Propagation](#gossip-propagation)
- [Gossip Mechanics](#gossip-mechanics)
- [Strategic Uses of Information](#strategic-uses-of-information)
- [FOMO and Time Pressure](#fomo-and-time-pressure)

---

## Information Architecture

### Core Principle: Imperfect Information

**NOT a fully transparent game:**

Players don't see everything. Information is a resource.

**What creates strategy:**
- ❌ You don't know what others are doing right now
- ❌ You don't know NPC relationship numbers
- ❌ You don't know what happened elsewhere while you were busy
- ✅ You must gather information through observation and gossip
- ✅ You must infer NPC feelings from dialogue and behavior
- ✅ You must make decisions with incomplete information

**Why this matters:**
- Creates value for social intelligence
- Makes friendship strategically important (friends share info)
- Creates emergent gameplay (discovery, surprise, betrayal)
- Prevents "solving" the game mechanically

---

## What the Player Sees

### Visible Information

**✅ Villa Map with Islander Positions**

```
VILLA MAP

🏊 Pool (4/8)                    [YOU ARE HERE]
   • You
   • Chloe (sunbathing)
   • Marcus (swimming)
   • Sophie (chatting)

💪 Gym (1/4)
   • Liam (working out)

🍳 Kitchen (2/6)
   • Aisha (making coffee)
   • Tom (cooking)
```

Player knows:
- ✅ Where everyone is
- ✅ What activity they're doing (sunbathing, swimming, etc.)
- ✅ How many people at each location

Player doesn't know:
- ❌ WHO they're talking to (unless you observe directly)
- ❌ WHAT they're talking about
- ❌ Their mood (unless you interact)

**✅ Your Current Location (Detailed View)**

```
You're at the POOL

You can see:
• Chloe is sunbathing on a lounger, looking content
• Marcus and Sophie are in the pool, talking quietly
• They seem to be having a serious conversation

Talk to:
→ Chloe
→ Marcus
→ Sophie
```

Player knows:
- ✅ Who's here
- ✅ General mood (from observation)
- ✅ Who's talking to who (if visible)
- ✅ General vibe ("serious conversation", "laughing together")

Player doesn't know:
- ❌ Exact dialogue
- ❌ What they're discussing
- ❌ Relationship changes happening

**✅ Your Own Stats**

```
YOUR STATS

Charm: 7/10
Banter: 6/10
Graft: 5/10
Loyalty: 8/10
Emotional Intelligence: 6/10
Physical: 5/10

Public Perception: 68/100
```

**✅ Your Relationships (Numbers)**

```
Relationship with Chloe
💕 Affection: 65
⚡ Chemistry: 58
🛡️ Trust: 72
👥 Friendship: 55
⚠️ Animosity: 0
📖 Familiarity: 45

Couple Strength: 68 (Strong)
```

**✅ Recent Events (That You Witnessed or Heard About)**

```
RECENT EVENTS

Day 4, Evening:
• You kissed Chloe on the terrace

Day 4, Night:
• Liam told you: "Marcus and Sophie argued in the bedroom"
  Source: Liam (witnessed it)
  Reliability: High

Day 5, Morning:
• You saw: Aisha and Tom chatting closely at the kitchen
```

### Hidden Information

**❌ NPC Relationship Numbers**

Player doesn't see:
- Marcus's affection for Sophie: 45
- Sophie's trust in Marcus: 38
- Aisha's chemistry with Player: 62

**Why:** Must be inferred from dialogue and behavior

**❌ NPC Preferences (Until Discovered)**

```
Chloe's Type on Paper: (HIDDEN until familiarity 40+)
Physical: ???
Personality: ???
Values: ???
Dealbreakers: ???
```

Unlocks as familiarity increases.

**❌ Other People's Conversations**

Unless you:
- Witness it directly (same location, paying attention)
- Hear gossip about it
- Ask someone what happened

**❌ What Happened While You Were Busy**

```
While you were talking to Chloe (20 min):
• Marcus pulled Aisha for a chat (you don't know)
• Liam and Sophie had coffee (you don't know)
• Tom moved from kitchen to gym (you can see on map)
```

You only know:
- Location changes (visible on map)
- What people tell you (gossip)

---

## Knowledge System

### Knowledge Fact Schema

```typescript
interface KnowledgeFact {
  id: string
  fact: string              // "Marcus kissed Aisha on the terrace"
  type: "event" | "preference" | "secret" | "opinion"

  // PARTICIPANTS
  participants: string[]     // ["marcus", "aisha"]

  // SOURCE
  originalSource: "witnessed" | "confession" | "rumor" | "caught"
  originalWitnesses: string[]  // Who directly saw it

  // TIMESTAMP
  timestamp: {
    day: number
    phase: string
  }
  location: string

  // METADATA
  juiciness: number          // 0-100, how dramatic/interesting
  isSecret: boolean          // Should NPCs hide this?
  reliability: number        // 0-100, how accurate is this?

  // PROPAGATION (who knows)
  knownBy: Array<{
    islanderId: string
    learnedFrom: string | null  // null if witnessed, islander ID if gossip
    learnedDay: number
    willingnessToShare: number  // 0-100
    hasSharedWith: string[]     // Who they've told
  }>
}
```

### Example Knowledge Facts

**Event: Marcus kissed Aisha**

```javascript
{
  id: "kiss_marcus_aisha_day4",
  fact: "Marcus kissed Aisha on the terrace",
  type: "event",

  participants: ["marcus", "aisha"],

  originalSource: "witnessed",
  originalWitnesses: ["player"],

  timestamp: { day: 4, phase: "evening" },
  location: "terrace",

  juiciness: 85, // very dramatic (Marcus coupled with Sophie!)
  isSecret: false, // not intentionally hidden
  reliability: 100, // player saw it directly

  knownBy: [
    {
      islanderId: "player",
      learnedFrom: null, // witnessed
      learnedDay: 4,
      willingnessToShare: 80, // likely to gossip
      hasSharedWith: []
    }
  ]
}
```

**Preference: Chloe's Type**

```javascript
{
  id: "chloe_type_physical",
  fact: "Chloe is attracted to tall, athletic guys with good smiles",
  type: "preference",

  participants: ["chloe"],

  originalSource: "confession",
  originalWitnesses: [],

  timestamp: { day: 2, phase: "afternoon" },
  location: "pool",

  juiciness: 30, // mildly interesting
  isSecret: false,
  reliability: 100, // she told you directly

  knownBy: [
    {
      islanderId: "player",
      learnedFrom: null, // she told player directly
      learnedDay: 2,
      willingnessToShare: 50, // might tell others
      hasSharedWith: []
    }
  ]
}
```

**Secret: Chloe's Insecurity**

```javascript
{
  id: "chloe_secret_fear",
  fact: "Chloe fears she's too much for people and will end up alone",
  type: "secret",

  participants: ["chloe"],

  originalSource: "confession",
  originalWitnesses: [],

  timestamp: { day: 6, phase: "evening" },
  location: "terrace",

  juiciness: 60, // personal, vulnerable
  isSecret: true, // Chloe doesn't want others to know
  reliability: 100,

  knownBy: [
    {
      islanderId: "player",
      learnedFrom: null,
      learnedDay: 6,
      willingnessToShare: 10, // very unlikely to share (it's personal)
      hasSharedWith: []
    }
  ]
}
```

### Player Knowledge Storage

```javascript
player.knowledge = [
  {
    fact: "Marcus kissed Aisha",
    source: "witnessed",
    day: 4,
    reliability: "confirmed" // witnessed directly
  },
  {
    fact: "Marcus and Sophie argued about trust",
    source: "gossip",
    sourceIslander: "liam",
    day: 5,
    reliability: "rumor" // heard from someone else
  },
  {
    fact: "Chloe dreams of opening a cafe",
    source: "conversation",
    day: 2,
    reliability: "confirmed" // she told you
  }
]
```

---

## The Gossip System

### How Gossip Works

**Flow:**

1. **Event happens** (Marcus kisses Aisha)
2. **Witnesses added to knowledge** (Player witnessed it)
3. **Player can share gossip** with others
4. **NPCs decide whether to share** based on personality + relationship
5. **Gossip spreads through network**
6. **Player can gather gossip** by asking others

### Gossip Availability Calculation

```javascript
function getAvailableGossip(speaker, listener) {
  const availableGossip = []

  for (let knowledge of speaker.knowledge) {
    // 1. Skip if listener already knows
    if (listenerAlreadyKnows(listener, knowledge.id)) {
      continue
    }

    // 2. Calculate willingness to share
    let shareChance = knowledge.willingnessToShare // base 0-100

    // Relationship bonuses
    shareChance += speaker.relationships[listener.id].friendship / 2 // 0-50
    shareChance += speaker.relationships[listener.id].trust / 3 // 0-33

    // Personality modifiers
    if (speaker.personality.agreeableness > 7) {
      shareChance += 10 // agreeable people share more
    }

    if (speaker.personality.extraversion > 8) {
      shareChance += 15 // extraverts love to gossip
    }

    // Low agreeableness = less likely to share
    if (speaker.personality.agreeableness < 4) {
      shareChance -= 15
    }

    // Juiciness bonus (dramatic gossip is more likely to be shared)
    if (knowledge.juiciness > 70) {
      shareChance += 10
    }

    // Secret penalty
    if (knowledge.isSecret) {
      shareChance -= 30 // much less likely
    }

    // Check if they'll share
    if (shareChance > 30) { // threshold
      availableGossip.push({
        knowledge: knowledge,
        shareChance: shareChance,
        speaker: speaker.id
      })
    }
  }

  return availableGossip
}
```

### Gossip Menu

**When talking to Liam:**

```
Talk to Liam

Friendly: 💬
→ Ask how he's doing
→ Chat about the villa

Banter: 😄
→ Tell a joke
→ Roast him playfully

Gossip: 🗨️
→ "Heard any drama lately?" (General)
→ Ask about Marcus (Liam knows something - 85% chance to share)
→ Ask about Aisha (Liam knows something - 60% chance to share)
→ Ask about the new bombshell
```

**Player selects: "Ask about Marcus"**

```javascript
// Algorithm rolls
const gossip = getGossipAbout(liam, "marcus")
const shareChance = gossip.shareChance // 85%

const roll = random(1, 100)
const willShare = roll <= 85 // true

if (willShare) {
  // LLM generates gossip delivery
  const dialogue = await generateGossipDialogue({
    speaker: liam,
    fact: gossip.knowledge.fact,
    target: "marcus",
    relationship: liam.relationships.player
  })

  // Add to player knowledge
  player.knowledge.push({
    fact: gossip.knowledge.fact,
    source: "gossip",
    sourceIslander: "liam",
    day: currentDay,
    reliability: "rumor"
  })

  // Update gossip propagation
  gossip.knowledge.knownBy.push({
    islanderId: "player",
    learnedFrom: "liam",
    learnedDay: currentDay,
    willingnessToShare: calculatePlayerWillingnessToShare(gossip.knowledge),
    hasSharedWith: []
  })

  // Mark that Liam shared it
  const liamKnowledge = gossip.knowledge.knownBy.find(k => k.islanderId === "liam")
  liamKnowledge.hasSharedWith.push("player")

  return dialogue
}
```

**LLM Prompt:**

```
You are Liam, talking to the player.

Liam's personality: Loyal, bit of a gossip, casual bro-y vibe.

The player asked about Marcus.

Fact you know: Marcus kissed Aisha on the terrace last night
You witnessed it yourself.

Your relationship with player:
- Friendship: 75 (good friends)
- Trust: 65

Context: You're at the gym, just you two.

Generate 2-3 lines revealing this gossip in Liam's voice.
- Casual, bro-y language
- Maybe a bit disapproving of Marcus (he's coupled with Sophie)
- Feel free to add Liam's opinion

Format: Just natural dialogue.
```

**LLM Returns:**

```
Liam leans in and lowers his voice. "Mate, I probably shouldn't say this, but... I saw Marcus and Aisha on the terrace last night. Properly going at it."

He shakes his head. "Sophie has no idea. That's gonna blow up."
```

**Player sees:**

```
You ask Liam about Marcus.

Liam leans in and lowers his voice. "Mate, I probably shouldn't say this, but... I saw Marcus and Aisha on the terrace last night. Properly going at it."

He shakes his head. "Sophie has no idea. That's gonna blow up."

📚 New Information Learned:
"Marcus kissed Aisha" (Source: Liam - rumor)

💬 Friendship +3 (Liam trusts you with gossip)

⏰ 20 minutes passed
```

---

## Gossip Propagation

### How Gossip Spreads

**Example propagation chain:**

**Day 4, Evening:**
- Marcus kisses Aisha on terrace
- Player witnesses it

```javascript
knowledge.knownBy = [
  { islanderId: "player", learnedFrom: null, ... }
]
```

**Day 5, Morning:**
- Player tells Liam

```javascript
knowledge.knownBy = [
  { islanderId: "player", learnedFrom: null, hasSharedWith: ["liam"] },
  { islanderId: "liam", learnedFrom: "player", ... }
]
```

**Day 5, Afternoon:**
- Liam tells Chloe (autonomously, during their conversation)

```javascript
knowledge.knownBy = [
  { islanderId: "player", learnedFrom: null, hasSharedWith: ["liam"] },
  { islanderId: "liam", learnedFrom: "player", hasSharedWith: ["chloe"] },
  { islanderId: "chloe", learnedFrom: "liam", ... }
]
```

**Day 5, Evening:**
- Chloe tells Sophie (because Sophie is her friend and deserves to know)

```javascript
knowledge.knownBy = [
  { islanderId: "player", learnedFrom: null, hasSharedWith: ["liam"] },
  { islanderId: "liam", learnedFrom: "player", hasSharedWith: ["chloe"] },
  { islanderId: "chloe", learnedFrom: "liam", hasSharedWith: ["sophie"] },
  { islanderId: "sophie", learnedFrom: "chloe", ... }
]
```

**Day 6, Morning:**
- Sophie confronts Marcus (DRAMA!)

**Result:** Gossip that started with player witnessing something creates villa-wide drama.

### NPC Gossip Sharing (Autonomous)

```javascript
function simulateNPCGossipSharing(npc1, npc2) {
  // During NPC-to-NPC conversation, they might share gossip

  const npc1Gossip = getAvailableGossip(npc1, npc2)

  for (let gossip of npc1Gossip) {
    const roll = random(100)

    if (roll < gossip.shareChance) {
      // NPC1 shares with NPC2

      // Add to NPC2's knowledge
      npc2.knowledge.push({
        fact: gossip.knowledge.fact,
        source: "gossip",
        sourceIslander: npc1.id,
        timestamp: { day: currentDay, phase: currentPhase },
        reliability: calculateReliability(gossip.knowledge, npc1, npc2)
      })

      // Update propagation
      gossip.knowledge.knownBy.push({
        islanderId: npc2.id,
        learnedFrom: npc1.id,
        learnedDay: currentDay,
        willingnessToShare: calculateNPCWillingnessToShare(npc2, gossip.knowledge),
        hasSharedWith: []
      })

      // Mark that NPC1 shared it
      const npc1Knowledge = gossip.knowledge.knownBy.find(k => k.islanderId === npc1.id)
      npc1Knowledge.hasSharedWith.push(npc2.id)

      // Generate event
      createGossipEvent(npc1, npc2, gossip.knowledge)
    }
  }
}
```

### Reliability Decay

Gossip becomes less reliable as it spreads:

```javascript
function calculateReliability(knowledge, speaker, listener) {
  let reliability = knowledge.reliability // original reliability (0-100)

  // Each link in chain reduces reliability
  const chainLength = getGossipChainLength(knowledge, speaker)
  reliability -= chainLength * 10 // -10 per link

  // Speaker's reliability affects it
  const speakerReliability = speaker.stats.emotional_intelligence * 10 // 0-100
  reliability = (reliability + speakerReliability) / 2

  // Listener's agreeableness affects how much they trust it
  const listenerSkepticism = (10 - listener.personality.agreeableness) * 5 // 0-50
  reliability -= listenerSkepticism

  return Math.max(20, Math.min(100, reliability)) // clamp
}

function getGossipChainLength(knowledge, speaker) {
  const speakerKnowledge = knowledge.knownBy.find(k => k.islanderId === speaker.id)

  if (!speakerKnowledge.learnedFrom) {
    return 0 // witnessed directly
  }

  // Count links: A witnessed → told B → told C → told speaker
  let chain = 1
  let current = speakerKnowledge.learnedFrom

  while (current) {
    const link = knowledge.knownBy.find(k => k.islanderId === current)
    if (!link || !link.learnedFrom) break
    chain++
    current = link.learnedFrom
  }

  return chain
}
```

**Example:**

```
Marcus kisses Aisha
↓
Player witnesses (reliability: 100)
↓
Player tells Liam (reliability: 95 - slight uncertainty in retelling)
↓
Liam tells Chloe (reliability: 85 - second-hand)
↓
Chloe tells Sophie (reliability: 70 - third-hand)
```

Sophie might doubt it or ask for confirmation.

---

## Gossip Mechanics

### Strategic Gossip Use

**1. Weaponized Gossip (Creating Drama)**

Player can reveal damaging information:

```
Talk to Sophie

⚠️ Confrontational:
→ "I heard something about Marcus..." (Reveal gossip)
```

**Effect:**
- Sophie learns Marcus kissed Aisha
- Sophie's trust in Marcus plummets
- Sophie's animosity toward Aisha increases
- Creates public drama (affects villa state)
- Player's public perception might drop (seen as troublemaker)

```javascript
function revealGossip(gossipId, target) {
  const gossip = getKnowledgeById(gossipId)

  // Target learns information
  target.knowledge.push({
    fact: gossip.fact,
    source: "told_directly",
    sourceIslander: "player",
    day: currentDay,
    reliability: "confirmed" // player told them directly
  })

  // SIDE EFFECTS

  // If gossip is about their partner
  if (gossip.participants.includes(target.coupledWith)) {
    // Massive trust damage
    const partner = getIslanderById(target.coupledWith)
    target.relationships[partner.id].trust -= 25
    target.relationships[partner.id].animosity += 15

    // Mood change
    target.mood = "angry"

    // Create confrontation event
    scheduleEvent({
      type: "confrontation",
      day: currentDay,
      phase: "next_available",
      participants: [target.id, partner.id],
      trigger: gossip.fact
    })
  }

  // If gossip involves another Islander
  if (gossip.participants.length > 1) {
    const otherPerson = gossip.participants.find(id => id !== target.id)
    if (otherPerson) {
      target.relationships[otherPerson].animosity += 10
    }
  }

  // Public perception impact (depends on how others view this)
  if (gossip.juiciness > 70) {
    player.publicPerception -= 5 // seen as stirring drama
  }

  // Generate LLM reaction
  const reaction = await generateGossipReaction(target, gossip)

  return {
    reaction: reaction,
    dramaTrigger: true,
    relationshipChanges: { /* ... */ }
  }
}
```

**2. Protective Gossip (Warning Allies)**

Player can warn friends:

```
Talk to Chloe

🗨️ Gossip:
→ "Just so you know, Aisha has been asking about your relationship..."
```

**Effect:**
- Chloe learns Aisha is a threat
- Chloe prepares to defend relationship
- Chloe's trust in player increases (you looked out for her)

**3. Intelligence Gathering**

Player asks around to learn villa state:

```
Talk to Liam

🗨️ Gossip:
→ "What's the vibe in the villa lately?"
→ "Heard any drama?"
→ "How are Marcus and Sophie doing?"
```

**Effect:**
- Player learns about events they missed
- Can make informed strategic decisions
- Builds friendship with gossip source

### Gossip as Currency

Gossip has strategic value:

**High-value gossip:**
- "Marcus kissed someone else" (partner betrayal)
- "Sophie is planning to recouple" (strategic intel)
- "Aisha is fake" (reputation damage)

**Low-value gossip:**
- "Tom likes the gym" (trivial)
- "Chloe ate cereal for breakfast" (boring)

**Trading gossip:**
```javascript
// NPC more likely to share if you share first
function gossipReciprocity(player, npc) {
  if (playerSharedGossipRecently(player, npc)) {
    // Bonus to gossip sharing chance
    return +20
  }
  return 0
}
```

---

## Strategic Uses of Information

### Scenario 1: Preventing Betrayal

**Situation:**
- You're coupled with Chloe
- Liam tells you: "Marcus is planning to graft on Chloe tonight"

**Options:**

A) **Confront Marcus (aggressive)**
- Increases animosity with Marcus
- Might scare him off
- Creates public drama

B) **Reassure Chloe (defensive)**
- Increases trust with Chloe
- Makes her less receptive to Marcus
- No drama

C) **Tell Chloe about Marcus's plan (transparent)**
- Chloe knows and can choose
- Shows trust in her
- Might create drama

D) **Do nothing (risky)**
- See what happens
- Test Chloe's loyalty
- Could backfire

**Strategic decision based on incomplete information.**

### Scenario 2: Capitalizing on Drama

**Situation:**
- You witnessed Sophie and Marcus arguing
- Sophie is upset and vulnerable
- You're interested in Sophie

**Options:**

A) **Comfort Sophie immediately**
- Good timing (she's vulnerable)
- Might build connection
- Risky (Marcus will be angry)

B) **Wait and comfort later**
- Safer (less obvious)
- Might miss window

C) **Tell others about the argument**
- Spreads gossip
- Damages Sophie's reputation
- Might help you (if Sophie gets dumped, you can recouple)

D) **Help them reconcile**
- Builds friendship with both
- Earns trust
- But eliminates romantic opportunity with Sophie

### Scenario 3: Using Secret Knowledge

**Situation:**
- Chloe told you her secret fear (being alone)
- She's feeling insecure about new bombshell

**Options:**

A) **Use it to reassure her (positive)**
- "I know you worry about this, but you're not too much"
- Massive trust boost
- Shows emotional intelligence

B) **Weaponize it (malicious)**
- Tell others her secret
- Damages her reputation
- Massive trust loss if she finds out

C) **Keep it private (neutral)**
- Don't use it at all
- Respect her privacy

**Ethical choices with mechanical consequences.**

---

## FOMO and Time Pressure

### What You Miss While Busy

**While talking to Chloe (20 min):**

Simulated events elsewhere:
```javascript
// NPC behavior simulation runs
simulateNPCBehavior(20)

// Events that might happen:
- Marcus pulls Aisha for a chat (builds chemistry)
- Liam and Sophie gossip about you (spreads info)
- Tom moves to gym (visible on map)
- New knowledge created (you don't learn until later)
```

**You find out later through:**

```
Talk to Liam

"Mate, while you were with Chloe, Marcus and Aisha were all over each other by the pool. Just thought you should know."
```

**This creates:**
- ✅ FOMO (fear of missing out)
- ✅ Strategic choice (who to spend time with)
- ✅ Replayability (different choices = different discoveries)

### Information Advantage

**Players with high friendship:**
- Get more gossip
- Learn about threats earlier
- Can make better strategic decisions

**Players who spread out interactions:**
- Talk to more people = more intel
- But shallow relationships

**Players who focus on one person:**
- Deep relationship
- But miss villa dynamics
- Might be blindsided

**Tradeoff creates strategy.**

---

## Implementation Details

### Gossip Data Structure

```javascript
// Global gossip network
const villaKnowledge = {
  facts: [
    {
      id: "kiss_marcus_aisha_day4",
      fact: "Marcus kissed Aisha",
      type: "event",
      participants: ["marcus", "aisha"],
      timestamp: { day: 4, phase: "evening" },
      location: "terrace",
      juiciness: 85,
      isSecret: false,
      reliability: 100,
      knownBy: [
        {
          islanderId: "player",
          learnedFrom: null,
          learnedDay: 4,
          willingnessToShare: 80,
          hasSharedWith: ["liam"]
        },
        {
          islanderId: "liam",
          learnedFrom: "player",
          learnedDay: 5,
          willingnessToShare: 90,
          hasSharedWith: ["chloe"]
        }
      ]
    }
  ]
}
```

### Query Functions

```javascript
// Get all gossip that speaker can share with listener
function getShareableGossip(speaker, listener) {
  return villaKnowledge.facts.filter(fact => {
    // Speaker knows it
    const speakerKnows = fact.knownBy.some(k => k.islanderId === speaker.id)
    if (!speakerKnows) return false

    // Listener doesn't know it
    const listenerKnows = fact.knownBy.some(k => k.islanderId === listener.id)
    if (listenerKnows) return false

    // Speaker is willing to share
    const speakerKnowledge = fact.knownBy.find(k => k.islanderId === speaker.id)
    return speakerKnowledge.willingnessToShare > 30
  })
}

// Check if player knows a fact
function playerKnows(factId) {
  const fact = villaKnowledge.facts.find(f => f.id === factId)
  if (!fact) return false

  return fact.knownBy.some(k => k.islanderId === "player")
}

// Get all facts about a specific Islander
function getFactsAbout(islanderId) {
  return villaKnowledge.facts.filter(fact =>
    fact.participants.includes(islanderId)
  )
}
```

---

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 08-Daily-Loop.md for run structure and pacing
