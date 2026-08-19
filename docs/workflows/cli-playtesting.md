# Subagent CLI Playtest Protocol

This protocol is for Codex subagents asked to play Paradise Hearts as a real
player through the CLI. The goal is to battle-test game feel and feature
coverage, not to generate a perfect deterministic fixture.

## Contract

- Prefer the persisted turn interface:
  - `uv run python -m src.game.cli play-session start --name <name> --seed 42 --record .game_traces/<name>.json`
  - `uv run python -m src.game.cli play-session resume --name <branch-name> --from-checkpoint <checkpoint> --record .game_traces/<branch-name>.json`
  - `uv run python -m src.game.cli play-session show --name <name>`
  - `uv run python -m src.game.cli play-session choose --name <name> --action <n> [--intent <n>]`
- If a true interactive terminal is available, `uv run python -m src.game.cli play` is also acceptable.
- The old autopilot mode has been removed. Drive the game through visible
  player actions using `play-session` or the interactive CLI.
- Do not use `--mock-llm` unless the caller explicitly asks for a mock run.
- Do not write a script, policy runner, action list generator, or fixture to play
  the game for you.
- Do not edit code, prompts, fixtures, docs, or content during the playtest.
- Choose actions from the visible CLI menu as a player would, based on the
  current resort state and your persona.
- Use `/state`, `/background`, `/checkpoint <name>`, and `/hash` as player-side
  inspection tools when useful.
- Record the run to `.game_traces/<descriptive-name>.json`.
- If the run gets stuck, save a checkpoint and report the exact turn, visible
  actions, and why progress is blocked.

## Checkpoint-First Workflow

Do not start a fresh full run when a checkpoint can test the change.

Use a fresh run only when validating character creation, opening coupling, day-1
intros, or a state/schema change that invalidates all existing saves. For
targeted engine and renderer fixes, branch from the closest existing checkpoint:

```bash
uv run python -m src.game.cli play-session resume \
  --name pairing-branch \
  --from-checkpoint day3-text-pairing-warning \
  --record .game_traces/pairing-branch.json
uv run python -m src.game.cli play-session show --name pairing-branch
uv run python -m src.game.cli play-session choose --name pairing-branch --action <n>
```

Save named checkpoints before major irreversible choices:

```bash
uv run python -m src.game.cli play-session checkpoint \
  --name pairing-branch \
  --checkpoint before-day3-pairing
```

When reporting, distinguish:

- `fresh run` — started from character creation.
- `checkpoint branch` — resumed from a saved state and ran only the relevant
  turns.

Prefer checkpoint branches for regression confirmation. A full fresh run is a
release-level validation, not the default debugging loop.

## Default Persona

Use this persona unless the caller provides another one:

- Gender: man
- Archetype: loyal friend
- Core goal: build one convincing primary couple while still learning Sunset Bay.
- Style: emotionally intelligent, curious, not passive.
- Risk appetite: take medium risks when the situation supports them; take at
  least a few high-risk actions to test balance.
- Social coverage: do not tunnel on one heartbreaker. Meet everyone, move locations,
  ask gossip when it appears, and check background activity.
- Romance coverage: build a main connection, but test at least one private chat with
  someone who is busy or in another conversation.

## Coverage Goals

Try to hit as many as possible without forcing nonsense:

- Complete character creation.
- Complete Day-1 opening coupling.
- Complete all Day-1 intros with varied dynamics, not all Friendly.
- Use at least three different ambient actions.
- Move through at least three locations.
- Start conversations with at least four different Heartbreakers.
- Use at least one Friendly, Flirty, Deep, Banter, Bromance, or Gossip Ring option
  where available and contextually appropriate.
- Pick at least one gossip option if it surfaces.
- Trigger or attempt at least one private-chat situation.
- Respond to interruption options if they appear.
- Let at least one phase expire naturally through time budget.
- Use `/background` at least once after background conversations have happened.
- Save at least two checkpoints: one after Day-1 intros and one before a major
  ceremony or Flush of Hearts decision.
- Reach at least Day 3. Prefer a full run to finale if the game remains healthy.

## Reporting Back

Return:

- Trace path.
- Checkpoint paths created.
- Final day/phase/outcome.
- Features hit and missed.
- Three strongest game-feel positives.
- Three concrete problems observed.
- Any exact turn numbers worth reviewing.
- Packet generation command to run next, or generate the packet if asked.

Do not summarize raw JSON. Report player-facing observations.
