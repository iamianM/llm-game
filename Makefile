.PHONY: install test test-fast lint type-check content-lint scenarios smoke determinism qa play verify verify-script smoke-real-llm test-llm

install:
	uv sync --extra dev

test:
	uv run pytest -m "not llm" -n auto

test-fast:
	uv run pytest tests/engine -m "not llm" -n auto

lint:
	uv run ruff check .

type-check:
	uv run mypy src/game/state src/game/engine src/game/content

content-lint:
	uv run python -m src.game.cli content lint

scenarios:
	uv run pytest tests/scenarios

smoke:
	uv run python -m src.game.cli verify-script --seed 1 --actions tests/scenarios/fixtures/day1-happy-path.yaml --mock-llm --exit-on-end

determinism:
	uv run python -m src.game.cli verify --all

qa: lint type-check content-lint test smoke determinism

play:
	uv run python -m src.game.cli play

verify:
	uv run python -m src.game.cli verify --all

verify-script:
	uv run python -m src.game.cli verify-script

test-llm:
	uv run pytest -m llm

smoke-real-llm:
	uv run python -m src.game.cli play --record .game_traces/manual-real-g8.json
