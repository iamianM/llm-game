# Paradise Hearts — Final Glossary

**Status:** Locked. All player-facing copy in Phase 3 UI uses these terms. Engine
internals (action kinds, ceremony event kinds, location IDs) keep their generic
identifiers through Phase 3; a separate post-Phase-3 rename PR aligns them.

## Brand

- **Working title / show name:** Paradise Hearts
- **Setting:** Sunset Bay, a tropical resort
- **Cast role:** Heartbreakers (each contestant)
- **Premise:** a reality dating show where Heartbreakers pair into couples,
  weather a mid-show twist (a Flush of Hearts from Sirens' Cove), and survive
  to the finale via audience favor

## Final term table

| Concept | Paradise Hearts term |
|---|---|
| Show name / brand | **Paradise Hearts** |
| The cast collectively | **Heartbreakers** |
| One contestant | **Heartbreaker** |
| The main resort (location) | **Sunset Bay** |
| Mid-show new arrival | **Heart Throb** |
| Rival location + twist mechanic | **Flush of Hearts** |
| Coupling ceremony (the event) | **Pairing Ceremony** |
| Re-pairing (the action) | **Heart Swap** |
| Day-1 opening ceremony | **First Spark** |
| Romantic pursuit (verb) | **Spark / Sparking** |
| Private couple-only room | **Paradise Suite** |
| Eliminated / dumped | **Heart Out** |
| Rejected by someone | **Cooled on** |
| Producer-text catchphrase | **Paradise Calls** |
| Audience meter (per run, live) | **Pulse** |
| Audience leaderboard view | **The Pulse Board** |
| Meta-currency (persistent) | **Heart Beats** |
| End-of-run / between-run hub | **The Reunion** |
| Producer (in-fiction) | **The Producer** |
| Public / audience body | **The Audience** |
| Daily competition (generic) | Challenge |
| Compatibility Quiz | Compatibility Quiz |
| Snog Marry Pie | **Kiss Wed Pass** |
| Mr & Mrs | **The Couples Quiz** |
| Heart Rate Challenge | **Pulse Race** |
| Ideal-partner criteria | Type on Paper |
| Couple status (high-tier reward) | **Soul Match** *(Phase 4 mechanic — see below)* |

## Soul Match — Phase 4 mechanic, flagged now

A couple reaches **Soul Match** status when their chemistry **and** affection
**and** trust all reach a high threshold (proposal: ≥75 each). When Soul
Matched, the couple:

- Receives a stronger audience sympathy weight (Pulse penalties from Heart
  Throbs reduced)
- Becomes harder to break via Heart Swap proposals (NPC initiator acceptance
  rolls penalized)
- Earns bonus Heart Beats at run end
- Surfaces visually in the UI as a dedicated badge on the Couples panel

Out of Phase 3 scope; do not implement during the UI build. Flagged here so it
isn't forgotten when Phase 4 (meta-progression) lands.

## Pulse vs Heart Beats — important distinction

These are both heart-themed and easy to confuse. Lock the distinction:

- **Pulse**: the **current run's** audience score (0–100). Visible as the
  meter in the top bar of the stage. Changes turn by turn based on player
  actions and audience reactions. Resets at the start of every new run.
- **Heart Beats**: the **persistent** meta-currency. Earned at the end of a
  run as a function of Pulse-at-finale, days survived, drama generated, and
  any memorable-moment bonuses. Spent in The Reunion (Phase 4) on
  archetypes, perks, and content unlocks. Carries across runs.

During a game, the player watches their **Pulse**. After the finale, they
bank **Heart Beats**. They are not interchangeable in UI copy or code.

## Example copy — stress-test paragraph

This single paragraph uses most of the vocabulary in natural sequence. Codex
should use it as the tonal reference for UI copy:

> *Eight Heartbreakers arrive at Sunset Bay for the First Spark. Two days in,
> the Pulse Board has the player's couple at #1 — until Paradise Calls
> announces a Flush of Hearts is on its way. Three Heart Throbs land at Sunset
> Bay, Sparking with the existing couples and cooling on the ones who don't
> bite. At the Pairing Ceremony, the player has a choice: Heart Swap with a
> new arrival, or stay loyal. Either way, someone's going Heart Out.*

If a UI string ever reads more clinical or more campy than that example, push
it back toward this tone.

## Tone notes

- **Cinematic, slightly literary** — the brand sells warmth with edge, not
  saccharine fluff. Sweet Hearts was rejected for being too sugary.
- **Place names matter** — Sunset Bay and Flush of Hearts are specific. They
  should appear in every ceremony and producer-text moment.
- **Verbs over nouns** — "she's Sparking with Liam" is more alive than "they
  have chemistry." Lean on Spark / cooling on / Heart Swap as verbs.
- **Avoid LI residue** — never write "the islanders" (it's "Heartbreakers"),
  "the villa" (it's "Sunset Bay"), "Casa Amor" (it's "Flush of Hearts"),
  "bombshell" (it's "Heart Throb"), "recoupling" (it's "Heart Swap" or
  "Pairing Ceremony"), "graft / grafting" (it's "Sparking"), "pied off /
  mugged off" (it's "cooled on"), "dumped from the island" (it's "Heart
  Out"), "I've got a text" (it's "Paradise Calls").

## Engine internal names (UNCHANGED through Phase 3)

The FastAPI server translates engine identifiers into display strings. The
engine code itself keeps the existing generic names; a post-Phase-3 rename
PR aligns them.

| Engine identifier | Display string |
|---|---|
| `bombshell` | Heart Throb |
| `casa_amor` | Flush of Hearts |
| `casa_amor_announce` | Flush of Hearts Announcement |
| `casa_amor_arrival` | Flush of Hearts Arrival |
| `casa_amor_decision` | Flush of Hearts Decision |
| `casa_amor_return_reveal` | Sunset Bay Return |
| `casa_pool` (location) | Sirens' Cove · Pool |
| `casa_kitchen` (location) | Sirens' Cove · Kitchen |
| `recouple` (action) | Heart Swap |
| `recoupling` (event) | Pairing Ceremony |
| `opening` (formed_via value) | First Spark |
| `proposal` (formed_via value) | Heart Swap Proposal |
| `hideaway` | Paradise Suite |
| `elimination` | Heart Out |
| `villa: paradise` (state) | Sunset Bay |
| `villa: casa_amor` (state) | Sirens' Cove |
| `phase: intros` | Day-1 Introductions |
| Challenge `compatibility_quiz` | Compatibility Quiz |
| Challenge `heart_rate` | Pulse Race |
| Challenge `mr_and_mrs` | The Couples Quiz |
| Challenge `snog_marry_pie` | Kiss Wed Pass |
| Challenge `lie_detector` | Lie Detector |
| Challenge `final_couples` | Final Couples Challenge |
| `audience_appeal` / `AP` | Heart Beats |
| `public_perception` | Pulse |

(Note: "Sirens' Cove" was an alternate name considered for Casa Amor — we
landed on Flush of Hearts. Kept here as the **internal location label** for
where the Flush of Hearts contestants come from, to give the geography
character — but UI surfaces everything as "Flush of Hearts" by default.
If this feels redundant during implementation, simplify to just "Flush of
Hearts" everywhere and drop Sirens' Cove. Codex's call.)

## Capitalization

- **Proper nouns** (capitalized mid-sentence): Paradise Hearts, Heartbreakers
  (when collective), Sunset Bay, Heart Throb, Flush of Hearts, Heart Swap,
  Pairing Ceremony, First Spark, Paradise Suite, Heart Out, Paradise Calls,
  Pulse Board, Heart Beats, The Reunion, Soul Match, Kiss Wed Pass, The
  Couples Quiz, Pulse Race
- **Sentence-cased** (lowercase mid-sentence): heartbreaker (individual), the
  audience, the producer, sparking, cooled on, pulse (as a generic word, e.g.
  "her pulse quickened"), heart beats (the literal sound, not the currency)
- **Distinction** — capital **Pulse** = the currency/meter; lowercase
  **pulse** = a literal heartbeat in dialogue
