import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypeScript,
  {
    // Several scene components intentionally synchronize local animation state
    // with server turns or browser persistence. Their effects are covered by
    // the action-contract Playwright suite; the generic compiler rule cannot
    // distinguish those state machines from derived-state effects.
    rules: {
      "react-hooks/set-state-in-effect": "off"
    }
  },
  globalIgnores([
    ".next/**",
    ".next-*/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "playwright-report/**",
    "test-results/**"
  ])
]);
