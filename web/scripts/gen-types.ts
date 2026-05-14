import { execFileSync } from "node:child_process";

execFileSync("npx", ["openapi-typescript", "http://127.0.0.1:8000/openapi.json", "-o", "lib/openapi-types.ts"], {
  stdio: "inherit",
  shell: process.platform === "win32"
});
