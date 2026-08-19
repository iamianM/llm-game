# Reality Dating Sim Reference Observations

## Conversation Scene Grammar

The reference screenshots from a reality dating show mobile game use a
full-scene background with character art placed directly over the environment.
Characters are not inside cards during normal play; the card-like elements are
reserved for speech, narration, and choices. This is the main lesson for
Paradise Hearts: the cast should feel physically present in Sunset Bay, while
UI should float over them.

Characters are staged as cutouts with strong silhouettes. The active speaker is
usually foregrounded by scale and placement rather than by a heavy outline.
Secondary characters can remain visible but should visually recede through
scale, opacity, and position.

## Bubble Shape And Pagination

The visible reference bubbles are compact white or pale panels with colored
outlines, placed in the lower middle of the screen or near the speaker/choice
zone. The sample text length is short, roughly one or two sentences. For
Paradise Hearts, 180 characters per bubble is a reasonable starting maximum.
Longer LLM dialogue should paginate into consecutive bubbles rather than
growing a single box and covering the scene.

Pagination affordance should be subtle: a small continue chevron or dots on the
bubble, not a large button. Tapping the stage advances when no choices are
visible.

## Character Pose Vocabulary

The mobile game relies on static poses and composition more than complex
animation. The useful pose vocabulary for v1 is:

- idle: character stands in the scene.
- talking: active speaker is brighter and slightly forward.
- listening: player or NPC faces the conversation.
- reacting_good: a quick positive pop/tilt.
- reacting_bad: a quick flinch/tilt and dim.
- exiting: slide/fade toward the nearest edge.

No lip-sync or expression-specific asset set is needed for v1.

## Camera And Scene Motion

The reference grammar supports simple camera cuts:

- wide group: everyone visible in the environment before a choice.
- speaker focus: one NPC moves forward while others recede.
- two-shot: player plus one NPC are dominant.
- narrator full: scene dims and a top/center panel carries show narration.
- cutscene: a character briefly enters, performs, and exits for challenges.

The motion should feel like a reality-TV visual novel: fast, legible, and
confident. Avoid dashboard-style panel transitions.

## Choices

Choices appear as compact rounded options near the lower portion of the screen.
They are closer to speech choices than menu cards. In Paradise Hearts, player
options should anchor near the always-visible player sprite. When selected, the
chosen option should collapse into a player speech bubble before the NPC
response appears.

For more than four choices, use a scrollable stack inside the choice fan rather
than shrinking text below tap-safe size.

## Challenge And Minigame Framing

Challenge references emphasize staged moments more than full mechanical boards.
Paradise Hearts should keep the current deterministic challenge boards, but the
board should sit inside the scene as a prop or overlay while characters remain
visible. The player sprite should stay mounted during every challenge round.

For Pulse Race and Kiss/Wed/Pass-style moments, quick cutscene beats are more
important than dense mechanics: character enters, narrator sets up, choice
appears, reveal pops.

## Delta Feedback

The reference material shows choices as the main source of consequence. For
Paradise Hearts, audience/relationship changes should appear as short in-scene
pops near the relevant character or player, not as a separate dashboard row.

## Implementation Takeaways

1. Replace the dashboard branch with a staged renderer.
2. Always render the player at the bottom-center.
3. Render all present NPCs during idle choice beats.
4. Foreground the active NPC during conversations.
5. Use bubbles for narrator, NPC speech, player speech, and choices.
6. Keep minigames scene-native by embedding the board in the stage.
7. Keep motion simple and named: enter, walk forward, walk back, bubble pop,
   choice settle, choice select, delta pop, camera cut.
