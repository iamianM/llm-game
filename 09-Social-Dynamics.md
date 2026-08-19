# Social Dynamics

*Interruptions, movement interceptions, and group conversations*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Overview](#overview)
- [The Pull System](#the-pull-system)
- [Conversation Interruptions](#conversation-interruptions)
- [Movement Interceptions](#movement-interceptions)
- [Group Conversations](#group-conversations)
- [NPC Interruption Behavior](#npc-interruption-behavior)
- [Strategic Implications](#strategic-implications)

---

## Overview

### Core Paradise Hearts Dynamics

**The "Private Chat"** is essential to Paradise Hearts:
- Heart Throbs steal people mid-conversation
- Partners get interrupted by rivals
- Drama happens when pulls are blocked
- Public vs. private interruptions matter

**Three systems:**
1. **Conversation Interruptions** - Someone pulls your partner (or you) away
2. **Movement Interceptions** - Someone stops you while walking
3. **Group Conversations** - Multiple people chatting together

---

## The Pull System

### When NPCs Interrupt

**Triggers for interruption:**

```javascript
function shouldNPCInterrupt(npc, targetConversation) {
  let interruptChance = 0

  // 1. ROMANTIC INTEREST
  if (npc.interests.includes(targetConversation.participant.id)) {
    interruptChance += 40  // wants to spark

    // Higher if target is their "type"
    if (matchesPreferences(targetConversation.participant, npc.preferences)) {
      interruptChance += 20
    }
  }

  // 2. STRATEGIC TIMING
  if (resortState.scheduledEvents.some(e => e.type === "pairing_ceremony" && e.day === resortState.currentDay)) {
    interruptChance += 30  // urgency before Pairing Ceremony
  }

  // 3. PERSONALITY
  interruptChance += npc.stats.spark * 3  // 0-30 based on spark stat
  interruptChance += (npc.personality.extraversion - 5) * 2  // -10 to +10

  // 4. RELATIONSHIP WITH CONVERSATION PARTNER
  if (targetConversation.otherPerson === "player" && npc.animosity.player > 50) {
    interruptChance += 25  // wants to disrupt player's conversation
  }

  // 5. CURRENT MOOD
  if (npc.mood === "anxious" && npc.coupledWith === targetConversation.participant.id) {
    interruptChance += 35  // worried partner checking in
  }

  // 6. LOCATION (less likely to interrupt in private areas)
  if (targetConversation.location.privacy === "private") {
    interruptChance -= 40
  }

  return Math.max(0, Math.min(90, interruptChance))
}
```

**Example scenarios:**

```javascript
// Scenario 1: Heart Throb sparking
const aisha = {
  interests: ["player"],
  stats: { spark: 9 },
  personality: { extraversion: 9 }
}

// Player is talking to Chloe at pool (public)
shouldNPCInterrupt(aisha, { participant: player, location: pool })
// Returns: 40 (romantic interest) + 27 (spark) + 8 (extraversion) = 75% chance

// Scenario 2: Anxious partner
const chloe = {
  mood: "anxious",
  coupledWith: "player",
  attachmentStyle: "anxious"
}

// Player is talking to Aisha
shouldNPCInterrupt(chloe, { participant: player, otherPerson: aisha })
// Returns: 35 (anxious partner) + base = ~50% chance

// Scenario 3: Private conversation (low chance)
// Player and Chloe on terrace (private)
shouldNPCInterrupt(aisha, { participant: player, location: terrace })
// Returns: 75% - 40 (private location) = 35% chance
```

---

## Conversation Interruptions

### Scenario 1: Someone Pulls Your Partner Away

**Setup:**
```javascript
{
  situation: "interruption",
  target: chloe,  // your partner
  interrupter: aisha,  // Heart Throb
  playerCurrentlyTalking: true,
  location: pool  // public
}
```

**Display:**
```
You're talking to Chloe at the pool.

Aisha approaches with a smile.

"Chloe, can I borrow you for a quick chat?"

Chloe looks at you, waiting for your reaction.

What do you do?
```

### Player Options

#### Option A: Allow (Respectful)

```javascript
{
  action: "allow_interruption",
  label: "\"Yeah, of course. Catch up later, Chloe.\"",
  tone: "respectful",

  immediate_effects: {
    chloe_trust: +3,        // respects your confidence
    chloe_mood: "neutral",
    aisha_animosity: 0,      // no conflict created
    pulse: +2    // mature, confident behavior
  },

  outcome: "conversation_ends",
  next_state: {
    chloe_location: "pool",
    chloe_activity: "talking_to_aisha",
    aisha_location: "pool",
    aisha_activity: "talking_to_chloe",
    player_free: true
  },

  risks: [
    "Aisha can spark with Chloe without interference",
    "Chloe might be swayed if Aisha is persuasive",
    "No control over what they discuss"
  ],

  time_cost: 0  // your conversation ends
}
```

**LLM Prompt:**
```
You are generating the outcome of a Paradise Hearts interruption.

Situation: Player allowed Aisha to pull Chloe away for a chat.

Chloe's reaction to player allowing it:
- Personality: Secure attachment, confident
- Relationship: Trusts player (trust 72)
- Feels: Appreciates the confidence

Generate 2-3 lines showing:
- Chloe's response to player
- Her going with Aisha
- Player's observation

Tone: Positive, confident couple dynamic
```

**Returns:**
```
Chloe smiles at you. "Thanks, babe. I'll be right back."

She stands up and walks off with Aisha toward the loungers.

You notice Aisha glancing back at you with a slight smirk.
```

---

#### Option B: Request Delay (Defensive)

```javascript
{
  action: "request_delay",
  label: "\"Can we have a few more minutes? We're in the middle of something.\"",
  tone: "defensive",
  risky: true,

  success_check: {
    base: 50,
    modifiers: {
      chloe_affection: chloe.relationships.player.affection / 2,  // 0-50
      couple_strength: getCoupleStrength(player, chloe) / 4,      // 0-25
      aisha_spark_penalty: -(aisha.stats.spark * 5),              // -45
      chloe_curiosity: chloeWantsToTalkToAisha ? -20 : 0
    }
  },

  if_success: {
    chloe_trust: +2,
    aisha_animosity: +3,
    aisha_mood: "annoyed",
    extra_time: 10,  // 10 more minutes with Chloe

    outcome: "aisha_backs_off",
    dialogue: "Aisha rolls her eyes but steps back. \"Sure, I'll wait.\" She walks to nearby lounger, watching."
  },

  if_failure: {
    chloe_trust: -2,           // she wanted to go
    chloe_mood: "uncomfortable",
    aisha_animosity: +5,
    pulse: -3,      // looks controlling

    outcome: "chloe_goes_anyway",
    dialogue: "Chloe looks uncomfortable. \"Actually, I should see what she wants.\" She goes with Aisha, glancing back apologetically."
  },

  display_success_chance: true  // show player "~65% chance"
}
```

**Success Calculation Example:**
```javascript
// Player + Chloe: Strong couple (affection 65, couple strength 75)
// Aisha: High spark (9)
// Chloe: Slightly curious about what Aisha wants

const chance = 50  // base
  + (65 / 2)       // +32.5 (affection bonus)
  + (75 / 4)       // +18.75 (couple strength)
  - (9 * 5)        // -45 (Aisha's spark)
  - 20             // -20 (Chloe is curious)

// = 36.25% chance of success

// Low chance - risky move!
```

---

#### Option C: Refuse (Aggressive)

```javascript
{
  action: "block_interruption",
  label: "\"Actually, we're talking right now. Can you wait?\"",
  tone: "aggressive",
  very_risky: true,
  warning: "⚠️ This could backfire badly",

  success_check: {
    base: 30,  // harder than delay
    modifiers: {
      couple_strength: getCoupleStrength(player, chloe) / 2,  // 0-50
      aisha_spark_penalty: -(aisha.stats.spark * 7),          // -63
      public_location_penalty: location.privacy === "public" ? -15 : 0
    }
  },

  if_success: {
    chloe_trust: +5,           // defended relationship
    chloe_affection: +3,
    aisha_animosity: +10,      // made an enemy
    pulse: -5,      // seen as possessive

    outcome: "aisha_walks_away_angry",
    dialogue: "Aisha's eyes narrow. \"Wow, okay.\" She walks away, clearly annoyed. Chloe looks surprised but stays."
  },

  if_failure: {
    chloe_trust: -5,           // embarrassed by you
    chloe_animosity: +3,
    chloe_mood: "angry",
    aisha_animosity: +8,
    pulse: -8,      // looks insecure

    outcome: "major_backfire",
    dialogue: "Chloe stands up abruptly. \"Don't speak for me.\" She walks off with Aisha, clearly annoyed at you. Others are watching.",

    side_effects: {
      witnesses_gossip: true,
      creates_drama_event: {
        type: "public_confrontation",
        participants: ["player", "chloe", "aisha"],
        juiciness: 75
      }
    }
  },

  display_success_chance: true  // "~22% chance - very risky!"
}
```

---

#### Option D: Join Them (Strategic)

```javascript
{
  action: "join_conversation",
  label: "\"Mind if I join? We can all chat.\"",
  tone: "strategic",

  immediate_effects: {
    chloe_reaction: "mixed",      // wanted private chat with Aisha
    aisha_animosity: +5,          // blocked her strategy
    aisha_frustration: true
  },

  outcome: "three_way_conversation",

  new_conversation: {
    type: "group",
    participants: ["player", "chloe", "aisha"],
    tension: "high",
    aisha_can_spark: false  // can't spark effectively with player present
  },

  consequences: {
    positive: "Prevents Aisha from sparking privately",
    negative: "Chloe might be annoyed you didn't give her space",
    awkward: "Three-way conversation is tense"
  },

  time_cost: 20  // 20 min awkward group chat
}
```

---

### Scenario 2: Someone Pulls YOU Away

**Setup:**
```javascript
{
  situation: "pull_player",
  current_partner: chloe,
  interrupter: aisha,
  location: pool
}
```

**Display:**
```
You're talking to Chloe at the pool.

Aisha approaches.

"Hey, can I steal you for a quick chat?"

Chloe's smile fades. She's not happy about this.

What do you do?
```

### Player Options

#### Option A: Go With Them

```javascript
{
  action: "accept_pull",
  label: "\"Sure, yeah. Chloe, I'll be right back.\"",

  effects: {
    // Current partner reaction (calculated dynamically)
    chloe_trust: calculatePartnerReaction(chloe, aisha, player),

    // Interrupter reaction
    aisha_chemistry: +5,
    aisha_affection: +3,
    aisha_mood: "pleased",

    // Public perception
    pulse: player.stats.loyalty > 7 ? 0 : -3  // loyal players less penalized
  },

  outcome: "switch_conversation",

  risks: [
    "Chloe will worry while you're gone",
    "Chloe might spark with someone else (counter-move)",
    "Signals you're open to exploring options"
  ],

  time_cost: 0  // switches conversations
}
```

**Partner Reaction System:**

```javascript
function calculatePartnerReaction(partner, interrupter, player) {
  let trustChange = -5  // base penalty

  // ATTACHMENT STYLE
  if (partner.attachmentStyle === "secure") {
    trustChange = -2  // less worried
    partner.dialogue = "Okay, I'll catch up with you later."
  } else if (partner.attachmentStyle === "anxious") {
    trustChange = -8  // very worried
    partner.mood = "anxious"
    partner.dialogue = "Oh... okay. Don't be too long?"
  } else if (partner.attachmentStyle === "avoidant") {
    trustChange = 0  // doesn't care much
    partner.dialogue = "Sure, whatever."
  }

  // TRUST LEVEL
  if (partner.relationships.player.trust > 70) {
    trustChange += 3  // high trust = less penalty
  } else if (partner.relationships.player.trust < 40) {
    trustChange -= 5  // low trust = big penalty
  }

  // INTERRUPTER THREAT LEVEL
  const interrupterChemistry = interrupter.relationships.player.chemistry
  if (interrupterChemistry > 50) {
    trustChange -= 5  // they see Aisha as a threat
    partner.mood = "jealous"
  }

  // PERSONALITY
  if (partner.personality.neuroticism > 7) {
    trustChange -= 3  // anxious personality
  }

  // STRATEGIC COUNTER-MOVE
  if (partnerHasOtherInterests(partner)) {
    partner.counter_spark = true
    partner.dialogue = "Sure. Actually, I might go chat with Marcus while you're gone."
    trustChange = 0  // neutral - they'll use the time too
  }

  return trustChange
}
```

**Example outcomes:**

```javascript
// Scenario A: Secure Chloe (high trust)
{
  chloe_trust: -2,
  chloe_mood: "neutral",
  chloe_dialogue: "Okay babe, I'll be here. Don't be too long.",
  chloe_action: "wait_at_pool"
}

// Scenario B: Anxious Chloe (low trust, sees Aisha as threat)
{
  chloe_trust: -13,  // -8 (anxious) -5 (low trust) = -13
  chloe_mood: "anxious",
  chloe_dialogue: "Oh... okay. Don't be too long?",
  chloe_action: "worry",
  chloe_internal_state: {
    insecurity_triggered: true,
    might_seek_reassurance_from: "emma"  // friend
  }
}

// Scenario C: Strategic Chloe (has other options)
{
  chloe_trust: 0,
  chloe_mood: "strategic",
  chloe_dialogue: "Sure. Actually, I might go chat with Marcus while you're gone.",
  chloe_action: "spark_on_marcus",  // counter-move!
  creates_drama: true
}
```

---

#### Option B: Delay

```javascript
{
  action: "delay",
  label: "\"Can you give me a few minutes? I'll come find you after.\"",

  effects: {
    chloe_trust: +3,           // prioritized her
    chloe_affection: +2,
    aisha_reception: "mixed",   // she'll wait but annoyed
    aisha_mood: "impatient"
  },

  outcome: "promise_to_talk_later",

  followup: {
    obligation: "must_talk_to_aisha_later",
    time_window: "within_30_min",
    if_ignored: {
      aisha_animosity: +10,
      aisha_interest: -15,  // might move on
      pulse: -5  // seen as rude
    }
  },

  time_cost: 0  // finish current conversation first
}
```

---

#### Option C: Refuse

```javascript
{
  action: "decline",
  label: "\"Actually, I'm good here. Maybe later?\"",
  tone: "loyal",

  effects: {
    chloe_trust: +7,           // strong loyalty signal
    chloe_affection: +4,
    chloe_mood: "secure",

    aisha_animosity: +8,
    aisha_interest: -10,        // might move on to other targets
    aisha_mood: "rejected",

    pulse: {
      if_loyal_player: +5,      // audience loves loyalty
      if_exploring: -3          // or looks scared of temptation
    }
  },

  outcome: "aisha_rebuffed",

  dialogue_variants: {
    if_aisha_persistent: "Aisha looks surprised. \"Seriously? Your loss.\" She walks away.",
    if_aisha_graceful: "Aisha shrugs. \"No worries, another time.\"",
  }
}
```

---

#### Option D: Include Partner

```javascript
{
  action: "include_partner",
  label: "\"Chloe can hear whatever you want to say. What's up?\"",
  tone: "transparent",

  effects: {
    chloe_trust: +5,           // transparency appreciated
    aisha_frustration: true,
    aisha_animosity: +5
  },

  outcome: "aisha_decides",

  aisha_decision: {
    if_important: "awkward_three_way_chat",  // she needs to say something
    if_sparking: "backs_off",                // can't spark in front of Chloe

    dialogue_if_backs_off: "Aisha hesitates. \"Actually, never mind. It can wait.\" She walks away, annoyed."
  }
}
```

---

## Movement Interceptions

### When Interceptions Happen

**Not every movement triggers interception.** Only during:

```javascript
function shouldCheckForInterception(movement) {
  // 1. SHORT MOVEMENTS - No check
  if (movement.distance === "adjacent") {
    return false  // pool → kitchen is instant
  }

  // 2. LOW DRAMA PERIODS - Low chance
  if (resortState.metrics.dramaLevel < 30 && resortState.timeRemaining > 60) {
    return random(100) < 10  // 10% chance
  }

  // 3. HIGH STAKES MOMENTS - High chance
  if (resortState.scheduledEvents.some(e => e.type === "pairing_ceremony" && e.day === resortState.currentDay)) {
    return random(100) < 50  // 50% chance - people want to talk before Pairing Ceremony
  }

  // 4. SOMEONE LOOKING FOR YOU
  if (getHeartbreakersLookingForPlayer().length > 0) {
    return random(100) < 70  // 70% chance
  }

  // 5. CROSSING HIGH-TRAFFIC AREAS
  if (movement.path.includes("living_area") || movement.path.includes("pool")) {
    return random(100) < 20  // 20% chance
  }

  return false
}
```

### Interception Flow

```javascript
function handleMovementInterception(player, targetLocation) {
  // 1. Check if interception should happen
  if (!shouldCheckForInterception({ from: player.currentLocation, to: targetLocation })) {
    // No interception - complete movement instantly
    completeMovement(player, targetLocation)
    return
  }

  // 2. Choose interceptor
  const path = calculatePath(player.currentLocation, targetLocation)
  const interceptor = chooseInterceptor(path)

  if (!interceptor) {
    completeMovement(player, targetLocation)
    return
  }

  // 3. Show interception
  showInterception({
    location: path.midpoint,  // where you were intercepted
    interceptor: interceptor,
    reason: determineInterceptionReason(interceptor, player)
  })

  // 4. Player choice
  const choice = await showInterceptionMenu(interceptor)

  // 5. Execute choice
  handleInterceptionChoice(choice, interceptor, targetLocation)
}

function chooseInterceptor(path) {
  const candidatesInArea = getHeartbreakersInArea(path.midpoint)

  if (candidatesInArea.length === 0) return null

  // Weight by motivation to intercept
  const weights = candidatesInArea.map(npc => {
    let weight = 10  // base

    // High chemistry = wants to talk
    weight += npc.relationships.player.chemistry / 5

    // High spark = actively pursuing
    weight += npc.stats.spark * 3

    // Romantic interest
    if (npc.interests.includes("player")) {
      weight += 25
    }

    // Has important info to share
    if (npcHasImportantGossipForPlayer(npc)) {
      weight += 20
    }

    // Needs to warn player
    if (npcWantsToWarnPlayer(npc)) {
      weight += 30
    }

    // Currently upset with player
    if (npc.relationships.player.animosity > 50) {
      weight += 15  // wants to confront
    }

    return weight
  })

  return weightedRandom(candidatesInArea, weights)
}

function determineInterceptionReason(interceptor, player) {
  // Why are they stopping you?

  if (interceptor.interests.includes("player") && !interceptor.coupledWith) {
    return "spark"  // wants to flirt
  }

  if (interceptor.coupledWith === player.id && interceptor.mood === "anxious") {
    return "check_in"  // worried partner
  }

  if (npcHasImportantGossipForPlayer(interceptor)) {
    return "share_info"  // has intel
  }

  if (interceptor.relationships.player.animosity > 60) {
    return "confront"  // wants to address issue
  }

  if (interceptor.relationships.player.friendship > 70) {
    return "friendly_chat"  // just wants to hang
  }

  return "casual"
}
```

### Interception Menu

```javascript
function showInterceptionMenu(interceptor) {
  const reason = determineInterceptionReason(interceptor, player)

  // Generate LLM dialogue for interception
  const dialogue = await generateInterceptionDialogue({
    interceptor: interceptor,
    reason: reason,
    location: player.currentLocation
  })

  // Display
  return showChoiceMenu({
    title: `${interceptor.name} stops you`,
    description: dialogue,

    options: [
      {
        id: "stop",
        label: "Stop and talk (20 min)",
        time: 20,
        description: "Have a full conversation"
      },
      {
        id: "brief",
        label: "Quick chat (5 min)",
        time: 5,
        description: "Hear what they have to say briefly"
      },
      {
        id: "later",
        label: "\"I'll catch up with you later\"",
        time: 2,
        description: "Polite decline, continue to destination"
      },
      {
        id: "ignore",
        label: "Keep walking",
        time: 0,
        description: "⚠️ Ignore them (rude)",
        risky: true
      }
    ]
  })
}
```

### Example Interception

**Scenario: Marcus intercepts you**

```
You're walking from the pool to the kitchen.

As you pass through the living area, Marcus approaches you.

"Hey mate, got a sec? Need to talk to you about something."

He looks serious.

What do you do?
→ Stop and talk (20 min)
→ Quick chat (5 min)
→ "I'll catch you later?" (2 min)
→ Keep walking (ignore)
```

**If player chooses "Quick chat":**

```javascript
{
  action: "brief_chat",
  time: 5,

  outcome: {
    type: "quick_conversation",
    content: await generateBriefInterception({
      interceptor: marcus,
      reason: "share_info",
      timeLimit: 5
    })
  }
}
```

**LLM generates:**

```
You stop briefly.

"Look, I'll keep this quick," Marcus says. "Aisha has been asking a lot about you and Chloe. I think she's planning to make a move before the Pairing Ceremony."

He pats your shoulder. "Just thought you should know, mate."

📚 New Information: Aisha planning to spark with you before Pairing Ceremony

💬 Friendship with Marcus +3

⏰ 5 minutes passed
```

**Player continues to kitchen.**

---

**If player chooses "Ignore":**

```javascript
{
  action: "ignore",
  time: 0,

  effects: {
    marcus_animosity: +5,
    marcus_mood: "upset",
    marcus_dialogue: "Marcus frowns as you walk past. \"Alright then, your loss.\""
  },

  consequences: {
    missed_information: true,  // didn't learn about Aisha
    damaged_relationship: true,
    pulse: -2  // others might have seen
  }
}
```

---

## Group Conversations

### When Groups Form

```javascript
function checkForGroupChat(location) {
  const heartbreakersHere = getHeartbreakersAtLocation(location)

  // Need 2-3 others present (player + 2-3 NPCs = 3-4 total)
  if (heartbreakersHere.length < 2 || heartbreakersHere.length > 3) {
    return null  // no group chat option
  }

  // Check if they're already in a group conversation
  const groupActivity = analyzeGroupActivity(heartbreakersHere)

  if (groupActivity.type === "group_chat") {
    return {
      type: "joinable_group",
      participants: heartbreakersHere,
      activity: groupActivity.description
    }
  }

  return null
}
```

### Group Conversation UI

**When arriving at location:**

```
POOL AREA

You see Chloe, Liam, and Emma sitting together by the pool, chatting and laughing.

They're talking about last night's drama.

What do you do?
→ Join the group chat
→ Pull Chloe aside (private)
→ Pull Liam aside (private)
→ Pull Emma aside (private)
→ Leave pool
```

**If player joins group:**

```
GROUP CHAT
Pool Area

Participants:
• You
• Chloe (your partner)
• Liam (friend)
• Emma (Liam's partner)

Vibe: Relaxed, friendly

Liam is telling a story about his gym fails earlier.
Everyone's laughing.

What do you do?
→ Tell your own funny story (Banter check)
→ Support Liam ("Liam, you're a legend")
→ Flirt with Chloe (in front of others)
→ Share gossip about Marcus (spreads to all)
→ Pull Chloe aside (go private)
→ Leave group
```

### Group Actions

```javascript
const groupActions = {
  tell_joke: {
    label: "Tell a funny story",
    stat: "banter",

    success_check: {
      base: 50,
      stat_bonus: player.stats.banter * 5,
      group_mood_bonus: groupMood === "happy" ? 10 : 0,
      audience_size_penalty: -(participants.length * 5)  // harder with more people
    },

    if_success: {
      all_participants: {
        friendship: +4,
        affection: +2,
        mood: "happy"
      },
      pulse: +3,
      llm_prompt: "Generate group laughing at player's joke"
    },

    if_failure: {
      all_participants: {
        friendship: -2
      },
      awkwardness: true,
      llm_prompt: "Generate awkward silence after bad joke"
    },

    time: 10
  },

  share_gossip: {
    label: "Share resort gossip",
    requires: "have_gossip",

    outcome: {
      spreads_to: "all_participants",  // all learn the gossip

      effects: {
        if_juicy: {
          all_participants: { friendship: +2 },  // interesting info
          pulse: +2
        },
        if_mean: {
          pulse: -5,  // seen as stirring drama
          target_of_gossip: { animosity_from_all: +3 }
        }
      },

      llm_prompt: "Generate group reacting to gossip revelation"
    },

    time: 15
  },

  support_someone: {
    label: "Support someone in the group",
    select_target: true,

    outcome: {
      target: {
        friendship: +6,
        trust: +3,
        mood: "appreciated"
      },
      others: {
        friendship: +1  // being supportive is good
      },

      llm_prompt: "Generate player supporting [target] in group setting"
    },

    time: 10
  },

  public_flirt: {
    label: "Flirt with someone (public)",
    select_target: true,
    requires_relationship: 30,
    risky: true,

    outcome: {
      if_coupled_with_target: {
        target: { chemistry: +3, affection: +2 },
        pulse: +5,  // cute couple
        others: { reaction: "supportive" }
      },

      if_not_coupled: {
        target: { chemistry: +5 },
        pulse: -3,  // playing the field
        current_partner_if_present: { trust: -10, animosity: +8 },  // drama!
        others: { reaction: "awkward" }
      },

      llm_prompt: "Generate public flirting moment in group"
    },

    time: 10
  },

  pull_aside: {
    label: "Pull someone aside (go private)",
    select_target: true,

    outcome: "transition_to_private",

    others_reaction: {
      if_target_coupled: "suspicious",
      if_just_friendly: "neutral"
    },

    time: 0  // transitions to new conversation
  },

  leave_group: {
    label: "Leave group",

    outcome: "end_group_conversation",

    effects: {
      all_participants: { friendship: +1 }  // social interaction bonus
    },

    time: 0
  }
}
```

### Group LLM Integration

**Single LLM call for whole group:**

```javascript
async function executeGroupAction(action, participants) {
  // 1. Calculate outcome (algorithm)
  const result = calculateGroupActionOutcome(action, participants)

  // 2. Apply mechanical changes
  applyGroupEffects(result, participants)

  // 3. Single LLM call for group reaction
  const groupReaction = await generateGroupReaction({
    action: action.type,
    participants: participants.map(p => ({
      name: p.name,
      personality: p.personality,
      relationship_with_player: p.relationships.player
    })),
    outcome: result.success ? "positive" : "negative",
    context: {
      location: player.currentLocation,
      vibe: determineGroupVibe(participants)
    }
  })

  return {
    dialogue: groupReaction,
    mechanicalChanges: result.changes,
    timeCost: action.time
  }
}
```

**Example LLM Prompt:**

```
You are generating a Paradise Hearts group conversation.

Location: Pool
Participants:
- Chloe (24, bubbly, extraverted, player's partner)
- Liam (26, bro-y, funny, player's friend)
- Emma (23, sweet, quiet, Liam's partner)

Player action: Told a funny story about their first date with Chloe
Outcome: SUCCESS (made everyone laugh)

Generate a brief group reaction (3-4 lines) showing:
- The group's response (laughter, reactions)
- Each person's personality in their reaction
- Natural group dynamic

Format: Narrative description, not individual dialogue lines.
Keep it concise and natural.
```

**LLM Returns:**

```
The group erupts in laughter. Liam nearly spills his drink.

"Mate, that's brilliant!" he wheezes, wiping tears from his eyes.

Chloe leans into you, still giggling. "I can't believe you told them that!" Emma's shaking her head but grinning.

The vibe is warm and fun.
```

**Display to player:**

```
You tell the story about your disastrous first date with Chloe.

The group erupts in laughter. Liam nearly spills his drink.

"Mate, that's brilliant!" he wheezes, wiping tears from his eyes.

Chloe leans into you, still giggling. "I can't believe you told them that!" Emma's shaking her head but grinning.

The vibe is warm and fun.

✨ Banter check: SUCCESS
👥 Friendship +4 (all participants)
💕 Affection +2 (all participants)
📺 Public Perception +3

⏰ 10 minutes passed

Continue group chat?
```

### Group Conversation Limits

**Max 4 people total (player + 3 NPCs)**

**Why:**
- ❌ More = too complex to track
- ❌ More = expensive LLM calls
- ❌ More = diluted relationships
- ✅ 3-4 = manageable and realistic

**If 4+ NPCs at location:**

```
POOL AREA

You see several Heartbreakers scattered around the pool:
• Chloe, Liam, Emma (chatting together)
• Marcus, Aisha (by the far end)
• Sophie, Tom (in the pool)

What do you do?
→ Join Chloe's group (Chloe, Liam, Emma)
→ Join Marcus's group (Marcus, Aisha)
→ Talk to Sophie (Sophie alone in pool - Tom just left)
→ Talk to someone privately
```

**Multiple groups, player chooses which to join.**

---

## NPC Interruption Behavior

### When NPCs Pull Each Other

**NPCs autonomously interrupt each other:**

```javascript
function simulateNPCInterruptions(timeElapsed) {
  const activeConversations = getActiveNPCConversations()

  for (let conversation of activeConversations) {
    // Check if any NPC wants to interrupt this conversation
    const potentialInterrupters = getAllNPCs().filter(npc =>
      npc.id !== conversation.participant1 &&
      npc.id !== conversation.participant2 &&
      npc.currentLocation === conversation.location
    )

    for (let npc of potentialInterrupters) {
      const interruptChance = shouldNPCInterrupt(npc, conversation)

      if (random(100) < interruptChance) {
        // NPC interrupts
        executeNPCInterruption(npc, conversation)
        break  // only one interruption per conversation
      }
    }
  }
}

function executeNPCInterruption(interrupter, targetConversation) {
  const target = chooseInterruptionTarget(interrupter, targetConversation)

  // Calculate if interruption succeeds
  const acceptance = calculateNPCInterruptionAcceptance(target, interrupter, targetConversation)

  const success = random(100) < acceptance

  if (success) {
    // Target goes with interrupter
    endNPCConversation(targetConversation)
    startNPCConversation(interrupter, target)

    // Create event
    createEvent({
      type: "npc_interruption",
      interrupter: interrupter.id,
      target: target.id,
      abandoned: targetConversation.otherPerson,
      location: targetConversation.location,
      witnessed_by: getHeartbreakersAtLocation(targetConversation.location)
    })

    // Add to knowledge (witnesses know this happened)
    const witnesses = getHeartbreakersAtLocation(targetConversation.location)
    for (let witness of witnesses) {
      witness.knowledge.push({
        fact: `${interrupter.name} pulled ${target.name} away from ${targetConversation.otherPerson.name}`,
        source: "witnessed",
        timestamp: { day: currentDay, phase: currentPhase },
        juiciness: calculateInterruptionJuiciness(interrupter, target, targetConversation)
      })
    }
  }
}
```

### Player Observing NPC Interruptions

**If player is at location:**

```
You're at the pool.

You notice Aisha approach Marcus and Sophie's conversation.

"Marcus, can I borrow you for a sec?"

Sophie's face tightens. Marcus hesitates, then stands up.

"Yeah, sure." He walks off with Aisha.

Sophie looks upset.

📚 Observed: Aisha pulled Marcus away from Sophie
   This might be important.

What do you do?
→ Comfort Sophie (she's upset and alone)
→ Observe Aisha and Marcus (eavesdrop)
→ Do something else
```

**Creates opportunity for player to intervene/capitalize.**

---

## Strategic Implications

### Interruption Strategy

**Offensive (sparking):**
- Pull targets away from partners
- Creates private time
- Tests couple strength
- Risk: Makes enemies

**Defensive (protecting couple):**
- Block interruptions
- Stay with partner
- Public displays of commitment
- Risk: Looks possessive

**Information gathering:**
- Accept pulls to learn info
- Brief chats during movement
- Join group conversations
- Risk: Partner worries

**Alliance building:**
- Support friends publicly
- Share gossip in groups
- Help others during interruptions
- Risk: Drama by association

### Timing Interruptions

**Best times to interrupt:**
- Before Pairing Ceremony (make final moves)
- After drama (comfort/capitalize)
- When target is vulnerable (alone, upset)
- Public locations (witnesses)

**Worst times:**
- Private locations (looks intrusive)
- When couple is strong (low success)
- When you have low stats (will fail)

### Group Chat Strategy

**Benefits:**
- Efficient (multiple relationships +friendship)
- Safe (no romantic pressure)
- Gossip spreads quickly
- Public perception boost

**Drawbacks:**
- Shallow (can't build deep connection)
- No privacy (can't be vulnerable)
- Diluted attention
- Time inefficient for romance

**When to use:**
- Building social safety net
- Spreading information
- After individual conversations (social cooldown)
- Low time pressure

---

**Version:** 1.0
**Status:** ✅ Complete
**Cross-references:**
- See 05-Interaction-System.md for base conversation mechanics
- See 06-Location-System.md for location contexts
- See 07-Gossip-And-Information.md for knowledge propagation
