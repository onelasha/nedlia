.PHONY: install lint test build format clean

install:
	pnpm install
	cd nedlia-back-end/python && uv sync
	cd nedlia-sdk/python && uv sync

lint:
	pnpm lint
	cd nedlia-back-end/python && ruff check .
	cd nedlia-sdk/python && ruff check .

test:
	pnpm test
	cd nedlia-back-end/python && pytest
	cd nedlia-sdk/python && pytest

build:
	pnpm build

format:
	pnpm format
	cd nedlia-back-end/python && ruff format .
	cd nedlia-sdk/python && ruff format .

clean:
	rm -rf node_modules
	rm -rf nedlia-back-end/nestjs/node_modules
	rm -rf nedlia-front-end/web/node_modules
	rm -rf nedlia-sdk/js/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".venv" -exec rm -rf {} +
