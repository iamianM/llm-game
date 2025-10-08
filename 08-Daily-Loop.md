# Daily Loop and Run Structure

*Pacing, progression, and the structure of a complete season*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Run Length and Pacing](#run-length-and-pacing)
- [The Four Phases](#the-four-phases)
- [Daily Structure](#daily-structure)
- [Week-by-Week Progression](#week-by-week-progression)
- [The Strategic Layer](#the-strategic-layer)
- [Escalation Curve](#escalation-curve)
- [Example Full Day](#example-full-day)
- [Run Completion](#run-completion)

---

## Run Length and Pacing

### Target Run Time

**2-3 hours per complete season**

**Why this length:**
- ✅ Long enough to build emotional investment
- ✅ Short enough to complete in one session
- ✅ Respects player time (not 40+ hour commitment)
- ✅ Encourages replaying (try different approaches)
- ✅ Matches "binge 3-4 episodes of Love Island" experience

**Not 20 minutes (too short):**
- ❌ Can't build relationships
- ❌ No emotional attachment
- ❌ Feels arcadey

**Not 10+ hours (too long):**
- ❌ Exhausting for casual audience
- ❌ Hard to replay
- ❌ Requires too much commitment

### Days vs. Real-Time

**In-game time:** 15-20 key days (not full 42 days)

**Real-time:** 2-3 hours

**Math:**
- 18 days × 8-10 minutes per day = 144-180 minutes = 2.4-3 hours

**Compression strategy:**
- Not every day is played
- "Highlight reel" of important moments
- Time skips between key days: "Three days later..."

**Example progression:**
```
Day 1: Villa entry, initial coupling
Day 2-3: Getting to know people
[Skip to Day 5]
Day 5: First recoupling
Day 6-7: New dynamics
[Skip to Day 9]
Day 9: Bombshell arrives
...
Day 18: Final vote
```

---

## The Four Phases

Each played day has **four phases:**

### 1. Morning Free Time

**Duration:** 90 minutes (game time)

**Real-time:** 6-8 minutes

**Purpose:** Social time, relationship building, gossip gathering

**Player actions:**
- 3-4 conversations (20-25 min each)
- Move between locations
- Choose who to prioritize

**What happens:**
- Reinforce existing relationships
- Gather information about last night
- Plan strategy for the day
- Respond to recent drama

**NPCs:**
- Move around villa autonomously
- Have their own conversations
- Build/damage relationships
- Create drama

**Example morning:**
```
MORNING - Day 5

You wake up in the bedroom. Chloe is getting ready nearby.

Time available: 90 minutes

Recent events:
• Last night: You kissed Chloe on the terrace
• Rumor: Marcus and Sophie argued (heard from Liam)

Who do you want to talk to?
→ Chloe (reassure after last night)
→ Liam (get details about Marcus/Sophie drama)
→ Marcus (confront or befriend?)
→ Check on Sophie (opportunity?)

Or move to:
→ Pool (Aisha, Tom sunbathing)
→ Gym (Marcus working out)
→ Kitchen (Sophie making coffee)
```

**Strategic choices:**
- Do I reinforce my couple or explore options?
- Do I gather intel or avoid drama?
- Do I talk to many people briefly or few people deeply?

---

### 2. Daily Challenge

**Duration:** 60 minutes (game time)

**Real-time:** 4-6 minutes

**Purpose:** Stat-based competition, win advantages, test relationships

**Types of challenges:**
- **Couple compatibility quiz** (tests how well you know partner)
- **Physical challenge** (beach volleyball, obstacle course)
- **Banter/performance** (stand-up comedy, impression contest)
- **Trust challenge** (blindfolded tasks, truth/dare)

**Mechanics:**
```javascript
const challenge = {
  type: "compatibility_quiz",
  stat_used: "emotional_intelligence",
  difficulty: 60, // threshold

  questions: [
    {
      question: "What is Chloe's dream job?",
      correctAnswer: "open a cafe",
      playerKnows: player.knowledge.includes("chloe_dream_cafe")
    },
    // ... 5-7 questions
  ],

  prize: {
    type: "date_for_two",
    location: "beach_picnic",
    duration: 60, // extra time with partner
    bonuses: {
      affection: +10,
      trust: +8,
      chemistry: +7
    }
  }
}
```

**Challenge flow:**

1. **Announcement**
   ```
   🔔 "ISLANDERS, IT'S TIME FOR TODAY'S CHALLENGE!"

   Today: Couple Compatibility Quiz
   Test how well you know your partner!

   Prize: Romantic beach picnic date for two
   ```

2. **Player participates**
   ```
   Question 1: What is Chloe's biggest fear?

   A) Being judged
   B) Being alone
   C) Heights
   D) Failure

   [You know this from your deep conversation on Day 6]
   → Select B (Correct!)
   ```

3. **Stat check per question**
   ```javascript
   const success = (player.stats.emotional_intelligence * 10) + (familiarity with partner) > difficulty
   // Or: player actually knows the answer (learned through conversation)
   ```

4. **Results**
   ```
   Challenge Results:

   1st Place: You and Chloe (6/7 correct)
   2nd Place: Liam and Emma (5/7)
   3rd Place: Marcus and Sophie (3/7)

   🏆 You won the beach picnic date!
   💕 Chloe is impressed by how well you know her (+5 Trust)
   📺 Public Perception +8 (audience loves genuine couples)
   ```

5. **Prize execution**
   - Scheduled for afternoon phase
   - Private time with partner
   - Massive relationship boost
   - Other Islanders continue without you

**Challenge benefits:**
- ✅ Breaks up social gameplay
- ✅ Uses stats meaningfully
- ✅ Creates advantages (dates, immunity)
- ✅ Public perception impact
- ✅ Tests relationships

---

### 3. Afternoon Free Time

**Duration:** 90 minutes (game time)

**Real-time:** 6-8 minutes

**Purpose:** Strategic positioning, final moves before evening event

**Differences from morning:**
- More urgency (evening event approaching)
- Knowledge of challenge results (winners/losers)
- Reactions to morning drama
- Bombshells enter here (if scheduled)

**Strategic focus:**
- If recoupling tonight: Lock down your position
- If bombshell entered: Assess threat/opportunity
- If partner seems distant: Repair relationship
- If exploring options: Make moves now

**Example afternoon:**
```
AFTERNOON - Day 7

Challenge winner: You and Chloe (won beach date)

You return from your date. The villa feels tense.

Time available: 90 minutes

⚠️ TONIGHT: Recoupling ceremony (girls choose)

New situation:
• Bombshell Aisha entered while you were on date
• She's been chatting with Marcus
• Sophie looks upset
• Chloe is confident (your couple is strong)

Strategic priorities:
→ Talk to Chloe (ensure she picks you)
→ Talk to Aisha (assess if she's a threat)
→ Check on Sophie (she might recouple away from Marcus)
→ Talk to Marcus (understand his play)
```

**This is the "make or break" phase:**
- Last chance before major event
- Information gathering critical
- Strategic moves must happen NOW

---

### 4. Evening Event

**Duration:** Variable (story-driven)

**Real-time:** 5-10 minutes

**Purpose:** Major dramatic event, state changes, eliminations

**Event types:**
- **Recoupling ceremony**
- **Dumping/elimination**
- **Bombshell arrival**
- **Casa Amor twist**
- **Truth/dare drama**
- **Lie detector test**

**No time limit:**
- Player doesn't choose actions
- Events unfold narratively
- LLM-generated drama
- State changes applied

**Example recoupling ceremony:**

```
EVENING - Day 7: Recoupling Ceremony

All Islanders gather around the fire pit.

The girls will choose who they want to couple with.
The boy not picked will be dumped from the island.

Current couples:
• You + Chloe
• Marcus + Sophie
• Liam + Emma
• Tom + (single)
• Aisha (bombshell, single)

The girls choose in this order: Sophie, Chloe, Emma, Aisha

---

SOPHIE'S CHOICE:

Sophie steps forward. She looks at Marcus, then away.

"I've struggled with trust this week. Marcus, we've had our ups and downs..."

She pauses.

"...but I believe we can work through it. I choose to stay coupled with Marcus."

Marcus breathes a sigh of relief.

---

CHLOE'S CHOICE:

Chloe grins. "This is the easiest choice I've had to make."

She walks straight to you. "I'm recoupling with [Player Name]."

💕 Your couple is safe!
💪 Couple Strength: 68 → 75 (public declaration)

---

EMMA'S CHOICE:

"Liam, you've been nothing but a gentleman. I choose Liam."

---

AISHA'S CHOICE (Final pick):

Aisha looks between Tom and (no one left).

"I'm choosing Tom."

Tom smiles. "Happy to get to know you better."

---

RESULT: All boys are safe. No one is dumped tonight.

Villa dynamics have shifted:
• Your couple is stronger (public commitment)
• Marcus and Sophie are still together (but tension remains)
• Tom is now coupled with Aisha (new dynamic)

📺 Public Perception: +5 (Chloe choosing you looked genuine)
```

**Evening events create:**
- ✅ High drama
- ✅ State changes (couples formed/broken)
- ✅ Eliminations (run can end here)
- ✅ New dynamics for next day

---

## Daily Structure

### Phase Transitions

**Morning → Challenge:**
```javascript
function transitionToChallenge() {
  // 1. Save current state
  savePhaseState()

  // 2. Announce challenge
  const challenge = scheduledEvents.find(e => e.day === currentDay && e.phase === "challenge")

  // 3. Generate challenge content
  const challengeContent = generateChallenge(challenge.type)

  // 4. Execute challenge
  executeChallengePhase(challengeContent)

  // 5. Award prizes, update stats
  applyChallengeResults()
}
```

**Challenge → Afternoon:**
```javascript
function transitionToAfternoon() {
  // 1. Simulate NPC behavior during challenge
  simulateNPCBehavior(60) // 60 min of challenge time

  // 2. Update locations (NPCs moved)
  redistributeIslanders()

  // 3. Set afternoon state
  villaState.currentPhase = "afternoon"
  villaState.timeRemaining = 90

  // 4. Check for bombshell arrival
  if (scheduledEvents.some(e => e.type === "bombshell" && e.day === currentDay && e.phase === "afternoon")) {
    executeBombshellArrival()
  }
}
```

**Afternoon → Evening:**
```javascript
function transitionToEvening() {
  // 1. Simulate NPC behavior
  simulateNPCBehavior(villaState.timeRemaining)

  // 2. Check for scheduled event
  const eveningEvent = scheduledEvents.find(e => e.day === currentDay && e.phase === "evening")

  if (eveningEvent) {
    // Execute event (recoupling, dumping, etc.)
    executeEveningEvent(eveningEvent)
  } else {
    // Free evening (rare)
    executeFreeEvening()
  }
}
```

**Evening → Next Day:**
```javascript
function advanceToNextDay() {
  // 1. Apply end-of-day effects
  applyRelationshipDecay()
  updateAllMoods()
  updatePublicPerception()

  // 2. Check for run end
  if (currentDay >= 18 || playerEliminated) {
    endRun()
    return
  }

  // 3. Increment day
  villaState.currentDay++
  villaState.currentPhase = "morning"
  villaState.timeRemaining = 90

  // 4. Producer AI decides tomorrow's events
  const newEvents = await getProducerDecisions(villaState)
  scheduleEvents(newEvents)

  // 5. Save
  saveToLocalStorage()

  // 6. Show transition
  showDayTransition()
}
```

---

## Week-by-Week Progression

### Week 1: Settling In (Days 1-3)

**Goals:**
- Meet all Islanders
- Form initial couple
- Build foundation relationships
- Learn preferences

**Events:**
- Day 1: Initial coupling (random or strategic choice)
- Day 2: First challenge (icebreaker)
- Day 3: First recoupling (small stakes)

**Difficulty:** Easy
- Low elimination risk
- Time to explore
- Mistakes forgiven

**Player focus:**
- Build base stats through interactions
- Gather information
- Establish couple

---

### Week 2: Drama Emerges (Days 5-9)

**Goals:**
- Deepen primary relationship
- Navigate first bombshell
- Build social alliances
- Manage emerging rivalries

**Events:**
- Day 5: First bombshell arrival
- Day 7: Recoupling (girls/boys choose)
- Day 9: Challenge with meaningful prize

**Difficulty:** Moderate
- Real elimination risk
- Bombshells create pressure
- Drama intensifies

**Player focus:**
- Defend couple from bombshell
- OR explore new connection
- Build friendships (safety net)
- Manage reputation

---

### Week 3: Peak Drama (Days 11-15)

**Goals:**
- Solidify couple OR make big switch
- Navigate maximum chaos
- Survive eliminations
- Manage multiple competing interests

**Events:**
- Day 11: Second bombshell
- Day 12: Casa Amor (ultimate test)
- Day 14: Public vote (eliminations)
- Day 15: Explosive recoupling

**Difficulty:** Hard
- High elimination risk
- Casa Amor temptations
- Public perception critical
- Complex social dynamics

**Player focus:**
- Major strategic decisions
- Trust vs. temptation
- Social positioning
- Damage control

---

### Week 4: Endgame (Days 16-18)

**Goals:**
- Final couple commitment
- Maximize public perception
- Win final vote
- Create legacy

**Events:**
- Day 16: Final dates
- Day 17: Declarations
- Day 18: Final vote and winner announcement

**Difficulty:** Moderate (but high stakes)
- No more eliminations (final 4 couples)
- Pure competition for votes
- Public perception everything
- Relationship quality matters

**Player focus:**
- Prove genuine connection
- Final reassurances
- Public displays of affection
- Winning moments

---

## The Strategic Layer

### Competing Priorities

Every day, player must balance:

**1. Stay Coupled (Survival)**
- Maintain Couple Strength ≥50
- Prevent partner from recoupling away
- Defend against bombshells

**2. Build Friendships (Safety Net)**
- Friends vote to save you
- Friends share gossip
- Friends provide support

**3. Explore New Connections (Opportunity)**
- High chemistry with bombshells
- Better long-term match?
- Risky but potentially rewarding

**4. Manage Reputation (Public Vote)**
- Loyal players win audience favor
- Game-players lose favor
- Drama is double-edged (entertaining vs. toxic)

**5. Prepare for Challenges (Advantages)**
- Build relevant stats
- Win prizes (dates, immunity)
- Public perception boost

**6. Gather Intelligence (Information)**
- Know who's planning what
- Discover threats early
- Make informed decisions

**Time forces tradeoffs:**
- Can't maximize everything
- Must choose priorities
- Different playstyles emerge

---

### Playstyle Archetypes

**The Loyal Partner:**
- Focuses on one person
- High trust, high couple strength
- Wins public perception
- Vulnerable to better match entering
- Strategy: Deep over wide

**The Game-Player:**
- Keeps options open
- High chemistry with multiple people
- Strategic recoupling
- Low public perception
- Strategy: Wide over deep

**The Social Butterfly:**
- Builds friendships first
- Romance secondary
- High safety in votes
- Might not win (no strong couple)
- Strategy: Safety over glory

**The Chaos Agent:**
- Creates maximum drama
- Weaponizes gossip
- High animosity
- Entertaining to audience
- Strategy: Drama over relationships

**All are valid.** Game supports multiple approaches.

---

## Escalation Curve

### Drama Intensity Over Time

```
Drama Level

100 |                                    ╱╲
    |                                   ╱  ╲
 75 |                       ╱╲         ╱    ╲
    |                      ╱  ╲       ╱      ╲
 50 |            ╱╲       ╱    ╲     ╱        ╲
    |           ╱  ╲     ╱      ╲   ╱          ╲
 25 |     ╱╲   ╱    ╲   ╱        ╲ ╱            ╲
    |    ╱  ╲ ╱      ╲ ╱          ╲              ╲
  0 |___╱____╲________╲____________╲______________╲___
     1  3  5  7  9 11 12    14     16        18
    Days

Key moments:
Day 5: First bombshell
Day 7: First major recoupling
Day 9: Second bombshell
Day 12: Casa Amor (peak drama)
Day 14: Public vote
Day 16-18: Endgame (lower drama, higher stakes)
```

**Pacing strategy:**
- Start calm (learning phase)
- Ramp up gradually (bombshells, recouplings)
- Peak at Casa Amor (maximum chaos)
- Cool down for finale (emotional payoff)

---

## Example Full Day

### Day 7: Recoupling Day

**Context:**
- Player coupled with Chloe (Couple Strength: 68)
- Bombshell Aisha entered Day 5
- Marcus and Sophie are fighting
- Tonight: Girls choose (recoupling)

---

**MORNING PHASE (90 min available)**

```
🌅 DAY 7 - MORNING

You wake up in the bedroom. Tonight is recoupling night (girls choose).

Recent events:
• Aisha (bombshell) has been grafting on Marcus
• Sophie confronted Marcus about it yesterday
• Chloe seems confident in your couple

Time: 90 minutes

VILLA MAP:
🏊 Pool: Aisha, Marcus, Tom
💪 Gym: Sophie (working out alone)
🍳 Kitchen: Chloe, Emma, Liam

Where do you go?
```

**Player choice:** Go to kitchen (talk to Chloe)

```
You head to the kitchen.

Chloe is making coffee with Emma. They're chatting and laughing.

Talk to:
→ Chloe (your partner)
→ Emma (friend)
→ Both (group chat)
```

**Player choice:** Talk to Chloe privately

```
You pull Chloe aside.

"Morning, you." She smiles and kisses your cheek.

Talk to Chloe:

Friendly: 💬
→ Ask how she slept

Flirty: 💕
→ "You look beautiful this morning"

Deep: 🗨️
→ "How are you feeling about tonight?"

Reassure: 🛡️
→ "You know you're the only one I'm interested in, right?"
```

**Player choice:** Reassure about tonight

```
You take her hand. "You know you're the only one I'm interested in, right? I'm not worried about tonight."

Chloe's eyes soften. "I know. I'm not worried either. You've been amazing."

She squeezes your hand. "I'm picking you tonight, obviously. No question."

✨ Loyalty check: SUCCESS
💕 Trust +7, Affection +4
💪 Couple Strength: 68 → 75

Chloe seems very secure.

⏰ 20 minutes passed (70 min remaining)

Continue talking to Chloe?
→ Keep talking
→ End conversation
```

**Player choice:** End conversation

```
You head back out to the villa.

Time remaining: 70 minutes

VILLA MAP:
🏊 Pool: Aisha, Marcus, Tom (Aisha and Marcus laughing together)
💪 Gym: Sophie (still alone)
🍳 Kitchen: Emma, Liam (chatting)

⚠️ You notice: Aisha and Marcus seem very close.

Where do you go?
→ Pool (observe Aisha/Marcus, talk to them)
→ Gym (check on Sophie, opportunity?)
→ Kitchen (gather gossip from Liam)
```

**Player choice:** Gym (check on Sophie)

```
You find Sophie in the gym, running on the treadmill.

She slows down when she sees you. She looks upset.

Talk to Sophie:

Friendly: 💬
→ "You okay?"

Supportive: 🤗
→ "I saw you're alone. Want to talk?"

Risky Flirty: 💕
→ "Mind if I join you?" (Risky - she's coupled)
```

**Player choice:** Supportive

```
You approach gently. "I saw you're alone. Want to talk?"

Sophie stops the treadmill and grabs a towel. "Is it that obvious I'm upset?"

She sighs. "Marcus has been all over Aisha. I don't know what to do tonight."

✨ Emotional Intelligence check: SUCCESS
💬 Friendship +5, Familiarity +4

Sophie trusts you.

What do you say?
→ "You deserve better than someone who doesn't appreciate you"
→ "Maybe give him one more chance?"
→ "What does your gut say?"
```

**Player choice:** "What does your gut say?"

```
Sophie thinks for a moment. "Honestly? I think I should recouple away from him."

She looks at you. "Tom has been really sweet. I might pick him."

📚 New Information:
Sophie is planning to recouple with Tom (not Marcus)

This means:
• Marcus might be available (or picked by Aisha)
• Drama will happen tonight

💬 Trust +3 (Sophie shared her plan with you)

⏰ 25 minutes passed (45 min remaining)

Continue talking?
→ Keep talking
→ End conversation
```

**Player choice:** End conversation

```
Time remaining: 45 minutes

You could:
→ Talk to Marcus (warning? gather info?)
→ Talk to Liam (gossip about villa dynamics)
→ Talk to Aisha (assess her strategy)
→ Relax until challenge (save energy)
```

**Player choice:** Talk to Liam (gossip)

```
[20 min conversation with Liam]

Liam tells you:
• "Aisha is 100% picking Marcus tonight"
• "Marcus doesn't realize Sophie is done with him"
• "Tonight is going to be explosive"

⏰ Morning phase complete
```

---

**CHALLENGE PHASE (60 min)**

```
🔔 CHALLENGE TIME!

Today's Challenge: "Snog, Marry, Pie"

Each Islander picks three people:
- SNOG: Who they'd kiss
- MARRY: Who they'd couple with long-term
- PIE: Who they'd pie in the face (least compatible)

This reveals true feelings and creates drama.

Your turn:
SNOG: ???
MARRY: ???
PIE: ???
```

**[Challenge plays out, drama ensues]**

```
Results:
• You picked: Snog-Chloe, Marry-Chloe, Pie-Marcus
• Aisha picked: Snog-Marcus, Marry-Marcus, Pie-Tom

Marcus looks pleased. Sophie looks hurt.

Challenge complete.
```

---

**AFTERNOON PHASE (90 min)**

```
🌤️ AFTERNOON - Day 7

The tension is thick. Recoupling is in 90 minutes.

Aisha is with Marcus at the pool.
Sophie is in her room, getting ready.
Chloe is confident and relaxed.

Time: 90 minutes

This is your last chance before tonight.

What do you do?
→ Spend time with Chloe (reinforce couple)
→ Check on Sophie (support friend)
→ Observe Marcus/Aisha (gather intel)
→ Talk strategy with Liam
```

**[Player makes final moves]**

---

**EVENING EVENT: Recoupling**

```
🔥 RECOUPLING CEREMONY

[Dramatic LLM-narrated ceremony as shown earlier]

Results:
• Sophie recoupled with Tom (dumped Marcus!)
• Aisha picked Marcus (he's happy)
• Chloe picked you (strong declaration)
• Emma picked Liam

Marcus was dumped by Sophie but saved by Aisha.

New couples:
• You + Chloe (stronger than ever)
• Marcus + Aisha (new pairing)
• Sophie + Tom (fresh start)
• Liam + Emma (stable)

📺 Public Perception: +8 (genuine couple moment)
💕 Couple Strength: 75 → 82

Villa dynamics have completely shifted.
```

---

**DAY COMPLETE**

```
Day 7 Summary:

💕 Relationships:
• Chloe: 82 (Very Strong)
• Sophie: +10 Friendship (you supported her)
• Liam: +5 Friendship (gossip buddy)

📚 Knowledge Gained:
• Sophie's recoupling plan (correctly predicted)
• Aisha's strategy (targeting Marcus)
• Villa dynamics (major shift)

⭐ Achievements:
• "Solid Couple" - Survived first major recoupling
• "Friend Indeed" - Supported Sophie through crisis

💾 Progress saved.
```

---

## Run Completion

### Ending Conditions

**Winning:**
- Survive to Day 18 (final)
- Win final public vote
- Earn maximum Audience Appeal

**Losing (early):**
- Dumped before Day 10
- Low Audience Appeal

**Losing (late):**
- Dumped Days 10-17
- Moderate Audience Appeal

**Alternative endings:**
- Fan Favorite (high public perception, didn't win couple vote)
- Friendship Ending (left with strong friendships)
- Chaos Ending (maximum drama generated)

### Final Day (Day 18)

```
🏆 FINAL DAY

The final four couples:
1. You + Chloe
2. Marcus + Aisha
3. Liam + Emma
4. Sophie + Tom

Each couple makes a final declaration.

Then the public votes.

Your declaration:
[LLM generates based on your relationship history]

You take Chloe's hand.

"These past few weeks have been incredible. I came here not knowing what to expect, but I found something real. Chloe, you've been amazing - funny, supportive, genuine. Whatever happens tonight, I'm grateful for every moment."

Chloe tears up. The audience cheers.

Public Vote Results:
1st Place: You and Chloe (42% of vote)
2nd Place: Liam and Emma (31%)
3rd Place: Sophie and Tom (17%)
4th Place: Marcus and Aisha (10%)

🏆 YOU WON LOVE ISLAND! 🏆

Rewards:
• 500 Audience Appeal (maximum)
• "Champions" achievement
• Unlock: "Heartthrob" archetype
• Unlock: "Villa Legend" perk

Your story will be remembered.

Play again?
```

---

**Version:** 1.0
**Status:** ✅ Complete
**Documentation:** All 8 core system files complete!
