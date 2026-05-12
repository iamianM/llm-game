# How To Reproduce

```bash
uv run python -m src.game.cli play --record .game_traces/manual-g8.json
uv run python -m src.game.cli play --replay .game_traces/manual-g8.json
uv run python -m src.game.cli report packet --trace .game_traces/manual-g8.json --out review-packet
uv run python -m src.game.cli verify --playthrough .game_traces/manual-g8.json
uv run python -m src.game.cli verify --all
```
