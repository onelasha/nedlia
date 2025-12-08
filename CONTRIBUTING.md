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

## Branch Naming

Use prefixes:

- `feature/` – new functionality
- `fix/` – bug fixes
- `chore/` – maintenance, refactoring, tooling
- `docs/` – documentation only

Example: `feature/user-authentication`

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
5. Ensure CI passes.
6. Request review from at least one maintainer.
7. Squash and merge after approval.

## Code Style

- **JS/TS**: ESLint + Prettier (configured per project).
- **Python**: Ruff + Black.
- **Swift**: SwiftLint (optional).

Run formatters before committing:

```bash
pnpm format
cd nedlia-back-end/python && ruff format .
```

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
