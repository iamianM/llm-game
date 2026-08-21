# Replay and Review

Paradise Hearts treats reproducibility as part of the game architecture. A
playthrough is not merely a transcript: it is a sequence of actions,
deterministic state transitions, recorded agent contributions, and hashes that
can be executed again through the production turn path.

## Why Replay Is Different in an LLM Game

Seeded RNG is sufficient for deterministic mechanics, but not for generated
dialogue. Repeating a live model request can produce different prose and can
make a later turn observe different text. Paradise Hearts therefore records
the typed agent commits that affected the turn and reuses those commits during
replay. The model is not called again.

## Trace Contract

Each recorded turn contains the evidence needed to inspect and reproduce it:

- player action and canonical action kind;
- input and output state hashes;
- deterministic `MechanicalResult`;
- dialogue exchange, event narration, and contextual follow-up menu;
- ceremony, audience, challenge, producer, and group-event output;
- typed agent commits and diagnostic agent traces;
- visible state, resort snapshot, known preferences, and review bookmarks.

The recording package also contains the initial seed and character-creation
choices, final canonical state, final hash, LLM mode, and optional branch or
persona metadata.

## Replay Algorithm

`play --replay` reconstructs the starting game from the recorded seed and
character creation. For every recorded turn it:

1. verifies that the reconstructed state matches the recorded input hash;
2. supplies the recorded agent commits through `RecordedAgents`;
3. executes the original action through `run_turn`;
4. verifies the resulting output hash; and
5. finally verifies the recording's final state hash.

A mismatch fails loudly and identifies the turn. Replay is consequently useful
for engine regressions, state-schema migrations, agent-boundary changes, and
"only happened once" narrative bugs.

```bash
uv run python -m src.game.cli play --replay .game_traces/<trace>.json
uv run python -m src.game.cli trace inspect .game_traces/<trace>.json
uv run python -m src.game.cli verify --playthrough .game_traces/<trace>.json
```

## Checkpoints and Branches

A checkpoint stores canonical game state and the seeded RNG snapshot. Resuming
from it restores the exact decision point. A branch name labels the new trace
without changing engine behavior.

```bash
uv run python -m src.game.cli play --from-checkpoint <checkpoint> --branch-name <name>
uv run python -m src.game.cli play-session resume --name <session> --from-checkpoint <checkpoint>
```

Two traces from one checkpoint can be rendered as a comparison report:

```bash
uv run python -m src.game.cli report compare \
  --checkpoint <checkpoint> \
  --trace-a <trace-a> \
  --trace-b <trace-b> \
  --out <comparison.html>
```

The report makes relationship, audience, state, and story consequences visible
side by side. This supports deliberate narrative design: reviewers can compare
two choices from identical initial conditions instead of relying on separate
runs that quietly diverged earlier.

## Review Packets

`report packet` turns a trace into a portable static review surface. A packet
contains the rendered session, playthrough evaluation, final state, raw trace,
review notes, and reproduction instructions.

```bash
uv run python -m src.game.cli report packet \
  --trace .game_traces/<trace>.json \
  --out review-packet/<name>
```

Review bookmarks attach noteworthy beats to trace turns. The interactive CLI's
`review` and persisted `play-session` surfaces let a playtester keep the
evidence and the human observation together.

## Boundaries

- Replay proves that recorded inputs still produce recorded state. It does not
  claim that a new live LLM call would return identical prose.
- A passing replay proves determinism and compatibility, not narrative quality.
- Golden LLM scenarios cover expected agent behavior; see
  [`llm-evals.md`](llm-evals.md).
- Local trace and save directories are development artifacts and are not a
  production persistence design.
