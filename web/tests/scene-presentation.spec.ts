import { expect, test } from "@playwright/test";
import { NO_MINIGAME_PRESENTATION, planScene } from "../components/scene/SceneDirector";
import { flattenPlan } from "../components/scene/useScenePlayback";
import type {
  MinigamePresentationPort,
  PresentationTransition,
  SceneSegment,
} from "../lib/scene/presentation";
import type { AvailableAction, SessionState, TurnResponse } from "../lib/types";

test("scene planning is deterministic and routes each action exactly once", () => {
  const actions = [
    action("start_conversation", "Talk to Liam", "liam"),
    action("move", "Move to the terrace", "terrace"),
    action("ambient", "Watch the pool", "ambient_wait"),
  ];
  const transition: PresentationTransition = { kind: "baseline", state: state(), actions };

  const first = planScene(transition, NO_MINIGAME_PRESENTATION);
  const second = planScene(transition, NO_MINIGAME_PRESENTATION);

  expect(second).toEqual(first);
  expect(first.actionLanes.character).toEqual([actions[0]]);
  expect(first.actionLanes.move).toEqual([actions[1]]);
  expect(first.actionLanes.fan).toEqual([actions[2]]);
  expect([
    ...first.actionLanes.character,
    ...first.actionLanes.move,
    ...first.actionLanes.fan,
  ]).toHaveLength(actions.length);
  expect(first.frames).toHaveLength(first.segments.flatMap((segment) => segment.beats).length);
});

test("baseline establishes history without replaying old recaps", () => {
  const baseline = planScene(
    {
      kind: "baseline",
      state: state({ daily_recaps: [recap(4)] }),
      actions: [action("ambient", "Wait")],
    },
    NO_MINIGAME_PRESENTATION,
  );

  expect(baseline.features).toEqual([]);
});

test("pending presentation never treats the selected intent label as player dialogue", () => {
  const previous = state();
  const selectedAction = action("flirt", "Push the flirt", "liam");
  const pending = planScene(
    {
      kind: "pending",
      previous,
      state: previous,
      actions: [],
      selectedAction,
      stream: {
        speakerId: "liam",
        speakerName: "Liam",
        text: "I was hoping you would say that.",
      },
    },
    NO_MINIGAME_PRESENTATION,
  );

  const speech = pending.segments.flatMap((segment) => segment.beats).filter((beat) => beat.kind === "speech");
  expect(speech).toEqual([
    {
      kind: "speech",
      speakerId: "liam",
      text: "I was hoping you would say that.",
      pose: "talking",
    },
  ]);
  expect(JSON.stringify(pending)).not.toContain(selectedAction.label);
});

test("pending and resolved plans share consumed stream beat identities", () => {
  const previous = state();
  const pendingTransition: PresentationTransition = {
    kind: "pending",
    previous,
    state: previous,
    actions: [],
    selectedAction: action("chat", "Open up", "liam"),
    stream: {
      speakerId: "liam",
      speakerName: "Liam",
      text: "I hear you.",
    },
  };
  const resolvedTransition: PresentationTransition = {
    kind: "resolved",
    previous,
    response: turn({
      state: state({ turn_index: 89 }),
      exchange: {
        speaker_id: "liam",
        speaker_name: "Liam",
        player_dialogue: "Here is what I actually meant.",
        npc_dialogue: "I hear you.",
        npc_tone: "warm",
        npc_mood_after: "warm",
      },
    }),
  };

  const pending = planScene(pendingTransition, NO_MINIGAME_PRESENTATION);
  const resolved = planScene(resolvedTransition, NO_MINIGAME_PRESENTATION);
  const pendingNpc = flattenPlan(pending).find((item) => item.beat.kind === "speech");
  const resolvedNpc = flattenPlan(resolved).find(
    (item) => item.beat.kind === "speech" && item.beat.speakerId === "liam",
  );

  expect(resolved.id).toBe(pending.id);
  expect(resolvedNpc?.id).toBe(pendingNpc?.id);
});

test("resolved features keep event order and append only new recaps", () => {
  const previous = state({ daily_recaps: [recap(4)] });
  const response = turn({
    state: state({ turn_index: 89, daily_recaps: [...previous.daily_recaps, recap(5)] }),
    ceremony_events: [
      { kind: "producer_text", message: "Meet at the Flame Deck." },
      { kind: "pairing", message: "The couples lock in." },
      { kind: "elimination", message: "Someone leaves." },
    ],
  });

  const plan = planScene({ kind: "resolved", previous, response }, NO_MINIGAME_PRESENTATION);

  expect(plan.features.map((feature) => feature.kind)).toEqual(["ceremony", "ceremony", "recap"]);
  expect(plan.features.map((feature) => feature.id)).toEqual([
    "hash-89:ceremony:1",
    "hash-89:ceremony:2",
    "hash-89:recap:1",
  ]);
});

test("large casts keep the focus staged and move overflow into one group panel", () => {
  const heartbreakers = Array.from({ length: 10 }, (_, index) => heartbreaker(`npc-${index}`));
  const focused = heartbreakers[9];
  const plan = planScene(
    {
      kind: "baseline",
      state: state({ heartbreakers, active_conversation_target_id: focused.id }),
      actions: [action("chat", "Keep talking", focused.id)],
    },
    NO_MINIGAME_PRESENTATION,
  );

  const frame = plan.frames[0];
  expect(frame.cast.filter((member) => member.id !== "player")).toHaveLength(7);
  expect(frame.cast.some((member) => member.id === focused.id)).toBe(true);
  expect(frame.groupPanelIds).toHaveLength(3);
});

test("minigame presentation is composed through the port without scene interpretation", () => {
  type Slot = { kind: "test-board" };
  const segment: SceneSegment<Slot> = {
    id: "test-minigame",
    beats: [{ kind: "narrator", text: "Board-owned beat." }],
    slot: { kind: "test-board" },
  };
  const port: MinigamePresentationPort<Slot> = { plan: () => segment };
  const actions = [action("challenge_response", "Answer A", "answer-a")];

  const plan = planScene({ kind: "baseline", state: state(), actions }, port);

  expect(plan.segments).toContain(segment);
  expect(plan.actionLanes.fan).toEqual(actions);
  expect(plan.segments.flatMap((candidate) => candidate.beats)).toContainEqual({
    kind: "narrator",
    text: "Board-owned beat.",
  });
});

function action(kind: string, label: string, targetId: string | null = "ambient_wait"): AvailableAction {
  return {
    kind,
    label,
    target_id: targetId,
    intent_id: null,
    option_index: null,
    audience_hint: "",
    risk: null,
    stat_used: null,
  };
}

function recap(day: number): SessionState["daily_recaps"][number] {
  return {
    day,
    resort_id: day <= 3 ? "main" : "flush_of_hearts",
    resort_label: day <= 3 ? "Sunset Bay" : "Flush of Hearts",
    items: [],
  };
}

function state(overrides: Partial<SessionState> = {}): SessionState {
  return {
    session_id: "scene-test",
    schema_version: 26,
    seed: 42,
    day: 5,
    phase: "afternoon",
    phase_label: "Afternoon",
    turn_index: 88,
    location_id: "pool",
    location_label: "Pool",
    resort: "main",
    resort_label: "Sunset Bay",
    phase_clock: {},
    player: {
      id: "player",
      name: "You",
      gender: "woman",
      archetype_id: "loyal_friend",
      public_perception: 50,
      stats: {},
      memories: [],
    },
    heartbreakers: [heartbreaker("liam")],
    couples: [],
    audience: { public_perception: 50, recent_delta: null, trend: "steady" },
    pending_pair_proposal: null,
    pending_challenge: null,
    outcome: null,
    active_conversation_target_id: null,
    resort_snapshot: {},
    daily_recaps: [],
    intros_greetings: {},
    ...overrides,
  };
}

function turn(overrides: Partial<TurnResponse> = {}): TurnResponse {
  const nextState = overrides.state ?? state({ turn_index: 89 });
  return {
    state: nextState,
    exchange: null,
    available_actions: [action("ambient", "Wait")],
    ceremony_events: [],
    event_narration: null,
    audience_delta: null,
    audience_delta_reason: null,
    memories_formed: [],
    background_activity: [],
    state_hash: `hash-${nextState.turn_index}`,
    ...overrides,
  };
}

function heartbreaker(id: string) {
  return {
    id,
    name: id === "liam" ? "Liam" : id,
    gender: "man" as const,
    archetype: "friend",
    mood: "content",
    location_id: "pool",
    location_label: "Pool",
    eliminated: false,
    coupled: false,
    familiarity_with_player: 40,
  };
}
