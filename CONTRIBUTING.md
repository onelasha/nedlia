# Contributing to Nedlia

## Getting Started

1. Clone the repository.
2. Install dependencies:
   ```bash
   pnpm install
   ```
3. For Python projects:
   ```bash
   cd nedlia-back-end/python && uv sync
   cd nedlia-sdk/python && uv sync
   ```

## Branching Strategy

We use **Trunk-Based Development** with **feature flags** (LaunchDarkly).

See [Branching Strategy](docs/branching-strategy.md) for full details.

### Key Points

- `main` is the only long-lived branch
- Feature branches should live **1-3 days max**
- Use feature flags for incomplete work
- Merge frequently (at least daily)

### Branch Naming

Use prefixes:

- `feat/` – new functionality
- `fix/` – bug fixes
- `chore/` – maintenance, refactoring, tooling
- `docs/` – documentation only
- `exp/` – spikes, POCs (may be discarded)

Example: `feat/user-authentication`

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`, `perf`, `ci`

Examples:

```text
feat(backend): add user registration endpoint
fix(frontend): resolve login redirect loop
docs: update ARCHITECTURE.md with SDK structure
chore: upgrade pnpm to v9
```

## Pull Request Workflow

1. Create a branch from `main`.
2. Make changes following clean architecture rules (see `ARCHITECTURE.md`).
3. Run linting and tests locally:
   ```bash
   pnpm lint
   pnpm test
   ```
4. Push and open a PR against `main`.
5. **Use a conventional commit format for your PR title** (this becomes the commit message on merge):
   ```
   feat(backend): add user authentication endpoint
   fix(frontend): resolve login redirect loop
   ```
6. Ensure CI passes (including PR title validation).
7. Request review from at least one maintainer.
8. Squash and merge after approval.

### PR Title Format

PR titles **must** follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`

**Scopes** (optional): `backend`, `frontend`, `sdk`, `plugin`, `iac`, `ci`, `docs`, `deps`

**Examples**:

- `feat(backend): add PR webhook handler`
- `fix(frontend): resolve dark mode toggle`
- `docs: update API documentation`
- `chore(deps): upgrade axios to v1.6`

> **Note**: PR titles are automatically validated by the `pr-title.yml` workflow. Invalid titles will block the PR from merging.

For complete PR guidelines including description format, review process, and examples, see [Pull Request Guidelines](docs/pull-request-guidelines.md).

## Code Style

- **JS/TS**: ESLint + Prettier (see `tools/js/`)
- **Python**: Ruff (see `pyproject.toml` at root)

Run formatters before committing:

```bash
pnpm format
ruff format nedlia-back-end/
```

### Tooling Configuration

Language-specific configs live in `tools/`:

```text
tools/
  js/                    # ESLint, Prettier, TSConfig, Commitlint
  python/                # Python version, documentation
```

> **Note**: `pyproject.toml` stays at root (required by `uv` for workspace resolution).

## Nx Monorepo

This project uses **Nx** for monorepo management. Common commands:

```bash
# Lint all projects
pnpm nx run-many -t lint

# Lint only affected projects
pnpm nx affected -t lint

# Build all projects
pnpm nx run-many -t build

# View dependency graph
pnpm nx graph
```

## SOLID Principles

ESLint enforces SOLID principles via rules for:

- **Single Responsibility**: `max-lines`, `max-lines-per-function`, `complexity`
- **Open/Closed**: `explicit-member-accessibility`, TypeScript strict mode
- **Liskov Substitution**: `explicit-function-return-type`
- **Interface Segregation**: `consistent-type-definitions`, `no-empty-interface`
- **Dependency Inversion**: `@nx/enforce-module-boundaries`, `import/no-cycle`

See [SOLID Principles](docs/SOLID-PRINCIPLES.md) for full details.

## Architecture Rules

All code must respect clean architecture layer boundaries:

- Domain imports nothing.
- Application imports only Domain.
- Infrastructure imports Application and Domain.
- Interface imports Application (and uses Infrastructure via dependency injection).

See `ARCHITECTURE.md` for details.

## Testing

- Write tests for new features and bug fixes.
- Aim for high coverage in Domain and Application layers.
- Integration tests go in Infrastructure.
- E2E tests go in Interface or a dedicated `e2e/` folder.

Run all tests:

```bash
pnpm test
cd nedlia-back-end/python && pytest
```

## Questions?

Open an issue or start a discussion in the repository.
