# Action Script Fixture Format

Action scripts describe deterministic player inputs for replay and scenario tests.

Scripts should be paired with a seed or a snapshot. Prefer snapshot-paired scripts when NPC names or generated cast details matter.

Future YAML shape:

```yaml
name: day1-happy-path
seed: 1
actions:
  - kind: start_conversation
    target_id: chloe
    intent_id: friendly_chat_villa
  - kind: advance_phase
```
