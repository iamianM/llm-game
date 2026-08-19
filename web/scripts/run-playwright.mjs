import { spawn } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const generatedTypeFiles = ["next-env.d.ts", "tsconfig.json"].map((name) => resolve(webRoot, name));
const originals = new Map(generatedTypeFiles.map((path) => [path, readFileSync(path, "utf8")]));
const playwrightCli = resolve(webRoot, "node_modules", "@playwright", "test", "cli.js");

let result;
try {
  result = await run(process.execPath, [playwrightCli, "test", ...process.argv.slice(2)]);
} finally {
  // Next.js rewrites these files when an isolated Playwright distDir is used.
  // They are generated configuration, so return them to their pre-test state.
  for (const [path, content] of originals) {
    if (readFileSync(path, "utf8") !== content) writeFileSync(path, content, "utf8");
  }
}

if (result.signal) {
  process.kill(process.pid, result.signal);
} else {
  process.exitCode = result.code ?? 1;
}

function run(command, args) {
  return new Promise((resolveResult, reject) => {
    const child = spawn(command, args, { cwd: webRoot, env: process.env, stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", (code, signal) => resolveResult({ code, signal }));
  });
}
