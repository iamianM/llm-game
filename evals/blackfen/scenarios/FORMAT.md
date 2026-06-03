# Blackfen Eval Scenario Format

Blackfen eval scenarios are deterministic freeform-input scripts. The parser may be local/mock or LLM-backed later, but the engine owns all state changes, rolls, combat, inventory, death, and victory.

Required fields:

- `name`: stable scenario id.
- `seed`: deterministic run seed.
- `class_id`: `fighter`, `rogue`, or `mage`.
- `player_name`: display name.
- `intent`: what player experience the scenario protects.
- `actions`: freeform player inputs in order.
- `expected_hash`: final deterministic state hash.
- `expected_status`: `active`, `dead`, or `victory`.
