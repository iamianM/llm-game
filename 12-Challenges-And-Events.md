# Challenges, Social Events, and Special Events

*Daily activities, challenges, social bonding events, and dramatic twists*

**Document Status:** Design canon (intent).
**Last Updated:** 2025-10-08

> **Implementation note.** This document is the design intent for daily
> challenges. The **shared minigame harness** that turns these from single
> dice rolls into real player-driven scenes is defined in
> [docs/minigame-system.md](docs/minigame-system.md). The **per-minigame
> implementation specs** live under [docs/minigames/](docs/minigames/):
> [Compatibility Quiz](docs/minigames/compatibility-quiz.md) ·
> [The Couples Quiz](docs/minigames/couples-quiz.md) ·
> [Lie Detector](docs/minigames/lie-detector.md) ·
> [Pulse Race](docs/minigames/heart-rate.md) ·
> [Kiss Wed Pass](docs/minigames/snog-marry-pie.md) ·
> [Final Couples](docs/minigames/final-couples.md). When the implementation
> docs and this canon disagree, the implementation docs win
> ([current-plan.md](docs/current-plan.md), "Documentation Rules").

---

## Table of Contents

- [Challenge System (No Physical)](#-challenge-system-no-physical)
- [Social Events (Round-Table Sharing)](#-social-events-round-table-sharing)
- [Casa Amor](#-casa-amor-days-12-14)
- [Special Events](#-special-events)

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


---

**Version:** 1.0
**Status:** ✅ Complete
**Last Updated:** 2025-10-08

**Related Files:**
- **10-Elimination-System.md** - Producer AI, recouplings, voting, bombshells
- **08-Daily-Loop.md** - Daily phase structure and timing
- **07-Gossip-And-Information.md** - Knowledge system used by social events
