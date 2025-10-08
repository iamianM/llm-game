# LLM Architecture

*How AI and code work together to create dynamic gameplay*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Core Philosophy](#core-philosophy)
- [Algorithm vs LLM Boundaries](#algorithm-vs-llm-boundaries)
- [The Multi-AI System](#the-multi-ai-system)
- [Personality System](#personality-system)
- [Prompt Engineering](#prompt-engineering)
- [Cost Analysis](#cost-analysis)
- [Performance Requirements](#performance-requirements)
- [Error Handling](#error-handling)

---

## Core Philosophy

### Algorithm First, LLM Second

**The Principle:**

The LLM is the **narrative flavor**, NOT the **game engine**.

```
WRONG APPROACH:
User action → Ask LLM "what happens?" → Display result
Problems: Slow, inconsistent, unpredictable, expensive

RIGHT APPROACH:
User action → Code calculates outcome → Ask LLM to narrate → Display result
Benefits: Fast, consistent, strategic, affordable
```

**Why this matters:**

1. **LLMs are bad at math**
   - Can't reliably track numbers
   - Inconsistent with probability
   - Will "cheat" for narrative reasons

2. **LLMs are expensive**
   - $0.01-0.10 per call
   - 40-60 calls per run adds up
   - Code is free

3. **LLMs are slow**
   - 1-3 second response time
   - Can't afford multiple calls per action
   - Code is instant

4. **LLMs are unpredictable**
   - Same prompt = different results
   - Hard to balance
   - Players can't strategize

**What LLMs ARE good at:**
- Writing character-specific dialogue
- Expressing personality consistently
- Creating narrative flavor
- Generating unique content
- Responding to context

---

## Algorithm vs LLM Boundaries

### Code Handles (Deterministic Systems)

**✅ Interaction Success Calculation**
```javascript
const success = calculateSuccess(action, target, player, context)
// Code does all math, returns true/false
```

**✅ Relationship Value Changes**
```javascript
applyRelationshipChange(action, target, success)
// Code updates all numbers
```

**✅ NPC Location/Activity Simulation**
```javascript
simulateNPCBehavior(timeElapsed)
// Code decides where NPCs go, what they do
```

**✅ Gossip Availability**
```javascript
const availableGossip = getAvailableGossip(speaker, player)
// Code determines what gossip can be shared
```

**✅ Event Triggering**
```javascript
if (shouldTriggerRecoupling(villaState)) {
  scheduleEvent("recoupling", day, phase)
}
// Code decides when events happen
```

**✅ Compatibility Calculation**
```javascript
const compatibility = calculateCompatibility(player, target)
// Code uses personality numbers to calculate chemistry
```

### LLM Handles (Narrative Systems)

**✅ Islander Personality Generation**
```javascript
const islander = await generateIslander(archetype)
// LLM creates name, backstory, personality, appearance
```

**✅ Dialogue Writing**
```javascript
const dialogue = await generateDialogue(character, situation, outcome)
// LLM writes what the character says
```

**✅ Gossip Delivery**
```javascript
const gossipText = await generateGossip(speaker, fact, context)
// LLM writes how gossip is revealed
```

**✅ Event Narration**
```javascript
const narration = await narrateEvent(eventType, participants, context)
// LLM describes ceremonies, arrivals, etc.
```

**✅ Contextual Options**
```javascript
const specialOptions = await generateContextualOptions(situation)
// LLM suggests 1-2 situational dialogue choices
```

### The Handoff Point

**Example: Player flirts with Chloe**

```javascript
// 1. PLAYER SELECTS ACTION (UI)
const action = { type: "flirt", target: "chloe" }

// 2. CODE CALCULATES OUTCOME (instant)
const successChance = calculateInteractionSuccess(action, chloe, player, context)
// Returns: 72%

const roll = random(1, 100)
const success = roll <= successChance // true or false

// 3. CODE APPLIES MECHANICAL CHANGES (instant)
if (success) {
  chloe.relationships.player.chemistry += 5
  chloe.relationships.player.affection += 3

  if (playerIsCoupledWithSomeoneElse) {
    checkIfCaught() // might trigger drama
  }
}

// 4. LLM GENERATES NARRATIVE (1-2 seconds)
const prompt = buildDialoguePrompt({
  character: chloe,
  situation: "player_flirted",
  outcome: success ? "positive" : "rejected",
  context: getCurrentContext()
})

const dialogue = await callLLM(prompt)
// Returns: "Chloe blushes and bites her lip. \"You're trouble, you know that?\""

// 5. DISPLAY TO PLAYER
showResult({
  dialogue: dialogue,
  mechanicalChanges: { chemistry: +5, affection: +3 },
  success: true
})
```

**The LLM only writes the dialogue. Everything else is code.**

---

## The Multi-AI System

We don't use one LLM for everything. We use **specialized AI calls** for different tasks.

### 1. Producer AI

**Job:** Decide what dramatic events happen

**When it runs:** Once per day (between phases)

**Input:**
```javascript
{
  villaState: {
    currentDay: 5,
    couples: [...],
    averageCoupleStrength: 62,
    dramaLevel: 45,
    daysSinceLastBombshell: 3
  },
  recentEvents: [
    "Marcus and Sophie argued",
    "Player kissed Chloe on terrace"
  ]
}
```

**Prompt:**
```
You are the Love Island producer. Based on villa state, decide what event should happen tomorrow.

Current situation:
- Day 5 of 18
- Average couple strength: 62 (stable)
- Drama level: 45 (moderate)
- Last bombshell: 3 days ago

Options:
1. Send in a new bombshell (shake things up)
2. Schedule a recoupling (force decisions)
3. Create a challenge (test couples)
4. Send couples on dates (build connections)
5. Create a dramatic twist (Casa Amor, lie detector, etc.)

Respond with JSON:
{
  "event": "bombshell_arrival",
  "reasoning": "Couples are too stable, need disruption",
  "timing": "afternoon",
  "bombshellGender": "female"
}
```

**Output:**
```json
{
  "event": "bombshell_arrival",
  "reasoning": "Average couple strength too high. Player and Chloe need testing.",
  "timing": "afternoon",
  "bombshellGender": "female",
  "targetCouple": "player_chloe"
}
```

**Cost:** ~500 tokens (~$0.0015 per call)

**Frequency:** Once per day = ~20 calls per run = ~$0.03 per run

---

### 2. Islander Generator AI

**Job:** Create complete Islander personalities

**When it runs:** When new Islander enters villa (start + bombshells)

**Input:**
```javascript
{
  archetype: "The Charmer", // or randomly selected
  gender: "female",
  existingIslanders: [...], // to avoid duplicates
  targetPlayer: true // is this a bombshell targeting player?
}
```

**Prompt:**
```
Generate a Love Island contestant with the following requirements:

Archetype: The Charmer
Gender: Female
Age range: 22-28

Create a psychologically realistic character using the Big 5 personality model (OCEAN).

Output JSON with this exact schema:
{
  "name": "string",
  "age": number,
  "occupation": "string",
  "hometown": "string",

  "appearance": {
    "description": "string (2-3 sentences)",
    "hairColor": "string",
    "eyeColor": "string",
    "height": "string",
    "build": "string",
    "style": "string"
  },

  "personality": {
    "openness": number (1-10),
    "conscientiousness": number (1-10),
    "extraversion": number (1-10),
    "agreeableness": number (1-10),
    "neuroticism": number (1-10)
  },

  "attachmentStyle": "secure" | "anxious" | "avoidant" | "fearful",

  "preferences": {
    "physicalType": "string",
    "personalityType": "string",
    "values": ["string", "string", "string"],
    "dealbreakers": ["string", "string"]
  },

  "backstory": "string (3-4 sentences)",
  "secret": "string (hidden insecurity or past)",
  "chatUpLine": "string (what they'd say when entering)",
  "strategy": "string (why they're on Love Island)"
}

Ensure:
- Big 5 scores are varied (don't make everyone 7-8)
- Preferences should be specific but not impossible to match
- Secret should be something that could create drama if revealed
- Personality should match archetype but feel realistic
```

**Output:**
```json
{
  "name": "Aisha",
  "age": 25,
  "occupation": "Fashion Buyer",
  "hometown": "Manchester",

  "appearance": {
    "description": "Stunning with an effortless elegance. Designer wardrobe, always impeccably styled. Knows she's attractive and carries herself with confidence.",
    "hairColor": "Dark brown, long and wavy",
    "eyeColor": "Hazel",
    "height": "5'7\"",
    "build": "Slim, athletic",
    "style": "High fashion, trendy"
  },

  "personality": {
    "openness": 8,
    "conscientiousness": 7,
    "extraversion": 9,
    "agreeableness": 5,
    "neuroticism": 6
  },

  "attachmentStyle": "avoidant",

  "preferences": {
    "physicalType": "Tall, well-groomed, stylish",
    "personalityType": "Confident, ambitious, can keep up with her",
    "values": ["ambition", "style", "adventure"],
    "dealbreakers": ["insecurity", "clinginess", "lack of ambition"]
  },

  "backstory": "Grew up in a competitive family of high achievers. Worked her way up in the fashion industry through sheer determination. Used to getting what she wants. Past relationships failed because she struggles with vulnerability.",

  "secret": "Terrified of being vulnerable. Uses confidence as armor. Deep down, fears she's unlovable.",

  "chatUpLine": "Hope you're all ready for some real competition. May the best woman win.",

  "strategy": "Play the game strategically. Pursue the most attractive/popular guy. Build alliances with other girls but don't get too close."
}
```

**Cost:** ~1500 tokens (~$0.005 per Islander)

**Frequency:** ~10 Islanders per run = ~$0.05 per run

---

### 3. Dialogue AI

**Job:** Generate conversation exchanges

**When it runs:** Every player interaction (~40-60 times per run)

**This is the MOST FREQUENT and MOST EXPENSIVE call.**

**Input:**
```javascript
{
  character: islanderObject, // full personality
  situation: "player_flirted",
  outcome: "success",
  context: {
    location: "pool",
    timeOfDay: "morning",
    mood: "flirty",
    relationship: {
      affection: 65,
      chemistry: 58,
      trust: 72
    },
    recentHistory: [
      "kissed on terrace 2 nights ago",
      "player has been loyal and attentive",
      "new bombshell Aisha arrived yesterday"
    ],
    currentlyPresent: ["Marcus", "Sophie", "Liam"]
  }
}
```

**Prompt:**
```
You are Chloe, a 24-year-old marketing manager on Love Island.

PERSONALITY:
- Openness: 7/10 (creative, open-minded)
- Conscientiousness: 6/10 (organized but spontaneous)
- Extraversion: 9/10 (very social and outgoing)
- Agreeableness: 8/10 (warm, compassionate)
- Neuroticism: 4/10 (confident, emotionally stable)

ATTACHMENT STYLE: Secure (comfortable with intimacy and independence)

CURRENT RELATIONSHIP WITH PLAYER:
- Affection: 65 (strong feelings developing)
- Chemistry: 58 (attracted)
- Trust: 72 (trusts them)
- Coupled together for 3 days

RECENT CONTEXT:
- You kissed the player on the terrace 2 nights ago
- Player has been loyal and attentive to you
- New bombshell Aisha arrived yesterday (you're slightly worried)
- Currently at the pool with others around

SITUATION:
The player just flirted with you poolside.

OUTCOME: SUCCESS (it was charming and well-received)

Generate a brief response (2-3 lines) showing Chloe reacting positively to the flirt.

Requirements:
- Show her personality (playful, warm, extraverted)
- Include subtle hint of worry about Aisha
- Keep it natural and in-character
- No narration tags (no *smiles* or [laughs]), just dialogue and brief description

Format:
Just write the exchange naturally. Example:
Chloe blushes and playfully pushes your shoulder. "You're such a charmer, you know that?"
```

**Output:**
```
Chloe blushes and bites her lip. "You're going to give me a big head with all these compliments."

She glances toward Aisha across the pool, then back to you. "I'm glad we're solid though. You're not getting your head turned, right?"
```

**Cost:** ~800 tokens (~$0.0024 per conversation)

**Frequency:** ~50 conversations per run = ~$0.12 per run

**Optimization strategies:**
- Cache character personality (don't resend each time)
- Use cheaper model (Claude 3.5 Sonnet, not GPT-4)
- Limit conversation history to last 3 interactions
- Compress context to essential info only

---

### 4. Event Narrator AI

**Job:** Describe ceremonies, arrivals, challenges

**When it runs:** Special events (5-8 times per run)

**Input:**
```javascript
{
  eventType: "recoupling_ceremony",
  participants: [...],
  couplingChoices: [
    { chooser: "Aisha", chosen: "Marcus", stolen: true, previousPartner: "Sophie" }
  ],
  context: {
    day: 7,
    tension: "high",
    shockedIslanders: ["Sophie", "Liam", "Player"]
  }
}
```

**Prompt:**
```
Narrate a Love Island recoupling ceremony in dramatic fashion.

EVENT: Aisha (bombshell) chooses to couple with Marcus

CONTEXT:
- Marcus was previously coupled with Sophie
- This is a shock - Marcus and Sophie seemed stable
- Others watching: Player, Chloe, Liam, Emma

Write 3-4 lines of dramatic narration capturing the tension and reactions.
Style: Reality TV narrator voice (dramatic, punchy)

Don't include dialogue from characters, just set the scene.
```

**Output:**
```
"Aisha, you have chosen to couple up with... Marcus."

Sophie's face falls. Marcus looks shocked but doesn't protest. The tension is unbearable.

Sophie stands alone, dumped from the island. The other Islanders exchange uncomfortable glances.
```

**Cost:** ~600 tokens (~$0.002 per event)

**Frequency:** ~6 events per run = ~$0.012 per run

---

### 5. NPC Behavior Simulator

**Job:** Decide what NPCs do autonomously

**When it runs:** Once per phase transition (4x per day = ~80 times per run)

**This is OPTIONAL - can be purely algorithmic. Using LLM adds personality but costs more.**

**Algorithmic approach (recommended for POC):**
```javascript
function simulateNPCBehavior(npc, timeElapsed) {
  // Code-driven decisions based on personality

  // Location change chance (based on extraversion)
  if (random(100) < npc.personality.extraversion * 5) {
    npc.location = chooseNewLocation(npc) // algorithmic
  }

  // Social interaction chance
  if (random(100) < npc.personality.extraversion * 6) {
    const target = chooseSocialTarget(npc) // algorithmic: highest chemistry, or coupled partner, or friend
    simulateNPCtoNPCInteraction(npc, target) // uses same success formulas as player
  }

  // Mood update (based on recent events)
  updateMood(npc) // algorithmic
}
```

**LLM-enhanced approach (future enhancement):**
```javascript
// Ask LLM for decision, constrain to valid options
const decision = await getLLMDecision({
  character: npc,
  currentState: npc.currentState,
  availableActions: getAvailableActions(npc),
  recentEvents: npc.recentEvents
})

// LLM suggests: "Aisha should graft on Marcus"
// Code executes the interaction using normal formulas
```

**Recommendation:** Start with algorithmic, add LLM enhancement post-POC if needed

---

## Personality System

### Big 5 OCEAN Model

**Why Big 5:**
- ✅ Scientifically validated (most robust personality model)
- ✅ Continuous scores (not binary like Myers-Briggs)
- ✅ Predicts behavior well
- ✅ Easy to explain to LLM

**The Five Dimensions:**

**Openness (0-10)**
- Low: Traditional, practical, routine-oriented
- High: Creative, curious, adventurous

**Affects:**
- Deep conversation success
- Enjoyment of new experiences
- Compatibility with similar/different personalities

**Conscientiousness (0-10)**
- Low: Spontaneous, flexible, messy
- High: Organized, disciplined, reliable

**Affects:**
- Keep promises behavior
- Strategic planning ability
- Time management

**Extraversion (0-10)**
- Low: Reserved, quiet, introspective
- High: Outgoing, social, energetic

**Affects:**
- Social interaction frequency
- Group vs. one-on-one preference
- Energy from social events

**Agreeableness (0-10)**
- Low: Competitive, skeptical, assertive
- High: Compassionate, cooperative, warm

**Affects:**
- Conflict behavior
- Gossip willingness
- Relationship building ease

**Neuroticism (0-10)**
- Low: Calm, confident, stable
- High: Anxious, sensitive, emotional

**Affects:**
- Trust building difficulty
- Response to stress
- Jealousy tendency

### Attachment Styles

Layered on top of Big 5 for relationship behavior:

**Secure (40% of Islanders)**
- Comfortable with intimacy and independence
- Trusts easily, communicates well
- Balanced expectations

**Behaviors:**
- Handles conflicts maturely
- Not overly jealous
- Appreciates reassurance but doesn't need constant validation

**Anxious (30% of Islanders)**
- Craves closeness, fears abandonment
- Needs frequent reassurance
- Worries about partner's feelings

**Behaviors:**
- Gets jealous easily
- Needs more "reassure" interactions
- Trust drops faster when neglected
- Responds very positively to attention

**Avoidant (20% of Islanders)**
- Values independence, uncomfortable with too much intimacy
- Pulls away when things get serious
- Struggles with vulnerability

**Behaviors:**
- Resists "deep" conversations early
- Chemistry builds easily, trust builds slowly
- May sabotage relationships when they get too close
- Needs space

**Fearful (10% of Islanders)**
- Wants closeness but fears getting hurt
- Push-pull behavior
- Trust issues

**Behaviors:**
- Inconsistent responses
- High neuroticism overlap
- Difficult to build stable relationship with
- Dramatic potential

### Type on Paper (Preferences)

Each Islander has discoverable preferences:

```javascript
preferences: {
  // Physical preferences
  physicalType: "Tall, athletic, dark features",

  // Personality preferences
  personalityType: "Funny, confident, ambitious",

  // Core values
  values: ["loyalty", "adventure", "honesty"],

  // Absolute dealbreakers
  dealbreakers: ["arrogance", "laziness", "drama"]
}
```

**How preferences work:**

```javascript
function checkPreferenceMatch(player, target) {
  let matchBonus = 0

  // Physical match (harder to change)
  if (playerMatchesPhysicalType(player, target.preferences.physicalType)) {
    matchBonus += 10 // significant bonus
  }

  // Personality match (based on stats)
  if (playerHasHighStat(player, target.preferences.personalityType)) {
    matchBonus += 8
  }

  // Values alignment
  const sharedValues = countSharedValues(player.values, target.preferences.values)
  matchBonus += sharedValues * 3 // 0-9 bonus

  // Dealbreakers (PENALTY)
  if (playerHasDealbreaker(player, target.preferences.dealbreakers)) {
    matchBonus -= 15 // major penalty
  }

  return matchBonus
}
```

**Discovery mechanic:**
- Preferences are hidden at start
- Revealed through conversations (increase familiarity)
- At familiarity 40: Learn physical type
- At familiarity 60: Learn personality type
- At familiarity 80: Learn values and dealbreakers

**Strategic depth:** Once you know someone's type, you can tailor your approach

---

## Prompt Engineering

### Best Practices

**1. Always include personality in prompt**
```
GOOD:
"You are Chloe. Extraversion 9/10, Agreeableness 8/10..."

BAD:
"You are Chloe. She's friendly and outgoing."
```

**2. Specify outcome before asking for narration**
```
GOOD:
"OUTCOME: SUCCESS. Generate positive response."

BAD:
"The player flirted. How does she respond?"
```

**3. Constrain output format**
```
GOOD:
"Generate 2-3 lines. No asterisks or brackets. Just natural dialogue."

BAD:
"Write a response."
```

**4. Include recent context, not full history**
```
GOOD:
"Recent context: Kissed 2 days ago, player been loyal, new bombshell arrived"

BAD:
[Sends entire conversation history - 2000 tokens]
```

**5. Use structured output when possible**
```
GOOD:
"Respond with JSON: { dialogue: string, emotion: string }"

BAD:
[Free text that needs parsing]
```

### Prompt Templates

**Dialogue Generation Template:**
```
You are {CHARACTER_NAME}, a {AGE}-year-old {OCCUPATION} on Love Island.

PERSONALITY (Big 5):
- Openness: {OPENNESS}/10
- Conscientiousness: {CONSCIENTIOUSNESS}/10
- Extraversion: {EXTRAVERSION}/10
- Agreeableness: {AGREEABLENESS}/10
- Neuroticism: {NEUROTICISM}/10

ATTACHMENT STYLE: {ATTACHMENT_STYLE}
{ATTACHMENT_DESCRIPTION}

CURRENT RELATIONSHIP WITH PLAYER:
- Affection: {AFFECTION}
- Chemistry: {CHEMISTRY}
- Trust: {TRUST}
- {COUPLED_STATUS}

RECENT CONTEXT:
{RECENT_EVENTS}

CURRENT SITUATION:
Location: {LOCATION}
Time: {TIME_OF_DAY}
Mood: {MOOD}
Others present: {OTHERS}

PLAYER ACTION: {ACTION_DESCRIPTION}
OUTCOME: {SUCCESS/FAILURE}

Generate a brief response (2-3 lines) showing {CHARACTER_NAME} reacting to this situation.

Requirements:
- Show personality through dialogue
- {SPECIFIC_REQUIREMENTS}
- Natural, in-character
- No narration tags
```

**Islander Generation Template:**
```
Generate a Love Island contestant.

REQUIREMENTS:
- Archetype: {ARCHETYPE}
- Gender: {GENDER}
- Age range: 22-28

Use the Big 5 personality model (OCEAN). Create a psychologically realistic character.

Output JSON with this schema:
{SCHEMA}

Ensure:
- Big 5 scores are varied (avoid clustering at 7-8)
- Preferences are specific but achievable
- Secret creates potential drama
- Personality matches archetype
- Unique from existing Islanders: {EXISTING_NAMES}
```

---

## Cost Analysis

### Per-Run Breakdown

**Islander Generation:**
- 10 Islanders × $0.005 = **$0.05**

**Dialogue Generation:**
- 50 interactions × $0.0024 = **$0.12**

**Producer AI:**
- 20 decisions × $0.0015 = **$0.03**

**Event Narration:**
- 6 events × $0.002 = **$0.012**

**Total per run: ~$0.21**

### Model Selection

**Claude 3.5 Sonnet (recommended):**
- Input: $0.003 / 1K tokens
- Output: $0.015 / 1K tokens
- Fast, cheap, good quality

**GPT-4 Turbo:**
- Input: $0.01 / 1K tokens
- Output: $0.03 / 1K tokens
- 3x more expensive

**GPT-4o-mini:**
- Input: $0.00015 / 1K tokens
- Output: $0.0006 / 1K tokens
- 10x cheaper but lower quality

**Recommended approach:**
- Use Claude 3.5 Sonnet for POC
- If costs too high, try GPT-4o-mini for simple tasks
- Reserve expensive models for complex generation

### Optimization Strategies

**1. Prompt caching**
- Vercel AI SDK supports caching
- Cache Islander personalities (reused every conversation)
- Save ~30% on dialogue calls

**2. Batch operations**
- Generate all Islanders at run start (one call)
- Cheaper than individual calls

**3. Reduce context size**
- Last 3 interactions, not full history
- Compress events to key facts
- Save ~40% on token costs

**4. Strategic LLM use**
- Use LLM for unique content (dialogue)
- Use code for repetitive content (stats, locations)

**Target: <$0.30 per run**

---

## Performance Requirements

### Response Time Targets

**Dialogue generation:** <2 seconds
- Player expects immediate response
- Anything longer feels broken

**Islander generation:** <5 seconds
- Happens at run start, player expects brief load
- Can show loading screen

**Event narration:** <3 seconds
- Ceremonial, player expects drama buildup
- Slight delay acceptable

### Optimization Techniques

**1. Streaming responses**
```javascript
// Use Vercel AI SDK streaming
const { textStream } = await streamText({
  model: claude,
  prompt: dialoguePrompt
})

// Display text as it generates (typewriter effect)
for await (const chunk of textStream) {
  displayText(chunk)
}
```

**2. Parallel generation**
```javascript
// Generate all starting Islanders in parallel
const islanders = await Promise.all(
  archetypes.map(archetype => generateIslander(archetype))
)
// 5 seconds total instead of 5 × 5 = 25 seconds
```

**3. Pregeneration**
```javascript
// Generate next day's events during player actions
// Player won't notice background generation
preloadNextDayEvents()
```

---

## Error Handling

### LLM Failures

**Timeout:**
```javascript
try {
  const dialogue = await generateDialogue(params, { timeout: 5000 })
} catch (timeoutError) {
  // Fallback to generic response
  return getGenericResponse(character, situation)
}
```

**Malformed output:**
```javascript
const result = await generateIslander(archetype)

if (!validateIslanderSchema(result)) {
  // Retry once
  const retry = await generateIslander(archetype)

  if (!validateIslanderSchema(retry)) {
    // Use template Islander as fallback
    return getTemplateIslander(archetype)
  }
}
```

**Inappropriate content:**
```javascript
const dialogue = await generateDialogue(params)

if (containsInappropriateContent(dialogue)) {
  // Regenerate with stronger constraints
  return await generateDialogue({
    ...params,
    constraints: "Keep PG-13, no explicit content"
  })
}
```

### Fallback Systems

**Generic dialogue templates:**
```javascript
const fallbacks = {
  flirt_success: [
    "{name} smiles warmly. \"That's sweet of you to say.\"",
    "{name} laughs. \"You're a charmer, aren't you?\""
  ],
  flirt_failure: [
    "{name} looks away awkwardly. \"Uh, thanks I guess.\"",
    "{name} changes the subject quickly."
  ]
}

function getFallbackDialogue(character, situation) {
  const template = random(fallbacks[situation])
  return template.replace("{name}", character.name)
}
```

**Template Islanders:**
```javascript
// Pre-written Islanders as fallback
const templateIslanders = {
  "The Charmer": { /* full Islander object */ },
  "The Sweetheart": { /* full Islander object */ },
  // ...
}
```

---

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 04-State-Management.md for data structures that power this system
