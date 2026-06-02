import { expect, test, type Page } from "@playwright/test";

const SESSION_ID = "contract-session";
const API = process.env.PLAYWRIGHT_API_BASE ?? "http://127.0.0.1:8000";

test("choice menu exposes every API action and keeps memory keys stable", async ({ page }) => {
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

test("challenge overlays use challenge titles without showing stale pairings", async ({ page }) => {
  const state = fakeState({ couples: sixCouples() });
  await installSession(page, state, [action("ambient", "Resolve challenge")]);
  await page.route(`${API}/session/turn/stream`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: [
        "event: response",
        `data: ${JSON.stringify({
          view: {
            state,
            exchange: null,
            available_actions: [],
            ceremony_events: [{ kind: "challenge", sub_kind: "kiss_wed_pass", message: "Challenge completed." }],
            event_narration: {
              prose:
                "The challenge lands with messy laughter and a few looks that last too long. " +
                "Nobody leaves certain where the line between joke and truth was meant to be.",
            },
            audience_delta: null,
            audience_delta_reason: null,
            memories_formed: [],
            background_activity: [],
            state_hash: "hash-after-challenge",
          },
          persisted: persistedEnvelope(),
        })}`,
        "",
        "",
      ].join("\n"),
    });
  });

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByRole("button", { name: "Resolve challenge" }).click();

  const ceremony = page.locator('[data-screen="ceremony"]');
  await expect(ceremony.getByRole("heading", { name: "Kiss Wed Pass" })).toBeVisible();
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

test("challenge banner keeps choices usable on a short viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 700 });
  await installSession(
    page,
    fakeState({
      pending_challenge: {
        kind: "heart_rate",
        finished: false,
        round_index: 1,
        round_count: 3,
        stem: "Whose pulse jumps when you walk past?",
        target_id: "liam",
        answered_rounds: [
          {
            round_index: 0,
            stem: "First walkout",
            chosen_label: "Liam",
            correct_label: "Liam",
            is_correct: true,
            points: 3,
            reaction_line: "Sunset Bay notices."
          }
        ]
      }
    }),
    [action("challenge_response", "Hold Liam's gaze", "liam")],
  );

  await page.goto(`/play/${SESSION_ID}`);

  await expect(page.getByTestId("challenge-banner")).toBeVisible();
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
    schema_version: 25,
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
    outcome: null,
    active_conversation_target_id: null,
    resort_snapshot: { Pool: ["You", "Liam"], Kitchen: ["Chloe"], Terrace: ["Maya"] },
    daily_recaps: [],
    ...overrides,
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
