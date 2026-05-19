# Balance Data Format

Files in this folder are deterministic mechanical tuning data, not narrator-facing content.

Allowed here:

- relationship deltas
- unlock thresholds
- stat references
- risk levels
- deterministic weights or schedules

Not allowed here:

- prose for the player or narrator
- formulas or branching logic
- prompt text
- free-form rules that require interpretation outside the Python engine

Every file must be loaded through a Pydantic model and interpreted only by `src/game/engine/`.
