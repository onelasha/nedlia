# Code Quality

This guide covers code quality standards, tools, and best practices for Nedlia.

## Overview

We use multiple layers of code quality enforcement:

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Code Quality Stack                        │
├─────────────────────────────────────────────────────────────────┤
│  SonarCloud          │  Deep analysis, security, tech debt      │
├─────────────────────────────────────────────────────────────────┤
│  Linters             │  ESLint, Ruff, SwiftLint                 │
├─────────────────────────────────────────────────────────────────┤
│  Formatters          │  Prettier, Ruff                          │
├─────────────────────────────────────────────────────────────────┤
│  Pre-commit Hooks    │  Local enforcement before push           │
├─────────────────────────────────────────────────────────────────┤
│  IDE                 │  Real-time feedback in editor            │
└─────────────────────────────────────────────────────────────────┘
```

---

## SonarCloud

[SonarCloud](https://sonarcloud.io/) provides continuous code quality and security analysis.

### What SonarCloud Analyzes

| Category              | Description                                          |
| --------------------- | ---------------------------------------------------- |
| **Bugs**              | Code that is demonstrably wrong or will cause errors |
| **Vulnerabilities**   | Security issues (SQL injection, XSS, etc.)           |
| **Code Smells**       | Maintainability issues (complexity, duplication)     |
| **Security Hotspots** | Code that needs security review                      |
| **Coverage**          | Test coverage percentage                             |
| **Duplications**      | Copy-pasted code blocks                              |

### Quality Gate

Our Quality Gate requires:

| Metric                     | Requirement | Rationale               |
| -------------------------- | ----------- | ----------------------- |
| **New Bugs**               | 0           | No new bugs introduced  |
| **New Vulnerabilities**    | 0           | No new security issues  |
| **New Code Coverage**      | ≥ 80%       | New code must be tested |
| **Duplicated Lines**       | < 3%        | Minimize copy-paste     |
| **Maintainability Rating** | A           | Keep code maintainable  |
| **Reliability Rating**     | A           | Keep code reliable      |
| **Security Rating**        | A           | Keep code secure        |

### Viewing Results

1. **PR Comments**: SonarCloud posts analysis summary on PRs
2. **Dashboard**: [sonarcloud.io/project/overview?id=onelasha_Nedlia](https://sonarcloud.io/project/overview?id=onelasha_Nedlia)
3. **IDE**: Install SonarLint extension for real-time feedback

### SonarLint IDE Extension

Install SonarLint for real-time analysis in your IDE:

- **VS Code**: [SonarLint Extension](https://marketplace.visualstudio.com/items?itemName=SonarSource.sonarlint-vscode)
- **IntelliJ**: [SonarLint Plugin](https://plugins.jetbrains.com/plugin/7973-sonarlint)

Connect to SonarCloud for synchronized rules:

```json
// .vscode/settings.json
{
  "sonarlint.connectedMode.connections.sonarcloud": [
    {
      "organizationKey": "onelasha",
      "connectionId": "nedlia-sonarcloud"
    }
  ],
  "sonarlint.connectedMode.project": {
    "connectionId": "nedlia-sonarcloud",
    "projectKey": "onelasha_Nedlia"
  }
}
```

### Fixing Issues

#### Bugs

```typescript
// ❌ Bug: Possible null dereference
function getUser(id: string) {
  const user = users.find(u => u.id === id);
  return user.name; // Bug: user might be undefined
}

// ✅ Fixed
function getUser(id: string) {
  const user = users.find(u => u.id === id);
  if (!user) {
    throw new Error(`User ${id} not found`);
  }
  return user.name;
}
```

#### Code Smells

```typescript
// ❌ Code Smell: High cognitive complexity
function processData(data: Data) {
  if (data.type === 'A') {
    if (data.status === 'active') {
      if (data.value > 10) {
        // ... nested logic
      }
    }
  }
}

// ✅ Fixed: Extract and simplify
function processData(data: Data) {
  if (!isProcessable(data)) return;

  const processor = getProcessor(data.type);
  return processor.process(data);
}
```

#### Security Hotspots

```python
# ❌ Security Hotspot: Hardcoded credentials
password = "admin123"

# ✅ Fixed: Use environment variables
import os
password = os.environ.get("DB_PASSWORD")
```

### Suppressing False Positives

Only suppress when you're certain it's a false positive:

```typescript
// TypeScript
// NOSONAR: False positive - value is validated upstream
const result = unsafeOperation(); // NOSONAR

// Or use specific rule
// @ts-ignore S1234
```

```python
# Python
result = unsafe_operation()  # noqa: S101
```

**Always add a comment explaining why** the suppression is valid.

---

## Linters

### ESLint (JavaScript/TypeScript)

Configuration: `.eslintrc.js`

```bash
# Run ESLint
pnpm lint

# Fix auto-fixable issues
pnpm lint --fix
```

Key rules enforced:

- No unused variables
- Consistent import order
- No console.log in production code
- Proper TypeScript types

### Ruff (Python)

Configuration: `ruff.toml`

```bash
# Run Ruff
cd nedlia-back-end/python
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

Key rules enforced:

- PEP 8 style
- Import sorting (isort)
- No unused imports
- Type annotation requirements

### SwiftLint (Swift)

Configuration: `.swiftlint.yml`

```bash
# Run SwiftLint
cd nedlia-plugin
swiftlint

# Auto-correct
swiftlint --fix
```

---

## Formatters

### Prettier (JS/TS/JSON/YAML/MD)

Configuration: `.prettierrc`

```bash
# Format all files
pnpm format

# Check formatting without changing
pnpm format --check
```

### Ruff Format (Python)

```bash
cd nedlia-back-end/python
uv run ruff format .
```

---

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit.

### Setup

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
pre-commit install --hook-type commit-msg
```

### What Runs

| Hook                  | Purpose                       |
| --------------------- | ----------------------------- |
| `trailing-whitespace` | Remove trailing whitespace    |
| `end-of-file-fixer`   | Ensure files end with newline |
| `check-yaml`          | Validate YAML syntax          |
| `check-json`          | Validate JSON syntax          |
| `gitleaks`            | Detect secrets                |
| `ruff`                | Python linting                |
| `ruff-format`         | Python formatting             |
| `eslint`              | JS/TS linting                 |
| `prettier`            | JS/TS formatting              |
| `commitlint`          | Validate commit message       |

### Bypassing Hooks (Emergency Only)

```bash
# Skip all hooks (use sparingly!)
git commit --no-verify -m "emergency fix"
```

**Note**: CI will still run all checks. Bypassing locally doesn't bypass CI.

---

## Code Quality Metrics

### Coverage Targets

| Layer          | Target | Rationale                                |
| -------------- | ------ | ---------------------------------------- |
| Domain         | 90%+   | Core business logic must be well-tested  |
| Application    | 80%+   | Use cases need good coverage             |
| Infrastructure | 70%+   | Adapters can be harder to test           |
| Interface      | 60%+   | Controllers often tested via integration |

### Complexity Limits

| Metric                | Limit       | Description                    |
| --------------------- | ----------- | ------------------------------ |
| Cyclomatic Complexity | ≤ 10        | Number of independent paths    |
| Cognitive Complexity  | ≤ 15        | How hard code is to understand |
| Function Length       | ≤ 50 lines  | Keep functions focused         |
| File Length           | ≤ 400 lines | Split large files              |

### Duplication

- **Threshold**: < 3% duplicated lines
- **Block size**: 10+ lines triggers duplication warning
- **Action**: Extract to shared function/module

---

## Best Practices

### Writing Clean Code

1. **Single Responsibility**: Each function/class does one thing
2. **Meaningful Names**: Variables and functions describe their purpose
3. **Small Functions**: Prefer many small functions over few large ones
4. **No Magic Numbers**: Use named constants
5. **Early Returns**: Reduce nesting with guard clauses

### Code Review Checklist

- [ ] No SonarCloud issues introduced
- [ ] Coverage maintained or improved
- [ ] No new code smells
- [ ] Security hotspots reviewed
- [ ] Complexity within limits

---

## CI Integration

SonarCloud runs on every PR and push to main:

```yaml
# .github/workflows/sonarcloud.yml
- Checkout code
- Install dependencies
- Run tests with coverage
- SonarCloud scan
- Post results to PR
```

### Required Secrets

Add these in GitHub repository settings:

| Secret        | Description               | How to Get                                                     |
| ------------- | ------------------------- | -------------------------------------------------------------- |
| `SONAR_TOKEN` | SonarCloud authentication | [sonarcloud.io](https://sonarcloud.io) → My Account → Security |

`GITHUB_TOKEN` is automatically provided by GitHub Actions.

---

## Troubleshooting

### SonarCloud scan fails

```bash
# Check sonar-project.properties syntax
# Verify SONAR_TOKEN is set in GitHub secrets
# Check SonarCloud project exists
```

### False positive issues

1. First, verify it's actually a false positive
2. If confirmed, suppress with comment explaining why
3. Consider reporting to SonarSource if it's a rule bug

### Coverage not showing

```bash
# Ensure coverage reports are generated
pnpm test --coverage

# Check report paths in sonar-project.properties
sonar.javascript.lcov.reportPaths=coverage/lcov.info
```

---

## Related Documentation

- [Testing](testing.md) – Test strategy and coverage
- [Contributing](../CONTRIBUTING.md) – Code standards
- [Pull Request Guidelines](pull-request-guidelines.md) – PR quality checks
