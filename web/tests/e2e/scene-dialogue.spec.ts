import { expect, test, type Page } from "@playwright/test";

const SESSION_ID = "scene-dialogue-session";
const API = process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8000";

test("idle scene shows player and all present NPCs", async ({ page }) => {
  const state = fakeState();
  await installSession(page, state, [action("ambient", "Let the villa breathe")]);
  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("scene-stage")).toBeVisible();
  await expect(page.getByTestId("character-sprite")).toHaveCount(state.islanders.length + 1);
  await expect(page.locator('[data-testid="character-sprite"][data-role="player"][data-position="bottom"]')).toBeVisible();
});

test("NPC speaks with a bubble anchored to that NPC", async ({ page }) => {
  await installSession(page, fakeState({ active_conversation_target_id: "liam" }), [action("flirt", "Ask Liam where his head is", "liam")]);
  await routeTurn(page, fakeTurn({ exchange: exchange("liam", "Liam", "Ask Liam where his head is", "I was hoping you would ask. My head is very much here, with you.") }));

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Ask Liam where his head is" }).click();
  await expect(page.getByTestId("player-bubble")).toBeVisible();
  await page.getByTestId("scene-stage").click();

  const bubble = page.getByTestId("speech-bubble");
  await expect(bubble).toHaveAttribute("data-anchor-id", "liam");
  const bubbleBox = await bubble.boundingBox();
  const npcBox = await page.locator('[data-character-id="liam"]').boundingBox();
  expect(bubbleBox).not.toBeNull();
  expect(npcBox).not.toBeNull();
  expect(bubbleBox!.y).toBeLessThan(npcBox!.y + npcBox!.height * 0.45);
});

test("conversation keeps every co-located islander on stage, not just the partner", async ({ page }) => {
  // Regression guard for Casa-Amor embodiment: when the player is mid-chat the
  // focused partner is emphasized, but the rest of the room must stay visible
  // (dimmed, not yanked off-stage) so the player is never talking to an empty
  // pool. All three fakeState islanders share the player's location.
  const state = fakeState({ active_conversation_target_id: "liam" });
  await installSession(page, state, [
    action("flirt", "Tease Liam", "liam"),
    action("end_conversation", "Step away", "liam"),
  ]);
  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("scene-stage")).toBeVisible();
  // The conversation partner is present...
  await expect(page.locator('[data-character-id="liam"]')).toBeVisible();
  // ...and so is the rest of the co-located cast plus the player.
  await expect(page.getByTestId("character-sprite")).toHaveCount(state.islanders.length + 1);
});

test("narrator beat uses a top narrator bubble", async ({ page }) => {
  await installSession(page, fakeState(), [action("ambient", "Trigger text")]);
  await routeTurn(page, fakeTurn({ event_narration: { prose: "A text lands and the villa freezes for the kind of silence producers dream about." } }));

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Trigger text" }).click();

  const narrator = page.getByTestId("narrator-bubble");
  await expect(narrator).toBeVisible();
  await expect(page.getByTestId("speech-bubble")).toHaveCount(0);
  const box = await narrator.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y).toBeLessThan(120);
});

test("tap anywhere advances a long bubble", async ({ page }) => {
  await installSession(page, fakeState({ active_conversation_target_id: "liam" }), [action("chat", "Open up to Liam", "liam")]);
  await routeTurn(page, fakeTurn({
    exchange: exchange(
      "liam",
      "Liam",
      "Open up to Liam",
      "I like that you are not treating this place like a scoreboard. It makes me feel like I can breathe for a second. But I am also scared because every good conversation in this villa turns into a headline by breakfast. So if we are doing this, I need it to be honest."
    ),
  }));

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Open up to Liam" }).click();
  await expect(page.getByTestId("player-bubble")).toBeVisible();
  await page.getByTestId("scene-stage").click();
  const first = await page.getByTestId("speech-bubble").textContent();
  await page.getByTestId("scene-stage").click();
  const second = await page.getByTestId("speech-bubble").textContent();
  expect(second).not.toEqual(first);
});

test("choice fan appears near the player", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installSession(page, fakeState(), [action("ambient", "Choice one"), action("ambient", "Choice two")]);
  await page.goto(`/play/${SESSION_ID}`);

  const player = await page.locator('[data-role="player"]').boundingBox();
  const fan = await page.getByTestId("choice-fan").boundingBox();
  expect(player).not.toBeNull();
  expect(fan).not.toBeNull();
  const playerCenter = player!.x + player!.width / 2;
  const fanCenter = fan!.x + fan!.width / 2;
  expect(Math.abs(playerCenter - fanCenter)).toBeLessThan(390 * 0.4);
});

test("selecting a choice shows the player bubble then NPC reaction", async ({ page }) => {
  await installSession(page, fakeState({ active_conversation_target_id: "liam" }), [action("chat", "Tell Liam the truth", "liam")]);
  await routeTurn(page, fakeTurn({ audience_delta: 4, exchange: exchange("liam", "Liam", "Tell Liam the truth", "That is exactly what I needed to hear.") }));

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Tell Liam the truth" }).click();
  await expect(page.getByTestId("player-bubble")).toBeVisible({ timeout: 1000 });
  await page.getByTestId("scene-stage").click();
  await expect(page.locator('[data-character-id="liam"][data-pose="talking"]')).toBeVisible({ timeout: 1500 });
});

test("pulse race opening cutscene changes an NPC pose", async ({ page }) => {
  await installSession(page, fakeState({ phase: "challenge", pending_challenge: { kind: "heart_rate", round_index: 0, round_count: 3, stem: "Whose pulse jumps?", finished: false } }), [action("challenge_response", "Pick Liam", "liam")]);
  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("scene-minigame-board")).toBeVisible();
  await expect(page.locator('[data-pose="exiting"]').first()).toBeVisible({ timeout: 1500 });
});

test("compat quiz keeps player visible during round", async ({ page }) => {
  await installSession(page, fakeState({ phase: "challenge", pending_challenge: { kind: "compatibility_quiz", round_index: 0, round_count: 3, stem: "What does Liam value?", finished: false } }), [action("challenge_response", "Honesty", "liam")]);
  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("scene-minigame-board")).toBeVisible();
  await expect(page.locator('[data-role="player"][data-position="bottom"]')).toBeVisible();
});

test("mobile portrait has no horizontal scroll", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installSession(page, fakeState(), [action("ambient", "Let it breathe")]);
  await page.goto(`/play/${SESSION_ID}`);

  const overflow = await page.evaluate(() => document.body.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("desktop scene scales with player bottom-center", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === "mobile", "desktop geometry is covered by desktop projects");
  await page.setViewportSize({ width: 1280, height: 800 });
  await installSession(page, fakeState(), [action("ambient", "Let it breathe")]);
  await page.goto(`/play/${SESSION_ID}`);

  const box = await page.locator('[data-role="player"]').boundingBox();
  expect(box).not.toBeNull();
  const center = box!.x + box!.width / 2;
  expect(Math.abs(center - 640)).toBeLessThan(64);
});

test("reduced motion keeps focus changes fast", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await installSession(page, fakeState({ active_conversation_target_id: "liam" }), [action("chat", "Talk to Liam", "liam")]);
  await routeTurn(page, fakeTurn({ exchange: exchange("liam", "Liam", "Talk to Liam", "Fast focus check.") }));

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Talk to Liam" }).click();
  await expect(page.locator('[data-role="player"]')).toBeVisible();
  await page.waitForTimeout(100);
  await expect(page.getByTestId("player-bubble")).toBeVisible();
});

async function installSession(page: Page, state: Record<string, unknown>, actions: Array<Record<string, unknown>>) {
  await page.addInitScript(
    ({ sessionId, persisted }) => {
      window.localStorage.setItem(`paradise.session.${sessionId}`, JSON.stringify(persisted));
      window.localStorage.setItem("paradise.currentSessionId", sessionId);
    },
    { sessionId: SESSION_ID, persisted: persistedEnvelope() },
  );
  await page.route(`${API}/session/view`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ session_id: SESSION_ID, state, available_actions: actions }),
    });
  });
}

async function routeTurn(page: Page, turn: Record<string, unknown>) {
  await page.route(`${API}/session/turn/stream`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        "event: response",
        `data: ${JSON.stringify({ view: turn, persisted: persistedEnvelope() })}`,
        "",
        'event: turn_end',
        'data: {"state_hash":"scene-hash"}',
        "",
        "",
      ].join("\n"),
    });
  });
}

function persistedEnvelope() {
  return {
    schema_version: 1,
    session_id: SESSION_ID,
    user_id: null,
    rng_state: [],
    game_state: {},
    mock_llm: true,
  };
}

function fakeTurn(overrides: Record<string, unknown>) {
  return {
    state: fakeState(),
    exchange: null,
    available_actions: [action("ambient", "Let the villa breathe")],
    ceremony_events: [],
    event_narration: null,
    audience_delta: null,
    audience_delta_reason: null,
    memories_formed: [],
    background_activity: [],
    state_hash: "scene-hash",
    ...overrides,
  };
}

function exchange(speakerId: string, speakerName: string, playerDialogue: string, npcDialogue: string) {
  return {
    speaker_id: speakerId,
    speaker_name: speakerName,
    player_dialogue: playerDialogue,
    npc_dialogue: npcDialogue,
    npc_tone: "warm",
    npc_mood_after: "warm",
  };
}

function action(kind: string, label: string, target = "ambient_wait") {
  return {
    kind,
    label,
    target_id: target,
    intent_id: null,
    option_index: null,
    audience_hint: "",
    risk: null,
    stat_used: null,
    description: null,
  };
}

function fakeState(overrides: Record<string, unknown> = {}) {
  return {
    session_id: SESSION_ID,
    schema_version: 26,
    seed: 42,
    day: 5,
    phase: "afternoon",
    phase_label: "Afternoon",
    turn_index: 88,
    location_id: "pool",
    location_label: "Pool",
    villa: "main",
    villa_label: "Sunset Bay",
    phase_clock: {},
    player: {
      id: "player",
      name: "You",
      gender: "woman",
      archetype_id: "loyal_friend",
      public_perception: 100,
      stats: { charm: 6, banter: 6, eq: 6, graft: 6, loyalty: 9 },
      memories: [],
    },
    islanders: [
      islander("liam", "Liam", "man"),
      islander("chloe", "Chloe", "woman"),
      islander("maya", "Maya", "woman"),
    ],
    couples: [],
    audience: { public_perception: 100, recent_delta: null, trend: "steady" },
    pending_recouple_proposal: null,
    outcome: null,
    active_conversation_target_id: null,
    villa_snapshot: { Pool: ["You", "Liam"], Kitchen: ["Chloe"], Terrace: ["Maya"] },
    daily_recaps: [],
    ...overrides,
  };
}

function islander(id: string, name: string, gender: "man" | "woman") {
  return {
    id,
    name,
    gender,
    archetype: "friend",
    mood: "content",
    location_id: "pool",
    location_label: "Pool",
    eliminated: false,
    coupled: false,
    familiarity_with_player: 40,
  };
}
