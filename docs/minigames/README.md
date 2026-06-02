# Per-Minigame Specs

This folder contains one implementation spec per Paradise Hearts daily
challenge. Every spec extends the shared contract in
[../minigame-system.md](../minigame-system.md) — read that first.

The specs are the source of truth for **how the minigame is currently
implemented** (present tense once shipped) and **what acceptance evidence
is required to merge**. Design intent for each challenge lives in
[../../12-Challenges-And-Events.md](../../12-Challenges-And-Events.md); the
specs translate that intent into engine, agent, content, and UI work.

| Day | Engine kind | Player-facing name | Spec | Rollout step |
|---|---|---|---|---|
| 1 | `compatibility_quiz` | Compatibility Quiz | [compatibility-quiz.md](compatibility-quiz.md) | 1 |
| 2 | `heart_rate` | Pulse Race | [heart-rate.md](heart-rate.md) | 4 |
| 3 | `couples_quiz` | The Couples Quiz | [couples-quiz.md](couples-quiz.md) | 2 |
| 4 | `lie_detector` | Lie Detector | [lie-detector.md](lie-detector.md) | 3 |
| 5 | `kiss_wed_pass` | Kiss Wed Pass | [kiss-wed-pass.md](kiss-wed-pass.md) | 5 |
| 6 | `final_couples` | Final Couples Challenge | [final-couples.md](final-couples.md) | 6 |

Rollout order is set by the shared system doc (§11). Compatibility Quiz
proves the harness; the others reuse it.
