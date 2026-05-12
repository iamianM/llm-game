.PHONY: install test lint type-check content-lint scenarios smoke determinism qa play replay verify simulate test-llm codegen

install:
	uv sync --extra dev

test:
	uv run pytest -m "not llm"

lint:
	uv run ruff check .

type-check:
	uv run mypy src/game/state src/game/engine src/game/content

content-lint:
	uv run python -m src.game.cli content lint

scenarios:
	uv run pytest tests/scenarios

smoke:
	uv run python -m src.game.cli replay --seed 1 --actions tests/scenarios/fixtures/day1-happy-path.yaml --mock-llm --exit-on-end

determinism:
	uv run python -m src.game.cli verify --all

qa: lint type-check content-lint test smoke determinism

play:
	uv run python -m src.game.cli play

replay:
	uv run python -m src.game.cli replay

verify:
	uv run python -m src.game.cli verify --all

simulate:
	uv run python -m src.game.cli simulate --seeds 1000

test-llm:
	uv run pytest -m llm

codegen:
	uv run python -m src.game.cli codegen --out web/src/types/generated.ts
