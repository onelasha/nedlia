.PHONY: install lint test build format clean

# All orchestration via Nx - this Makefile is a convenience wrapper

install:
	pnpm install

lint:
	pnpm nx run-many -t lint

test:
	pnpm nx run-many -t test

build:
	pnpm nx run-many -t build

format:
	pnpm nx run-many -t format

clean:
	rm -rf node_modules
	rm -rf **/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".venv" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
