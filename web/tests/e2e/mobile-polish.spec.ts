import { expect, test, type Page } from "@playwright/test";

const SESSION_ID = "mobile-polish-session";
const API = "http://127.0.0.1:8000";

test("mobile right rail opens as a full-width drawer", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 740 });
  await installSession(page, fakeState(), [action("ambient", "Let the villa breathe")]);

  await page.goto(`/play/${SESSION_ID}`);
  await page.getByLabel("Open right rail").click();

  const rail = page.locator("aside").first();
  await expect(page.getByText("Field Report")).toBeVisible();
  const box = await rail.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(Math.round(box!.x)).toBe(0);
  expect(Math.round(box!.width)).toBeLessThanOrEqual(viewport!.width);
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
