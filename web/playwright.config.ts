import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://127.0.0.1:3210",
    trace: "retain-on-failure"
  },
  webServer: [
    {
      command: "cd .. && uv run python -m uvicorn src.api.app:app --port 8000",
      url: "http://127.0.0.1:8000/healthz",
      reuseExistingServer: true,
      env: { PARADISE_MOCK_LLM: "1" },
      timeout: 120_000
    },
    {
      command: "powershell -NoProfile -ExecutionPolicy Bypass -Command \"$env:NEXT_DIST_DIR='.next-playwright'; npm run dev -- --hostname 127.0.0.1 --port 3210\"",
      url: "http://127.0.0.1:3210",
      reuseExistingServer: true,
      timeout: 120_000
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } }
    },
    {
      name: "chromium-small",
      testMatch: /no-scroll|title|new-run|rail-popouts|settings/,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 720 } }
    },
    {
      name: "mobile",
      testMatch: /no-scroll|title|new-run|mobile/,
      use: { ...devices["Pixel 7"] }
    },
    {
      name: "golden",
      testDir: "./tests/golden",
      timeout: 600_000,
      use: { ...devices["Desktop Chrome"], viewport: { width: 1600, height: 900 } }
    }
  ]
});
