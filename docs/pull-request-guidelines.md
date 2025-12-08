# Pull Request Guidelines

This guide covers best practices for creating, reviewing, and merging pull requests in Nedlia.

## PR Title (Commit Message)

Since we use **squash merge**, the PR title becomes the final commit message. It **must** follow [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```text
<type>(<scope>): <description>
```

### Components

| Component     | Required    | Description                                |
| ------------- | ----------- | ------------------------------------------ |
| `type`        | ✅ Yes      | Category of change                         |
| `scope`       | ❌ Optional | Area of codebase affected                  |
| `description` | ✅ Yes      | Short summary (imperative mood, lowercase) |

### Types

| Type       | Description                     | Example                                         |
| ---------- | ------------------------------- | ----------------------------------------------- |
| `feat`     | New feature                     | `feat(api): add webhook endpoint`               |
| `fix`      | Bug fix                         | `fix(auth): resolve token expiration issue`     |
| `docs`     | Documentation only              | `docs: update API reference`                    |
| `style`    | Formatting, no code change      | `style: fix indentation in utils`               |
| `refactor` | Code change, no new feature/fix | `refactor(reviews): extract validation logic`   |
| `perf`     | Performance improvement         | `perf(db): optimize query for reviews`          |
| `test`     | Adding/updating tests           | `test(api): add integration tests for webhooks` |
| `chore`    | Maintenance, tooling            | `chore: update dependencies`                    |
| `ci`       | CI/CD changes                   | `ci: add Python 3.12 to test matrix`            |
| `build`    | Build system changes            | `build: upgrade webpack to v5`                  |
| `revert`   | Revert previous commit          | `revert: feat(api): add webhook endpoint`       |

### Scopes

| Scope      | Area                             |
| ---------- | -------------------------------- |
| `backend`  | Python/NestJS backend services   |
| `frontend` | React web application            |
| `sdk`      | SDK packages (Python, JS, Swift) |
| `plugin`   | Native plugins (SwiftUI)         |
| `iac`      | Infrastructure as Code           |
| `api`      | API endpoints                    |
| `auth`     | Authentication/authorization     |
| `db`       | Database, migrations             |
| `ci`       | CI/CD pipelines                  |
| `docs`     | Documentation                    |
| `deps`     | Dependencies                     |

### Examples

```text
✅ Good:
feat(backend): add PR analysis webhook handler
fix(frontend): resolve infinite redirect on login
docs(sdk): add Python quickstart guide
chore(deps): bump axios from 1.5.0 to 1.6.0
refactor(api): extract review validation to separate module

❌ Bad:
Added new feature                    # No type, not descriptive
fix: stuff                           # Too vague
FEAT(API): Add Webhook               # Uppercase not allowed
feat(backend): Add PR analysis.      # No period, no capital
```

---

## PR Description

The PR description provides context for reviewers. Use the template provided.

### Required Sections

#### 1. Description

Explain **what** the PR does and **why**.

```markdown
## Description

Add webhook endpoint to receive GitHub PR events. This enables real-time
PR analysis when developers open or update pull requests.

**Why**: Currently we poll for PR changes every 5 minutes, causing delays
in review feedback. Webhooks provide instant notifications.
```

#### 2. Type of Change

Check the appropriate box(es):

```markdown
## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [x] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)
- [ ] Infrastructure/CI change
```

#### 3. Related Issues

Link to issues this PR addresses:

```markdown
## Related Issues

Fixes #123
Closes #456
Related to #789
```

**Keywords that auto-close issues**:

- `Fixes #123` – Closes issue when PR merges
- `Closes #123` – Same as Fixes
- `Resolves #123` – Same as Fixes
- `Related to #123` – Links without closing

#### 4. Checklist

Complete the checklist before requesting review:

```markdown
## Checklist

- [x] My code follows the project's coding standards
- [x] I have performed a self-review of my code
- [x] I have added tests that prove my fix/feature works
- [x] New and existing tests pass locally
- [x] I have updated documentation as needed
- [x] My changes respect clean architecture layer boundaries
```

### Optional Sections

#### Screenshots (for UI changes)

```markdown
## Screenshots

| Before         | After         |
| -------------- | ------------- |
| ![before](url) | ![after](url) |
```

#### Breaking Changes

If your PR introduces breaking changes:

````markdown
## ⚠️ Breaking Changes

- `ReviewService.analyze()` now requires a `config` parameter
- Removed deprecated `legacyAnalyze()` method

**Migration guide**:

```python
# Before
service.analyze(pr_url)

# After
service.analyze(pr_url, config=AnalysisConfig())
```
````

````

#### Feature Flag

If the feature is behind a flag:

```markdown
## Feature Flag

This feature is behind the `reviews.new-analysis-engine.enabled` flag.

- **Default**: `false` (disabled)
- **Rollout plan**: Internal → Beta (1 week) → GA
````

#### Testing Instructions

For complex changes, provide testing steps:

```markdown
## Testing Instructions

1. Set `ENABLE_WEBHOOKS=true` in `.env`
2. Start the backend: `pnpm --filter @nedlia/api dev`
3. Use ngrok to expose localhost: `ngrok http 3000`
4. Configure GitHub webhook to point to ngrok URL
5. Open a PR in a test repo
6. Verify webhook is received in backend logs
```

#### Performance Impact

For performance-sensitive changes:

```markdown
## Performance Impact

- **Before**: 450ms average response time
- **After**: 120ms average response time
- **Benchmark**: `pnpm test:perf -- --filter=reviews`
```

---

## PR Size Guidelines

| Size       | Lines Changed | Review Time | Recommendation    |
| ---------- | ------------- | ----------- | ----------------- |
| 🟢 Small   | < 100         | < 30 min    | Ideal             |
| 🟡 Medium  | 100-400       | 30-60 min   | Acceptable        |
| 🟠 Large   | 400-800       | 1-2 hours   | Split if possible |
| 🔴 X-Large | > 800         | > 2 hours   | Must split        |

### Tips for Smaller PRs

1. **One concern per PR** – Don't mix features with refactoring
2. **Stack PRs** – Break large features into dependent PRs
3. **Use feature flags** – Merge incomplete work safely
4. **Separate refactoring** – Do cleanup in a separate PR first

---

## PR Lifecycle

```text
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Draft     │────▶│   Ready     │────▶│  Approved   │────▶│   Merged    │
│             │     │ for Review  │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      │                   │                   │
   WIP, early         CI passes,          1+ approval,
   feedback           checklist done      no blockers
```

### 1. Draft PR

Open a draft PR early to:

- Get early feedback on approach
- Run CI on your changes
- Show progress to team

### 2. Ready for Review

Convert to ready when:

- All checklist items complete
- CI passes
- Self-review done
- Description is complete

### 3. Review Process

- **Minimum reviewers**: 1 (configured in CODEOWNERS)
- **Review types**:
  - ✅ Approve – Ready to merge
  - 💬 Comment – Feedback, no blocking
  - ❌ Request changes – Must address before merge

### 4. Addressing Feedback

```bash
# Make changes based on feedback
git add .
git commit -m "address review feedback"
git push

# Or amend if small fix
git add .
git commit --amend --no-edit
git push --force-with-lease
```

### 5. Merge

- Use **Squash and Merge**
- PR title becomes commit message
- Delete branch after merge

---

## Review Guidelines

### For Authors

- **Respond to all comments** – Even if just "Done" or "Won't fix because..."
- **Don't take it personally** – Reviews improve code quality
- **Explain your reasoning** – Help reviewers understand decisions
- **Be patient** – Complex PRs take time to review

### For Reviewers

- **Be constructive** – Suggest improvements, don't just criticize
- **Explain why** – Help authors learn
- **Distinguish blocking vs. non-blocking** – Use "nit:" for minor suggestions
- **Review promptly** – Aim for < 24 hour turnaround

### Comment Prefixes

| Prefix        | Meaning                          |
| ------------- | -------------------------------- |
| `nit:`        | Minor suggestion, non-blocking   |
| `question:`   | Seeking clarification            |
| `suggestion:` | Alternative approach to consider |
| `issue:`      | Must be addressed before merge   |
| `praise:`     | Positive feedback                |

Example:

```text
nit: Consider renaming `data` to `reviewData` for clarity.

issue: This query could cause N+1 problems. Consider using a join.

praise: Great test coverage! 🎉
```

---

## Automated Checks

Every PR runs these checks:

| Check          | Description                          | Required |
| -------------- | ------------------------------------ | -------- |
| PR Title       | Validates conventional commit format | ✅       |
| Lint JS/TS     | ESLint + Prettier                    | ✅       |
| Lint Python    | Ruff                                 | ✅       |
| Lint Terraform | terraform fmt                        | ✅       |
| Test JS/TS     | Jest/Vitest                          | ✅       |
| Test Python    | pytest                               | ✅       |
| Security       | Gitleaks secret scan                 | ✅       |
| Build          | Compile all projects                 | ✅       |

All checks must pass before merge.

---

## Example: Complete PR

### Title

```text
feat(backend): add GitHub webhook handler for PR events
```

### Description

```markdown
## Description

Add webhook endpoint to receive GitHub PR events (opened, synchronize, closed).
This enables real-time PR analysis instead of polling.

**Changes**:

- Add `POST /webhooks/github` endpoint
- Add webhook signature verification
- Add event handlers for PR lifecycle events
- Add integration tests

**Why**: Reduces feedback latency from 5 minutes (polling) to < 10 seconds.

## Type of Change

- [ ] Bug fix
- [x] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Refactoring
- [ ] Infrastructure/CI change

## Related Issues

Fixes #42
Related to #38

## Feature Flag

Behind `webhooks.github.enabled` flag (default: false).

## Checklist

- [x] My code follows the project's coding standards
- [x] I have performed a self-review of my code
- [x] I have added tests that prove my fix/feature works
- [x] New and existing tests pass locally
- [x] I have updated documentation as needed
- [x] My changes respect clean architecture layer boundaries

## Testing Instructions

1. Enable flag in LaunchDarkly for your user
2. Configure GitHub webhook in test repo
3. Open a PR and verify event is logged

## Additional Notes

Webhook secret should be configured via `GITHUB_WEBHOOK_SECRET` env var.
```

---

## PR Scope Rules

### Single-Project PRs (Preferred)

Each PR should ideally touch only **one project area**:

| Project  | Path                | Team          |
| -------- | ------------------- | ------------- |
| Backend  | `nedlia-back-end/`  | Backend team  |
| Frontend | `nedlia-front-end/` | Frontend team |
| IaC      | `nedlia-IaC/`       | Platform team |
| SDK      | `nedlia-sdk/`       | SDK team      |
| Plugin   | `nedlia-plugin/`    | Mobile team   |

### Cross-Project PRs

If your PR touches multiple projects, the `pr-scope-check` workflow will:

1. **Warn** with a comment explaining the concern
2. **List** which projects are affected
3. **Suggest** splitting into separate PRs

**When cross-project PRs are acceptable**:

- Coordinated API changes (backend + SDK)
- Breaking changes requiring simultaneous updates
- Initial feature scaffolding

### Restricted Areas

Some areas require specific team approval (enforced via CODEOWNERS):

| Area                                             | Required Reviewer    | Why                                            |
| ------------------------------------------------ | -------------------- | ---------------------------------------------- |
| `nedlia-IaC/`                                    | Platform team        | Infrastructure changes affect all environments |
| `.github/workflows/`                             | Platform team        | CI/CD changes affect all developers            |
| `nedlia-IaC/environments/production/`            | Platform team + Lead | Production is critical                         |
| Security files (`.gitleaks.toml`, `SECURITY.md`) | Security team        | Security policy changes                        |

### IaC Changes

PRs touching `nedlia-IaC/` trigger additional requirements:

1. **Platform team approval** required
2. **Terraform plan** must be reviewed
3. **No secrets** in code (use Secrets Manager)
4. **Backward compatible** or migration plan provided

The `pr-scope-check` workflow will add a checklist comment for IaC PRs.

---

## Related Documentation

- [Branching Strategy](branching-strategy.md) – Trunk-based development
- [Contributing](../CONTRIBUTING.md) – General contribution guidelines
- [Testing](testing.md) – Test requirements
