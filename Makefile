.PHONY: install test test-fast lint type-check content-lint docs-health scenarios smoke determinism web-check web-contracts qa play verify verify-script smoke-real-llm test-llm llm-eval-mock llm-eval-real llm-eval-real-judge playtest-live dev dev-start dev-stop dev-restart dev-status

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

docs-health:
	uv run python scripts/docs-health.py

scenarios:
	uv run pytest tests/scenarios

smoke:
	uv run python -m src.game.cli verify-script --seed 1 --actions tests/scenarios/fixtures/day1-happy-path.yaml --mock-llm --exit-on-end

determinism:
	uv run python -m src.game.cli verify --all

web-check:
	cd web && npm run type-check

web-contracts:
	cd web && npm run test:e2e -- tests/e2e/action-contracts.spec.ts

qa: lint type-check content-lint test smoke determinism llm-eval-mock web-check web-contracts

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

llm-eval-mock:
	uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-mock

llm-eval-real:
	uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-real --real-llm

llm-eval-real-judge:
	uv run python -m src.game.cli llm-eval --out review-packet/llm-eval-real-judge --real-llm --judge

playtest-live:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev-server.ps1 start
	node scripts/playtest-director.mjs --visible --persona loyal-chloe --stopAfter free-chat --checkpoint day1-post-greetings

dev: dev-start

dev-start:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev-server.ps1 start

dev-stop:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev-server.ps1 stop

dev-restart:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev-server.ps1 restart

dev-status:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dev-server.ps1 status
