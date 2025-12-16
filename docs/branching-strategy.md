# Branching Strategy

Nedlia uses **Trunk-Based Development** with **feature flags** (LaunchDarkly) and **short-lived feature branches**.

## Overview

```text
main (trunk)
  │
  ├── feat/user-auth (1-2 days) ──────┐
  │                                      │ PR + Squash Merge
  ├──────────────────────────────────────┘
  │
  ├── feat/pr-analysis (2-3 days) ────┐
  │                                      │ PR + Squash Merge
  ├──────────────────────────────────────┘
  │
  ▼
Continuous deployment to staging → production
```

## Core Principles

### 1. Single Trunk (`main`)

- `main` is the **only long-lived branch**
- All code flows through `main`
- `main` is always deployable
- No `develop`, `release/*`, or `hotfix/*` branches

### 2. Short-Lived Feature Branches

- Branch from `main`, merge back to `main`
- **Maximum lifetime: 2-3 days**
- Smaller is better – aim for < 400 lines changed
- Delete branch immediately after merge

### 3. Feature Flags for Incomplete Work

- Use LaunchDarkly to hide incomplete features
- Merge to `main` even if feature isn't ready for users
- Decouple **deployment** from **release**

### 4. Continuous Integration

- Every commit to `main` triggers CI
- Every PR must pass all checks
- Merge frequently (at least daily if working on something)

## Branch Naming Convention

```text
<type>/<short-description>
```

| Type     | Purpose                         | Example                  |
| -------- | ------------------------------- | ------------------------ |
| `feat/`  | New functionality               | `feat/github-webhook`    |
| `fix/`   | Bug fixes                       | `fix/auth-redirect-loop` |
| `chore/` | Maintenance, refactoring        | `chore/upgrade-deps`     |
| `docs/`  | Documentation only              | `docs/api-reference`     |
| `exp/`   | Spikes, POCs (may be discarded) | `exp/new-ai-model`       |

## Workflow

### 1. Start Work

```bash
# Always start from latest main
git checkout main
git pull origin main

# Create short-lived branch
git checkout -b feature/my-feature
```

### 2. Develop with Feature Flags

If the feature isn't ready for users, wrap it in a flag:

```typescript
// Check flag before showing new feature
if (await ldClient.variation('new-review-ui', user, false)) {
  return <NewReviewUI />;
}
return <CurrentReviewUI />;
```

### 3. Commit Frequently

```bash
# Small, focused commits
git add .
git commit -m "feat(backend): add webhook endpoint"

# Push to remote
git push -u origin feature/my-feature
```

### 4. Open PR Early

- Open a **draft PR** as soon as you push
- Get early feedback
- CI runs on every push

### 5. Keep Branch Updated

```bash
# Rebase on main daily (or more often)
git fetch origin
git rebase origin/main

# Resolve conflicts immediately
# Force push after rebase
git push --force-with-lease
```

### 6. Merge via Squash

- All PRs use **Squash and Merge**
- PR title becomes commit message (conventional format)
- Delete branch after merge

### 7. Deploy

- Merge to `main` → auto-deploy to **staging**
- Tag release → manual deploy to **production**
- Feature flag controls user visibility

## Feature Flags with LaunchDarkly

### Why Feature Flags?

| Benefit                          | Description                            |
| -------------------------------- | -------------------------------------- |
| **Decouple deploy from release** | Code can be in production but hidden   |
| **Gradual rollout**              | Release to 1%, 10%, 50%, 100% of users |
| **Kill switch**                  | Instantly disable problematic features |
| **A/B testing**                  | Test variations with real users        |
| **Trunk-based development**      | Merge incomplete work safely           |

### Flag Naming Convention

```text
<scope>.<feature>.<variant>
```

Examples:

- `reviews.ai-suggestions.enabled`
- `ui.new-dashboard.enabled`
- `api.v2-endpoints.enabled`
- `experiment.new-model.percentage`

### Flag Types

| Type        | Use Case           | Example                                      |
| ----------- | ------------------ | -------------------------------------------- |
| **Boolean** | On/off toggle      | `reviews.ai-suggestions.enabled`             |
| **String**  | Variant selection  | `ui.theme.variant` → "light", "dark", "auto" |
| **Number**  | Percentage, limits | `api.rate-limit.requests-per-minute`         |
| **JSON**    | Complex config     | `features.config` → `{ "maxItems": 10 }`     |

### LaunchDarkly Setup

#### Installation

```bash
# Backend (Python)
pip install launchdarkly-server-sdk

# Backend (Node.js)
pnpm add @launchdarkly/node-server-sdk

# Frontend (React)
pnpm add launchdarkly-react-client-sdk
```

#### Backend Integration (Python)

```python
# infrastructure/feature_flags.py
import ldclient
from ldclient.config import Config

class FeatureFlagService:
    def __init__(self, sdk_key: str):
        ldclient.set_config(Config(sdk_key))
        self.client = ldclient.get()

    def is_enabled(self, flag_key: str, user_id: str, default: bool = False) -> bool:
        context = {
            "kind": "user",
            "key": user_id,
        }
        return self.client.variation(flag_key, context, default)

    def get_variation(self, flag_key: str, user_id: str, default: any) -> any:
        context = {
            "kind": "user",
            "key": user_id,
        }
        return self.client.variation(flag_key, context, default)

# Usage in use case
class CreateReviewUseCase:
    def __init__(self, feature_flags: FeatureFlagService):
        self.feature_flags = feature_flags

    def execute(self, request: CreateReviewRequest) -> Review:
        review = Review.create(request)

        if self.feature_flags.is_enabled("reviews.ai-suggestions.enabled", request.user_id):
            review.suggestions = self.ai_service.analyze(review)

        return review
```

#### Backend Integration (NestJS)

```typescript
// infrastructure/feature-flags.service.ts
import * as LaunchDarkly from '@launchdarkly/node-server-sdk';

@Injectable()
export class FeatureFlagService {
  private client: LaunchDarkly.LDClient;

  constructor(@Inject('LD_SDK_KEY') sdkKey: string) {
    this.client = LaunchDarkly.init(sdkKey);
  }

  async isEnabled(flagKey: string, userId: string, defaultValue = false): Promise<boolean> {
    const context = { kind: 'user', key: userId };
    return this.client.variation(flagKey, context, defaultValue);
  }

  async getVariation<T>(flagKey: string, userId: string, defaultValue: T): Promise<T> {
    const context = { kind: 'user', key: userId };
    return this.client.variation(flagKey, context, defaultValue);
  }
}

// Usage in controller
@Controller('reviews')
export class ReviewsController {
  constructor(
    private readonly featureFlags: FeatureFlagService,
    private readonly createReview: CreateReviewUseCase
  ) {}

  @Post()
  async create(@Body() dto: CreateReviewDto, @User() user: UserContext) {
    const useNewEngine = await this.featureFlags.isEnabled(
      'reviews.new-analysis-engine.enabled',
      user.id
    );

    return this.createReview.execute(dto, { useNewEngine });
  }
}
```

#### Frontend Integration (React)

```tsx
// App.tsx
import { LDProvider } from 'launchdarkly-react-client-sdk';

function App() {
  return (
    <LDProvider
      clientSideID={import.meta.env.VITE_LD_CLIENT_ID}
      context={{
        kind: 'user',
        key: user.id,
        email: user.email,
        name: user.name,
      }}
    >
      <Router />
    </LDProvider>
  );
}

// Component usage
import { useFlags } from 'launchdarkly-react-client-sdk';

function ReviewDashboard() {
  const { newDashboardEnabled, dashboardLayout } = useFlags();

  if (newDashboardEnabled) {
    return <NewDashboard layout={dashboardLayout} />;
  }

  return <LegacyDashboard />;
}
```

### Flag Lifecycle

```text
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │────▶│   Develop   │────▶│   Rollout   │────▶│   Remove    │
│   Flag      │     │   Behind    │     │   Gradually │     │   Flag      │
│             │     │   Flag      │     │             │     │   & Code    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **Create**: Add flag in LaunchDarkly before starting work
2. **Develop**: Implement feature behind flag, merge to main
3. **Rollout**: Enable for internal → beta → percentage → 100%
4. **Remove**: Once stable, remove flag and dead code

### Rollout Strategy

| Phase        | Audience        | Duration | Purpose             |
| ------------ | --------------- | -------- | ------------------- |
| **Internal** | Team only       | 1-2 days | Catch obvious bugs  |
| **Beta**     | Opt-in users    | 3-5 days | Real-world feedback |
| **Canary**   | 5% of users     | 1-2 days | Monitor metrics     |
| **Gradual**  | 25% → 50% → 75% | 1 week   | Gradual exposure    |
| **GA**       | 100%            | -        | Full release        |

### Flag Cleanup

**Important**: Flags are technical debt. Remove them promptly.

```bash
# Track flag age in LaunchDarkly
# Set up alerts for flags older than 30 days
# Schedule cleanup sprints quarterly
```

When removing a flag:

1. Verify flag is 100% enabled for all users
2. Remove flag checks from code
3. Remove flag from LaunchDarkly
4. Delete any fallback/legacy code paths

## Environment Configuration

### LaunchDarkly SDK Keys

```bash
# .env.example
# Server-side SDK key (keep secret)
LD_SDK_KEY=sdk-xxx-xxx

# Client-side ID (safe to expose)
VITE_LD_CLIENT_ID=client-xxx-xxx
```

### Per-Environment Flags

LaunchDarkly supports environment-specific targeting:

| Environment | Default State      | Notes                   |
| ----------- | ------------------ | ----------------------- |
| Development | All flags ON       | Test everything locally |
| Testing     | All flags ON       | CI tests all code paths |
| Staging     | Match production   | Validate before release |
| Production  | Controlled rollout | Gradual enablement      |

## Comparison: Why Not GitFlow?

| Aspect              | GitFlow                | Trunk-Based        |
| ------------------- | ---------------------- | ------------------ |
| Long-lived branches | `develop`, `release/*` | Only `main`        |
| Merge frequency     | Weekly/monthly         | Daily              |
| Integration pain    | High (big merges)      | Low (small merges) |
| Release process     | Branch-based           | Flag-based         |
| Rollback            | Revert release branch  | Toggle flag off    |
| Complexity          | High                   | Low                |

## Best Practices

### Do

- ✅ Merge to main at least daily
- ✅ Keep branches under 2-3 days old
- ✅ Use feature flags for incomplete work
- ✅ Delete branches immediately after merge
- ✅ Rebase on main frequently
- ✅ Write small, focused PRs (< 400 lines)

### Don't

- ❌ Create long-lived feature branches
- ❌ Let branches diverge significantly from main
- ❌ Merge incomplete features without flags
- ❌ Leave stale flags in the codebase
- ❌ Use branch-based releases

## Troubleshooting

### Branch is too old

```bash
# If branch is > 3 days old, consider:
# 1. Break into smaller PRs
# 2. Merge what's done behind a flag
# 3. Rebase and resolve conflicts

git fetch origin
git rebase origin/main
# Resolve conflicts
git push --force-with-lease
```

### Feature not ready but need to merge

```bash
# 1. Create flag in LaunchDarkly (disabled by default)
# 2. Wrap feature in flag check
# 3. Merge to main
# 4. Feature is deployed but hidden
```

### Need to rollback a feature

```bash
# Don't revert code – just disable the flag
# In LaunchDarkly: Toggle flag OFF
# Instant rollback, no deployment needed
```

## Related Documentation

- [Contributing](../CONTRIBUTING.md) – PR workflow, commit conventions
- [Deployment](deployment.md) – CI/CD pipeline
- [ADR-003: Event-Driven](adr/003-event-driven.md) – Architecture decisions
