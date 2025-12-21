# Security Tooling

Security-related configuration for the Nedlia monorepo.

## Configuration Files

| File                 | Purpose                              |
| -------------------- | ------------------------------------ |
| **`.gitleaks.toml`** | Secrets detection rules for gitleaks |

## Gitleaks

[Gitleaks](https://github.com/gitleaks/gitleaks) scans for accidentally committed secrets.

### Installation

```bash
# macOS
brew install gitleaks

# or via Go
go install github.com/gitleaks/gitleaks/v8@latest
```

### Usage

Gitleaks runs automatically via the husky pre-commit hook (if installed).

Manual scan:

```bash
gitleaks detect --source . --config tools/security/.gitleaks.toml
```

### Custom Rules

The `.gitleaks.toml` file extends the default ruleset and adds:

- Nedlia API key detection
- Generic secret patterns
- Allowlisted paths (`.env.example`, `.github/`)
