# Python Tooling Configuration

Shared Python tooling configuration for the Nedlia monorepo.

## Configuration Files

| File                  | Purpose                                |
| --------------------- | -------------------------------------- |
| **`ruff.toml`**       | Shared Ruff linting & formatting rules |
| **`mypy.ini`**        | Shared MyPy type checking settings     |
| **`.python-version`** | Python version (3.13.5)                |

## Usage in Projects

Each Python project has its own `pyproject.toml` and manages its own dependencies via `uv`.
Projects extend the shared configs:

```toml
# In project's pyproject.toml
[tool.ruff]
extend = "../../tools/python/ruff.toml"
```

## Nx Orchestration

All Python tasks are run via Nx, not directly from this directory:

```bash
nx run placement-service:lint      # Lint a specific project
nx run placement-service:test      # Test a specific project
nx run-many -t lint --projects=tag:python  # Lint all Python projects
```

## Tools

| Tool       | Purpose                          |
| ---------- | -------------------------------- |
| **Ruff**   | Linting & Formatting             |
| **MyPy**   | Static Type Checking             |
| **Pytest** | Testing                          |
| **uv**     | Package management (per-project) |
