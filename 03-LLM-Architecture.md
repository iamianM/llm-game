# LLM Architecture

*How AI and code work together to create dynamic gameplay*

**Document Status:** ✅ Complete
**Last Updated:** 2026-05-11

**Implementation Update (2026-05-11):** The conceptual boundary in this file is still canon: code owns mechanics, the LLM owns narrative flavor. The concrete implementation stack has changed from TypeScript/Vercel AI SDK examples to a Python engine with Pydantic contracts, seeded RNG, FastAPI, and one v0 Narrator agent. Treat older TypeScript-style snippets as design pseudocode unless they have been converted to Python.

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
```python
success = calculate_success(action, target, player, context)
# Code does all math, returns true/false.
```

**✅ Relationship Value Changes**
```python
apply_relationship_change(state, action, target, success)
# Code updates all numbers.
```

**✅ NPC Location/Activity Simulation**
```python
simulate_npc_behavior(state, elapsed_phases, rng)
# Code decides where NPCs go and what they do.
```

**✅ Gossip Availability**
```python
available_gossip = get_available_gossip(speaker, player)
# Code determines what gossip can be shared.
```

**✅ Event Triggering**
```python
if should_trigger_recoupling(villa_state):
    schedule_event(state, event_type="recoupling", day=day, phase=phase)
# Code decides when events happen.
```

**✅ Compatibility Calculation**
```python
compatibility = calculate_compatibility(player, target)
# Code uses personality numbers to calculate chemistry.
```

### LLM Handles (Narrative Systems)

**✅ Islander Personality Generation**
```python
islander = await generate_islander(archetype)
# LLM creates name, backstory, personality, and appearance.
```

**✅ Dialogue Writing**
```python
dialogue = await narrate_result(character, situation, mechanical_result)
# LLM writes what the character says after code resolves the outcome.
```

**✅ Gossip Delivery**
```python
gossip_text = await narrate_gossip(speaker, fact, context)
# LLM writes how gossip is revealed.
```

**✅ Event Narration**
```python
narration = await narrate_event(event_type, participants, context)
# LLM describes ceremonies, arrivals, etc.
```

**✅ Contextual Options**
```python
special_options = await generate_contextual_options(situation)
# Future enhancement: LLM suggests 1-2 situational dialogue choices.
```

### The Handoff Point

**Example: Player flirts with Chloe**

```python
# 1. Player selects action in CLI or browser.
action = PlayerAction(kind="flirt", target_id="chloe")

# 2. Code calculates outcome through seeded RNG.
chance = calculate_interaction_success(state, action)
roll = rng.randint(1, 100)
success = roll <= chance

# 3. Code applies mechanical changes and records them.
result = apply_action(state, action, success=success, roll=roll)

# Example result:
# MechanicalResult(
#     action_kind="flirt",
#     target_id="chloe",
#     success=True,
#     relationship_deltas={"chloe": {"chemistry": 5, "affection": 3}},
#     tags=["flirty", "public", "partner_might_notice"],
# )

# 4. Narrator agent writes prose from the resolved result.
narration = await narrate_mechanical_result(result, visible_context)

# 5. CLI or browser displays the narration plus next available actions.
return TurnResult(
    state=state,
    mechanical_result=result,
    narration=narration,
    available_actions=available_actions(state),
)
```

**The LLM only writes the dialogue. Everything else is code.**

---

## The Multi-AI System

Long-term, we do not use one LLM for everything. We use **specialized AI calls** for different tasks.

**POC constraint:** v0 starts with one Narrator agent only. Producer AI, Curator, contextual option generation, and LLM-enhanced NPC behavior are future layers after the deterministic CLI loop is playable and replayable.

### 1. Producer AI

**Job:** Decide what dramatic events happen

**When it runs:** Future layer, likely once per day or at phase boundaries after deterministic scheduling works.

**Input shape:** A compact, code-derived villa summary: day, phase, couple stability, drama level, scheduled constraints, recent events, and valid event candidates.

**Output shape:** A typed event suggestion that code validates against allowed events. The Producer may recommend a bombshell, recoupling, date, challenge, or twist, but Python still schedules the event and applies all mechanics.

**POC status:** Deferred. Initial event selection is deterministic Python.

---

### 2. Islander Generator AI

**Job:** Create complete Islander personalities

**When it runs:** When new Islander enters villa (start + bombshells)

**Input shape:** Archetype id, gender/presentation constraints, existing cast summary, and any production role such as original Islander or bombshell.

**Output shape:** A Pydantic-validated Islander profile: identity, appearance, Big 5 traits, attachment style, preferences, backstory, secret, entrance line, and strategy.

**POC status:** Use deterministic seed characters or tiny content stubs first. LLM generation can be added after state models and replay are stable.

---

### 3. Dialogue AI

**Job:** Generate conversation exchanges

**When it runs:** Every player interaction (~40-60 times per run)

**This is the MOST FREQUENT and MOST EXPENSIVE call.**

**v0 name:** Narrator agent.

**Input shape:** `MechanicalResult`, visible scene context, target Islander personality summary, recent visible history, and relevant content snippets.

**Output shape:** A validated narration commit. It may include prose, dialogue, tone tags, and display hints, but it must not invent mechanics or mutate state.

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

**Input shape:** Resolved event result, participants, public/private visibility, emotional stakes, and ceremony beats.

**Output shape:** A validated narration commit for the event.

**Cost:** ~600 tokens (~$0.002 per event)

**Frequency:** ~6 events per run = ~$0.012 per run

---

### 5. NPC Behavior Simulator

**Job:** Decide what NPCs do autonomously

**When it runs:** Once per phase transition (4x per day = ~80 times per run)

**This is OPTIONAL - can be purely algorithmic. Using LLM adds personality but costs more.**

**Algorithmic approach (recommended for POC):** Code-driven decisions based on personality, relationship scores, goals, current phase, and location. NPCs use the same action validity and success formulas as the player.

**LLM-enhanced approach (future enhancement):** A future agent may recommend one valid NPC action from a constrained list, but code still validates and executes that action using normal formulas.

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

```python
preferences = Preferences(
    physical_type="Tall, athletic, dark features",
    personality_type="Funny, confident, ambitious",
    values=["loyalty", "adventure", "honesty"],
    dealbreakers=["arrogance", "laziness", "drama"],
)
```

**How preferences work:**

```python
def check_preference_match(player: PlayerState, target: IslanderState) -> int:
    match_bonus = 0

    if player_matches_physical_type(player, target.preferences.physical_type):
        match_bonus += 10

    if player_has_high_stat(player, target.preferences.personality_type):
        match_bonus += 8

    shared_values = count_shared_values(player.values, target.preferences.values)
    match_bonus += shared_values * 3

    if player_has_dealbreaker(player, target.preferences.dealbreakers):
        match_bonus -= 15

    return match_bonus
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
- Use provider/model prompt caching where available
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
```python
# Future enhancement: stream narrator text from the Python agent boundary.
async for chunk in narrator.stream(mechanical_result, visible_context):
    yield chunk
```

**2. Parallel generation**
```python
# Generate all starting Islanders concurrently when LLM generation is enabled.
islanders = await asyncio.gather(
    *(generate_islander(archetype) for archetype in archetypes)
)
# 5 seconds total instead of 5 x 5 = 25 seconds.
```

**3. Pregeneration**
```python
# Future enhancement: precompute narrator/event prose after deterministic
# mechanics have already scheduled the next beat.
await preload_next_day_narration(state)
```

---

## Error Handling

### LLM Failures

**Timeout:**
```python
try:
    narration = await narrate_mechanical_result(result, visible_context, timeout=5.0)
except TimeoutError as exc:
    raise NarrationError("Narrator timed out") from exc
```

**Malformed output:**
```python
try:
    narration = NarrationCommit.model_validate(raw_agent_output)
except ValidationError as exc:
    raise NarrationError("Narrator returned invalid output") from exc
```

**Inappropriate content:**
```python
narration = await narrate_mechanical_result(result, visible_context)
if violates_content_rules(narration):
    raise NarrationError("Narrator returned content outside the game rating")
```

### Fallback Systems

For the POC, fail loud instead of silently substituting generic LLM content. If the Narrator times out or returns malformed output, surface the error in CLI/dev traces so prompts and contracts can be fixed.

Template content is still useful, but as authored content or mock data:

- seed characters for engine tests
- mock narration for `--mock-llm`
- fallback-free local test fixtures

It should not silently replace a failed live LLM call in normal gameplay.

---

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 04-State-Management.md for data structures that power this system
