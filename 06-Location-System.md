# Location System

*Resort layout, spatial gameplay, and location-based actions*

**Document Status:** ✅ Complete
**Last Updated:** 2025-10-08

---

## Table of Contents

- [Resort Overview](#resort-overview)
- [Location Specifications](#location-specifications)
- [Location-Specific Actions](#location-specific-actions)
- [Movement System](#movement-system)
- [Invitation System](#invitation-system)
- [Strategic Location Choices](#strategic-location-choices)
- [NPC Location Behavior](#npc-location-behavior)
- [Sprite Integration](#sprite-integration)

---

## Resort Overview

### Sunset Bay

The resort is divided into **discrete locations** (not a continuous map).

**Design philosophy:**
- Each location serves a specific social purpose
- Actions are tied to locations (context matters)
- Player can see all locations and who's where
- Movement is quick (not a time sink)
- Privacy levels create strategic choices

### Location Types

**Public** (6+ capacity, everyone can see/hear):
- Pool
- Kitchen
- Gym
- Beach

**Semi-Private** (2-4 capacity, some privacy):
- Bedroom (shared space but more intimate)
- Terrace (visible but conversationally private)

**Private** (2 capacity, requires invitation):
- Terrace (when claimed)
- Paradise Suite (requires unlock)

---

## Location Specifications

### Pool

```javascript
{
  id: "pool",
  name: "Pool Area",
  description: "The heart of the resort. Sun loungers, a sparkling blue pool, and always buzzing with activity.",

  capacity: 8,
  privacy: "public",

  activities: [
    "swim",
    "sunbathe",
    "pool_volleyball",
    "lounge_chat",
    "make_drinks"
  ],

  unlockableActions: [
    {
      id: "splash",
      name: "Splash playfully",
      requires: "both_in_pool",
      statUsed: "banter",
      effects: { chemistry: +4, friendship: +3 }
    },
    {
      id: "underwater_chat",
      name: "Swim closer and chat",
      requires: "both_in_pool",
      statUsed: "charm",
      effects: { chemistry: +5, affection: +3 }
    },
    {
      id: "chicken_fight",
      name: "Challenge to chicken fight",
      requires: "both_in_pool + 2_others",
      statUsed: "physical",
      effects: { friendship: +5, mood: "happy" }
    },
    {
      id: "underwater_kiss",
      name: "Kiss underwater",
      requires: "both_in_pool + relationship_60",
      statUsed: "charm",
      effects: { chemistry: +10, affection: +8 },
      risky: true // others might see
    }
  ],

  atmosphereBonus: {
    flirty: +5,    // good for flirting
    friendly: +5,  // social atmosphere
    deep: -5       // too public for deep talks
  },

  backgroundImage: "/backgrounds/resort-pool-day.jpg",
  ambientSound: "pool-water-splashing.mp3"
}
```

---

### Gym

```javascript
{
  id: "gym",
  name: "Gym",
  description: "Weights, cardio machines, yoga mats. A place to show off or work together.",

  capacity: 4,
  privacy: "semi-private",

  activities: [
    "workout_alone",
    "cardio",
    "weights",
    "yoga",
    "boxing"
  ],

  unlockableActions: [
    {
      id: "workout_together",
      name: "Work out together",
      duration: 35,
      statUsed: null, // automatic success
      effects: {
        friendship: +5,
        player_physical: +0.1,
        mood: "energized"
      }
    },
    {
      id: "spot_weights",
      name: "Spot them during weights",
      requires: "target_working_out",
      statUsed: "physical",
      effects: { trust: +5, friendship: +4 }
    },
    {
      id: "flex",
      name: "Show off / flex",
      statUsed: "physical",
      effects: { chemistry: +5 },
      failureEffects: { animosity: +2 }, // they think you're vain
      risky: true
    },
    {
      id: "boxing_together",
      name: "Spar together (boxing)",
      statUsed: "physical",
      effects: { chemistry: +6, friendship: +4, mood: "energized" }
    }
  ],

  atmosphereBonus: {
    friendly: +10,  // great for bonding
    physical: +15,  // physical stat bonus
    deep: 0,
    flirty: +5      // showing off physique
  },

  backgroundImage: "/backgrounds/resort-gym.jpg",
  ambientSound: "gym-equipment.mp3"
}
```

---

### Kitchen

```javascript
{
  id: "kitchen",
  name: "Kitchen",
  description: "Open kitchen with a large island. Great for casual chats while cooking or making drinks.",

  capacity: 6,
  privacy: "public",

  activities: [
    "cook_together",
    "make_breakfast",
    "make_drinks",
    "chat_at_counter",
    "bake_together"
  ],

  unlockableActions: [
    {
      id: "cook_for_them",
      name: "Cook breakfast for them",
      duration: 30,
      statUsed: "emotional_intelligence", // thoughtful gesture
      effects: { affection: +6, trust: +4, mood: "content" }
    },
    {
      id: "make_coffee_together",
      name: "Make coffee and chat",
      duration: 20,
      statUsed: null,
      effects: { friendship: +4, familiarity: +3 }
    },
    {
      id: "taste_test",
      name: "Feed them a taste (flirty)",
      requires: "cooking + relationship_30",
      statUsed: "charm",
      effects: { chemistry: +5, affection: +3 }
    },
    {
      id: "food_fight",
      name: "Playful food fight",
      requires: "relationship_40",
      statUsed: "banter",
      effects: { chemistry: +6, friendship: +5, mood: "happy" },
      sideEffect: "makes_mess" // might annoy neat Heartbreakers
    }
  ],

  atmosphereBonus: {
    friendly: +10,  // casual, comfortable
    deep: +5,       // intimate setting
    banter: +5,
    flirty: +3
  },

  backgroundImage: "/backgrounds/resort-kitchen.jpg",
  ambientSound: "kitchen-ambient.mp3"
}
```

---

### Bedroom

```javascript
{
  id: "bedroom",
  name: "Bedroom",
  description: "Shared bedroom with multiple beds. More private than the pool, but still shared space.",

  capacity: 10, // everyone sleeps here
  privacy: "semi-private",

  activities: [
    "get_ready",
    "chat_on_bed",
    "nighttime_chat",
    "chill",
    "gossip_session"
  ],

  unlockableActions: [
    {
      id: "private_chat_on_bed",
      name: "Private chat on your bed",
      requires: "relationship_40",
      duration: 25,
      statUsed: "emotional_intelligence",
      effects: { trust: +5, affection: +4, familiarity: +5 }
    },
    {
      id: "cuddle",
      name: "Cuddle on bed",
      requires: "coupled + relationship_60",
      statUsed: null,
      effects: { chemistry: +8, affection: +6, trust: +3 },
      publicReaction: true // others might see and react
    },
    {
      id: "nighttime_reassurance",
      name: "Bedtime reassurance chat",
      requires: "evening_phase + coupled",
      statUsed: "loyalty",
      effects: { trust: +7, affection: +4, mood: "secure" }
    },
    {
      id: "gossip_huddle",
      name: "Gossip session with the girls/boys",
      requires: "2+_same_gender",
      duration: 30,
      statUsed: "banter",
      effects: { friendship: +6 },
      outcome: "learn_gossip" // chance to learn new info
    }
  ],

  atmosphereBonus: {
    deep: +10,       // good for serious talks
    friendly: +5,
    flirty: +5,      // intimate setting
    gossip: +10      // classic bedroom gossip
  },

  backgroundImage: "/backgrounds/resort-bedroom.jpg",
  ambientSound: "bedroom-ambient.mp3"
}
```

---

### Terrace

```javascript
{
  id: "terrace",
  name: "Terrace",
  description: "Romantic rooftop terrace with a view. The classic spot for serious chats and romantic moments.",

  capacity: 2,
  privacy: "private",
  requiresInvitation: true,

  activities: [
    "stargaze",
    "sunset_watch",
    "deep_talk",
    "romantic_moment"
  ],

  unlockableActions: [
    {
      id: "stargaze_together",
      name: "Stargaze together",
      requires: "relationship_40",
      duration: 25,
      statUsed: null,
      effects: {
        affection: +7,
        trust: +5,
        chemistry: +4,
        mood: "romantic"
      }
    },
    {
      id: "confession",
      name: "Confess your feelings",
      requires: "relationship_70",
      statUsed: "emotional_intelligence",
      effects: { affection: +10, trust: +8 },
      failureEffects: { trust: -5, awkwardness: true },
      risky: true
    },
    {
      id: "first_kiss",
      name: "Kiss",
      requires: "relationship_50",
      statUsed: "charm",
      effects: { chemistry: +12, affection: +8, trust: +3 },
      milestone: true // records as major moment
    },
    {
      id: "define_relationship",
      name: "Define the relationship (DTR)",
      requires: "relationship_65",
      duration: 30,
      statUsed: "emotional_intelligence",
      effects: { trust: +10, affection: +7 },
      outcome: "exclusive_couple" // triggers game state change
    }
  ],

  atmosphereBonus: {
    romantic: +20,   // best for romance
    deep: +15,       // perfect for serious talks
    flirty: +10,
    friendly: +5
  },

  backgroundImage: "/backgrounds/resort-terrace-night.jpg",
  ambientSound: "night-crickets.mp3"
}
```

---

### Beach

```javascript
{
  id: "beach",
  name: "Beach",
  description: "Private beach just steps from the resort. Sand, waves, and romantic sunsets.",

  capacity: 6,
  privacy: "semi-private",

  activities: [
    "walk_on_beach",
    "sit_by_fire",
    "watch_sunset",
    "beach_games"
  ],

  unlockableActions: [
    {
      id: "romantic_walk",
      name: "Romantic walk along the shore",
      requires: "relationship_40",
      duration: 30,
      statUsed: "charm",
      effects: {
        affection: +6,
        chemistry: +5,
        trust: +4,
        mood: "romantic"
      }
    },
    {
      id: "heart_to_heart",
      name: "Heart-to-heart by the fire",
      requires: "evening_phase + relationship_50",
      duration: 35,
      statUsed: "emotional_intelligence",
      effects: { trust: +8, affection: +6, familiarity: +8 }
    },
    {
      id: "write_in_sand",
      name: "Write your names in the sand",
      requires: "coupled + relationship_60",
      statUsed: null,
      effects: { affection: +5, chemistry: +4, mood: "happy" },
      pulseBonus: +3 // audience loves this
    },
    {
      id: "beach_volleyball",
      name: "Beach volleyball (group)",
      requires: "4+_heartbreakers",
      statUsed: "physical",
      effects: { friendship: +5, mood: "energized" }
    }
  ],

  atmosphereBonus: {
    romantic: +15,
    deep: +10,
    friendly: +5,
    flirty: +8
  },

  backgroundImage: "/backgrounds/resort-beach.jpg",
  ambientSound: "ocean-waves.mp3"
}
```

---

### Paradise Suite

```javascript
{
  id: "private_suite",
  name: "The Paradise Suite",
  description: "Ultra-private luxury bedroom. Only accessible to challenge winners or as special rewards.",

  capacity: 2,
  privacy: "completely_private",
  requiresInvitation: true,
  requiresUnlock: "challenge_winner", // or special event

  activities: [
    "overnight_stay",
    "private_time"
  ],

  unlockableActions: [
    {
      id: "private_suite_overnight",
      name: "Spend the night together",
      requires: "coupled + relationship_70 + unlock",
      duration: 480, // 8 hours (happens overnight)
      statUsed: null,
      effects: {
        chemistry: +20,
        affection: +15,
        trust: +10,
        coupleStrength: +15,
        mood: "euphoric"
      },
      milestone: true,
      pulseBonus: +5 // audience loves committed couples
    },
    {
      id: "private_suite_confession",
      name: "Deepest confession",
      requires: "relationship_75",
      statUsed: "emotional_intelligence",
      effects: { trust: +12, affection: +10, familiarity: +15 },
      outcome: "reveals_secret" // might reveal Heartbreaker's secret
    }
  ],

  atmosphereBonus: {
    romantic: +25,   // maximum romance bonus
    deep: +20,       // perfect for vulnerability
    intimate: +30    // special intimate category
  },

  backgroundImage: "/backgrounds/resort-private-suite.jpg",
  ambientSound: "romantic-ambient.mp3"
}
```

---

## Location-Specific Actions

### Action Schema

```typescript
interface LocationAction {
  id: string
  name: string
  category: "activity" | "romantic" | "friendly" | "physical"

  // Requirements
  requires?: string // "both_in_pool", "relationship_60", etc.
  requiresRelationship?: number
  requiresContext?: string

  // Mechanics
  duration: number // minutes
  statUsed: string | null
  successFormula?: (player, target, context) => number

  // Effects
  effects: {
    affection?: number
    chemistry?: number
    trust?: number
    friendship?: number
    mood?: string
    // ... other effects
  }

  failureEffects?: object
  sideEffects?: string[] // "makes_mess", "others_jealous", etc.

  // Metadata
  risky?: boolean // warns player
  milestone?: boolean // records as major moment
  animation?: string // sprite animation to play
}
```

### Universal Actions (Available Everywhere)

```javascript
const universalActions = [
  {
    id: "chat",
    name: "Chat casually",
    category: "friendly",
    duration: 15,
    statUsed: null,
    effects: { friendship: +3, familiarity: +2 }
  },
  {
    id: "joke",
    name: "Tell a joke",
    category: "friendly",
    duration: 10,
    statUsed: "banter",
    effects: { friendship: +4, affection: +2 }
  },
  {
    id: "compliment_personality",
    name: "Compliment their personality",
    category: "friendly",
    duration: 10,
    statUsed: "emotional_intelligence",
    effects: { affection: +4, trust: +2 }
  }
]
```

### Context-Based Action Availability

```javascript
function getAvailableActions(location, target, player) {
  const actions = [...universalActions]

  // Add location-specific actions
  const locationActions = locations[location].unlockableActions

  for (let action of locationActions) {
    // Check requirements
    if (action.requiresRelationship) {
      if (target.relationships.player.affection < action.requiresRelationship) {
        continue // skip
      }
    }

    if (action.requires) {
      if (!checkRequirement(action.requires, location, target, player)) {
        continue // skip
      }
    }

    actions.push(action)
  }

  return actions
}

function checkRequirement(requirement, location, target, player) {
  switch (requirement) {
    case "both_in_pool":
      return player.currentActivity === "swimming" && target.currentActivity === "swimming"

    case "target_working_out":
      return target.currentActivity === "working_out"

    case "evening_phase":
      return resortState.currentPhase === "evening"

    case "coupled":
      return player.coupledWith === target.id

    case "2+_same_gender":
      const sameGender = getHeartbreakersAtLocation(location).filter(i => i.gender === player.gender)
      return sameGender.length >= 2

    // ... more requirements

    default:
      return true
  }
}
```

---

## Movement System

### Moving Between Locations

```javascript
function moveToLocation(newLocationId) {
  const location = locations[newLocationId]

  // Check if location requires unlock
  if (location.requiresUnlock && !player.unlockedLocations.includes(newLocationId)) {
    return error(`${location.name} is locked. ${location.unlockHint}`)
  }

  // Check if location requires invitation
  if (location.requiresInvitation) {
    return error(`${location.name} is private. You need to invite someone or be invited.`)
  }

  // Check capacity
  if (location.heartbreakersPresent.length >= location.capacity) {
    return error(`${location.name} is full.`)
  }

  // Move player
  const oldLocation = locations[player.currentLocation]
  oldLocation.heartbreakersPresent = oldLocation.heartbreakersPresent.filter(id => id !== "player")

  location.heartbreakersPresent.push("player")
  player.currentLocation = newLocationId

  // Time cost
  const timeCost = 5
  resortState.timeRemaining -= timeCost

  // Update view
  return {
    newLocation: location,
    timeCost: timeCost,
    heartbreakersHere: location.heartbreakersPresent.map(id => getHeartbreakerById(id))
  }
}
```

### Resort Map Display

```javascript
function getResortMapState() {
  return {
    locations: Object.values(locations).map(loc => ({
      id: loc.id,
      name: loc.name,
      heartbreakersPresent: loc.heartbreakersPresent.map(id => ({
        id: id,
        name: getHeartbreakerById(id).name,
        activity: getHeartbreakerById(id).currentActivity
      })),
      capacity: loc.capacity,
      isFull: loc.heartbreakersPresent.length >= loc.capacity,
      isLocked: loc.requiresUnlock && !player.unlockedLocations.includes(loc.id),
      requiresInvitation: loc.requiresInvitation,
      isPlayerHere: loc.heartbreakersPresent.includes("player")
    })),
    currentLocation: player.currentLocation,
    timeRemaining: resortState.timeRemaining
  }
}
```

**UI Display:**
```
SUNSET BAY MAP                    Time Remaining: 70 min

🏊 Pool (4/8)                      [YOU ARE HERE]
   • You
   • Chloe (sunbathing)
   • Marcus (swimming)
   • Sophie (chatting)

💪 Gym (1/4)
   • Liam (working out)

🍳 Kitchen (2/6)
   • Aisha (making coffee)
   • Tom (cooking)

🏠 Bedroom (0/10)
   (Empty)

🌅 Terrace (0/2) 🔒 Private
   (Invite someone for private chat)

🏖️ Beach (0/6)
   (Empty)

💎 Paradise Suite 🔒 Locked
   (Win a challenge to unlock)

---
Where do you want to go?
→ Stay at Pool
→ Move to Gym (5 min)
→ Move to Kitchen (5 min)
→ Move to Beach (5 min)
```

---

## Invitation System

### Inviting Someone to Private Location

```javascript
function inviteToLocation(targetId, locationId) {
  const target = getHeartbreakerById(targetId)
  const location = locations[locationId]

  // Check if location allows invitations
  if (!location.requiresInvitation) {
    return error("This location doesn't require invitations.")
  }

  // Check if player has access
  if (location.requiresUnlock && !player.unlockedLocations.includes(locationId)) {
    return error("You don't have access to this location.")
  }

  // Calculate acceptance probability
  const acceptanceChance = calculateInviteAcceptance(target, location, player)

  const roll = random(1, 100)
  const accepted = roll <= acceptanceChance

  if (accepted) {
    // Both move to location
    moveToLocation(locationId)
    moveTo(target, locationId)

    // Generate LLM acceptance dialogue
    const dialogue = await generateInviteAcceptance(target, location, true)

    return {
      accepted: true,
      dialogue: dialogue,
      timeCost: 10
    }
  } else {
    // Rejection
    const dialogue = await generateInviteAcceptance(target, location, false)

    return {
      accepted: false,
      dialogue: dialogue,
      timeCost: 5,
      relationshipChange: { animosity: +2 }
    }
  }
}

function calculateInviteAcceptance(target, location, player) {
  let chance = 50

  // Relationship bonus
  chance += target.relationships.player.affection / 2 // 0-50

  // Chemistry bonus (for romantic locations)
  if (location.atmosphereBonus.romantic > 10) {
    chance += target.relationships.player.chemistry / 3 // 0-33
  }

  // Trust bonus
  chance += target.relationships.player.trust / 4 // 0-25

  // Personality modifiers
  if (target.personality.extraversion < 5) {
    chance -= 10 // introverts more hesitant
  }

  // Attachment style
  if (target.attachmentStyle === "avoidant" && location.id === "private_suite") {
    chance -= 20 // avoidants resist intimacy
  }

  // If coupled with someone else (very risky)
  if (target.coupledWith && target.coupledWith !== player.id) {
    chance -= 30
  }

  // Time of day
  if (location.id === "terrace" && resortState.currentPhase === "evening") {
    chance += 10 // terrace is romantic at night
  }

  return Math.max(10, Math.min(95, chance))
}
```

---

## Strategic Location Choices

### Why Location Matters

**Privacy Level:**
- Public = Others can see/hear → builds public perception, but less intimate
- Private = No witnesses → can be riskier (flirting while coupled), more romantic

**Activity Options:**
- Pool = Physical, playful
- Gym = Bonding through activity
- Terrace = Romance and depth
- Beach = Romantic and scenic

**Who's There:**
- Go where your target is (save time)
- Avoid locations with rivals
- Go where drama is happening (gather intel)

**Atmosphere Bonus:**
- Terrace gives +20 romantic → best for confessions
- Gym gives +10 friendly → best for building friendship
- Kitchen gives +10 friendly → casual bonding

### Strategic Scenarios

**Scenario 1: Reassure Partner**

Player coupled with Chloe, new Heart Throb Aisha arrived.

Option A: Public reassurance (pool)
- ✅ Others see your loyalty → +Public Perception
- ✅ Chloe feels secure (public display)
- ❌ Less intimate
- ❌ Others might gossip

Option B: Private reassurance (terrace)
- ✅ More intimate (+trust bonus)
- ✅ Deep conversation possible
- ❌ No public proof of loyalty
- ❌ Takes more time (invite + chat)

**Scenario 2: Spark with New Heart Throb**

Player wants to explore connection with Aisha while coupled.

Option A: Talk at pool (public)
- ❌ High risk of being seen
- ❌ -30 penalty to flirt success
- ❌ Partner might find out

Option B: Invite to terrace (private)
- ✅ No witnesses
- ✅ Romantic atmosphere bonus
- ❌ Very obvious (others notice you left together)
- ❌ If caught, trust damage is severe

**Scenario 3: Gather Intel**

Player wants to know what Marcus and Sophie argued about.

Option A: Talk to Marcus directly
- ✅ Get his side of story
- ❌ Might not tell the truth
- ❌ Might create animosity

Option B: Find Liam (who witnessed it)
- ✅ More objective account
- ✅ Liam loves to gossip
- ❌ Need to find where Liam is
- ❌ Takes more time (movement)

---

## NPC Location Behavior

### Autonomous Movement

```javascript
function simulateNPCLocationChanges(timeElapsed) {
  for (let npc of allNPCs) {
    // Skip if in conversation with player
    if (npc.currentActivity === "talking_to_player") continue

    // Extraversion affects movement frequency
    const movementChance = npc.personality.extraversion * 5 // 0-50%

    if (random(100) < movementChance) {
      const newLocation = chooseNPCLocation(npc)
      if (newLocation !== npc.currentLocation) {
        moveTo(npc, newLocation)
      }
    }
  }
}

function chooseNPCLocation(npc) {
  const options = []

  // Weighted by personality and goals
  if (npc.personality.physical > 7) {
    options.push({ location: "gym", weight: 3 })
  }

  if (npc.personality.extraversion > 7) {
    options.push({ location: "pool", weight: 4 }) // social hotspot
  }

  if (npc.mood === "hungry") {
    options.push({ location: "kitchen", weight: 5 })
  }

  // Strategic: Go where romantic interest is
  if (npc.interests.length > 0) {
    const interestLocation = getHeartbreakerById(npc.interests[0]).currentLocation
    options.push({ location: interestLocation, weight: 6 })
  }

  // Strategic: Avoid rivals
  if (npc.threats.length > 0) {
    const rivalLocation = getHeartbreakerById(npc.threats[0]).currentLocation
    options = options.filter(o => o.location !== rivalLocation)
  }

  return weightedRandom(options)
}
```

### NPC Activity Choices

```javascript
function chooseNPCActivity(npc, location) {
  const activities = locations[location].activities

  // Personality-based preferences
  if (npc.personality.physical > 7 && location === "gym") {
    return "working_out"
  }

  if (npc.personality.extraversion > 7 && location === "pool") {
    return "chatting"
  }

  if (npc.mood === "anxious" && location === "bedroom") {
    return "lying_down"
  }

  // Default: random from available
  return random(activities)
}
```

---

## Sprite Integration

### Linking Actions to Animations

```javascript
const actionAnimations = {
  // Pool actions
  swim_together: {
    sprite: "swim_animation",
    duration: 2000, // ms
    participants: 2,
    foreground: true
  },

  splash: {
    sprite: "splash_animation",
    duration: 1000,
    participants: 2,
    effect: "water_splash_particles"
  },

  underwater_kiss: {
    sprite: "underwater_kiss_animation",
    duration: 3000,
    participants: 2,
    camera: "underwater_view"
  },

  // Gym actions
  workout_together: {
    sprite: "workout_animation",
    duration: 2500,
    participants: 2,
    variants: ["weights", "cardio", "yoga"]
  },

  spot_weights: {
    sprite: "spot_animation",
    duration: 2000,
    participants: 2
  },

  // Terrace actions
  stargaze: {
    sprite: "stargaze_animation",
    duration: 3000,
    participants: 2,
    camera: "wide_shot",
    background: "stars_overlay"
  },

  kiss: {
    sprite: "kiss_animation",
    duration: 2500,
    participants: 2,
    effect: "romantic_particles",
    variants: ["first_kiss", "passionate", "gentle"]
  }
}

function playActionAnimation(actionId, participants) {
  const animation = actionAnimations[actionId]

  if (!animation) {
    return null // no animation for this action
  }

  // Load sprite animation
  loadSprite(animation.sprite)

  // Position participants
  positionSprites(participants, animation)

  // Play animation
  playSpriteAnimation(animation.sprite, animation.duration)

  // Add effects
  if (animation.effect) {
    playParticleEffect(animation.effect)
  }

  // Adjust camera
  if (animation.camera) {
    setCameraView(animation.camera)
  }

  return animation
}
```

### Location Backgrounds

```javascript
const locationBackgrounds = {
  pool: {
    day: "/backgrounds/resort-pool-day.jpg",
    evening: "/backgrounds/resort-pool-sunset.jpg",
    night: "/backgrounds/resort-pool-night.jpg"
  },

  gym: {
    day: "/backgrounds/resort-gym.jpg",
    evening: "/backgrounds/resort-gym-evening.jpg",
    night: "/backgrounds/resort-gym-night.jpg"
  },

  terrace: {
    day: "/backgrounds/resort-terrace-day.jpg",
    evening: "/backgrounds/resort-terrace-sunset.jpg",
    night: "/backgrounds/resort-terrace-stars.jpg"
  },

  // ...
}

function getLocationBackground(locationId, timeOfDay) {
  return locationBackgrounds[locationId][timeOfDay]
}
```

---

**Version:** 1.0
**Status:** ✅ Complete
**Next:** See 07-Gossip-And-Information.md for knowledge systems and information flow

**Note:** For movement interceptions and being stopped while walking, see **09-Social-Dynamics.md**
