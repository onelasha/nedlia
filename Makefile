.PHONY: install lint test build format clean

install:
	pnpm install
	cd nedlia-back-end/services/placement-service && uv sync
	cd nedlia-sdk/python && uv sync

lint:
	pnpm nx run-many -t lint
	ruff check nedlia-back-end/ nedlia-sdk/python/ tools/performance-tests/

test:
	pnpm nx run-many -t test
	cd nedlia-back-end/services/placement-service && pytest
	cd tools/performance-tests && pytest

build:
	pnpm nx run-many -t build

format:
	pnpm nx run-many -t format
	ruff format nedlia-back-end/ nedlia-sdk/python/ tools/performance-tests/

clean:
	rm -rf node_modules
	rm -rf **/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".venv" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
