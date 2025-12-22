# Getting Started

This guide will help you set up your local development environment for Nedlia.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required

| Tool        | Version | Installation                                                  |
| ----------- | ------- | ------------------------------------------------------------- |
| **Node.js** | 20.x    | [nodejs.org](https://nodejs.org/) or `nvm install 20`         |
| **pnpm**    | 10.x    | `corepack enable && corepack prepare pnpm@latest --activate`  |
| **Python**  | 3.11+   | [python.org](https://www.python.org/) or `pyenv install 3.11` |
| **uv**      | latest  | `curl -LsSf https://astral.sh/uv/install.sh \| sh`            |
| **Git**     | 2.x     | [git-scm.com](https://git-scm.com/)                           |

### Optional (for infrastructure work)

| Tool           | Version | Installation                          |
| -------------- | ------- | ------------------------------------- |
| **Terraform**  | 1.5+    | `brew install terraform`              |
| **Terragrunt** | 0.50+   | `brew install terragrunt`             |
| **AWS CLI**    | 2.x     | `brew install awscli`                 |
| **Docker**     | latest  | [docker.com](https://www.docker.com/) |

## Clone the Repository

```bash
git clone https://github.com/onelasha/Nedlia.git
cd Nedlia
```

## Install Dependencies

### JavaScript/TypeScript

```bash
# Install all JS dependencies (runs across all workspaces)
pnpm install
```

### Python (via Nx)

Python dependencies are managed per-project via `uv`. Use Nx to install:

```bash
# Install API dependencies
nx run api:install

# Install placement-service dependencies
nx run placement-service:install
```

Or install manually:

```bash
cd nedlia-back-end/api && uv sync
cd nedlia-back-end/services/placement-service && uv sync
```

## Environment Setup

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in required values:

   ```bash
   # Required for local development
   NODE_ENV=development
   DATABASE_URL=postgresql://localhost:5432/nedlia_dev
   ```

3. For AWS services (optional for local dev):

   ```bash
   aws configure
   # Or set AWS_PROFILE in .env
   ```

## Verify Installation

Run the following to verify everything is set up:

```bash
# Check Node.js
node --version  # Should be v20.x

# Check pnpm
pnpm --version  # Should be 10.x

# Check Python
python --version  # Should be 3.11.x

# Check uv
uv --version

# Check Nx
pnpm nx --version

# Lint all code
pnpm nx run-many -t lint

# Run tests
make test
```

## Nx Monorepo

This project uses **Nx** for monorepo management with enforced module boundaries.

```bash
# View all projects
pnpm nx show projects

# Lint all projects
pnpm nx run-many -t lint

# Lint only affected projects (faster for PRs)
pnpm nx affected -t lint

# View project dependency graph
pnpm nx graph
```

## IDE Setup

We recommend **VS Code** or **Windsurf** with the extensions listed in `.vscode/extensions.json`.

To install recommended extensions:

1. Open the project in VS Code
2. Press `Cmd+Shift+P` → "Extensions: Show Recommended Extensions"
3. Install all workspace recommendations

## Git Hooks (MANDATORY)

> **⚠️ Git hooks are required for all developers.** They enforce code quality and commit standards.

Git hooks are managed via **husky** and installed automatically with `pnpm install`.

### What the hooks do

| Hook           | Purpose                                                                      |
| -------------- | ---------------------------------------------------------------------------- |
| **pre-commit** | Runs gitleaks (secrets detection) + lint-staged (lints only staged files)    |
| **commit-msg** | Validates [conventional commit](https://www.conventionalcommits.org/) format |

### lint-staged

We use **lint-staged** to run linters only on staged files, making commits fast:

| File Type           | Command              |
| ------------------- | -------------------- |
| `*.{js,jsx,ts,tsx}` | ESLint with auto-fix |
| `*.py`              | Ruff check + format  |
| `*.md`              | Prettier             |

> **Note**: Full `nx affected` validation runs in CI, not locally.

### Verify hooks are installed

```bash
pnpm verify-hooks
# Should output: ✅ Git hooks installed
```

### If hooks are missing

```bash
pnpm exec husky install
```

### Commit message format

All commits must follow conventional commits:

```
<type>(<scope>): <description>

# Examples:
feat(backend): add user authentication
fix(portal): resolve login redirect
chore(deps): upgrade axios
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`

> **Note**: To temporarily skip hooks (not recommended), use `git commit --no-verify`

## Next Steps

- [Local Development](local-development.md) – Running services locally
- [Testing](testing.md) – Running and writing tests
- [Architecture](../ARCHITECTURE.md) – Understanding the codebase structure
- [SOLID Principles](SOLID-PRINCIPLES.md) – ESLint rules enforcing SOLID design
- [Contributing](../CONTRIBUTING.md) – How to submit changes

## Troubleshooting

### pnpm install fails

```bash
# Clear cache and retry
pnpm store prune
rm -rf node_modules
pnpm install
```

### Python dependency issues

```bash
# Recreate virtual environment
cd nedlia-back-end/api
rm -rf .venv
uv sync

# Or via Nx
nx run api:install
```

### Git hooks not running

```bash
pnpm exec husky install
```

### Node version mismatch

```bash
# Use nvm to switch versions
nvm use
# Or install the correct version
nvm install
```

## Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/onelasha/Nedlia/discussions)
- **Bugs**: File an [Issue](https://github.com/onelasha/Nedlia/issues)
- **Security**: See [SECURITY.md](../SECURITY.md)
