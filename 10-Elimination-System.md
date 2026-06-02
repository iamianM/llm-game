# Elimination System, Producer AI, and Pairing Ceremonies

*How the game orchestrates drama, eliminations, and strategic event timing*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Core Decisions](#-core-decisions-what-were-doing-differently)
- [The Producer AI System](#-the-producer-ai-system)
- [Audience/Public Perception System](#-audiencepublic-perception-system)
- [Pairing Ceremonies](#-pairing-ceremonies)
- [Heart Throb System](#-heart-throb-system)
- [Voting and Eliminations](#️-voting-and-eliminations)
- [Weekly Event Flow](#-weekly-event-flow-producer-ai-schedule)
- [Playing to Character Strengths/Weaknesses](#-playing-to-character-strengthsweaknesses)

---

## 🎯 Core Decisions: What We're Doing Differently

### What We're NOT Doing (From the Show)

❌ **Physical Challenges**
- **Why not:** Hard to animate, not fun in visual novel format
- **Instead:** Focus on social/compatibility challenges that use stats and relationships

❌ **Random Audience Eliminations**
- **Why not:** Feels unfair, player can't strategize
- **Instead:** Visible audience rankings, player knows if they're at risk

❌ **Opaque Producer Decisions**
- **Why not:** Frustrating when you don't understand why events happen
- **Instead:** Producer AI follows clear rules based on game state

❌ **Large Cast (10-12 Heartbreakers)**
- **Why not:** Too many to track, dilutes focus
- **Instead:** 4 couples (8 Heartbreakers) - player's couple + 3 others

❌ **Purely Couple-Based Votes**
- **Why not:** Doesn't account for individual popularity
- **Instead:** Hybrid system (individual + couple rankings)

### What We ARE Doing

✅ **Visible Audience Meter**
- Player sees their individual ranking (1-8)
- Player sees their couple ranking (1-4)
- Forces entertaining gameplay (drama, romance, strategy)

✅ **Personality-Driven Interactions**
- Playing against your type = penalties
- Introvert flirting with everyone = unnatural, lowers scores
- Must play to character strengths

✅ **Character Compatibility Matters**
- If NPC dislikes smug behavior, smug responses = negative
- Forcing romance with incompatible match = "fake" penalty
- Chemistry requires actual compatibility

✅ **Smart Producer AI**
- Analyzes game state
- Introduces mechanics strategically
- Helps struggling players, challenges strong couples

✅ **Clear Elimination Rules**
- Single at Pairing Ceremony + no one picks you = Heart Out
- Bottom audience ranking at vote = AT RISK
- Pressure to couple up and be interesting

✅ **Flush of Hearts (6 new Heartbreakers)**
- Only need to generate 6 more (3 boys, 3 girls)
- Ultimate mid-game test

---

## 🤖 The Producer AI System

### Core Function

**The Producer AI is a strategic game master that:**
1. Analyzes current resort state (relationships, drama level, player position)
2. Decides which event type would create maximum drama/help player
3. Triggers that event at optimal moment

**Philosophy:** The Producer AI balances challenge with fairness. It won't let the game become boring OR impossible to win.

### State Analysis (What Producer AI Evaluates)

**Every morning (before announcing daily event), Producer AI checks:**

```javascript
const resortState = {
  // PLAYER STATUS
  playerCoupleStrength: playerCouple.affection + playerCouple.trust, // 0-200
  playerIsInCouple: player.coupledWith !== null,
  playerAudienceRank: getAudienceRank(player), // 1-8
  playerCoupleRank: getCoupleRank(playerCouple), // 1-4

  // DRAMA LEVEL
  dramaLevel: calculateDramaLevel(), // 0-100
  // Based on: recent arguments, love triangles, secrets, recency of last Heart Throb

  // STABILITY
  strongCouples: couples.filter(c => c.strength > 120).length, // 0-4
  weakCouples: couples.filter(c => c.strength < 60).length, // 0-4
  singleHeartbreakers: heartbreakers.filter(i => i.coupledWith === null).length,

  // TIME
  currentDay: resortState.day, // 1-20
  daysSinceLastHeartThrob: calculateDays(lastHeartThrob),
  daysSinceLastPairingCeremony: calculateDays(lastPairingCeremony),

  // STORY MOMENTUM
  recentMajorEvents: getEventsInLast2Days(), // Heart Throbs, Heart Outs, arguments
  playerEngagement: calculateEngagement(), // based on audience score trajectory
}
```

### Event Decision Logic

**Producer AI follows this priority system:**

#### Priority 1: Prevent Player Failure (If At Risk)

```javascript
if (playerAudienceRank >= 7 || playerCoupleRank === 4) {
  // Player is bottom 2 in individual OR worst couple

  if (playerIsInCouple && playerCoupleStrength < 50) {
    return triggerEvent("PAIRING_CEREMONY", "Boys Choose")
    // Give player chance to switch to better match
  }

  if (!playerIsInCouple) {
    return triggerEvent("HEART_THROB", generateCompatibleHeartThrob(player))
    // Send in Heart Throb who's player's type
  }

  if (playerCoupleStrength >= 50 && playerCoupleRank === 4) {
    // Couple is decent but unpopular (probably boring)
    return triggerEvent("FORCED_DATE", { who: player, with: createDramaPairing() })
    // Force player to create drama/test loyalty
  }
}
```

**Translation:** If player is failing, Producer helps:
- Bad couple? Trigger Pairing Ceremony (fresh start)
- Single? Send compatible Heart Throb (give option)
- Boring couple? Force dramatic date (create content)

#### Priority 2: Prevent Boredom (If Drama Too Low)

```javascript
if (dramaLevel < 30 && strongCouples >= 3) {
  // Resort is stable and boring

  if (daysSinceLastHeartThrob >= 3) {
    const targetCouple = getStrongestCouple()
    return triggerEvent("HEART_THROB", generateWeaponHeartThrob(targetCouple))
    // Send Heart Throb designed to tempt strongest couple
  }

  if (daysSinceLastPairingCeremony >= 4) {
    return triggerEvent("PAIRING_CEREMONY", "Surprise")
    // Shake things up
  }

  return triggerEvent("COMPATIBILITY_CHALLENGE", "Lie Detector Test")
  // Force couples to reveal secrets
}
```

**Translation:** If game is boring, Producer escalates:
- Send Heart Throb to tempt strong couples
- Force surprise Pairing Ceremony
- Run lie detector test (reveals secrets)

#### Priority 3: Challenge Strong Players (If Player Too Comfortable)

```javascript
if (playerCoupleStrength > 140 && playerAudienceRank <= 3) {
  // Player is in very strong couple AND popular (might coast to victory)

  if (currentDay >= 12 && !flushOfHeartsTriggered) {
    return triggerEvent("FLUSH_OF_HEARTS")
    // Ultimate test of loyalty
  }

  if (currentDay < 12) {
    return triggerEvent("FORCED_DATE", {
      who: player.partner,
      with: getMostCompatibleNonPlayer()
    })
    // Send player's partner on date with their perfect match (create jealousy/doubt)
  }
}
```

**Translation:** If player is winning easily, Producer creates challenge:
- Send partner on date with perfect match
- Trigger Flush of Hearts (test loyalty)

#### Priority 4: Scheduled Events (Required Story Beats)

```javascript
if (currentDay === 1) {
  return triggerEvent("INITIAL_COUPLING")
}

if (currentDay === 5) {
  return triggerEvent("FIRST_PAIRING_CEREMONY", "Girls Choose")
}

if (currentDay === 8) {
  return triggerEvent("PUBLIC_VOTE", "Bottom 2 Couples")
}

if (currentDay === 12) {
  return triggerEvent("FLUSH_OF_HEARTS")
}

if (currentDay === 18) {
  return triggerEvent("FINAL_VOTE")
}
```

**Translation:** Some events are locked to specific days (story structure).

#### Priority 5: Default (Generate Momentum)

```javascript
// If no special conditions met, maintain momentum

if (daysSinceLastHeartThrob >= 2) {
  return triggerEvent("HEART_THROB", generateBalancedHeartThrob())
}

if (random(100) < 40) {
  return triggerEvent("SOCIAL_CHALLENGE")
}

return triggerEvent("FREE_DAY") // Morning + afternoon only, no evening event
```

### Event Type Catalog

**The Producer AI can trigger:**

1. **PAIRING_CEREMONY** (Boys Choose / Girls Choose / Surprise)
2. **PUBLIC_VOTE** (Bottom 2 Couples / Bottom 3 Heartbreakers / Top Couple Safe)
3. **HEART_THROB** (Weapon / Rescue / Balanced)
4. **FORCED_DATE** (Player / Player's Partner / Other Couple)
5. **COMPATIBILITY_CHALLENGE** (Lie Detector / Quiz / Rank Couples)
6. **SOCIAL_CHALLENGE** (Pulse Race / Who's Most Likely / Kiss Wed Pass)
7. **FLUSH_OF_HEARTS** (3-day event)
8. **PRIVATE_SUITE_ACCESS** (Reward or advantage)
9. **FREE_DAY** (No evening event, just socializing)

---

## 📊 Audience/Public Perception System

### How It Works

**Two separate rankings:**

#### 1. Individual Audience Ranking (1-8)

**Calculated by:**
```javascript
function calculateIndividualScore(heartbreaker) {
  let score = 50 // base

  // ENTERTAINMENT VALUE (+40 max)
  score += (heartbreaker.dramaMomentsCreated * 5) // up to +25
  score += (heartbreaker.funnyMoments * 3) // up to +15

  // LIKABILITY (+30 max)
  score += (heartbreaker.kindActions * 4) // up to +20
  score += (heartbreaker.authenticMoments * 2) // up to +10

  // PENALTIES (-40 max)
  score -= (heartbreaker.meanActions * 8) // up to -30
  score -= (heartbreaker.boringScore * 2) // up to -10

  // RELATIONSHIP AUTHENTICITY (±20)
  if (heartbreaker.coupledWith) {
    const couple = getCouple(heartbreaker)
    if (couple.strength > 120) score += 20 // genuine connection
    if (couple.strength < 40 && couple.daysTogether > 3) score -= 20 // fake couple
  }

  return Math.max(0, Math.min(100, score))
}
```

**What affects individual score:**
- ✅ Creating drama (+)
- ✅ Being funny (+)
- ✅ Being kind (+)
- ✅ Authentic moments (+)
- ❌ Being mean (-)
- ❌ Being boring (-)
- ❌ Fake relationships (-)

**Sorted 1-8, player sees:**
```
Audience Favorites:
1. 🥇 Marcus (85/100) ⬆️
2. 🥈 YOU (78/100) ⬆️
3. 🥉 Chloe (72/100) →
4. Aisha (68/100) ⬇️
5. Tom (55/100) →
6. Sophie (52/100) ⬆️
7. Liam (45/100) ⬇️ ⚠️ AT RISK
8. Emma (38/100) ⬇️ ⚠️ AT RISK
```

**Arrows show trajectory:**
- ⬆️ = Gained 5+ points since yesterday
- → = Stable (±4 points)
- ⬇️ = Lost 5+ points

#### 2. Couple Audience Ranking (1-4)

**Calculated by:**
```javascript
function calculateCoupleScore(couple) {
  let score = 50 // base

  // COUPLE STRENGTH (+30)
  const strength = couple.affection + couple.trust
  score += (strength / 200) * 30

  // ENTERTAINMENT (+20)
  score += couple.dramaCreated * 2 // arguments, makeups, jealousy

  // AUTHENTICITY (+30)
  if (strength > 140) score += 30 // very real
  if (strength > 100) score += 15 // pretty real
  if (strength < 40 && couple.daysTogether > 3) score -= 25 // clearly fake

  // PUBLIC MOMENTS (+20)
  score += couple.romanticMomentsWitnessed * 4 // public kisses, confessions

  return Math.max(0, Math.min(100, score))
}
```

**Player sees:**
```
Favorite Couples:
1. 🥇 Marcus & Aisha (88/100) 💕 Strong & Entertaining
2. 🥈 YOU & Chloe (76/100) 💕 Authentic
3. 🥉 Tom & Sophie (62/100) ⚠️ Shaky
4. Liam & Emma (45/100) 💔 Fake ⚠️ AT RISK
```

### Visibility & Strategic Use

**Player can see:**
- ✅ Their own individual rank (real-time)
- ✅ Their couple rank (real-time)
- ✅ All other rankings (updated each morning)
- ✅ Trajectory arrows (am I improving or falling?)
- ✅ Risk warnings (bottom 2 shown with ⚠️)

**Player CANNOT see:**
- ❌ Exact score numbers for others (just for themselves)
- ❌ How score is calculated (black box, just see results)

**Strategic implications:**
- If you're rank 7-8: **You MUST create drama or find love ASAP**
- If your couple is rank 4: **Heart Swap or inject drama into relationship**
- If you're rank 1-2: **You can coast OR create drama for entertainment**
- If falling (⬇️): **Something you did turned audience off, change approach**

### What Creates "Boring" Score (The Hidden Penalty)

```javascript
function calculateBoringScore(heartbreaker) {
  let boring = 0

  // No interactions with new people (stuck in couple bubble)
  if (heartbreaker.uniqueConversationsToday < 3) boring += 2

  // Repeating same conversations
  if (heartbreaker.conversationVariety < 50) boring += 3

  // No drama witnessed or created in 2 days
  if (daysSinceLastDramaMoment >= 2) boring += 5

  // Playing it too safe (no risky choices)
  if (heartbreaker.riskyChoicesInLast2Days === 0) boring += 3

  return boring
}
```

**Translation:** Audience wants:
- Talk to different people
- Vary your conversations
- Be involved in drama (witness or create)
- Take risks (flirt with someone new, confront someone, make bold moves)

---

## 💑 Pairing Ceremonies

### Types of Pairing Ceremonies

#### Type 1: Boys Choose (Player Chooses If Male)

**When:** Days 1, 9, 15

**Flow:**
1. All girls line up on one side
2. Boys stand on other side
3. Producer AI determines pick order:
   ```javascript
   // Order based on last challenge winner + audience favorites
   const order = [
     lastChallengeWinner,
     ...otherBoys.sort((a, b) => b.pulseScore - a.pulseScore)
   ]
   ```
4. Each boy picks one girl (speech optional)
5. Unpicked girl(s) = DUMPED

**Player Experience:**
- If player is boy: You choose (menu of all girls with relationship stats visible)
- If player is girl: You wait (see each boy's face as they decide, guess who'll pick you)

**NPC Decision Logic:**
```javascript
function npcBoyChooses() {
  const availableGirls = getAvailableGirls()

  // Sort by: relationship strength + chemistry + strategic value
  const ranked = availableGirls.map(girl => ({
    girl,
    score: (
      getRelationship(npc, girl).affection * 2 +
      getRelationship(npc, girl).chemistry * 1.5 +
      getStrategicValue(girl) // will she keep me safe from votes?
    )
  })).sort((a, b) => b.score - a.score)

  return ranked[0].girl
}
```

#### Type 2: Girls Choose (Player Chooses If Female)

**When:** Days 5, 12 (after Flush of Hearts), 18 (final)

**Flow:** Same as above but reversed

#### Type 3: Surprise Pairing Ceremony (Producer Decides Order)

**When:** Triggered by Producer AI when drama is low

**Flow:**
- No warning ("Heartbreakers, tonight there will be a Pairing Ceremony. I will read out the order.")
- Order is randomized OR based on drama potential
- Creates panic (no time to strategize)

**Order Logic:**
```javascript
function getSurpriseOrder() {
  // Put strongest couples LAST (force them to watch others steal partners)
  const couples = getAllCouples().sort((a, b) => b.strength - a.strength)

  // Mix it up for drama
  return [
    ...couples[couples.length - 1].members, // weakest couple picks first
    ...couples[0].members.reverse(), // strongest couple picks LAST
    ...shuffle(couples.slice(1, -1).flat())
  ]
}
```

### Pairing Ceremony UI/UX

**Player's Turn (If Choosing):**
```
It's your turn to pick.

Available Partners:
┌─────────────────────────────────────┐
│ 💕 Chloe                            │
│ Affection: 78  Chemistry: 85        │
│ She's been flirting with you        │
│ Audience: Rank #3                   │
│ [PICK CHLOE]                        │
├─────────────────────────────────────┤
│ 💔 Aisha                            │
│ Affection: 45  Chemistry: 60        │
│ She's coupled with Marcus           │
│ Audience: Rank #4                   │
│ [STEAL AISHA] (Risky)               │
├─────────────────────────────────────┤
│ ⚠️ Sophie                           │
│ Affection: 30  Chemistry: 20        │
│ She doesn't seem interested         │
│ Audience: Rank #6                   │
│ [PICK SOPHIE] (Safe but weak)       │
└─────────────────────────────────────┘
```

**Player Waiting (Being Picked):**
```
Marcus steps forward...

"I want to couple up with this girl because she makes me laugh
and I think we have a real connection..."

[Camera zooms on faces of available girls]

Chloe: 😊 (hopeful)
You: 😐 (nervous)
Sophie: 😰 (worried)

"The girl I want to couple up with is..."

[Dramatic pause]

"...Chloe."

[Chloe walks forward, couples with Marcus]

You: Status: Still available
Couples formed: 2/4
Next: Tom chooses...
```

### Elimination at Pairing Ceremony

**Clear Rule:** If you're not picked = Heart Out

**Scenario: 4 couples, 1 new Heart Throb (boy) enters**
- 9 people total (5 boys, 4 girls)
- Boys choose
- 5 boys pick 4 girls
- 1 girl left standing = Heart Out

**Player sees:**
```
⚠️ PAIRING CEREMONY ALERT ⚠️

5 boys will choose 4 girls.
1 girl will be dumped from the island.

Your current couple: Chloe (Strength: 85)
Your backups:
  - Tom has 68 chemistry with you
  - Liam has 45 chemistry with you

Strategy:
- Trust Chloe picks you? (85% likely based on strength)
- OR talk to Tom/Liam before ceremony (build backup)
```

---

## 💣 Heart Throb System

### Heart Throb Types (Producer AI Chooses)

#### Type 1: Weapon Heart Throb (Disrupt Strong Couple)

**When:** Strong couple exists (strength > 140) AND drama is low

**How It's Generated:**
```javascript
function generateWeaponHeartThrob(targetCouple) {
  const target = random(targetCouple.members)

  // Create Heart Throb who is target's PERFECT type
  const heartThrob = {
    personality: matchesPerfectly(target.preferences.personalityType),
    appearance: target.preferences.physicalType,

    // Also make them incompatible with their partner (create contrast)
    interests: opposite(target.partner.interests),

    // High chemistry with target, low with others
    relationships: {
      [target.id]: { chemistry: 85, affection: 0 },
      ...otherHeartbreakers.map(i => ({ [i.id]: { chemistry: 40, affection: 0 }))
    }
  }

  return heartThrob
}
```

**Example:**
- Player is in strong couple with Chloe (strength 150)
- Game generates Heart Throb "Zara"
- Zara is player's exact type (adventurous, brunette, funny)
- Zara has 85 base chemistry with player
- Temptation created

#### Type 2: Rescue Heart Throb (Help Vulnerable Player)

**When:** Player is single OR in bottom 2 Pulse ranking

**How It's Generated:**
```javascript
function generateRescueHeartThrob(player) {
  // Create Heart Throb compatible with player
  const heartThrob = {
    personality: complementary(player.personality),
    appearance: player.preferences.physicalType,

    relationships: {
      [player.id]: { chemistry: 75, affection: 0 },
      // But ALSO compatible with 1 other (balance)
      [random(otherHeartbreakers).id]: { chemistry: 70, affection: 0 }
    }
  }

  return heartThrob
}
```

**Example:**
- Player is single and at risk
- Game sends "Jake" who player will fancy
- Jake also fancies 1 other girl (not guaranteed coupling, must still work for it)

#### Type 3: Balanced Heart Throb (General Drama)

**When:** Need new energy but no specific target

**How It's Generated:**
```javascript
function generateBalancedHeartThrob() {
  // Compatible with 2-3 Heartbreakers
  const targets = random(heartbreakers, 3)

  const heartThrob = {
    relationships: targets.map(t => ({
      [t.id]: { chemistry: random(60, 80), affection: 0 }
    }))
  }

  return heartThrob
}
```

**Example:**
- Day 6, resort needs fresh energy
- "Ryan" enters, fancies Aisha (coupled), Sophie (single), and YOU (coupled)
- Creates 3 potential storylines

### Heart Throb Entry Flow

**1. Producer AI decides to send Heart Throb**

**2. Generates Heart Throb using appropriate type**

**3. Announces via Paradise Calls:**
```
📱 "Heartbreakers, you're about to meet a new Heart Throb.
   Boys, please gather at the Flame Deck."
```

**4. Heart Throb enters:**
```
[New character appears]

JAKE, 25, Personal Trainer
"Hey everyone, I'm Jake. I'm here to find a real connection...
and I'm not afraid to step on toes to get it."

[Heartbreakers react - LLM generates based on personality]
Marcus: "Great, more competition..." 😒
Chloe: "Ooh, he's fit!" 😍
You: [Choose reaction]
  - Welcome him warmly (friendly, +2 Pulse)
  - Size him up (competitive, -1 friendship with him)
  - Stay quiet (neutral)
```

**5. Heart Throb privilege: Chooses 2 Heartbreakers for dates**
```
JAKE: "I want to take... Chloe and Sophie on dates."

⚠️ Chloe is YOUR partner!

[You see Chloe leave with Jake]

Options:
- Trust her (high loyalty, no action)
- Spark with someone else (strategic, hedge your bets)
- Confront her when she returns (possessive, might push her away)
```

**6. Dates happen (player not present if not chosen)**
- If player on date: Normal conversation system, build chemistry
- If player NOT on date: Time passes, see other Heartbreakers' reactions, build jealousy

**7. Heart Throb must couple at next Pairing Ceremony**
- Gets first pick OR
- Can steal from existing couple

### Heart Throb Frequency

**Producer AI logic:**
```javascript
function shouldSendHeartThrob(state) {
  // Too soon (let last Heart Throb integrate)
  if (state.daysSinceLastHeartThrob < 2) return false

  // Too late (too many people, costly for LLM)
  if (state.totalHeartbreakers >= 12) return false

  // SHOULD send if:
  return (
    state.dramaLevel < 40 || // boring
    state.strongCouples >= 3 || // too stable
    state.playerAtRisk // player needs help
  )
}
```

**Average:** 1 Heart Throb every 2-3 days in Weeks 1-2, less in Week 3 (Flush of Hearts replaces)

---

## 🗳️ Voting and Eliminations

### Vote Types

#### Vote Type 1: Public Vote (Bottom Couples)

**When:** Days 8, 16
**Format:** Bottom 2 couples at risk

**Flow:**
```
1. Audience rankings calculated (couple scores)

2. Bottom 2 couples revealed:
   "The two couples with the lowest public support are..."

   💔 Tom & Sophie (Score: 45)
   💔 Liam & Emma (Score: 38)

3. Heartbreakers vote to save ONE couple:
   - Each Heartbreaker votes privately
   - Can't vote for own couple
   - Couple with most votes stays
   - Other couple DUMPED (both people leave)

4. Player votes:
   [ ] Save Tom & Sophie (They're your friends)
   [ ] Save Liam & Emma (Strategic, weaker competition)
```

**Effects:**
- Entire couple eliminated (2 people gone)
- Friendship matters (friends vote for you)
- Strategic voting (keep weaker couples)

#### Vote Type 2: Public Vote (Bottom Individuals)

**When:** Days 11, 17
**Format:** Bottom 3 individuals at risk

**Flow:**
```
1. Individual audience rankings calculated

2. Bottom 3 revealed:
   "The three Heartbreakers with the lowest Pulse are..."

   ⚠️ Liam (Rank 8, Score: 38)
   ⚠️ Emma (Rank 7, Score: 42)
   ⚠️ YOU (Rank 6, Score: 48)

3. Fellow Heartbreakers vote:
   - Vote to send one person Heart Out
   - Person with most votes leaves
   - Their partner becomes single

4. If YOU are at risk:
   ⚠️ You're at risk! Your fate is in other Heartbreakers' hands.

   Who might save you:
   ✅ Chloe (partner, will vote for someone else)
   ✅ Marcus (high friendship)
   ❓ Aisha (neutral)
   ❌ Tom (low friendship, might vote you out)
```

**Effects:**
- Individual eliminated (partner becomes single)
- Friendship critical (need allies)
- Creates singles before Pairing Ceremony

#### Vote Type 3: No Public Vote (Pairing Ceremony Only)

**When:** Days 5, 9, 15, 18
**Format:** No vote, just Pairing Ceremony

**Flow:**
- Pairing Ceremony happens
- Unpicked person = Heart Out
- No vote needed

### When Player Is At Risk

**Bottom 2 Couple:**
```
⚠️ DANGER ⚠️

You and Chloe are in the bottom 2 couples.

Why?
- Couple score: 52/100 (boring, no drama)
- You've been too stable (no storylines)

Heartbreakers will vote to save one couple:

Who might save you:
✅ Marcus & Aisha (friends, 80% will vote for you)
❓ Tom & Sophie (neutral, 50/50)

You need 2 votes to stay.
Current prediction: 50% survival rate

If dumped: Game Over (both you and Chloe eliminated)
If saved: You stay, Tom & Sophie go home
```

**Bottom 3 Individual:**
```
⚠️ DANGER ⚠️

You're in bottom 3 for individual votes.

Why?
- Audience rank: 6/8
- Boring score: 15 (not enough drama)
- Recent mean action: -8 (confronted Aisha rudely)

Heartbreakers vote to send one person Heart Out:

Who will vote you out:
❌ Tom (you have 25 friendship, he dislikes you)
❌ Aisha (you just argued, she wants you gone)

Who will save you:
✅ Chloe (partner, loyal)
✅ Marcus (high friendship)
❓ Sophie (neutral)

Prediction: 60% chance you're dumped

If dumped: Game Over (you leave, Chloe becomes single)
```

### Vote Frequency

**Producer AI determines:**
```javascript
function shouldCallVote(state) {
  // Scheduled votes
  if (state.day === 8 || state.day === 16) {
    return { type: "COUPLE_VOTE", reason: "scheduled" }
  }

  if (state.day === 11 || state.day === 17) {
    return { type: "INDIVIDUAL_VOTE", reason: "scheduled" }
  }

  // Dynamic vote (if resort stale)
  if (state.dramaLevel < 20 && state.daysSinceLastElimination >= 4) {
    return { type: "INDIVIDUAL_VOTE", reason: "boring resort" }
  }

  // No vote (Pairing Ceremonies handle elimination)
  return { type: "NONE" }
}
```

**Average:** 1 vote every 4-5 days

---

## 📅 Weekly Event Flow (Producer AI Schedule)

### Week 1: Settling In (Days 1-5)

**Day 1:**
- Morning: Initial coupling (first impressions)
- Afternoon: Free socializing
- Evening: Couples established

**Day 2:**
- Morning: Get to know partner
- Afternoon: Challenge (Couple Quiz - easy)
- Evening: Free day

**Day 3:**
- Morning: Free socializing
- Afternoon: Heart Throb arrives (balanced type)
- Evening: Heart Throb dates 2 Heartbreakers

**Day 4:**
- Morning: Drama from Heart Throb
- Afternoon: Challenge (Who's Most Likely)
- Evening: Free day

**Day 5:**
- Morning: Pre-ceremony conversations
- Afternoon: Free time (spark/secure position)
- Evening: **First Pairing Ceremony (Girls Choose)**
  - 1 boy goes Heart Out

**State at end of Week 1:**
- 7 Heartbreakers remain (lost 1)
- Couples established
- First drama created

### Week 2: Drama Escalates (Days 6-10)

**Day 6:**
- Morning: New couples settling
- Afternoon: Free day
- Evening: Free day

**Day 7:**
- Morning: Free socializing
- Afternoon: Heart Throb arrives (weapon type - targets strong couple)
- Evening: Heart Throb dates

**Day 8:**
- Morning: Fallout from dates
- Afternoon: Challenge (Pulse Race)
- Evening: **Public Vote (Bottom 2 Couples)**
  - Heartbreakers save 1 couple
  - 1 couple dumped (2 people gone)

**Day 9:**
- Morning: Recovery from elimination
- Afternoon: Free time
- Evening: **Pairing Ceremony (Boys Choose)**
  - 1 girl goes Heart Out

**Day 10:**
- Morning: New couples
- Afternoon: Challenge (Rank Couples)
- Evening: Free day (build drama for Flush of Hearts)

**State at end of Week 2:**
- 6 Heartbreakers remain (lost 3 total)
- Drama high
- Couples tested
- Ready for Flush of Hearts

### Week 3: Flush of Hearts & Peak Drama (Days 11-15)

**Day 11:**
- Morning: Free socializing
- Afternoon: Free time
- Evening: **Individual Vote (Bottom 3)**
  - 1 person dumped
  - Creates singles before the Flush of Hearts

**Day 12:**
- Morning: **FLUSH OF HEARTS BEGINS**
  - Resort splits
  - 6 new Heart Throbs (3 boys, 3 girls)
- Afternoon: Flush of Hearts Day 1
- Evening: Flush of Hearts Day 1

**Day 13:**
- Morning: Flush of Hearts Day 2
- Afternoon: Flush of Hearts Day 2 (Postcard twist)
- Evening: Flush of Hearts Day 2

**Day 14:**
- Morning: Flush of Hearts Day 3 (final sparking)
- Afternoon: Flush of Hearts Day 3 (decision time)
- Evening: **FLUSH OF HEARTS PAIRING CEREMONY (Girls Choose)**
  - Massive drama
  - Couples break/stay together

**Day 15:**
- Morning: Fallout from Flush of Hearts
- Afternoon: Challenge (Lie Detector Test) - expose remaining secrets
- Evening: **Pairing Ceremony (Boys Choose)**
  - Clean up broken couples

**State at end of Week 3:**
- 8-10 Heartbreakers (some Flush people stayed)
- Major drama from Flush of Hearts
- Couples reformed
- Clear frontrunners emerging

### Week 4: Final Push (Days 16-18)

**Day 16:**
- Morning: Free socializing
- Afternoon: Free time
- Evening: **Public Vote (Bottom 2 Couples)**
  - Down to 3 couples

**Day 17:**
- Morning: Final 6 Heartbreakers
- Afternoon: Final challenge (declarations of love)
- Evening: **Individual Vote (Bottom 3)**
  - Down to 5 Heartbreakers (one single goes Heart Out, creates odd number)

**Day 18:**
- Morning: Final day preparation
- Afternoon: Final dates
- Evening: **FINAL PAIRING CEREMONY (Girls Choose)**
  - Lock in final couples
  - 1 person goes Heart Out
  - Down to 4 Heartbreakers (2 couples)

**Day 19-20:**
- **FINAL VOTE**
- Public chooses winning couple
- Prize ceremony

---

## 🧠 Playing to Character Strengths/Weaknesses

### The Core Problem

**Bad:** Player with Introvert personality tries to flirt with everyone
**Result:** Should feel fake, lower scores

**Good:** Player with Introvert personality focuses on deep 1-on-1 connections
**Result:** Feels authentic, higher scores

### How It Works

#### Personality Modifiers

```javascript
function calculateInteractionSuccess(action, target, player, context) {
  let chance = 50 // base

  // ... [existing modifiers from 02-Core-Mechanics.md] ...

  // PERSONALITY COMPATIBILITY CHECK
  const personalityPenalty = checkPersonalityMismatch(action, player.personality)
  chance -= personalityPenalty

  return Math.max(10, Math.min(95, chance))
}

function checkPersonalityMismatch(action, personality) {
  let penalty = 0

  // INTROVERT penalties
  if (personality.extraversion <= 3) { // introvert
    if (action.type === "public_flirt") penalty += 20 // unnatural in group
    if (action.type === "loud_joke") penalty += 15
    if (action.type === "center_attention") penalty += 25
  }

  // EXTROVERT penalties
  if (personality.extraversion >= 7) { // extrovert
    if (action.type === "deep_talk" && context.location === "public") penalty += 10 // prefers groups
    if (action.type === "quiet_moment") penalty += 5
  }

  // LOW AGREEABLENESS (argumentative)
  if (personality.agreeableness <= 3) {
    if (action.type === "apologize") penalty += 20 // can't apologize easily
    if (action.type === "be_supportive") penalty += 10
  }

  // HIGH NEUROTICISM (anxious)
  if (personality.neuroticism >= 7) {
    if (action.type === "bold_move") penalty += 15 // too risky, causes anxiety
    if (action.type === "public_declaration") penalty += 20
  }

  // LOW OPENNESS (traditional)
  if (personality.openness <= 3) {
    if (action.type === "experimental_flirt") penalty += 15
    if (action.type === "unconventional_approach") penalty += 10
  }

  return penalty
}
```

**Translation:**
- Introvert doing public flirting = -20% success (feels fake)
- Extrovert trying deep talk in public = -10% success (they need audience)
- Anxious person making bold move = -15% success (doesn't fit personality)
- Argumentative person apologizing = -20% success (insincere)

#### NPC Smug Response Example

**Scenario:** Player chooses flirty action, but player's Charm is low (3/10)

```javascript
// 1. Player chooses "Compliment her looks" with Chloe
// 2. Success calculation:
const chance = 50 + (player.stats.charm * 5) // 50 + 15 = 65%
// 3. Roll fails (rolled 72)
// 4. Generate failure dialogue

const failureContext = {
  action: "flirty_compliment",
  player_stat: "charm",
  player_value: 3, // low
  outcome: "awkward",
  npc_personality: chloe.personality,
  npc_preferences: chloe.preferences
}

const dialogue = await LLM.generate({
  prompt: `Player tried to flirt but failed (low charm).
           Chloe's personality: high standards, dislikes try-hards.
           Generate awkward/smug response.`,
  context: failureContext
})

// LLM returns:
{
  npcDialogue: "Chloe raises an eyebrow. 'That's... sweet, I guess?
                You should probably work on your delivery though.'",
  npcExpression: "amused_but_unimpressed",
  mechanicalEffect: {
    affection: -3,
    chemistry: -5,
    playerFeels: "embarrassed"
  }
}
```

**Player sees:**
```
You: "You look absolutely stunning tonight."

Chloe raises an eyebrow.

"That's... sweet, I guess? You should probably work on your delivery though."

She turns back to her drink, trying not to laugh.

💔 Affection -3
💔 Chemistry -5
😳 You feel embarrassed
```

#### Detecting "Fake" Relationships

**Scenario:** Player keeps pushing romance with incompatible NPC

```javascript
function detectFakeCouple(player, partner) {
  const compatibility = calculateCompatibility(player, partner) // -20 to +20
  const relationshipStrength = partner.relationships[player.id].affection
  const daysInCouple = getDaysCoupled(player, partner)

  let fakeScore = 0

  // Low compatibility but forcing it
  if (compatibility < -10 && relationshipStrength > 50) {
    fakeScore += 30 // "trying too hard with wrong person"
  }

  // Player keeps choosing flirty actions despite low chemistry
  const recentActions = getRecentActions(player, partner, days=2)
  const flirtyActions = recentActions.filter(a => a.type === "flirty").length

  if (flirtyActions >= 5 && partner.chemistry < 40) {
    fakeScore += 20 // "forcing chemistry that isn't there"
  }

  // Partner's actual preference doesn't match player
  if (!playerMatchesPreferences(player, partner.preferences)) {
    fakeScore += 25
  }

  // Apply audience penalty
  if (fakeScore >= 40) {
    partner.relationships[player.id].affection -= 10 // partner feels pressure
    player.pulseScore -= 15 // audience sees through it

    triggerEvent("FAKE_COUPLE_DETECTED", {
      message: "Audience thinks your couple is fake (-15 Pulse)"
    })
  }
}
```

**Player sees:**
```
⚠️ Public Perception Alert ⚠️

The audience thinks you and Chloe are forcing it.

Why?
- You're not her type (she likes confident guys, you're shy)
- Low chemistry (38/100) despite being together 5 days
- You keep pushing romance despite her lukewarm responses

Effect: -15 Audience Score

Advice: Either build genuine connection (deep talks, shared interests)
        OR consider a Heart Swap with someone more compatible
```

### Strengths-Based Gameplay

**Design Goal:** Player should discover their character's strengths through gameplay

**Example: High Banter, Low Charm Character**

```
Day 1: Player tries flirty approach (uses Charm)
Success rate: 55% (low Charm = 3)
Result: Awkward, some failures

Day 2: Player tries funny approach (uses Banter)
Success rate: 80% (high Banter = 8)
Result: Success! NPC laughs, affection increases

Day 3: Player realizes "I should be funny, not flirty"
Leans into Banter actions
Becomes "the funny guy" (unique role at the resort)
Audience loves it (+10 audience score)
```

**UI Feedback:**
```
Action Success Rates (Last 3 Days):

Flirty actions: 2/5 succeeded (40%) 📉
Funny actions: 7/8 succeeded (87%) 📈
Deep talk: 3/6 succeeded (50%) →

💡 Tip: You seem to excel at humor!
   Try more Banter-based actions to play to your strengths.
```

---


---

**Version:** 1.0
**Status:** ✅ Complete
**Last Updated:** 2025-10-08

**Related Files:**
- **12-Challenges-And-Events.md** - Challenges, social events, Flush of Hearts, special events
- **08-Daily-Loop.md** - Daily phase structure and timing
- **02-Core-Mechanics.md** - Stats, relationship scoring formulas
