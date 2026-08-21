import { expect, test, type Page } from "@playwright/test";

const SESSION_ID = "contract-session";
const API = process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8000";

test("scene action fan exposes every API action and keeps memory keys stable", async ({ page }) => {
  const consoleIssues: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "warning" || message.type() === "error") {
      consoleIssues.push(message.text());
    }
  });
  await installSession(page, fakeState(), manyActions(8));

  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("choice-fan")).toBeVisible();
  await expect(page.getByTestId("choice")).toHaveCount(8);
  await expect(page.getByRole("button", { name: "Choice eight" })).toBeVisible();
  expect(consoleIssues).toEqual([]);
});

test("long ceremony overlays keep Continue visible and clickable", async ({ page }) => {
  const state = fakeState({ couples: sixCouples() });
  await installSession(page, state, [action("ambient", "Trigger ceremony")]);
  await page.route(`${API}/session/turn/stream`, async (route) => {
    const turn = {
      view: {
        state,
        exchange: null,
        available_actions: [],
        ceremony_events: [{ kind: "pairing", message: "Pairing ceremony completed." }],
        event_narration: {
          prose:
            "The flame_deck fills with held breath as every choice lands in public. " +
            "Couples settle, doubts surface, and Sunset Bay feels sharper than it did an hour ago.",
        },
        audience_delta: null,
        audience_delta_reason: null,
        memories_formed: [],
        background_activity: [],
        state_hash: "hash-after-ceremony",
      },
      persisted: persistedEnvelope(),
    };
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        "event: response",
        `data: ${JSON.stringify(turn)}`,
        "",
        "event: turn_end",
        'data: {"state_hash":"hash-after-ceremony"}',
        "",
        "",
      ].join("\n"),
    });
  });

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Trigger ceremony" }).click();

  const ceremony = page.locator('[data-screen="ceremony"]');
  await expect(ceremony).toBeVisible();
  const continueButton = ceremony.getByRole("button", { name: "Continue" });
  await expect(continueButton).toBeVisible();
  const box = await continueButton.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.y + box!.height).toBeLessThanOrEqual(900);
  await continueButton.click();
  await expect(ceremony).toHaveCount(0);
});

test("feature queue shows ceremony before the new day recap", async ({ page }) => {
  const initial = fakeState({ daily_recaps: [] });
  const recap = {
    day: 5,
    resort_id: "flush_of_hearts",
    resort_label: "Flush of Hearts",
    items: [{
      section: "your_day",
      speaker_label: "You",
      content: "You noticed the resort shift.",
      emphasis: "standard",
    }],
  };
  const next = fakeState({ day: 6, turn_index: 89, daily_recaps: [recap] });
  await installSession(page, initial, [action("ambient", "Close the day")]);
  await page.route(`${API}/session/turn/stream`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        "event: response",
        `data: ${JSON.stringify({
          view: {
            state: next,
            exchange: null,
            available_actions: [],
            ceremony_events: [{ kind: "pairing", message: "The couples lock in." }],
            event_narration: { prose: "The night settles around the new couples." },
            audience_delta: null,
            audience_delta_reason: null,
            memories_formed: [],
            background_activity: [],
            state_hash: "feature-order-hash",
          },
          persisted: persistedEnvelope(),
        })}`,
        "",
        "",
      ].join("\n"),
    });
  });

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Close the day" }).click();

  const ceremony = page.locator('[data-screen="ceremony"]');
  await expect(ceremony).toBeVisible();
  await expect(page.locator('[data-screen="day-recap"]')).toHaveCount(0);
  await ceremony.getByRole("button", { name: "Continue" }).click();
  const dayRecap = page.locator('[data-screen="day-recap"]');
  await expect(dayRecap).toBeVisible();
  await expect(dayRecap).toContainText("You noticed the resort shift.");
  await dayRecap.getByRole("button", { name: "Continue" }).click();
  await expect(dayRecap).toHaveCount(0);
});

test("initial session view does not replay historical recaps", async ({ page }) => {
  await installSession(
    page,
    fakeState({
      daily_recaps: [{
        day: 4,
        resort_id: "flush_of_hearts",
        resort_label: "Flush of Hearts",
        items: [{
          section: "your_day",
          speaker_label: "You",
          content: "Old news.",
          emphasis: "standard",
        }],
      }],
    }),
    [action("ambient", "Stay present")],
  );

  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByRole("button", { name: "Stay present" })).toBeVisible();
  await expect(page.locator('[data-screen="day-recap"]')).toHaveCount(0);
});

test("minigame inserts use challenge titles without showing stale pairings", async ({ page }) => {
  const state = fakeState({
    couples: sixCouples(),
    pending_challenge: minigameWrap("kiss_wed_pass", {
      kind: "kiss_wed_pass",
      allocations: [
        { role: "kiss", subject_id: "liam" },
        { role: "wed", subject_id: "chloe" },
        { role: "pass", subject_id: "maya" },
      ],
    }),
  });
  await installSession(page, state, []);

  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("minigame-insert").getByRole("heading", { name: "Kiss Wed Pass" })).toBeVisible();
  await expect(page.getByTestId("pairing-list")).toHaveCount(0);
});

test("public first screens do not expose development controls", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("MVP build")).toHaveCount(0);
  await expect(page.getByText("Phase 4")).toHaveCount(0);

  await page.goto("/new-run");
  await expect(page.getByText("Test mode")).toHaveCount(0);
  await expect(page.getByText("Real mode")).toHaveCount(0);
});

test("compact minigame insert keeps choices usable on a short viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await installSession(
    page,
    fakeState({
      pending_challenge: {
        status: "round",
        kind: "heart_rate",
        round_index: 1,
        round_count: 3,
        narration: "",
        question: "Whose pulse jumps when you walk past?",
        target_id: "liam",
        answered_rounds: [
          {
            round_index: 0,
            chosen_label: "Liam",
            correct_label: "Liam",
            is_correct: true,
            points: 3,
            reaction_line: "Sunset Bay notices."
          }
        ],
        board: { kind: "heart_rate", readings: [] },
      }
    }),
    [action("challenge_response", "Hold Liam's gaze", "liam")],
  );

  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("minigame-insert")).toBeVisible();
  for (let attempt = 0; attempt < 8 && (await page.getByTestId("choice-fan").count()) === 0; attempt += 1) {
    await page.evaluate(() => window.dispatchEvent(new CustomEvent("paradise:reveal-all")));
    await page.getByTestId("scene-stage").click({ position: { x: 190, y: 320 }, force: true });
    await page.waitForTimeout(100);
  }
  await expect(page.getByTestId("choice-fan")).toBeVisible();
  await expect(page.getByRole("button", { name: "Hold Liam's gaze" })).toBeVisible();
});

test("finale screen avoids placeholder copy", async ({ page }) => {
  await installSession(page, fakeState({ outcome: "runner_up_couple" }), []);

  await page.goto(`/play/${SESSION_ID}/finale`);

  await expect(page.getByRole("heading", { name: "You made the final two" })).toBeVisible();
  await expect(page.getByText("next build")).toHaveCount(0);
  await expect(page.getByText("Phase 4")).toHaveCount(0);
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

function manyActions(count: number) {
  return Array.from({ length: count }, (_, index) => action("ambient", `Choice ${numberWord(index + 1)}`, `choice-${index}`));
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
    schema_version: 30,
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
      public_perception: 100,
      stats: { charm: 6, banter: 6, eq: 6, spark: 6, loyalty: 9 },
      memories: [
        memory("mem-one", "liam", 12),
        memory("mem-two", "liam", 12),
      ],
    },
    heartbreakers: [
      heartbreaker("liam", "Liam", "man"),
      heartbreaker("chloe", "Chloe", "woman"),
      heartbreaker("maya", "Maya", "woman"),
      heartbreaker("marcus", "Marcus", "man"),
      heartbreaker("beau", "Beau", "man"),
      heartbreaker("zara", "Zara", "woman"),
    ],
    couples: [],
    audience: { public_perception: 100, recent_delta: null, trend: "steady" },
    pending_pair_proposal: null,
    pending_challenge: null,
    outcome: null,
    active_conversation_target_id: null,
    resort_snapshot: { Pool: ["You", "Liam"], Kitchen: ["Chloe"], Terrace: ["Maya"] },
    daily_recaps: [],
    ...overrides,
  };
}

function minigameWrap(kind: string, board: Record<string, unknown>) {
  return {
    status: "wrap",
    kind,
    round_count: 3,
    narration: "The result is locked.",
    classification: "success",
    total_points: 8,
    audience_delta: 3,
    answered_rounds: [],
    board,
  };
}

function heartbreaker(id: string, name: string, gender: "man" | "woman") {
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

function memory(id: string, subjectId: string, turn: number) {
  return {
    id,
    holder_id: "player",
    subject_id: subjectId,
    content: "A tense chat stayed with you.",
    emotional_weight: 5,
    source: "direct",
    tags: ["direct"],
    formed_on_turn: turn,
  };
}

function sixCouples() {
  const pairs = [
    ["player", "liam", "You", "Liam", true],
    ["marcus", "chloe", "Marcus", "Chloe", false],
    ["beau", "zara", "Beau", "Zara", false],
    ["jordan", "maya", "Jordan", "Maya", false],
    ["blake", "nia", "Blake", "Nia", false],
    ["mateo", "sasha", "Mateo", "Sasha", false],
  ] as const;
  return pairs.map(([aId, bId, aName, bName, isPlayer], index) => ({
    partner_a_id: aId,
    partner_b_id: bId,
    partner_a_name: aName,
    partner_b_name: bName,
    strength: 70 - index,
    formed_on_day: 5,
    formed_via: "ceremony",
    formed_via_label: "Pairing Ceremony",
    rebound: false,
    is_player_couple: isPlayer,
  }));
}

function numberWord(value: number) {
  return ["one", "two", "three", "four", "five", "six", "seven", "eight"][value - 1] ?? String(value);
}
