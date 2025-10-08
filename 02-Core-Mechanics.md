# Core Mechanics

*The fundamental gameplay systems that power Isle of Echoes*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Player Stats](#player-stats)
- [Relationship Stats](#relationship-stats)
- [Interaction Categories](#interaction-categories)
- [Interaction Success Formula](#interaction-success-formula)
- [Relationship Change Calculation](#relationship-change-calculation)
- [Relationship Thresholds](#relationship-thresholds)
- [Couple Strength](#couple-strength)
- [Public Perception](#public-perception)
- [Win Conditions](#win-conditions)
- [NPC Stats](#npc-stats)

---

## Player Stats

These represent your Islander's natural abilities and personality traits. They grow slowly through successful interactions and challenges.

### Charm (0-10)

**What it is:** Natural charisma and romantic appeal

**Affects:**
- First impressions with new Islanders
- Romantic interaction success rates
- Flirting effectiveness
- Initial chemistry generation

**How it grows:**
- Successful flirts (+0.1 per success)
- Winning romantic challenges (+0.5)
- Positive feedback from partners (+0.1)
- Caps at 10

**Example usage:**
```javascript
// Flirting with Chloe
const baseChance = 50
const charmBonus = player.stats.charm * 5 // 0-50 bonus
const finalChance = baseChance + charmBonus + otherModifiers
```

### Banter (0-10)

**What it is:** Wit, humor, and conversational skill

**Affects:**
- Joke interaction success
- Group conversation effectiveness
- Challenge performance (humor-based challenges)
- Friendship building rate

**How it grows:**
- Successful jokes (+0.1)
- Making groups laugh (+0.2)
- Winning banter challenges (+0.5)
- Caps at 10

**Example usage:**
```javascript
// Telling a joke at the pool
const banterCheck = player.stats.banter >= 6 // threshold check
if (banterCheck) {
  // Unlock advanced joke options
}
```

### Graft (0-10)

**What it is:** Active pursuit and flirtation intensity (Love Island core concept)

**Affects:**
- Success at "pulling for a chat"
- Chemistry building rate
- Ability to steal partners
- Bombshell effectiveness

**How it grows:**
- Successfully pursuing new connections (+0.2)
- Bold romantic moves (+0.1)
- Winning coupling competitions (+0.5)
- Caps at 10

**Special mechanic:** High Graft unlocks aggressive options but can damage Trust with current partner

**Example usage:**
```javascript
// Trying to graft on a coupled Islander
const graftBonus = player.stats.graft * 7 // Higher weight for graft
const penalty = targetIsCoupled ? -30 : 0
const success = (baseChance + graftBonus + penalty) > roll
```

### Loyalty (0-10)

**What it is:** Faithfulness and commitment to current partner

**Affects:**
- Trust building rate with partner
- Partner's security level
- Public perception (audience loves loyalty)
- Resistance to bombshell temptation

**How it grows:**
- Staying coupled over time (+0.1 per day)
- Rejecting advances (+0.2)
- Reassuring partner (+0.1)
- Caps at 10

**Tradeoff:** High Loyalty limits chemistry with others, low Loyalty enables multi-connection play

**Example usage:**
```javascript
// Partner feels secure
const loyaltyBonus = player.stats.loyalty * 3
partner.relationships.player.trust += loyaltyBonus / 10 // daily passive gain
```

### Emotional Intelligence (0-10)

**What it is:** Reading emotions and responding appropriately

**Affects:**
- Deep conversation success
- Reading NPC moods accurately
- Gossip interpretation
- Conflict resolution

**How it grows:**
- Successful deep conversations (+0.2)
- Correctly reading situations (+0.1)
- Resolving arguments (+0.3)
- Caps at 10

**Example usage:**
```javascript
// Deep heart-to-heart conversation
const eiBonus = player.stats.emotional_intelligence * 6
const moodPenalty = target.mood === "upset" ? -20 : 0
// High EI overcomes mood penalty
```

### Physical (0-10)

**What it is:** Athletic ability and physical attractiveness

**Affects:**
- Physical challenge success
- Initial attraction
- Gym/sports activity effectiveness
- Some Islanders' preferences

**How it grows:**
- Winning physical challenges (+0.5)
- Working out (+0.1)
- Physical activities with others (+0.1)
- Caps at 10

**Example usage:**
```javascript
// Physical challenge: Beach volleyball
const physicalCheck = player.stats.physical * 10 // 0-100
const challengeDifficulty = 60
const success = physicalCheck > challengeDifficulty
```

---

## Relationship Stats

Tracked **per Islander** - every character has these stats with you (and with each other).

### Affection (0-100)

**What it is:** How much they like you romantically

**Increases from:**
- Successful flirts (+3-5)
- Deep conversations (+2-4)
- Compliments (+2-3)
- Gifts/dates (+5-10)
- Shared activities (+1-3)
- Reassurance (+2-4)

**Decreases from:**
- Failed flirts (-2-3)
- Neglect over time (-1 per day if no interaction)
- Seeing you with others (-3-5)
- Betrayal (-10-20)

**Critical thresholds:**
- 20: Interest sparked
- 40: Genuine attraction
- 60: Strong feelings
- 80: Falling in love

### Chemistry (0-100)

**What it is:** Physical/sexual attraction and "spark"

**Increases from:**
- Successful flirts (+4-6)
- Physical proximity activities (+3-5)
- Romantic locations (terrace, hideaway) (+5-8)
- Matching physical preferences (+10)
- Intimate moments (+8-12)

**Decreases from:**
- Failed flirts (-2-4)
- Awkward moments (-3-5)
- Lack of physical contact (-1 per 2 days)

**Special mechanic:** Chemistry can exist WITHOUT affection (pure physical attraction)

**Critical thresholds:**
- 30: Noticeable attraction
- 50: Strong chemistry
- 70: "Can't keep hands off each other"
- 90: Electric connection

### Trust (0-100)

**What it is:** Do they trust you and feel secure?

**Increases from:**
- Keeping promises (+5)
- Loyalty demonstrations (+4-6)
- Deep conversations (+3-5)
- Being there in tough moments (+6-8)
- Consistency over time (+1 per 2 days)

**Decreases from:**
- Lying or being caught (-15-25)
- Flirting with others (-5-10)
- Gossip about you (-3-8)
- Broken promises (-10-15)
- Neglect (-2 per 3 days)

**Critical thresholds:**
- 30: Basic trust established
- 50: Feels secure with you
- 70: Deep trust
- 90: Complete faith

**Special:** Trust is hardest to build, easiest to destroy

### Friendship (0-100)

**What it is:** Platonic bond independent of romance

**Increases from:**
- Non-romantic conversations (+3-5)
- Helping them (+5-8)
- Supporting them in conflicts (+6-10)
- Shared experiences (+4-6)
- Being genuine (+2-4)

**Decreases from:**
- Betrayal (-10-20)
- Using them (-5-10)
- Ignoring them (-1 per 2 days)

**Critical for:** Survival in votes, getting gossip, having allies

**Can exist with OR without romance** - you can have high romance AND high friendship, or high friendship with zero romance

### Animosity (0-100)

**What it is:** Negative feelings, rivalry, dislike

**Increases from:**
- Stealing their partner (+10-20)
- Public confrontations (+5-10)
- Spreading gossip about them (+8-15)
- Betrayal (+15-25)
- Competing for same person (+3-5 per day)

**Decreases from:**
- Apologies (-5-10)
- Time apart (-1 per 2 days)
- Making amends (-8-12)

**Effects when high:**
- They spread negative gossip about you
- They might try to sabotage you
- They vote against you
- Public drama (affects Public Perception)

**Critical thresholds:**
- 30: Annoyed by you
- 50: Dislikes you
- 70: Active rivalry
- 90: Vendetta

### Familiarity (0-100)

**What it is:** How well you know each other

**Increases from:**
- Every interaction (+1-3)
- Deep conversations (+5-8)
- Shared experiences (+3-6)
- Time coupled together (+2 per day)

**Never decreases** (you can't un-know someone)

**Effects:**
- Unlocks deeper conversation topics
- More accurate reading of their mood
- Better prediction of their preferences
- Gossip they share is more valuable

**Critical thresholds:**
- 20: Acquaintances
- 40: Know each other well
- 60: Close connection
- 80: Know them deeply

---

## Interaction Categories

These are the foundational interaction types available to the player.

### Friendly

**Purpose:** Build friendship, general positive interaction

**Options:**
- Ask how they're feeling
- Chat about the villa
- Compliment their personality
- Talk about shared interests
- Offer support

**Primary stats affected:**
- Friendship +3-5
- Affection +1-2
- Familiarity +2-3

**Stat used:** None (always available, moderate success rate)

**When to use:** Building social safety net, maintaining relationships

### Flirty

**Purpose:** Build chemistry and romance

**Options:**
- Compliment their looks
- Playful teasing
- Intimate eye contact
- Subtle touching
- Suggestive comments

**Primary stats affected:**
- Chemistry +4-6
- Affection +2-4
- Trust -1 if coupled with someone else

**Stat used:** Charm

**When to use:** Building romantic connection, testing chemistry

**Unlocked:** Relationship ≥20 OR high chemistry

### Deep

**Purpose:** Build trust and emotional connection

**Options:**
- Ask about their life back home
- Share your feelings
- Discuss your connection
- Vulnerable confession
- Future planning

**Primary stats affected:**
- Trust +4-6
- Affection +3-5
- Familiarity +5-8

**Stat used:** Emotional Intelligence

**When to use:** Deepening existing connection, building security

**Unlocked:** Relationship ≥40

### Banter

**Purpose:** Build friendship through humor

**Options:**
- Tell a joke
- Playful roasting
- Funny story
- Impression/performance
- Self-deprecating humor

**Primary stats affected:**
- Friendship +4-6
- Affection +2-3
- Public Perception +1-2 (if others witness)

**Stat used:** Banter

**When to use:** Group settings, lightening mood, building friendship

### Graft

**Purpose:** Actively pursue romantic connection (can be risky)

**Options:**
- Pull them for a private chat
- Make bold romantic move
- Declare interest
- Ask to couple up
- Steal from current partner

**Primary stats affected:**
- Chemistry +5-8 (if successful)
- Affection +4-6 (if successful)
- Animosity +5-10 from their current partner (if coupled)
- Public Perception -2-5 (if seen as sneaky)

**Stat used:** Graft

**When to use:** Pursuing new connections, competing for someone

**Risks:** Can damage reputation, create enemies, hurt current partner

### Reassure

**Purpose:** Build trust and security with current partner

**Options:**
- "You're the only one I'm interested in"
- "I'm not getting my head turned"
- Address their worries
- Physical reassurance (hug, kiss)
- Public displays of affection

**Primary stats affected:**
- Trust +5-8
- Affection +2-4
- Couple Strength +5-10

**Stat used:** Loyalty

**When to use:** Partner seems worried, bombshell arrived, before recoupling

**Contextual:** Only available with current partner or when concerns exist

### Confront

**Purpose:** Address conflicts or drama

**Options:**
- Call out their behavior
- Defend yourself
- Demand explanation
- Clear the air
- Escalate or de-escalate

**Primary stats affected:**
- Animosity +5-10 (if escalates)
- Trust +3-5 (if resolves honestly)
- Friendship +5-8 (if resolves well)
- Public Perception ±3-8 (depends on context)

**Stat used:** Emotional Intelligence (for de-escalation), Banter (for verbal sparring)

**When to use:** Addressing gossip, resolving conflicts, defending yourself

**Contextual:** Only available when drama exists

---

## Interaction Success Formula

Every interaction that requires a stat check uses this formula:

```javascript
function calculateInteractionSuccess(action, target, player, context) {
  // 1. BASE CHANCE
  let chance = 50 // Starting point

  // 2. STAT BONUS (0-50)
  const relevantStat = action.statUsed // "charm", "banter", "graft", etc.
  if (relevantStat) {
    const statValue = player.stats[relevantStat] // 0-10
    const statBonus = statValue * 5 // 0-50
    chance += statBonus
  }

  // 3. RELATIONSHIP BONUS (0-50)
  const relationshipValue = target.relationships.player.affection
  const relationshipBonus = relationshipValue / 2 // 0-50
  chance += relationshipBonus

  // 4. COMPATIBILITY BONUS (-20 to +20)
  const compatibility = calculateCompatibility(player, target)
  chance += compatibility

  // 5. MOOD MODIFIER (-30 to +30)
  const moodMod = getMoodModifier(target.currentMood, action.type)
  chance += moodMod

  // 6. CONTEXT BONUSES/PENALTIES

  // Location bonus
  if (action.preferredLocation === player.currentLocation) {
    chance += 10
  }

  // Privacy bonus (for romantic actions)
  if (action.requiresPrivacy && isPrivateLocation(player.currentLocation)) {
    chance += 15
  }

  // Time of day bonus
  if (action.preferredTime === villaState.currentPhase) {
    chance += 5
  }

  // 7. PENALTIES

  // Target is coupled with someone else
  if (action.type === "flirt" && target.coupledWith && target.coupledWith !== player.id) {
    chance -= 20
  }

  // Player is coupled with someone else (public location)
  if (action.type === "flirt" && player.coupledWith && player.coupledWith !== target.id) {
    if (!isPrivateLocation(player.currentLocation)) {
      chance -= 30 // risky public flirting
    } else {
      chance -= 15 // less risky in private
    }
  }

  // High animosity
  if (target.relationships.player.animosity > 50) {
    chance -= target.relationships.player.animosity / 2 // -25 to -50
  }

  // Recent failed interaction (discourage spam)
  if (recentlyFailed(action.type, target)) {
    chance -= 15
  }

  // 8. PERSONALITY MODIFIERS

  // Extraversion affects social interactions
  if (action.isGroupInteraction) {
    const extraversionBonus = (target.personality.extraversion - 5) * 3 // -15 to +15
    chance += extraversionBonus
  }

  // Openness affects deep conversations
  if (action.type === "deep") {
    const opennessBonus = (target.personality.openness - 5) * 4 // -20 to +20
    chance += opennessBonus
  }

  // Neuroticism affects trust-building
  if (action.builds === "trust") {
    const neuroticismPenalty = (target.personality.neuroticism - 5) * 2 // -10 to +10
    chance -= neuroticismPenalty // high neuroticism = harder to build trust
  }

  // 9. CLAMP TO VALID RANGE
  const finalChance = Math.max(10, Math.min(95, chance)) // Never impossible, never guaranteed

  return finalChance
}

// Compatibility calculation (based on Big 5)
function calculateCompatibility(player, target) {
  let compatibility = 0

  // Some traits attract opposites
  const extraversionDiff = Math.abs(player.personality.extraversion - target.personality.extraversion)
  if (extraversionDiff > 3 && extraversionDiff < 7) {
    compatibility += 10 // moderate difference is good (balance)
  }

  // Some traits need similarity
  const opennessSimilarity = 10 - Math.abs(player.personality.openness - target.personality.openness)
  compatibility += opennessSimilarity // 0-10 bonus for similar openness

  // Agreeableness always helps
  compatibility += target.personality.agreeableness / 2 // 0-5 bonus

  // High neuroticism makes them harder to connect with
  compatibility -= target.personality.neuroticism / 3 // 0-3 penalty

  return Math.max(-20, Math.min(20, compatibility))
}

// Mood modifiers
function getMoodModifier(mood, actionType) {
  const modifiers = {
    happy: { friendly: +10, flirty: +10, banter: +15, deep: 0, confront: -10 },
    flirty: { friendly: 0, flirty: +20, banter: +5, deep: +5, confront: -15 },
    upset: { friendly: +5, flirty: -20, banter: -15, deep: +15, confront: +10 },
    anxious: { friendly: +10, flirty: -10, banter: -5, deep: +10, confront: -15 },
    angry: { friendly: -15, flirty: -25, banter: -10, deep: -10, confront: +20 },
    content: { friendly: +5, flirty: +5, banter: +5, deep: +5, confront: 0 }
  }

  return modifiers[mood]?.[actionType] || 0
}
```

**Example calculation:**

```javascript
// Player (Charm: 7, coupled with Chloe) flirts with Aisha (single) at the pool

const action = { type: "flirt", statUsed: "charm", preferredLocation: "pool" }
const target = aisha // Single, mood: flirty, affection: 35, animosity: 0

let chance = 50 // base

// Stat bonus
chance += 7 * 5 // +35 (good charm)

// Relationship bonus
chance += 35 / 2 // +17.5 (some existing affection)

// Compatibility
chance += 5 // +5 (moderate compatibility)

// Mood
chance += 20 // +20 (she's in flirty mood, bonus to flirt actions)

// Location
chance += 10 // +10 (pool is good for flirting)

// PENALTY: Player is coupled with Chloe (not Aisha), public location
chance -= 30 // -30 (risky!)

// Final: 50 + 35 + 17.5 + 5 + 20 + 10 - 30 = 107.5 → clamped to 95%

// Very likely to succeed, but risky (Chloe might find out)
```

---

## Relationship Change Calculation

When an interaction succeeds or fails, relationships change:

```javascript
function applyRelationshipChange(action, target, success) {
  const changes = {
    affection: 0,
    chemistry: 0,
    trust: 0,
    friendship: 0,
    animosity: 0,
    familiarity: 1 // always increases slightly
  }

  if (success) {
    // SUCCESSFUL INTERACTION

    switch (action.category) {
      case "friendly":
        changes.friendship += 4
        changes.affection += 2
        changes.familiarity += 2
        break

      case "flirty":
        changes.chemistry += 5
        changes.affection += 3
        changes.familiarity += 1
        break

      case "deep":
        changes.trust += 5
        changes.affection += 3
        changes.familiarity += 6
        break

      case "banter":
        changes.friendship += 5
        changes.affection += 2
        break

      case "graft":
        changes.chemistry += 7
        changes.affection += 5
        changes.familiarity += 2
        break

      case "reassure":
        changes.trust += 7
        changes.affection += 3
        break
    }

    // Personality multipliers
    if (target.personality.agreeableness > 7) {
      // Agreeable people respond more positively
      changes.affection *= 1.2
      changes.friendship *= 1.2
    }

    if (target.personality.extraversion > 7 && action.isPublic) {
      // Extraverts love public interactions
      changes.affection *= 1.15
    }

  } else {
    // FAILED INTERACTION

    changes.animosity += 1 // slight negative

    switch (action.category) {
      case "flirty":
        changes.chemistry -= 3
        changes.affection -= 1
        // Awkwardness penalty
        break

      case "deep":
        changes.trust -= 2
        // Felt too vulnerable, pulled back
        break

      case "graft":
        changes.animosity += 3
        changes.chemistry -= 2
        // Rejected, feels disrespected
        break

      case "banter":
        changes.friendship -= 2
        // Joke didn't land, awkward
        break
    }

    // High neuroticism = takes failure harder
    if (target.personality.neuroticism > 7) {
      changes.animosity += 2
      changes.trust -= 1
    }
  }

  // Apply changes (with clamping)
  for (let [stat, change] of Object.entries(changes)) {
    const current = target.relationships.player[stat]
    const newValue = Math.max(0, Math.min(100, current + change))
    target.relationships.player[stat] = newValue
  }

  // SIDE EFFECTS

  // If flirting with someone else while coupled
  if (action.category === "flirty" && player.coupledWith && player.coupledWith !== target.id) {
    const partner = getIslanderById(player.coupledWith)

    // Risk of being caught
    const caughtChance = isPrivateLocation(player.currentLocation) ? 10 : 40

    if (random(100) < caughtChance) {
      // Partner finds out
      partner.relationships.player.trust -= 15
      partner.relationships.player.animosity += 10
      partner.mood = "upset"

      // Create drama event
      createDramaEvent("caught_flirting", player, target, partner)
    }
  }

  return changes
}
```

---

## Relationship Thresholds

Certain interactions unlock at specific relationship levels:

### Level 1: Stranger (0-19)
**Available:**
- Basic friendly interactions
- Ask about them
- Introduce yourself

**Locked:**
- Everything else

### Level 2: Acquaintance (20-39)
**Unlocks:**
- Flirty interactions (light)
- Joke around
- Suggest activities together

**Locked:**
- Deep conversations
- Romantic actions
- Couple-specific options

### Level 3: Friend/Interest (40-59)
**Unlocks:**
- Deep conversations
- Share vulnerabilities
- Private chats
- Ask to couple up

**Locked:**
- Intimate physical actions
- Serious commitment talks

### Level 4: Close/Romantic (60-79)
**Unlocks:**
- Kiss
- Physical intimacy options
- "Define the relationship" talks
- Strategic couple planning
- Hideaway access (if coupled)

**Locked:**
- Most intimate options

### Level 5: Strong Couple (80-100)
**Unlocks:**
- Most intimate interactions
- Future planning
- "I'm falling for you" confessions
- Hideaway overnight
- Joint strategy sessions

---

## Couple Strength

When you're coupled with someone, your overall couple strength is calculated:

```javascript
function calculateCoupleStrength(player, partner) {
  const affection = partner.relationships.player.affection
  const chemistry = partner.relationships.player.chemistry
  const trust = partner.relationships.player.trust

  // Weighted average
  const strength = (affection * 0.4) + (trust * 0.4) + (chemistry * 0.2)

  // Bonus for time together
  const daysCoupled = villaState.currentDay - coupleFormedDay
  const timeBonus = Math.min(10, daysCoupled * 2) // max +10

  // Penalty for high animosity
  const animosityPenalty = partner.relationships.player.animosity / 2

  const final = strength + timeBonus - animosityPenalty

  return Math.max(0, Math.min(100, final))
}
```

**Couple Strength determines:**
- Resistance to being stolen by bombshells
- Likelihood of staying together during recoupling
- Chance of winning final vote
- Partner's willingness to forgive mistakes

**Thresholds:**
- <30: Weak couple (vulnerable)
- 30-50: Stable but at risk
- 50-70: Strong couple
- 70-85: Very strong couple
- 85+: Power couple

---

## Public Perception

The simulated "audience" has an opinion of you:

```javascript
function calculatePublicPerception(player) {
  let perception = 50 // neutral start

  // BONUSES

  // Loyalty (audience loves loyal players)
  perception += player.stats.loyalty * 3 // 0-30

  // Being in a strong couple
  if (player.coupledWith) {
    const coupleStrength = getCoupleStrength(player)
    perception += coupleStrength / 4 // 0-25
  }

  // Being genuine (high affection across relationships)
  const avgAffection = getAverageAffection(player)
  perception += avgAffection / 5 // 0-20

  // Humor (audience loves banter)
  perception += player.stats.banter * 2 // 0-20

  // PENALTIES

  // Being "snakey" (flirting while coupled)
  const snakeyBehavior = countSnakeyActions(player)
  perception -= snakeyBehavior * 5 // variable

  // High animosity from others
  const avgAnimosity = getAverageAnimosity(player)
  perception -= avgAnimosity / 3 // variable

  // Being boring (low interaction count)
  if (player.totalInteractions < averageInteractions) {
    perception -= 10
  }

  // Creating drama (can be positive or negative)
  const dramaLevel = getDramaLevel(player)
  if (dramaLevel > 50 && dramaLevel < 80) {
    perception += 10 // good drama
  } else if (dramaLevel > 80) {
    perception -= 15 // too much drama
  }

  return Math.max(0, Math.min(100, perception))
}
```

**Public Perception affects:**
- Final vote outcome
- Bombshell targeting (they pursue popular players)
- Recoupling save chances
- Meta-progression rewards (Audience Appeal)

---

## Win Conditions

Multiple paths to "winning":

### Winning Couple (Best Ending)
**Requirements:**
- Be coupled at final (Day 18-20)
- Couple Strength ≥70
- Public Perception ≥65
- Win final vote

**Rewards:**
- Maximum Audience Appeal (500 AP)
- "Winners" achievement
- Unlock special archetypes

### Fan Favorite (Good Ending)
**Requirements:**
- Public Perception ≥80
- NOT necessarily coupled (can be single)
- High friendship across villa (avg 60+)

**Rewards:**
- High Audience Appeal (400 AP)
- "Fan Favorite" achievement

### Friendship Ending (Alt Good Ending)
**Requirements:**
- Leave villa with at least 2 friendships ≥80
- Public Perception ≥50
- Doesn't matter if coupled

**Rewards:**
- Moderate Audience Appeal (300 AP)
- "True Friends" achievement

### Chaos Agent (Unique Ending)
**Requirements:**
- High drama generated (75+ drama score)
- Average animosity from others ≥40
- Public Perception can be low

**Rewards:**
- Moderate Audience Appeal (250 AP)
- "Chaos Incarnate" achievement
- Unlock "Drama Queen/King" archetype

### Dumped (Failure - but early)
**Requirements:**
- Eliminated before Day 10

**Rewards:**
- Low Audience Appeal (50-100 AP based on days survived)

### Dumped (Failure - late)
**Requirements:**
- Eliminated Days 10-17

**Rewards:**
- Moderate Audience Appeal (150-250 AP based on performance)

---

## NPC Stats

NPCs have the same stats as the player, but generated procedurally:

```javascript
const npcStats = {
  // Social Stats (0-10)
  charm: random(4, 10),
  banter: random(3, 10),
  graft: random(2, 9),
  loyalty: random(3, 10),
  emotional_intelligence: random(3, 9),
  physical: random(4, 10),

  // Derived from Big 5 personality
  attractiveness: 5 + (personality.extraversion / 2), // 5-10
  humor: 3 + (personality.openness / 2), // 3-8
  charisma: 4 + (personality.extraversion / 2) + (personality.agreeableness / 3), // ~5-10
  confidence: 10 - personality.neuroticism // 0-10 (inverse of neuroticism)
}
```

NPCs use these stats for their autonomous interactions with each other.

---

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 03-LLM-Architecture.md for how AI integrates with these mechanics
