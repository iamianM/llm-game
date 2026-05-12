# How To Reproduce

```bash
uv run python -m src.game.cli report packet --out review-packet/
uv run python -m src.game.cli replay --actions tests/scenarios/fixtures/day6-full-run.yaml --mock-llm
uv run python -m src.game.cli verify --all
```
