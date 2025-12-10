# Feature Flags

Feature flag patterns and implementation for Nedlia's gradual rollouts and trunk-based development.

## Why Feature Flags?

1. **Trunk-Based Development**: Merge incomplete features to main without exposing them
2. **Gradual Rollouts**: Release to percentage of users, monitor, then expand
3. **Kill Switches**: Instantly disable problematic features without deployment
4. **A/B Testing**: Compare feature variants with real users
5. **Environment Differences**: Enable features in staging but not production

---

## Flag Types

| Type           | Lifespan    | Example                            |
| -------------- | ----------- | ---------------------------------- |
| **Release**    | Short-term  | `enable_new_validation_ui`         |
| **Experiment** | Medium-term | `experiment_placement_suggestions` |
| **Ops**        | Permanent   | `enable_debug_logging`             |
| **Permission** | Permanent   | `enable_enterprise_features`       |

---

## Implementation

### Configuration-Based (Simple)

For simple on/off flags, use environment configuration:

```python
# src/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Feature flags
    enable_validation_v2: bool = False
    enable_placement_suggestions: bool = False
    enable_async_file_generation: bool = True
    enable_debug_logging: bool = False

    # Rollout percentages (0-100)
    rollout_new_ui_percent: int = 0

    model_config = {"env_prefix": "NEDLIA_"}


settings = Settings()
```

```python
# Usage in code
from src.core.config import settings

async def validate_video(video_id: UUID) -> ValidationResult:
    if settings.enable_validation_v2:
        return await validate_v2(video_id)
    return await validate_v1(video_id)
```

### Feature Flag Service (Advanced)

For dynamic flags with user targeting:

```python
# src/core/feature_flags.py
from dataclasses import dataclass
from enum import Enum
from typing import Any
import hashlib


class FlagStatus(str, Enum):
    ON = "on"
    OFF = "off"
    ROLLOUT = "rollout"


@dataclass
class FeatureFlag:
    name: str
    status: FlagStatus
    rollout_percent: int = 0
    allowed_users: list[str] | None = None
    allowed_tenants: list[str] | None = None


class FeatureFlagService:
    """Service for evaluating feature flags."""

    def __init__(self, flags: dict[str, FeatureFlag]) -> None:
        self.flags = flags

    def is_enabled(
        self,
        flag_name: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ) -> bool:
        """Check if a feature flag is enabled for the given context."""
        flag = self.flags.get(flag_name)
        if not flag:
            return False

        if flag.status == FlagStatus.OFF:
            return False

        if flag.status == FlagStatus.ON:
            return True

        # Rollout: Check user/tenant allowlists first
        if flag.allowed_users and user_id in flag.allowed_users:
            return True

        if flag.allowed_tenants and tenant_id in flag.allowed_tenants:
            return True

        # Percentage rollout based on user_id hash
        if flag.rollout_percent > 0 and user_id:
            return self._in_rollout(flag_name, user_id, flag.rollout_percent)

        return False

    def _in_rollout(self, flag_name: str, user_id: str, percent: int) -> bool:
        """Deterministic rollout based on hash of flag + user."""
        hash_input = f"{flag_name}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100
        return bucket < percent
```

### Flag Configuration

```python
# src/core/flags_config.py
from src.core.feature_flags import FeatureFlag, FlagStatus

FLAGS = {
    "validation_v2": FeatureFlag(
        name="validation_v2",
        status=FlagStatus.ROLLOUT,
        rollout_percent=25,  # 25% of users
        allowed_tenants=["tenant_beta_testers"],
    ),
    "placement_suggestions": FeatureFlag(
        name="placement_suggestions",
        status=FlagStatus.OFF,
    ),
    "async_file_generation": FeatureFlag(
        name="async_file_generation",
        status=FlagStatus.ON,
    ),
    "debug_mode": FeatureFlag(
        name="debug_mode",
        status=FlagStatus.ROLLOUT,
        rollout_percent=0,
        allowed_users=["user_admin_123"],
    ),
}
```

### Dependency Injection

```python
# src/core/dependencies.py
from src.core.feature_flags import FeatureFlagService
from src.core.flags_config import FLAGS


def get_feature_flags() -> FeatureFlagService:
    return FeatureFlagService(FLAGS)


FeatureFlags = Annotated[FeatureFlagService, Depends(get_feature_flags)]
```

### Usage in Routes

```python
# src/placements/router.py
from src.core.dependencies import FeatureFlags, CurrentUser


@router.post("/validate")
async def validate_placement(
    placement_id: UUID,
    feature_flags: FeatureFlags,
    current_user: CurrentUser,
) -> ValidationResult:
    if feature_flags.is_enabled(
        "validation_v2",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    ):
        return await validate_v2(placement_id)

    return await validate_v1(placement_id)
```

---

## TypeScript Implementation

```typescript
// src/core/featureFlags.ts
interface FeatureFlag {
  name: string;
  status: 'on' | 'off' | 'rollout';
  rolloutPercent?: number;
  allowedUsers?: string[];
}

const FLAGS: Record<string, FeatureFlag> = {
  newPlacementUI: {
    name: 'newPlacementUI',
    status: 'rollout',
    rolloutPercent: 50,
  },
  darkMode: {
    name: 'darkMode',
    status: 'on',
  },
};

export function isEnabled(flagName: string, userId?: string): boolean {
  const flag = FLAGS[flagName];
  if (!flag) return false;

  if (flag.status === 'off') return false;
  if (flag.status === 'on') return true;

  if (flag.allowedUsers?.includes(userId ?? '')) return true;

  if (flag.rolloutPercent && userId) {
    const hash = simpleHash(`${flagName}:${userId}`);
    return hash % 100 < flag.rolloutPercent;
  }

  return false;
}

function simpleHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}
```

### React Hook

```typescript
// src/hooks/useFeatureFlag.ts
import { useAuth } from './useAuth';
import { isEnabled } from '../core/featureFlags';

export function useFeatureFlag(flagName: string): boolean {
  const { user } = useAuth();
  return isEnabled(flagName, user?.id);
}
```

```tsx
// src/components/PlacementEditor.tsx
import { useFeatureFlag } from '../hooks/useFeatureFlag';

export function PlacementEditor() {
  const showNewUI = useFeatureFlag('newPlacementUI');

  if (showNewUI) {
    return <NewPlacementEditor />;
  }

  return <LegacyPlacementEditor />;
}
```

---

## Best Practices

### Naming Conventions

```python
# ✅ Good: Clear, descriptive names
"enable_validation_v2"
"experiment_placement_suggestions"
"rollout_new_dashboard"

# ❌ Bad: Vague or unclear
"new_feature"
"test_flag"
"flag_123"
```

### Flag Lifecycle

1. **Create**: Add flag in OFF state
2. **Test**: Enable in dev/staging
3. **Rollout**: Gradual percentage increase
4. **Full Release**: Set to ON (100%)
5. **Cleanup**: Remove flag and old code path

### Cleanup Checklist

When removing a flag:

- [ ] Remove flag from configuration
- [ ] Remove all `is_enabled()` checks
- [ ] Remove old code path
- [ ] Update tests
- [ ] Document in changelog

### Logging

```python
import logging

logger = logging.getLogger(__name__)


def is_enabled(self, flag_name: str, user_id: str | None = None) -> bool:
    result = self._evaluate(flag_name, user_id)

    logger.debug(
        "Feature flag evaluated",
        extra={
            "flag": flag_name,
            "user_id": user_id,
            "enabled": result,
        },
    )

    return result
```

---

## External Services (Optional)

For larger teams, consider dedicated feature flag services:

| Service           | Pros                                  | Cons                    |
| ----------------- | ------------------------------------- | ----------------------- |
| **LaunchDarkly**  | Full-featured, SDKs for all languages | Expensive               |
| **Unleash**       | Open-source, self-hosted              | Requires infrastructure |
| **Flagsmith**     | Open-source, hosted option            | Fewer integrations      |
| **AWS AppConfig** | Native AWS, no extra service          | Limited targeting       |

### AWS AppConfig Example

```python
# src/core/feature_flags_appconfig.py
import boto3
from functools import lru_cache


class AppConfigFeatureFlags:
    def __init__(self):
        self.client = boto3.client('appconfig')
        self.app_id = "nedlia"
        self.env_id = "production"
        self.config_id = "feature-flags"

    @lru_cache(maxsize=1)
    def _get_config(self) -> dict:
        response = self.client.get_configuration(
            Application=self.app_id,
            Environment=self.env_id,
            Configuration=self.config_id,
            ClientId="api",
        )
        return json.loads(response['Content'].read())

    def is_enabled(self, flag_name: str) -> bool:
        config = self._get_config()
        return config.get(flag_name, {}).get("enabled", False)
```

---

## Related Documentation

- [Branching Strategy](branching-strategy.md) – Trunk-based development
- [Deployment](deployment.md) – Gradual rollouts
- [Testing Strategy](testing-strategy.md) – Testing with flags
