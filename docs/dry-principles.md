# DRY Principles

**Don't Repeat Yourself** (DRY) is a fundamental software development principle. This guide covers how we apply DRY across Nedlia's codebase.

## The Principle

> "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system."
> — Andy Hunt & Dave Thomas, _The Pragmatic Programmer_

DRY is about **knowledge duplication**, not just code duplication. Duplicated knowledge means changes require updates in multiple places, leading to bugs and inconsistency.

---

## DRY vs WET

| DRY (Don't Repeat Yourself)   | WET (Write Everything Twice)            |
| ----------------------------- | --------------------------------------- |
| Single source of truth        | Same logic in multiple places           |
| Change once, works everywhere | Change requires hunting down all copies |
| Easier to maintain            | Prone to inconsistencies                |
| May require abstraction       | Simpler initially, costly long-term     |

### When NOT to Apply DRY

DRY is not about eliminating all similar-looking code. **Premature abstraction** is worse than duplication:

- **Rule of Three**: Wait until you have 3+ duplicates before abstracting
- **Different reasons to change**: If two pieces of code look similar but change for different reasons, keep them separate
- **Coupling cost**: Don't couple unrelated modules just to share code

```python
# ❌ Over-DRY: Forced abstraction couples unrelated domains
def validate_entity(entity_type: str, data: dict) -> bool:
    if entity_type == "placement":
        return validate_placement(data)
    elif entity_type == "campaign":
        return validate_campaign(data)
    # ... endless if/else

# ✅ Better: Separate validators, even if similar structure
class PlacementValidator:
    def validate(self, data: PlacementCreate) -> list[ValidationError]:
        ...

class CampaignValidator:
    def validate(self, data: CampaignCreate) -> list[ValidationError]:
        ...
```

---

## Applying DRY in Nedlia

### 1. Shared Domain Models

Domain entities live in one place and are imported everywhere:

```
nedlia-back-end/
├── shared/
│   └── src/
│       └── domain/
│           ├── placement.py      # Single source of truth
│           ├── video.py
│           └── campaign.py
├── api/
│   └── src/
│       └── ... imports from shared
└── workers/
    └── src/
        └── ... imports from shared
```

```python
# ✅ Good: Import from shared domain
from nedlia_shared.domain.placement import Placement, PlacementStatus

# ❌ Bad: Redefine in each service
class Placement:  # Duplicated definition
    ...
```

### 2. Pydantic Schemas

Define base schemas once, extend for specific use cases:

```python
# src/placements/schemas.py

class PlacementBase(BaseModel):
    """Base placement fields - single source of truth."""
    video_id: UUID
    product_id: UUID
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., gt=0)
    description: str | None = None


class PlacementCreate(PlacementBase):
    """Request schema for creating a placement."""
    pass


class PlacementUpdate(BaseModel):
    """Request schema for updating a placement (all optional)."""
    start_time: float | None = Field(None, ge=0)
    end_time: float | None = Field(None, gt=0)
    description: str | None = None


class PlacementResponse(PlacementBase):
    """Response schema with additional fields."""
    id: UUID
    status: PlacementStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### 3. Constants and Configuration

Define constants once:

```python
# src/core/constants.py

# Status values - single source of truth
class PlacementStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


# Limits
MAX_PLACEMENTS_PER_VIDEO = 100
MAX_PLACEMENT_DURATION = 3600  # 1 hour
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# Error codes
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    # ...
```

```python
# ✅ Good: Use constants
from src.core.constants import MAX_PLACEMENTS_PER_VIDEO

if count >= MAX_PLACEMENTS_PER_VIDEO:
    raise LimitExceededError(...)

# ❌ Bad: Magic numbers scattered everywhere
if count >= 100:  # What is 100? Why 100?
    raise LimitExceededError(...)
```

### 4. Utility Functions

Extract common operations into utilities:

```python
# src/core/utils/time.py

def validate_time_range(start: float, end: float) -> None:
    """Validate a time range. Raises ValueError if invalid."""
    if start < 0:
        raise ValueError("Start time cannot be negative")
    if end <= start:
        raise ValueError("End time must be greater than start time")


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
```

```python
# Used everywhere
from src.core.utils.time import validate_time_range

class TimeRange:
    def __post_init__(self) -> None:
        validate_time_range(self.start_time, self.end_time)
```

### 5. Database Query Patterns

Use repository methods instead of duplicating queries:

```python
# ✅ Good: Repository encapsulates query logic
class PlacementRepository:
    async def find_by_video(
        self,
        video_id: UUID,
        status: PlacementStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Placement]:
        query = select(PlacementModel).where(
            PlacementModel.video_id == video_id,
            PlacementModel.deleted_at.is_(None),
        )
        if status:
            query = query.where(PlacementModel.status == status)
        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return [self._to_entity(row) for row in result.scalars()]


# ❌ Bad: Same query logic in multiple places
# In service A:
result = await session.execute(
    select(PlacementModel)
    .where(PlacementModel.video_id == video_id)
    .where(PlacementModel.deleted_at.is_(None))
)

# In service B (duplicated):
result = await session.execute(
    select(PlacementModel)
    .where(PlacementModel.video_id == video_id)
    .where(PlacementModel.deleted_at.is_(None))  # Easy to forget!
)
```

### 6. API Response Formatting

Centralize response envelope creation:

```python
# src/core/responses.py
from typing import Any, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def success_response(data: T | list[T], meta: dict[str, Any] | None = None) -> dict:
    """Create standardized success response."""
    response = {"data": data}
    if meta:
        response["meta"] = meta
    return response


def paginated_response(
    items: list[T],
    total: int,
    limit: int,
    offset: int,
) -> dict:
    """Create paginated response with metadata."""
    return {
        "data": items,
        "meta": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total,
        },
    }
```

### 7. Error Handling

Use the exception hierarchy from [Error Handling](error-handling.md):

```python
# ✅ Good: Reuse exception classes
from src.core.exceptions import NotFoundError
from src.domain.exceptions import VideoNotFoundError

# Specific domain exception
raise VideoNotFoundError(resource_id=str(video_id))

# ❌ Bad: Create HTTPException everywhere
raise HTTPException(
    status_code=404,
    detail=f"Video {video_id} not found",  # Inconsistent messages
)
```

### 8. TypeScript: Shared Types

```typescript
// packages/shared/src/types/placement.ts

export interface TimeRange {
  startTime: number;
  endTime: number;
}

export interface Placement {
  id: string;
  videoId: string;
  productId: string;
  timeRange: TimeRange;
  status: PlacementStatus;
  createdAt: string;
}

export type PlacementStatus = 'draft' | 'active' | 'archived';

// Used in portal, SDK, etc.
import { Placement, PlacementStatus } from '@nedlia/shared';
```

### 9. Configuration

Single configuration source with environment overrides:

```python
# src/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings - single source of truth."""

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str
    cache_ttl_seconds: int = 300

    # API
    api_rate_limit: int = 1000
    api_timeout_seconds: int = 30

    # Feature flags
    enable_validation: bool = True
    enable_notifications: bool = True

    model_config = {"env_file": ".env", "env_prefix": "NEDLIA_"}


# Singleton instance
settings = Settings()
```

```python
# ✅ Good: Import settings
from src.core.config import settings

timeout = settings.api_timeout_seconds

# ❌ Bad: Read env vars everywhere
timeout = int(os.getenv("API_TIMEOUT", "30"))  # Duplicated, error-prone
```

---

## DRY in Documentation

Documentation should also follow DRY:

```markdown
<!-- ✅ Good: Reference other docs -->

See [API Standards](api-standards.md) for error response format.

<!-- ❌ Bad: Duplicate content -->

Error responses follow this format:
{
"error": {
"code": "...",
...
}
}
```

---

## Code Smells: Signs of DRY Violations

| Smell                              | Solution                     |
| ---------------------------------- | ---------------------------- |
| Copy-pasted code blocks            | Extract to function or class |
| Same validation in multiple places | Create shared validator      |
| Magic numbers/strings repeated     | Define constants             |
| Similar SQL queries                | Use repository pattern       |
| Duplicated error messages          | Use exception hierarchy      |
| Same config read in many files     | Centralize configuration     |
| Repeated type definitions          | Create shared types package  |

---

## Nx Monorepo: Enforcing DRY

Nx helps enforce DRY through shared libraries:

```
libs/
├── shared/
│   ├── domain/          # Shared domain models
│   ├── utils/           # Common utilities
│   └── types/           # Shared TypeScript types
├── api/
│   └── data-access/     # API-specific data layer
└── portal/
    └── ui/              # Portal-specific UI components
```

### Import Constraints

```json
// nx.json or .eslintrc.js
{
  "@nx/enforce-module-boundaries": [
    "error",
    {
      "depConstraints": [
        {
          "sourceTag": "scope:api",
          "onlyDependOnLibsWithTags": ["scope:shared", "scope:api"]
        },
        {
          "sourceTag": "scope:portal",
          "onlyDependOnLibsWithTags": ["scope:shared", "scope:portal"]
        }
      ]
    }
  ]
}
```

---

## Related Documentation

- [SOLID Principles](SOLID-PRINCIPLES.md) – Object-oriented design principles
- [Architecture](../ARCHITECTURE.md) – Layer structure and dependencies
- [Code Quality](code-quality.md) – Linting and code standards
- [Python Style Guide](python-style-guide.md) – Python-specific patterns
