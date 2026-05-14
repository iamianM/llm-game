import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        card: "var(--card)",
        ink: "var(--ink)",
        accent: "var(--accent)",
        sage: "var(--sage)",
        gold: "var(--gold)",
        bad: "var(--bad)",
        line: "var(--line)"
      },
      fontFamily: {
        display: "var(--font-display)",
        body: "var(--font-body)",
        hand: "var(--font-hand)"
      }
    }
  },
  plugins: []
};

export default config;
