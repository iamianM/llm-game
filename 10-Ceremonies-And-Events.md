# Ceremonies, Events, and Producer AI System

*How the game orchestrates drama, eliminations, and event flow*

**Status:** Complete design based on core decisions
**Last Updated:** 2025-10-08

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

❌ **Large Cast (10-12 Islanders)**
- **Why not:** Too many to track, dilutes focus
- **Instead:** 4 couples (8 Islanders) - player's couple + 3 others

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
- Single at recoupling + no one picks you = DUMPED
- Bottom audience ranking at vote = AT RISK
- Pressure to couple up and be interesting

✅ **Casa Amor (6 new Islanders)**
- Only need to generate 6 more (3 boys, 3 girls)
- Ultimate mid-game test

---

## 🤖 The Producer AI System

### Core Function

**The Producer AI is a strategic game master that:**
1. Analyzes current villa state (relationships, drama level, player position)
2. Decides which event type would create maximum drama/help player
3. Triggers that event at optimal moment

**Philosophy:** The Producer AI balances challenge with fairness. It won't let the game become boring OR impossible to win.

### State Analysis (What Producer AI Evaluates)

**Every morning (before announcing daily event), Producer AI checks:**

```javascript
const villaState = {
  // PLAYER STATUS
  playerCoupleStrength: playerCouple.affection + playerCouple.trust, // 0-200
  playerIsInCouple: player.coupledWith !== null,
  playerAudienceRank: getAudienceRank(player), // 1-8
  playerCoupleRank: getCoupleRank(playerCouple), // 1-4

  // DRAMA LEVEL
  dramaLevel: calculateDramaLevel(), // 0-100
  // Based on: recent arguments, love triangles, secrets, recency of last bombshell

  // STABILITY
  strongCouples: couples.filter(c => c.strength > 120).length, // 0-4
  weakCouples: couples.filter(c => c.strength < 60).length, // 0-4
  singleIslanders: islanders.filter(i => i.coupledWith === null).length,

  // TIME
  currentDay: villaState.day, // 1-20
  daysSinceLastBombshell: calculateDays(lastBombshell),
  daysSinceLastRecoupling: calculateDays(lastRecoupling),

  // STORY MOMENTUM
  recentMajorEvents: getEventsInLast2Days(), // bombshells, dumps, arguments
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
    return triggerEvent("RECOUPLING", "Boys Choose")
    // Give player chance to switch to better match
  }

  if (!playerIsInCouple) {
    return triggerEvent("BOMBSHELL", generateCompatibleBombshell(player))
    // Send in bombshell who's player's type
  }

  if (playerCoupleStrength >= 50 && playerCoupleRank === 4) {
    // Couple is decent but unpopular (probably boring)
    return triggerEvent("FORCED_DATE", { who: player, with: createDramaPairing() })
    // Force player to create drama/test loyalty
  }
}
```

**Translation:** If player is failing, Producer helps:
- Bad couple? Trigger recoupling (fresh start)
- Single? Send compatible bombshell (give option)
- Boring couple? Force dramatic date (create content)

#### Priority 2: Prevent Boredom (If Drama Too Low)

```javascript
if (dramaLevel < 30 && strongCouples >= 3) {
  // Villa is stable and boring

  if (daysSinceLastBombshell >= 3) {
    const targetCouple = getStrongestCouple()
    return triggerEvent("BOMBSHELL", generateWeaponBombshell(targetCouple))
    // Send bombshell designed to tempt strongest couple
  }

  if (daysSinceLastRecoupling >= 4) {
    return triggerEvent("RECOUPLING", "Surprise")
    // Shake things up
  }

  return triggerEvent("COMPATIBILITY_CHALLENGE", "Lie Detector Test")
  // Force couples to reveal secrets
}
```

**Translation:** If game is boring, Producer escalates:
- Send bombshell to tempt strong couples
- Force surprise recoupling
- Run lie detector test (reveals secrets)

#### Priority 3: Challenge Strong Players (If Player Too Comfortable)

```javascript
if (playerCoupleStrength > 140 && playerAudienceRank <= 3) {
  // Player is in very strong couple AND popular (might coast to victory)

  if (currentDay >= 12 && !casaAmorTriggered) {
    return triggerEvent("CASA_AMOR")
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
- Trigger Casa Amor (test loyalty)

#### Priority 4: Scheduled Events (Required Story Beats)

```javascript
if (currentDay === 1) {
  return triggerEvent("INITIAL_COUPLING")
}

if (currentDay === 5) {
  return triggerEvent("FIRST_RECOUPLING", "Girls Choose")
}

if (currentDay === 8) {
  return triggerEvent("PUBLIC_VOTE", "Bottom 2 Couples")
}

if (currentDay === 12) {
  return triggerEvent("CASA_AMOR")
}

if (currentDay === 18) {
  return triggerEvent("FINAL_VOTE")
}
```

**Translation:** Some events are locked to specific days (story structure).

#### Priority 5: Default (Generate Momentum)

```javascript
// If no special conditions met, maintain momentum

if (daysSinceLastBombshell >= 2) {
  return triggerEvent("BOMBSHELL", generateBalancedBombshell())
}

if (random(100) < 40) {
  return triggerEvent("SOCIAL_CHALLENGE")
}

return triggerEvent("FREE_DAY") // Morning + afternoon only, no evening event
```

### Event Type Catalog

**The Producer AI can trigger:**

1. **RECOUPLING** (Boys Choose / Girls Choose / Surprise)
2. **PUBLIC_VOTE** (Bottom 2 Couples / Bottom 3 Islanders / Top Couple Safe)
3. **BOMBSHELL** (Weapon / Rescue / Balanced)
4. **FORCED_DATE** (Player / Player's Partner / Other Couple)
5. **COMPATIBILITY_CHALLENGE** (Lie Detector / Quiz / Rank Couples)
6. **SOCIAL_CHALLENGE** (Heart Rate / Who's Most Likely / Snog Marry Pie)
7. **CASA_AMOR** (3-day event)
8. **HIDEAWAY_ACCESS** (Reward or advantage)
9. **FREE_DAY** (No evening event, just socializing)

---

## 📊 Audience/Public Perception System

### How It Works

**Two separate rankings:**

#### 1. Individual Audience Ranking (1-8)

**Calculated by:**
```javascript
function calculateIndividualScore(islander) {
  let score = 50 // base

  // ENTERTAINMENT VALUE (+40 max)
  score += (islander.dramaMomentsCreated * 5) // up to +25
  score += (islander.funnyMoments * 3) // up to +15

  // LIKABILITY (+30 max)
  score += (islander.kindActions * 4) // up to +20
  score += (islander.authenticMoments * 2) // up to +10

  // PENALTIES (-40 max)
  score -= (islander.meanActions * 8) // up to -30
  score -= (islander.boringScore * 2) // up to -10

  // RELATIONSHIP AUTHENTICITY (±20)
  if (islander.coupledWith) {
    const couple = getCouple(islander)
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
- If your couple is rank 4: **Recouple or inject drama into relationship**
- If you're rank 1-2: **You can coast OR create drama for entertainment**
- If falling (⬇️): **Something you did turned audience off, change approach**

### What Creates "Boring" Score (The Hidden Penalty)

```javascript
function calculateBoringScore(islander) {
  let boring = 0

  // No interactions with new people (stuck in couple bubble)
  if (islander.uniqueConversationsToday < 3) boring += 2

  // Repeating same conversations
  if (islander.conversationVariety < 50) boring += 3

  // No drama witnessed or created in 2 days
  if (daysSinceLastDramaMoment >= 2) boring += 5

  // Playing it too safe (no risky choices)
  if (islander.riskyChoicesInLast2Days === 0) boring += 3

  return boring
}
```

**Translation:** Audience wants:
- Talk to different people
- Vary your conversations
- Be involved in drama (witness or create)
- Take risks (flirt with someone new, confront someone, make bold moves)

---

## 💑 Recoupling Ceremonies

### Types of Recouplings

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
     ...otherBoys.sort((a, b) => b.audienceScore - a.audienceScore)
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

**When:** Days 5, 12 (after Casa Amor), 18 (final)

**Flow:** Same as above but reversed

#### Type 3: Surprise Recoupling (Producer Decides Order)

**When:** Triggered by Producer AI when drama is low

**Flow:**
- No warning ("Islanders, tonight there will be a recoupling. I will read out the order.")
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

### Recoupling UI/UX

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

### Elimination at Recoupling

**Clear Rule:** If you're not picked = DUMPED

**Scenario: 4 couples, 1 new bombshell (boy) enters**
- 9 people total (5 boys, 4 girls)
- Boys choose
- 5 boys pick 4 girls
- 1 girl left standing = DUMPED

**Player sees:**
```
⚠️ RECOUPLING ALERT ⚠️

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

## 🎯 Challenge System (No Physical)

### Challenge Categories

#### 1. Compatibility Challenges (Test Knowledge)

**Purpose:** Reveal how well couples know each other

**Example: "Couple Quiz"**

**Format:**
1. Partners separated
2. Asked same questions about each other
3. Answers compared
4. Points for matches

**Questions:**
- "What's your partner's biggest fear?"
- "What's their love language?"
- "What would they say is your worst habit?"
- "What's their secret talent?"

**Success Calculation:**
```javascript
function compatibilityChallenge(couple) {
  const questions = generateQuestions(couple)
  let matches = 0

  questions.forEach(q => {
    const player1Answer = getPlayerAnswer(q, couple.person1)
    const player2Answer = getPlayerAnswer(q, couple.person2)

    // Check if answers align with actual NPC personality data
    if (answersMatch(player1Answer, couple.person2.actualTrait)) {
      matches++
    }
  })

  return (matches / questions.length) * 100 // 0-100%
}
```

**Player Experience:**
- LLM generates 5 questions based on Chloe's personality
- Player selects answers from multiple choice (based on what they learned in conversations)
- High familiarity score = more likely to guess correctly
- Wrong answers = reveals how little you know her

**Rewards:**
- Win: Private date with partner (+20 relationship)
- Lose: Revealed you don't know partner (public embarrassment, -5 audience)

#### 2. Social Strategy Challenges

**Example: "Who's Most Likely To...?"**

**Format:**
1. Everyone stands in circle
2. Question asked ("Who's most likely to cheat?")
3. Everyone points to one person
4. Person with most votes drinks/takes penalty

**Player Experience:**
```
"Who's most likely to play games?"

Your vote:
[ ] Marcus (He's been grafting on everyone)
[ ] Aisha (She's strategic)
[ ] Yourself (Own it, be funny)
[ ] Tom (Safe choice, won't offend)

⚠️ Warning: Voting for Marcus will damage friendship (-5)
✅ Voting for yourself will boost audience (+3, self-aware humor)
```

**Effects:**
- Voting honestly = might damage friendships
- Voting safe = boring (-2 audience)
- Voting self-deprecating = funny (+3 audience, +5 banter perception)

**Example: "Rank the Couples (Most to Least Compatible)"**

**Format:**
1. Islanders secretly rank couples 1-4
2. Results revealed publicly
3. Drama ensues

**Effects:**
- Ranking your own couple #1 = expected
- Ranking rival couple #4 = starts beef
- Accurate ranking = gains respect (+2 EQ perception)

#### 3. Loyalty Test Challenges

**Example: "Lie Detector Test"**

**Format:**
1. One partner hooked to "lie detector" (simulated)
2. Other asks questions
3. Machine determines if lying (based on actual game state)

**Questions:**
- "Do you still have feelings for your ex-coupling?"
- "Have you kissed anyone else in the villa?"
- "Am I your #1 choice?"
- "Would you recouple if the right person came in?"

**How It Works:**
```javascript
function lieDetectorTest(question, islander) {
  const truthValue = getActualTruth(islander, question)
  // e.g., "Have you kissed anyone else?" → check kiss history

  const islanderClaims = getPlayerAnswer(question)
  // Player says "No"

  if (islanderClaims === truthValue) {
    return { result: "TRUTH", effect: "Partner relieved" }
  } else {
    return { result: "LIE", effect: "Partner devastated, trust -20" }
  }
}
```

**Player Experience:**
- Asked 5 questions by partner
- Can choose to lie or tell truth
- Lie detector is accurate (based on actual game state, not random)
- Getting caught = massive trust penalty
- Telling hard truths = trust boost (authentic)

**Rewards:** None (just drama)

#### 4. Heart Rate Challenge (Most Popular)

**IMPORTANT: NON-INTERACTIVE** - Algorithm calculates results, exposes hidden chemistry scores

**Purpose:** Reveal hidden attractions and chemistry scores that player may not know about

**Format:**
1. Everyone performs for everyone (all combinations)
2. Heart rate calculated by algorithm based on chemistry scores
3. Results revealed publicly
4. **Exposes hidden chemistry - player learns who they have chemistry with**

**How It Works:**
```javascript
function heartRateChallenge() {
  // Everyone performs for everyone (not interactive, just calculated)
  const results = []

  islanders.forEach(performer => {
    islanders.filter(i => i !== performer).forEach(target => {
      const chemistry = getRelationship(performer, target).chemistry
      const heartRate = 60 + (chemistry * 0.4) // 60-100 BPM

      results.push({
        performer,
        target,
        heartRate,
        increase: heartRate - 60
      })
    })
  })

  // Reveal ALL results publicly (exposing hidden scores)
  return results
}
```

**Player Experience (NON-INTERACTIVE, just watch results):**
```
HEART RATE CHALLENGE RESULTS:

When YOU performed:
- Chloe (partner): 92 BPM (+32) ✅ Expected
- Aisha: 95 BPM (+35) 🔥 HIGHEST!
  → Hidden chemistry revealed: 87/100 with Aisha!
- Sophie: 78 BPM (+18)

When OTHERS performed for YOU:
- Chloe: 90 BPM (+30) ✅ Good
- Marcus: 88 BPM (+28) 😳 Unexpected
  → Hidden chemistry revealed: 70/100 with Marcus!
- Tom: 65 BPM (+5)

💔 Drama: Aisha had the highest reaction to you, but she's coupled with Marcus!
😳 Discovery: You have 70 chemistry with Marcus (you didn't realize)
```

**This exposes:**
- Hidden chemistry scores the player wasn't aware of
- Love triangles that are brewing
- Who your body responds to vs who you chose
- Creates drama automatically (no player input needed)

**Effects:**
- Reveals information (player learns hidden scores)
- Creates jealousy (if partner reacts strongly to someone else)
- Creates opportunities (if you react strongly to someone new)
- Public knowledge (everyone sees everyone's reactions)

**Rewards:**
- Winner (highest total reactions) gets Hideaway access

### Challenge Scheduling

**Producer AI decides challenges based on:**

```javascript
function selectChallenge(villaState) {
  // Week 1: Light, fun challenges
  if (villaState.day <= 5) {
    return random(["Couple Quiz", "Who's Most Likely"])
  }

  // Week 2: Test couples
  if (villaState.day <= 10) {
    if (strongCouplesCount >= 2) {
      return "Heart Rate Challenge" // create doubt
    }
    return "Rank Couples" // force opinions
  }

  // Week 3+: High stakes
  if (villaState.day > 10) {
    return "Lie Detector Test" // expose secrets
  }
}
```

---

## 💣 Bombshell System

### Bombshell Types (Producer AI Chooses)

#### Type 1: Weapon Bombshell (Disrupt Strong Couple)

**When:** Strong couple exists (strength > 140) AND drama is low

**How It's Generated:**
```javascript
function generateWeaponBombshell(targetCouple) {
  const target = random(targetCouple.members)

  // Create bombshell who is target's PERFECT type
  const bombshell = {
    personality: matchesPerfectly(target.preferences.personalityType),
    appearance: target.preferences.physicalType,

    // Also make them incompatible with their partner (create contrast)
    interests: opposite(target.partner.interests),

    // High chemistry with target, low with others
    relationships: {
      [target.id]: { chemistry: 85, affection: 0 },
      ...otherIslanders.map(i => ({ [i.id]: { chemistry: 40, affection: 0 }))
    }
  }

  return bombshell
}
```

**Example:**
- Player is in strong couple with Chloe (strength 150)
- Game generates bombshell "Zara"
- Zara is player's exact type (adventurous, brunette, funny)
- Zara has 85 base chemistry with player
- Temptation created

#### Type 2: Rescue Bombshell (Help Vulnerable Player)

**When:** Player is single OR in bottom 2 audience ranking

**How It's Generated:**
```javascript
function generateRescueBombshell(player) {
  // Create bombshell compatible with player
  const bombshell = {
    personality: complementary(player.personality),
    appearance: player.preferences.physicalType,

    relationships: {
      [player.id]: { chemistry: 75, affection: 0 },
      // But ALSO compatible with 1 other (balance)
      [random(otherIslanders).id]: { chemistry: 70, affection: 0 }
    }
  }

  return bombshell
}
```

**Example:**
- Player is single and at risk
- Game sends "Jake" who player will fancy
- Jake also fancies 1 other girl (not guaranteed coupling, must still work for it)

#### Type 3: Balanced Bombshell (General Drama)

**When:** Need new energy but no specific target

**How It's Generated:**
```javascript
function generateBalancedBombshell() {
  // Compatible with 2-3 Islanders
  const targets = random(islanders, 3)

  const bombshell = {
    relationships: targets.map(t => ({
      [t.id]: { chemistry: random(60, 80), affection: 0 }
    }))
  }

  return bombshell
}
```

**Example:**
- Day 6, villa needs fresh energy
- "Ryan" enters, fancies Aisha (coupled), Sophie (single), and YOU (coupled)
- Creates 3 potential storylines

### Bombshell Entry Flow

**1. Producer AI decides to send bombshell**

**2. Generates bombshell using appropriate type**

**3. Announces via text:**
```
📱 "Islanders, you're about to meet a new bombshell.
   Boys, please gather at the fire pit."
```

**4. Bombshell enters:**
```
[New character appears]

JAKE, 25, Personal Trainer
"Hey everyone, I'm Jake. I'm here to find a real connection...
and I'm not afraid to step on toes to get it."

[Islanders react - LLM generates based on personality]
Marcus: "Great, more competition..." 😒
Chloe: "Ooh, he's fit!" 😍
You: [Choose reaction]
  - Welcome him warmly (friendly, +2 audience)
  - Size him up (competitive, -1 friendship with him)
  - Stay quiet (neutral)
```

**5. Bombshell privilege: Chooses 2 Islanders for dates**
```
JAKE: "I want to take... Chloe and Sophie on dates."

⚠️ Chloe is YOUR partner!

[You see Chloe leave with Jake]

Options:
- Trust her (high loyalty, no action)
- Graft on someone else (strategic, hedge your bets)
- Confront her when she returns (possessive, might push her away)
```

**6. Dates happen (player not present if not chosen)**
- If player on date: Normal conversation system, build chemistry
- If player NOT on date: Time passes, see other Islanders' reactions, build jealousy

**7. Bombshell must couple at next recoupling**
- Gets first pick OR
- Can steal from existing couple

### Bombshell Frequency

**Producer AI logic:**
```javascript
function shouldSendBombshell(state) {
  // Too soon (let last bombshell integrate)
  if (state.daysSinceLastBombshell < 2) return false

  // Too late (too many people, costly for LLM)
  if (state.totalIslanders >= 12) return false

  // SHOULD send if:
  return (
    state.dramaLevel < 40 || // boring
    state.strongCouples >= 3 || // too stable
    state.playerAtRisk // player needs help
  )
}
```

**Average:** 1 bombshell every 2-3 days in Weeks 1-2, less in Week 3 (Casa Amor replaces)

---

## 🎭 Social Events (Round-Table Sharing)

### Purpose

**Replace "free days"** - Every evening has structure, either ceremony OR social event

**Create bonding moments** without challenges or eliminations

**Generate knowledge and gossip** - Islanders share stories, everyone learns facts

**Lower-cost content** - No complex mechanics, just sharing + reactions

### Format

**Location:** Firepit or terrace (all Islanders gather)

**Structure:**
1. Producer announces prompt/theme
2. Each Islander shares in turn (random order)
3. Player chooses tone when it's their turn
4. LLM generates player's story based on tone
5. Islanders react based on personalities
6. Everyone learns the facts shared (added to knowledge system)

**Player Interaction:**
- Player does NOT write story themselves
- Player chooses TONE (Vulnerable / Funny / Deflect)
- LLM generates appropriate story for that tone
- Different tones = different effects

### The 6 Social Events

#### Event 1: Never Have I Ever

**Prompt:** "We're playing Never Have I Ever. Share something you've never done!"

**How It Works:**
```javascript
function neverHaveIEver() {
  const order = shuffleOrder(allIslanders)

  order.forEach(islander => {
    if (islander === player) {
      // Player chooses tone
      const toneChoice = showPlayerMenu([
        "Vulnerable - Share something meaningful you've never done",
        "Funny - Share something ridiculous",
        "Deflect - Play it safe with something boring"
      ])

      // LLM generates story
      const playerStory = await LLM.generate({
        prompt: "Generate a 'never have I ever' statement",
        tone: toneChoice,
        archetype: player.archetype,
        context: villaState
      })

      // Apply effects
      applyToneEffects(toneChoice)

    } else {
      // NPC shares (LLM generates based on personality)
      const npcStory = await LLM.generate({
        character: islander,
        prompt: "Generate never have I ever statement",
        personality: islander.personality
      })

      // Everyone learns this fact
      addKnowledge({
        fact: npcStory,
        knownBy: allIslanders,
        source: "witnessed"
      })
    }
  })
}
```

**Player Experience:**
```
NEVER HAVE I EVER

Chloe: "Never have I ever... been in love. Like, real love."
Everyone: [reactions based on personalities]
Marcus: "Really? That's surprising."

YOUR TURN:

Choose your approach:
┌─────────────────────────────────────────────┐
│ [VULNERABLE] Share something meaningful     │
│ Example: Never traveled outside the country │
│ Effect: +5 EQ perception, +8 audience       │
│         Deep connection with compatible NPCs│
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [FUNNY] Share something ridiculous          │
│ Example: Never learned to ride a bike       │
│ Effect: +3 Banter perception, +5 audience   │
│         Makes everyone laugh, lighthearted  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [DEFLECT] Play it safe                      │
│ Example: Never been skydiving               │
│ Effect: +0 perception, +1 audience (boring) │
│         No risk, no reward                  │
└─────────────────────────────────────────────┘

You choose: VULNERABLE

You: "Never have I ever... been enough for someone.
     Every relationship I've been in, they've left."

[Silence]

Chloe: "That's really honest. Thank you for sharing that."
Marcus: "Mate, that's deep. Respect."

+5 EQ Perception
+8 Audience (authentic moment)
+10 Affection with Chloe (she values vulnerability)
+8 Friendship with Marcus
```

**Tone Effects:**
```javascript
const toneEffects = {
  vulnerable: {
    audience: +8,
    perception: { eq: +5 },
    relationshipBonus: { // with NPCs who value vulnerability
      affection: +10,
      trust: +8
    },
    knowledge: "deep personal fact"
  },

  funny: {
    audience: +5,
    perception: { banter: +3 },
    relationshipBonus: { // with everyone
      affection: +3,
      friendship: +5
    },
    knowledge: "lighthearted fact"
  },

  deflect: {
    audience: +1,
    perception: {},
    relationshipBonus: {
      affection: +1
    },
    knowledge: "boring fact"
  }
}
```

#### Event 2: Most Embarrassing Story

**Prompt:** "Share your most embarrassing moment!"

**Player Experience:**
```
MOST EMBARRASSING STORY

Marcus: "I once walked around with my fly down for an entire
         first date. She didn't tell me until we were saying goodbye."
Everyone: [laughter]

YOUR TURN:

Choose your approach:
┌─────────────────────────────────────────────┐
│ [VULNERABLE] Share a genuinely humiliating  │
│              story that hurt                │
│ Effect: +6 audience (relatable)             │
│         +8 trust with empathetic NPCs       │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [FUNNY] Tell an embarrassing but hilarious  │
│         story (self-deprecating humor)      │
│ Effect: +10 audience (entertaining!)        │
│         +5 Banter perception                │
│         Everyone likes you more             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [DEFLECT] Share something mildly awkward    │
│ Effect: +2 audience (safe but boring)       │
└─────────────────────────────────────────────┘

You choose: FUNNY

You: "I once accidentally sent a love letter meant for my crush...
     to my TEACHER. She read it out loud to the class thinking
     it was a homework assignment."

[Everyone DYING laughing]

Aisha: "Oh my god, STOP! That's hilarious!"
Chloe: [wiping tears] "That's amazing!"

+10 Audience (hilarious story)
+5 Banter Perception
+5 Affection with everyone
```

**Best Strategy:** Funny tone (this event rewards humor most)

#### Event 3: Worst Breakup

**Prompt:** "Tell us about your worst breakup."

**Player Experience:**
```
WORST BREAKUP STORY

Chloe: "My ex ghosted me after two years together. Just... vanished.
       Found out he moved cities and didn't tell me."
Everyone: "That's awful..." [sympathy]

YOUR TURN:

Choose your approach:
┌─────────────────────────────────────────────┐
│ [VULNERABLE] Share a painful breakup        │
│ Effect: +10 audience (relatable pain)       │
│         +12 affection with empathetic NPCs  │
│         +10 trust (opening up)              │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [FUNNY] Make light of a bad breakup         │
│         (coping mechanism)                  │
│ Effect: +4 audience                         │
│         +3 Banter perception                │
│         Some NPCs see it as deflecting      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [DEFLECT] "It wasn't that bad" or vague     │
│ Effect: +1 audience                         │
│         NPCs notice you're guarded          │
└─────────────────────────────────────────────┘

You choose: VULNERABLE

You: "She cheated on me with my best friend. I found out at
     my own birthday party when I walked in on them.
     Destroyed me for a year."

[Heavy silence]

Marcus: "Jesus, mate. That's brutal."
Chloe: [touches your hand] "I'm so sorry that happened to you."

+10 Audience (powerful vulnerability)
+12 Affection with Chloe (she empathizes deeply)
+10 Friendship with Marcus
+10 Trust with empathetic NPCs
```

**Best Strategy:** Vulnerable tone (event naturally rewards authenticity)

#### Event 4: What Are You Looking For?

**Prompt:** "What are you really looking for in a partner?"

**Player Experience:**
```
WHAT ARE YOU LOOKING FOR?

Marcus: "I want someone who makes me want to be better. Someone
        who challenges me but also has my back no matter what."

YOUR TURN:

Choose your approach:
┌─────────────────────────────────────────────┐
│ [VULNERABLE] Share your genuine desires     │
│              and insecurities               │
│ Effect: +8 audience (authentic)             │
│         NPCs who match your type: +15       │
│         NPCs who don't match: revealed      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [FUNNY] Make a joke or lighthearted list    │
│ Effect: +3 audience (entertaining)          │
│         Doesn't reveal much (safe)          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [DEFLECT] Generic answer ("someone kind")   │
│ Effect: +1 audience (boring)                │
│         No one learns your real preferences │
└─────────────────────────────────────────────┘

You choose: VULNERABLE

You: "I want someone I can be quiet with. Someone where silence
     isn't awkward, it's comfortable. And someone who won't give
     up on me when I push them away... because I do that."

Chloe: [looking at you] "That's beautiful."
Aisha: "Wow, that's really specific."

+8 Audience
+15 Affection with Chloe (if her personality matches this)
  OR
+2 Affection with Chloe (if she's looking for excitement, not comfort)

⚠️ This reveals your type - NPCs will know if they're compatible!
```

**Strategic Choice:**
- Vulnerable = reveals compatibility (good for finding right match)
- Deflect = hides preferences (good if playing the field)

#### Event 5: Biggest Fear

**Prompt:** "What's your biggest fear?"

**Player Experience:**
```
BIGGEST FEAR

Tom: "Dying alone. Like, actually ending up with no one."
Everyone: [quiet, serious]

YOUR TURN:

Choose your approach:
┌─────────────────────────────────────────────┐
│ [VULNERABLE] Share a deep, real fear        │
│ Effect: +10 audience (powerful moment)      │
│         +15 trust with partner              │
│         Creates intimate connection         │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [FUNNY] Deflect with humor ("spiders!")     │
│ Effect: +2 audience (breaks tension)        │
│         Seen as deflecting from real answer │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [DEFLECT] Surface-level fear                │
│ Effect: +1 audience                         │
└─────────────────────────────────────────────┘

You choose: VULNERABLE

You: "Letting someone in completely... and then they leave.
     So I just... never let anyone in. And I hate that about myself."

[Everyone quiet]

Chloe: "That's exactly how I feel."

+10 Audience (raw honesty)
+15 Trust with Chloe (if coupled)
+20 Affection with Chloe (deep connection moment)
+8 EQ Perception
```

**Best Strategy:** Vulnerable (creates bonding moments with partner)

#### Event 6: Celebrity Crush

**Prompt:** "Who's your celebrity crush and why?"

**Player Experience:**
```
CELEBRITY CRUSH

Aisha: "Michael B. Jordan. I mean, have you SEEN him?
       Plus he seems genuinely nice in interviews."

YOUR TURN:

Choose your approach:
┌─────────────────────────────────────────────┐
│ [VULNERABLE] Share crush and deeper reasons │
│              (what you're attracted to)     │
│ Effect: +4 audience                         │
│         Reveals your physical/personality   │
│         preferences (NPCs learn your type)  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [FUNNY] Pick a ridiculous/unexpected crush  │
│         with hilarious reasoning            │
│ Effect: +8 audience (entertaining)          │
│         +4 Banter perception                │
│         Gets big laughs                     │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ [DEFLECT] Generic safe answer               │
│ Effect: +1 audience                         │
└─────────────────────────────────────────────┘

You choose: FUNNY

You: "Danny DeVito. Absolute legend. Confidence, humor, fearless.
     That's the energy I want."

[Everyone LAUGHING]

Marcus: "You know what? Respect. Danny DeVito IS a catch."

+8 Audience (hilarious)
+4 Banter Perception
+5 Friendship with everyone
```

**Best Strategy:** Funny (lighthearted event, humor works best)

### Social Event Scheduling

**Producer AI decides when to trigger social events:**

```javascript
function shouldTriggerSocialEvent(state) {
  // Never on ceremony nights
  if (isCeremonyNight(state.day)) return false

  // Schedule social events on specific days
  const scheduledDays = [2, 6, 9, 11, 15, 17]
  if (scheduledDays.includes(state.day)) {
    return selectSocialEvent(state)
  }

  // Or trigger if drama is too high (need bonding moment)
  if (state.dramaLevel > 70) {
    return selectSocialEvent(state, type="bonding")
  }

  return false
}

function selectSocialEvent(state, type="balanced") {
  // Early game: Lighthearted events
  if (state.day <= 5) {
    return random(["Celebrity Crush", "Most Embarrassing Story", "Never Have I Ever"])
  }

  // Mid game: Mix of deep and light
  if (state.day <= 12) {
    return random(["Worst Breakup", "What Are You Looking For", "Biggest Fear"])
  }

  // Late game: Emotional depth (final bonding before finale)
  if (state.day > 12) {
    return random(["Biggest Fear", "What Are You Looking For"])
  }
}
```

**Frequency:** ~6 social events total across 20-day run

**Distribution:**
- Week 1: 1-2 lighthearted events (Celebrity Crush, Most Embarrassing)
- Week 2: 2 mixed events (Never Have I Ever, Worst Breakup)
- Week 3+: 2 deep events (Biggest Fear, What Are You Looking For)

### Effects Summary

**Tone Comparison:**

| Tone | Audience Gain | Relationship Gain | Perception Gain | Risk |
|------|---------------|-------------------|-----------------|------|
| **Vulnerable** | +6 to +10 | +10 to +20 (compatible NPCs) | +5 EQ | Reveals info |
| **Funny** | +3 to +10 | +3 to +8 (everyone) | +3 to +5 Banter | Safe |
| **Deflect** | +1 to +2 | +1 | None | Very safe, very boring |

**Strategic Considerations:**

**Always Vulnerable:**
- If in strong couple (deepen bond)
- If need to identify compatible matches
- If audience score is stable (can afford authenticity)

**Always Funny:**
- If audience score is low (need entertainment boost)
- If want to stay popular without revealing much
- If banter-focused character

**Mix:**
- Vulnerable on deep topics (Biggest Fear, Worst Breakup)
- Funny on light topics (Celebrity Crush, Most Embarrassing)
- Deflect = almost never optimal (boring penalty)

### Implementation Notes

**LLM Story Generation:**

```javascript
async function generatePlayerStory(event, tone, player) {
  const prompt = {
    event: event.type, // "biggest_fear", "celebrity_crush", etc.
    tone: tone, // "vulnerable", "funny", "deflect"
    archetype: player.archetype,
    backstory: player.backstoryHints, // if any
    context: {
      currentCouple: player.coupledWith,
      villaPosition: player.audienceRank,
      recentEvents: getRecentEvents(2)
    }
  }

  const story = await LLM.generate({
    system: `Generate a ${tone} response to the prompt: ${event.prompt}.
             Keep it 2-3 sentences, conversational, authentic to character.`,
    context: prompt
  })

  return story
}
```

**Example outputs:**

**Vulnerable + Biggest Fear:**
```
"My biggest fear is waking up one day and realizing I wasted my life
playing it safe. That I never took the risk, never put myself out there,
and just... ended up alone because I was too scared to try."
```

**Funny + Celebrity Crush:**
```
"Gordon Ramsay, hands down. The man is passionate, hilarious, and can cook.
Plus if we ever argue, at least the insults would be creative. 'You donkey!'"
```

**Deflect + Worst Breakup:**
```
"Oh, you know, the usual. We just grew apart. It was mutual.
Nothing too dramatic."
```

### Knowledge System Integration

**All social events add knowledge:**

```javascript
function processSocialEvent(event) {
  allIslanders.forEach(speaker => {
    const story = speaker === player ?
      playerStory :
      await generateNPCStory(speaker, event)

    // Create knowledge fact
    const fact = {
      type: event.type,
      speaker: speaker.id,
      content: story,
      emotionalDepth: getTone(story), // vulnerable/funny/deflect
      knownBy: allIslanders.map(i => i.id), // everyone witnessed
      source: "social_event",
      day: currentDay
    }

    addKnowledgeFact(fact)

    // NPCs remember this for future conversations
    // Can reference: "You mentioned at the firepit that..."
  })
}
```

**This creates:**
- Conversation continuity (NPCs reference past events)
- Gossip fuel (can tell others what someone shared)
- Relationship depth (shared vulnerable moments = bonding)

---

## 🏝️ Casa Amor (Days 12-14)

### What It Is

**The villa splits:**
- Original boys stay in main villa
- 3 new girls arrive (bombshells)
- Original girls go to "Casa Amor" villa
- 3 new boys arrive there
- **No communication for 3 days**

**Purpose:** Ultimate loyalty test

### How It Works

#### Day 12 Morning: The Split

```
📱 "Islanders, the girls must pack their bags immediately.
   You're going to Casa Amor!"

[Girls leave, boys stay]

MAIN VILLA (Player if male):
- You + 3 other original boys
- 3 new girls arrive
- Build new connections OR stay loyal

CASA AMOR VILLA (Player if female):
- You + 3 other original girls
- 3 new boys arrive
- Build new connections OR stay loyal
```

#### Days 12-14: Temptation

**Player Experience:**

```
You're in Casa Amor (if female) or Main Villa (if male).

New bombshells designed to be your type:
- Jake: 85 chemistry (adventurous, your type)
- Ryan: 70 chemistry (funny, compatible)
- Marcus: 60 chemistry (loyal, safe)

Your original partner (Chloe) is in other villa with new boys.
You have NO IDEA what she's doing.

Time: 3 days (morning + afternoon phases only)
```

**Each day in Casa Amor:**
1. Morning: Free socializing with new bombshells
2. Afternoon: No challenges, just graft/talk
3. Evening: See snippets from other villa (optional twist)

**The Postcard Twist (Optional Drama Boost):**
```
📱 "Islanders, you've received a postcard from the other villa..."

[Image shown: Chloe sitting close to new boy, laughing]

Caption: "Having a great time! 😘"

⚠️ Is she recoupling? Or just being friendly?
You don't know. Paranoia sets in.
```

#### Day 14 Evening: The Recoupling

**Format: Girls Choose (Most Dramatic)**

**Both villas reunite at firepit:**

```
1. Original girls return to main villa
2. New Casa Amor girls stay in lineup
3. Girls choose one by one:

CHLOE (Player's Original Partner):
"I want to couple up with this boy because..."

Options:
A) "...he's been loyal and I trust him. [Player Name]"
   → Stayed loyal, couple reunites ❤️

B) "...we have a real spark. Jake."
   → Recoupled with Casa boy 💔 Player heartbroken

Player's reaction options (if Chloe recoupled):
- Accept it gracefully (high EQ, +5 audience)
- Get angry (dramatic, +8 audience but -10 with Chloe)
- Recouple with new girl too (mutual, clean break)

2. PLAYER'S TURN (if male):
   - Stick with Chloe (if she picked you)
   - OR recouple with Casa girl (betrayal)

3. Other couples resolve...
```

**Possible Outcomes:**

**Outcome 1: Both Stayed Loyal**
- Couple strength +30
- Audience score +15
- Trust maxed out
- Often leads to victory

**Outcome 2: Player Loyal, Partner Recoupled**
- Player heartbroken
- Audience sympathy (+10 individual score)
- Player now single (must find new match)
- Becomes underdog story

**Outcome 3: Both Recoupled**
- Clean break
- No hard feelings
- Both in new couples
- Audience neutral (looks like it wasn't real)

**Outcome 4: Player Recoupled, Partner Loyal**
- Partner devastated
- Audience hates player (-15 score)
- Player in new couple but low trust
- Hard to recover

### Casa Amor Success Rates (NPC Behavior)

**NPCs decide to recouple based on:**
```javascript
function npcCasaAmorDecision(npc, originalPartner, bestCasaMatch) {
  const originalStrength = getRelationship(npc, originalPartner).strength
  const casaChemistry = getRelationship(npc, bestCasaMatch).chemistry

  let recoupleChance = 0

  // Base decision
  if (originalStrength < 60) recoupleChance = 70 // weak couple, likely switch
  if (originalStrength < 100) recoupleChance = 40 // decent couple, maybe switch
  if (originalStrength >= 100) recoupleChance = 15 // strong couple, unlikely

  // Casa chemistry modifier
  recoupleChance += (casaChemistry - 50) // high chemistry = more tempted

  // Personality modifier
  if (npc.stats.loyalty < 4) recoupleChance += 20 // low loyalty
  if (npc.attachmentStyle === "avoidant") recoupleChance += 15

  // Drama boost (producer AI)
  if (tooManyCouplesStayedLoyal) recoupleChance += 20 // force some drama

  return random(100) < recoupleChance
}
```

**Expected:** 2-3 out of 4 couples will have at least one person recouple

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

3. Islanders vote to save ONE couple:
   - Each Islander votes privately
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
   "The three Islanders with the lowest public support are..."

   ⚠️ Liam (Rank 8, Score: 38)
   ⚠️ Emma (Rank 7, Score: 42)
   ⚠️ YOU (Rank 6, Score: 48)

3. Fellow Islanders vote:
   - Vote to DUMP one person
   - Person with most votes leaves
   - Their partner becomes single

4. If YOU are at risk:
   ⚠️ You're at risk! Your fate is in other Islanders' hands.

   Who might save you:
   ✅ Chloe (partner, will vote for someone else)
   ✅ Marcus (high friendship)
   ❓ Aisha (neutral)
   ❌ Tom (low friendship, might vote you out)
```

**Effects:**
- Individual eliminated (partner becomes single)
- Friendship critical (need allies)
- Creates singles before recoupling

#### Vote Type 3: No Public Vote (Recoupling Only)

**When:** Days 5, 9, 15, 18
**Format:** No vote, just recoupling

**Flow:**
- Recoupling happens
- Unpicked person = dumped
- No vote needed

### When Player Is At Risk

**Bottom 2 Couple:**
```
⚠️ DANGER ⚠️

You and Chloe are in the bottom 2 couples.

Why?
- Couple score: 52/100 (boring, no drama)
- You've been too stable (no storylines)

Islanders will vote to save one couple:

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

Islanders vote to DUMP one person:

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

  // Dynamic vote (if villa stale)
  if (state.dramaLevel < 20 && state.daysSinceLastElimination >= 4) {
    return { type: "INDIVIDUAL_VOTE", reason: "boring villa" }
  }

  // No vote (recouplings handle elimination)
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
- Afternoon: Bombshell arrives (balanced type)
- Evening: Bombshell dates 2 Islanders

**Day 4:**
- Morning: Drama from bombshell
- Afternoon: Challenge (Who's Most Likely)
- Evening: Free day

**Day 5:**
- Morning: Pre-recoupling conversations
- Afternoon: Free time (graft/secure position)
- Evening: **First Recoupling (Girls Choose)**
  - 1 boy dumped

**State at end of Week 1:**
- 7 Islanders remain (lost 1)
- Couples established
- First drama created

### Week 2: Drama Escalates (Days 6-10)

**Day 6:**
- Morning: New couples settling
- Afternoon: Free day
- Evening: Free day

**Day 7:**
- Morning: Free socializing
- Afternoon: Bombshell arrives (weapon type - targets strong couple)
- Evening: Bombshell dates

**Day 8:**
- Morning: Fallout from dates
- Afternoon: Challenge (Heart Rate)
- Evening: **Public Vote (Bottom 2 Couples)**
  - Islanders save 1 couple
  - 1 couple dumped (2 people gone)

**Day 9:**
- Morning: Recovery from elimination
- Afternoon: Free time
- Evening: **Recoupling (Boys Choose)**
  - 1 girl dumped

**Day 10:**
- Morning: New couples
- Afternoon: Challenge (Rank Couples)
- Evening: Free day (build drama for Casa Amor)

**State at end of Week 2:**
- 6 Islanders remain (lost 3 total)
- Drama high
- Couples tested
- Ready for Casa Amor

### Week 3: Casa Amor & Peak Drama (Days 11-15)

**Day 11:**
- Morning: Free socializing
- Afternoon: Free time
- Evening: **Individual Vote (Bottom 3)**
  - 1 person dumped
  - Creates singles before Casa

**Day 12:**
- Morning: **CASA AMOR BEGINS**
  - Villa splits
  - 6 new bombshells (3 boys, 3 girls)
- Afternoon: Casa Amor Day 1
- Evening: Casa Amor Day 1

**Day 13:**
- Morning: Casa Amor Day 2
- Afternoon: Casa Amor Day 2 (Postcard twist)
- Evening: Casa Amor Day 2

**Day 14:**
- Morning: Casa Amor Day 3 (final grafting)
- Afternoon: Casa Amor Day 3 (decision time)
- Evening: **CASA AMOR RECOUPLING (Girls Choose)**
  - Massive drama
  - Couples break/stay together

**Day 15:**
- Morning: Fallout from Casa Amor
- Afternoon: Challenge (Lie Detector Test) - expose remaining secrets
- Evening: **Recoupling (Boys Choose)**
  - Clean up broken couples

**State at end of Week 3:**
- 8-10 Islanders (some Casa people stayed)
- Major drama from Casa Amor
- Couples reformed
- Clear frontrunners emerging

### Week 4: Final Push (Days 16-18)

**Day 16:**
- Morning: Free socializing
- Afternoon: Free time
- Evening: **Public Vote (Bottom 2 Couples)**
  - Down to 3 couples

**Day 17:**
- Morning: Final 6 Islanders
- Afternoon: Final challenge (declarations of love)
- Evening: **Individual Vote (Bottom 3)**
  - Down to 5 Islanders (one single dumped, creates odd number)

**Day 18:**
- Morning: Final day preparation
- Afternoon: Final dates
- Evening: **FINAL RECOUPLING (Girls Choose)**
  - Lock in final couples
  - 1 person dumped
  - Down to 4 Islanders (2 couples)

**Day 19-20:**
- **FINAL VOTE**
- Public chooses winning couple
- Prize ceremony

---

## 🎭 Special Events

### Event: Hideaway Access

**What:** Private bedroom for one couple, overnight

**When:** Reward for challenge OR Producer AI gift to strong couple

**Effects:**
- Couple goes to Hideaway (removed from villa for evening)
- Private conversation (3-5 exchanges, very intimate)
- Massive relationship boost:
  ```javascript
  hideawayEffects = {
    chemistry: +30,
    affection: +20,
    trust: +15,
    unlockActions: ["exclusive_couple", "future_plans_conversation"]
  }
  ```

**Strategic Value:**
- Makes couple very strong (harder to break)
- But removes couple from villa drama (boring if overused)

**Producer AI logic:**
```javascript
function shouldOfferHideaway(state) {
  // Reward challenge winner
  if (challengeJustCompleted) return true

  // Boost struggling but genuine couple
  if (state.playerCouple.strength > 100 && state.playerCouple.audienceRank === 4) {
    return true // help them with romantic content
  }

  return false
}
```

### Event: Forced Date

**What:** Producer chooses 2 Islanders to go on date

**When:** Triggered by Producer AI for drama

**Scenarios:**

**Scenario 1: Test Player's Couple**
```
📱 "Marcus and Chloe, you're going on a date.
   Please get ready to leave the villa."

⚠️ Chloe is YOUR partner!

She's going on a date with Marcus (high chemistry: 75)

While they're gone:
- You stay in villa (see other couples, build jealousy)
- OR graft on someone else (strategic backup)
```

**Scenario 2: Help Single Player**
```
📱 "You and Aisha are going on a date."

✅ You're single, this is your chance!

Aisha is coupled with Tom (weak couple, strength 45)
This is Producer helping you find a match
```

**Date Flow:**
- Romantic location (beach, rooftop dinner)
- 3-5 conversation exchanges
- +20 chemistry bonus (forced proximity)
- Return to villa, drama ensues

### Event: Love Triangle Lock-In

**What:** Producer forces 3 Islanders to spend evening together

**When:** Love triangle detected (2 people fancy same person)

**Example:**
```
📱 "Marcus, Chloe, and [Player Name], you three will spend
   the evening in the Hideaway. No one else allowed."

Setup: You and Marcus both fancy Chloe

Forced to confront it:
- 3-way conversation (group mechanics from 09-Social-Dynamics.md)
- Chloe must choose between you
- Loser watches it happen
- Drama maximized
```

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
    player.audienceScore -= 15 // audience sees through it

    triggerEvent("FAKE_COUPLE_DETECTED", {
      message: "Audience thinks your couple is fake (-15 public perception)"
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
        OR consider recoupling with someone more compatible
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
Becomes "the funny guy" (unique role in villa)
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

## ❓ Open Questions & Things to Review

### Questions for You

1. **Casa Amor Bombshell Quality**
   - Should Casa bombshells be higher quality (more compatible) than regular bombshells?
   - Or same level? (6 regular Islanders vs 6 Casa)

2. **Hideaway Rules**
   - Can you take someone OTHER than your partner to Hideaway? (drama bomb)
   - Or always must be coupled to use it?

3. **Vote Visibility**
   - Should player see individual Islander votes? ("Marcus voted to dump you")
   - Or just final tally? (More mystery but might feel unfair)

4. **Comeback Mechanic**
   - If dumped on Day 5, can you return as bombshell on Day 10?
   - Or elimination is final? (true roguelite)

5. **Final Vote Mechanics**
   - Is it JUST audience score that determines winner?
   - Or couple strength + audience combined?
   - Should player see exact formula?

6. **Challenge Variety**
   - 6 challenge types enough? (Quiz, Rank, Lie Detector, Heart Rate, Who's Most Likely, Love Triangle)
   - Need more? Or is variety achieved through LLM generating different questions/scenarios?

7. **Bombshell Integration**
   - If bombshell enters but NO ONE couples with them, do they auto-dump after 2 days?
   - Or can they stay single longer? (drains LLM cost)

### Things We Should Review

#### 1. Audience Score Formula Tuning

**Concern:** Is the formula too punishing for strategic play?

Current formula heavily rewards:
- Drama creation
- Authenticity
- Likeability

But penalizes:
- Mean behavior (even if strategic)
- Fake couples (even if trying to survive)

**Question:** Should we add "strategic gameplay" as positive factor?
- Reward smart recoupling decisions
- Reward successful grafting
- Make it viable to "play the game" without tanking audience score

**Proposed addition:**
```javascript
// Strategic skill bonus
if (playerMadeCleverMove) score += 5 // "They're playing the game well!"
```

#### 2. Introvert/Extrovert Balance

**Concern:** Is Introvert personality too limiting?

- Introverts get penalties for public actions (where most drama happens)
- Extroverts can do everything (groups AND 1-on-1)

**Possible solution:**
- Give Introverts unique advantages:
  - +20% success on deep 1-on-1 conversations
  - +10 audience when they DO make bold move (character growth)
  - Higher trust gains (seen as genuine)

#### 3. Producer AI Helping Too Much?

**Concern:** Does Producer AI remove challenge?

Current logic:
- Player at risk? Send rescue bombshell
- Player boring? Force dramatic date

**Question:** Should there be "hard mode" where Producer is neutral?
- Only triggers scheduled events
- No rescue mechanics
- Pure player skill

#### 4. Casa Amor Scope

**Concern:** Is Casa Amor too complex for POC?

Requirements:
- Generate 6 new Islanders (expensive)
- Track 2 villas simultaneously
- Parallel storylines
- Complex recoupling ceremony

**Alternative for POC:**
- Simplified Casa Amor: 3 new bombshells, don't split villa
- Or cut it entirely, add later

**My recommendation:** Keep it, it's too iconic. But make it Day 12-14 only (not longer).

#### 5. Elimination Frequency

**Current pace:**
- Day 1: 8 Islanders
- Day 5: 7 Islanders (-1)
- Day 8: 5 Islanders (-2, couple dumped)
- Day 9: 4 Islanders (-1)
- Day 11: 3 Islanders (-1)
- Day 12-14: Casa Amor (add 6, now 9 total)
- Day 15: 8 Islanders (-1)
- Day 16: 6 Islanders (-2, couple dumped)
- Day 17: 5 Islanders (-1)
- Day 18: 4 Islanders (-1, final)
- Day 20: 2 winners

**Question:** Is this too fast? Too slow?
- Too fast = not enough time to bond with characters
- Too slow = diluted focus, too many people to track

#### 6. Free Day Frequency

**Current:** Some days have no evening event (Free Days)

**Purpose:**
- Give player time to socialize without event pressure
- Build relationships organically
- Reduce LLM cost (no ceremony generation)

**Question:** How many free days?
- Current plan: ~4 free days out of 20 (20%)
- Too many = boring
- Too few = overwhelming pace

#### 7. Player Personality Choice

**Current:** Player picks personality at start (or random)

**Question:** Should player personality be:
- **Fixed choice** (pick Introvert/Extrovert, etc. before run)
- **Discovered** (game assigns hidden personality, player learns through feedback)
- **Hybrid** (player picks archetype, game fills in details)

**My recommendation:** Fixed choice with clear stat preview
```
Choose Your Islander:

THE HEARTTHROB
Charm: 8, Banter: 5, Loyalty: 6, EQ: 7
Personality: Confident Extrovert
Strengths: Flirting, first impressions, romantic moments
Weaknesses: Struggles with deep emotional talks

THE COMEDIAN
Charm: 5, Banter: 9, Loyalty: 7, EQ: 6
Personality: Witty Extrovert
Strengths: Group settings, diffusing tension, making people laugh
Weaknesses: Romantic moments can feel forced
```

#### 8. NPC Autonomous Coupling

**Current:** NPCs couple/recouple based on algorithm

**Concern:** Will it feel random to player?

**Example:**
```
Day 5 Recoupling:
Marcus picks... Chloe (your partner!)

Player: "Why did he pick her?!"
```

**Solution:** Show reasoning (optional UI toggle)
```
Marcus picked Chloe because:
- High chemistry: 78
- Compatible personalities (both extroverts)
- Strategic: Chloe is popular (rank 3)
- Your couple strength was only 65 (vulnerable)
```

Player can see WHY they lost partner (feels fair, not random)

#### 9. Challenge Reward Balance

**Current rewards:**
- Dates (+20 relationship)
- Hideaway (+30 chemistry)
- Immunity (safety from vote)
- Power (choose who goes on dates)

**Question:** Are these meaningful enough?
- +20 relationship = significant but not game-breaking ✅
- Immunity = very strong (guarantees survival) ⚠️ Maybe too strong?
- Power = creates drama ✅

**Possible nerf:** Immunity only saves you if bottom 3 (not if bottom 1)

#### 10. Win Condition Clarity

**Current:** Win final vote (based on audience score)

**Question:** Should player see EXACT win formula?

**Transparent (player sees):**
```
Final Vote Calculation:
- Individual Audience Score: 85/100 (50% weight)
- Couple Audience Score: 78/100 (30% weight)
- Couple Strength: 145/200 (20% weight)

Total Score: 83/100
Current ranking: 1st place (WINNING) 🥇
```

**Opaque (player doesn't see):**
```
You and Chloe seem to be fan favorites... but anything could happen!
```

**My recommendation:** Show ranking (1st/2nd) but not exact formula (keep some mystery)

---

## 📋 Summary: What We've Designed

### Core Systems

✅ **Producer AI**
- Analyzes villa state
- Triggers events strategically
- Balances challenge with fairness
- Helps struggling players, challenges strong ones

✅ **Audience System**
- Individual rankings (1-8, visible)
- Couple rankings (1-4, visible)
- Trajectory indicators (↑→↓)
- Visible to player (forces entertaining gameplay)

✅ **Recoupling Ceremonies**
- 3 types (Boys/Girls/Surprise)
- Single at ceremony + unpicked = DUMPED
- Player sees stats when choosing
- NPCs use algorithm (chemistry + strategy + compatibility)

✅ **Challenge System (No Physical)**
- Compatibility (Quiz, Lie Detector)
- Social (Who's Most Likely, Rank Couples)
- Loyalty (Heart Rate, Love Triangle)
- All use stats and relationships (no animation needed)

✅ **Bombshell System**
- 3 types (Weapon, Rescue, Balanced)
- Smart generation (compatible with 1-3 targets)
- Triggered by Producer AI based on state

✅ **Casa Amor (Days 12-14)**
- 6 new Islanders (3 boys, 3 girls)
- Villa splits (no communication)
- Ultimate loyalty test
- 4 possible outcomes (both loyal, one recouples, etc.)

✅ **Voting System**
- Couple votes (bottom 2, Islanders save 1)
- Individual votes (bottom 3, Islanders dump 1)
- Friendship matters (allies save you)

✅ **Personality-Driven Success**
- Playing against type = penalties
- Forcing fake romance = audience penalty
- Must play to character strengths

### Weekly Flow

**Week 1:** Settling, first bombshell, first recoupling
**Week 2:** Drama escalates, public votes, multiple recouplings
**Week 3:** Casa Amor (peak drama), couples reform
**Week 4:** Final eliminations, final vote

### What Makes It Work

1. **Visible stakes** (audience meter, clear elimination rules)
2. **Fair systems** (player can strategize, not random)
3. **Skill expression** (play to strengths, build relationships)
4. **Smart drama** (Producer AI creates moments, not chaos)
5. **Forgiving but challenging** (help when struggling, challenge when coasting)

---

*Next steps: Review open questions, tune formulas, design specific challenge templates*

**Version:** 1.0
**Last Updated:** 2025-10-08
