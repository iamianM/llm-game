import { defineConfig, devices } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

type RuntimeConfig = {
  runId: string;
  apiPort: number;
  uiPort: number;
  nextDistDir: string;
  slot: number;
};

const runtime = loadRuntimeConfig();
const { apiPort, uiPort, nextDistDir } = runtime;
const apiURL = `http://127.0.0.1:${apiPort}`;
const uiURL = `http://127.0.0.1:${uiPort}`;

process.env.PLAYWRIGHT_API_BASE = apiURL;
process.env.NEXT_PUBLIC_API_BASE = apiURL;

function loadRuntimeConfig(): RuntimeConfig {
  const runtimeDir = resolve(".playwright-runtime");
  mkdirSync(runtimeDir, { recursive: true });
  const runId = process.env.PLAYWRIGHT_RUN_ID || playwrightRootPid();
  const runtimePath = resolve(runtimeDir, `${runId}.json`);
  if (existsSync(runtimePath)) {
    return JSON.parse(readFileSync(runtimePath, "utf8")) as RuntimeConfig;
  }
  const slot = allocateSlot(runtimeDir, runId);
  const config: RuntimeConfig = {
    runId,
    apiPort: envPort("PLAYWRIGHT_API_PORT") ?? pickAvailablePort(),
    uiPort: envPort("PLAYWRIGHT_WEB_PORT") ?? pickAvailablePort(),
    nextDistDir: process.env.PLAYWRIGHT_NEXT_DIST_DIR ?? `.next-playwright-${slot}`,
    slot,
  };
  writeFileSync(runtimePath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
  return config;
}

function allocateSlot(runtimeDir: string, runId: string) {
  for (let slot = 0; slot < 16; slot += 1) {
    const lockDir = resolve(runtimeDir, `slot-${slot}.lock`);
    try {
      mkdirSync(lockDir);
      writeFileSync(resolve(lockDir, "owner.json"), `${JSON.stringify({ runId, pid: Number(runId) || process.pid })}\n`, "utf8");
      return slot;
    } catch {
      if (slotIsStale(lockDir)) {
        rmSync(lockDir, { recursive: true, force: true });
        slot -= 1;
      }
    }
  }
  throw new Error("No free Playwright Next.js dist slot is available.");
}

function slotIsStale(lockDir: string) {
  try {
    const ageMs = Date.now() - statSync(lockDir).mtimeMs;
    if (ageMs < 6 * 60 * 60 * 1000) return false;
    const owner = JSON.parse(readFileSync(resolve(lockDir, "owner.json"), "utf8")) as { pid?: number };
    if (!owner.pid) return true;
    return !processIsAlive(owner.pid);
  } catch {
    return true;
  }
}

function processIsAlive(pid: number) {
  const script = `if (Get-Process -Id ${pid} -ErrorAction SilentlyContinue) { Write-Output 1 }`;
  const output = execFileSync("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], {
    encoding: "utf8",
  }).trim();
  return output === "1";
}

function envPort(name: string) {
  const value = process.env[name];
  if (!value) return null;
  const port = Number(value);
  return Number.isInteger(port) && port > 0 && port < 65_536 ? port : null;
}

function pickAvailablePort() {
  const script = [
    "$listener = [System.Net.Sockets.TcpListener]::new([Net.IPAddress]::Parse('127.0.0.1'), 0)",
    "$listener.Start()",
    "$port = $listener.LocalEndpoint.Port",
    "$listener.Stop()",
    "Write-Output $port",
  ].join("; ");
  const output = execFileSync("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], {
    encoding: "utf8",
  }).trim();
  const port = Number(output);
  if (!Number.isInteger(port) || port <= 0 || port >= 65_536) {
    throw new Error(`Playwright could not allocate a valid local port: ${output || String(port)}`);
  }
  return port;
}

function playwrightRootPid() {
  const script = `
$pidValue = ${process.pid}
$root = $pidValue
while ($pidValue -and $pidValue -gt 0) {
  $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue"
  if (-not $proc) { break }
  if ($proc.CommandLine -match '@playwright\\\\test\\\\cli\\.js' -or $proc.CommandLine -match '@playwright/test/cli\\.js') {
    $root = $proc.ProcessId
    break
  }
  $pidValue = $proc.ParentProcessId
}
Write-Output $root
`;
  const output = execFileSync("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], {
    encoding: "utf8",
  }).trim();
  return output || String(process.pid);
}

export default defineConfig({
  testDir: "./tests",
  outputDir: `.playwright-results/${runtime.runId}`,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: uiURL,
    trace: "retain-on-failure"
  },
  webServer: [
    {
      command: `cd .. && uv run python -m uvicorn src.api.app:app --host 127.0.0.1 --port ${apiPort}`,
      url: `${apiURL}/healthz`,
      reuseExistingServer: false,
      env: { PARADISE_MOCK_LLM: "1" },
      timeout: 120_000
    },
    {
      command: `powershell -NoProfile -ExecutionPolicy Bypass -Command "$env:NEXT_DIST_DIR='${nextDistDir}'; $env:NEXT_PUBLIC_API_BASE='${apiURL}'; npm run dev -- --hostname 127.0.0.1 --port ${uiPort}"`,
      url: uiURL,
      reuseExistingServer: false,
      timeout: 120_000
    }
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], baseURL: uiURL, viewport: { width: 1440, height: 900 } }
    },
    {
      name: "chromium-small",
      testMatch: /no-scroll|title|new-run|rail-popouts|settings/,
      use: { ...devices["Desktop Chrome"], baseURL: uiURL, viewport: { width: 1280, height: 720 } }
    },
    {
      name: "mobile",
      testMatch: /no-scroll|title|new-run|mobile|scene-dialogue/,
      use: { ...devices["Pixel 7"], baseURL: uiURL }
    },
    {
      name: "golden",
      testDir: "./tests/golden",
      timeout: 600_000,
      use: { ...devices["Desktop Chrome"], baseURL: uiURL, viewport: { width: 1600, height: 900 } }
    }
  ]
});
