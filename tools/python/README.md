# Python Tooling Configuration

This directory contains Python-specific tooling configuration for the Nedlia monorepo.

## Configuration Files

### Root-Level (Required by uv)

The main Python configuration lives at the **repository root**:

- **`/pyproject.toml`** - UV workspace configuration, Ruff, MyPy, Pytest, and Coverage settings

> **Note**: `uv` requires `pyproject.toml` at the workspace root for proper workspace member resolution.
> This is a constraint of the Python tooling ecosystem, not a design choice.

### This Directory

- **`.python-version`** - Python version specification (used by pyenv, asdf, etc.)

## Why pyproject.toml is at Root

Unlike JavaScript tooling (ESLint, Prettier, TSConfig) which can be referenced from subdirectories,
Python's `uv` workspace feature requires the `[tool.uv.workspace]` configuration to be in a
`pyproject.toml` at the repository root to properly resolve workspace members.

This is the standard pattern for Python monorepos using uv, Poetry, or similar tools.

## Tools Configured

| Tool         | Purpose              | Config Section              |
| ------------ | -------------------- | --------------------------- |
| **Ruff**     | Linting & Formatting | `[tool.ruff]`               |
| **MyPy**     | Static Type Checking | `[tool.mypy]`               |
| **Pytest**   | Testing              | `[tool.pytest.ini_options]` |
| **Coverage** | Code Coverage        | `[tool.coverage.*]`         |

## Usage

```bash
# From repository root
uv sync                    # Install dependencies
ruff check .               # Lint Python code
ruff format .              # Format Python code
mypy nedlia-back-end/      # Type check
pytest                     # Run tests
```
