# Python Style Guide

PEP 8 compliant style guide for Nedlia's Python codebase (FastAPI, Lambda workers, services).

## Overview

We follow **PEP 8** with modern tooling:

| Tool       | Purpose              | Config Location  |
| ---------- | -------------------- | ---------------- |
| **Ruff**   | Linting + Formatting | `pyproject.toml` |
| **MyPy**   | Static type checking | `pyproject.toml` |
| **pytest** | Testing              | `pyproject.toml` |

### Why Ruff over Flake8/Black/isort?

Ruff replaces **Flake8 + Black + isort + pyupgrade + autoflake** with a single tool:

| Aspect         | Ruff                     | Flake8 + Black + isort  |
| -------------- | ------------------------ | ----------------------- |
| Speed          | 10-100x faster (Rust)    | Slow (Python)           |
| Tools needed   | 1                        | 3+ separate tools       |
| Config files   | 1 (`pyproject.toml`)     | Multiple configs        |
| Rule coverage  | 800+ rules (superset)    | Fragmented plugins      |
| Auto-fix       | Built-in                 | Requires separate tools |
| Formatting     | Built-in (`ruff format`) | Requires Black          |
| Import sorting | Built-in                 | Requires isort          |
| Maintained by  | Astral (well-funded)     | Volunteers              |

> ⚠️ **Flake8/Black/isort are not used in this project.** Ruff handles all linting and formatting.

---

## Quick Start

```bash
# Install dev dependencies
cd nedlia-back-end/api
uv sync --dev

# Lint code
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type check
uv run mypy src/

# Run all checks
uv run ruff check . && uv run ruff format --check . && uv run mypy src/
```

---

## PEP 8 Rules Enforced

### Naming Conventions

| Type               | Convention         | Example                |
| ------------------ | ------------------ | ---------------------- |
| **Modules**        | `snake_case`       | `placement_service.py` |
| **Packages**       | `snake_case`       | `domain/`              |
| **Classes**        | `PascalCase`       | `PlacementService`     |
| **Functions**      | `snake_case`       | `create_placement()`   |
| **Variables**      | `snake_case`       | `placement_id`         |
| **Constants**      | `UPPER_SNAKE_CASE` | `MAX_RETRIES`          |
| **Type Variables** | `PascalCase`       | `T`, `PlacementT`      |

```python
# ✅ Good
class PlacementService:
    MAX_PLACEMENTS = 100

    def create_placement(self, placement_data: PlacementCreate) -> Placement:
        placement_id = generate_id()
        return Placement(id=placement_id, **placement_data.model_dump())


# ❌ Bad
class placementService:  # Should be PascalCase
    maxPlacements = 100  # Should be UPPER_SNAKE_CASE

    def CreatePlacement(self, PlacementData):  # Should be snake_case
        PlacementId = generate_id()  # Should be snake_case
        return Placement(id=PlacementId)
```

### Line Length

- **Maximum**: 88 characters (Black-compatible)
- **Docstrings**: 72 characters recommended

```python
# ✅ Good - Break long lines
def create_placement(
    video_id: UUID,
    product_id: UUID,
    time_range: TimeRange,
    description: str | None = None,
) -> Placement:
    pass


# ❌ Bad - Line too long
def create_placement(video_id: UUID, product_id: UUID, time_range: TimeRange, description: str | None = None) -> Placement:
    pass
```

### Imports

Order (enforced by isort via Ruff):

1. Standard library
2. Third-party packages
3. Local imports

```python
# ✅ Good
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.placement import Placement, PlacementCreate
from src.infrastructure.database import get_session


# ❌ Bad - Wrong order, mixed imports
from src.domain.placement import Placement
import asyncio
from fastapi import APIRouter
from datetime import datetime
from src.infrastructure.database import get_session
from pydantic import BaseModel
```

### Whitespace

```python
# ✅ Good
def calculate_duration(start: float, end: float) -> float:
    return end - start


result = calculate_duration(10.0, 20.0)
items = [1, 2, 3]
mapping = {"key": "value"}


# ❌ Bad
def calculate_duration( start: float,end: float )->float:  # Spaces around params
    return end-start  # Missing spaces around operator


result = calculate_duration( 10.0, 20.0 )  # Extra spaces
items = [1,2,3]  # Missing spaces after commas
mapping = {"key" : "value"}  # Space before colon
```

### Blank Lines

- **2 blank lines**: Between top-level definitions (classes, functions)
- **1 blank line**: Between method definitions in a class

```python
# ✅ Good
import asyncio


class PlacementService:
    """Service for managing placements."""

    def __init__(self, repository: PlacementRepository) -> None:
        self.repository = repository

    async def create(self, data: PlacementCreate) -> Placement:
        """Create a new placement."""
        return await self.repository.save(data)

    async def get(self, placement_id: UUID) -> Placement | None:
        """Get placement by ID."""
        return await self.repository.find_by_id(placement_id)


class VideoService:
    """Service for managing videos."""
    pass
```

---

## Type Hints

### Required Everywhere

All functions must have type hints (enforced by MyPy strict mode):

```python
# ✅ Good
from typing import Any


def process_event(event: dict[str, Any]) -> bool:
    return True


async def get_placement(placement_id: UUID) -> Placement | None:
    pass


# ❌ Bad - Missing type hints
def process_event(event):
    return True


async def get_placement(placement_id):
    pass
```

### Common Patterns

```python
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

# Optional values (Python 3.10+)
def get_user(user_id: str) -> User | None:
    pass


# Collections
def process_items(items: list[str]) -> dict[str, int]:
    pass


# Callable
Handler = Callable[[dict[str, Any]], bool]


# Generic types
T = TypeVar("T")


def first(items: Sequence[T]) -> T | None:
    return items[0] if items else None


# TYPE_CHECKING for circular imports
if TYPE_CHECKING:
    from src.domain.placement import Placement
```

---

## Docstrings

We use **Google-style** docstrings:

```python
def create_placement(
    video_id: UUID,
    product_id: UUID,
    time_range: TimeRange,
    description: str | None = None,
) -> Placement:
    """Create a new placement for a video.

    Creates a placement record linking a product to a specific time range
    within a video. The placement is initially created in 'draft' status.

    Args:
        video_id: The unique identifier of the video.
        product_id: The unique identifier of the product to place.
        time_range: The time range within the video for the placement.
        description: Optional description of the placement.

    Returns:
        The newly created Placement object.

    Raises:
        ValidationError: If the time range is invalid.
        NotFoundError: If the video or product doesn't exist.

    Example:
        >>> placement = create_placement(
        ...     video_id=UUID("..."),
        ...     product_id=UUID("..."),
        ...     time_range=TimeRange(start=10.0, end=20.0),
        ... )
    """
    pass


class PlacementService:
    """Service for managing product placements.

    This service handles the business logic for creating, updating,
    and retrieving placements. It coordinates between the domain
    layer and infrastructure.

    Attributes:
        repository: The placement repository for data access.
        event_publisher: Publisher for domain events.

    Example:
        >>> service = PlacementService(repository, publisher)
        >>> placement = await service.create(data)
    """

    def __init__(
        self,
        repository: PlacementRepository,
        event_publisher: EventPublisher,
    ) -> None:
        """Initialize the placement service.

        Args:
            repository: Repository for placement data access.
            event_publisher: Publisher for domain events.
        """
        self.repository = repository
        self.event_publisher = event_publisher
```

---

## FastAPI Patterns

### Project Structure

Organize FastAPI applications by **feature/domain**, not by technical layer:

```
src/
├── main.py                      # App entry point, middleware registration
├── config.py                    # Settings and configuration
├── dependencies.py              # Shared dependencies (DB, auth, etc.)
│
├── placements/                  # Feature module
│   ├── __init__.py
│   ├── router.py                # Route definitions
│   ├── schemas.py               # Pydantic request/response models
│   ├── service.py               # Business logic
│   ├── repository.py            # Data access
│   └── dependencies.py          # Feature-specific dependencies
│
├── videos/                      # Another feature module
│   ├── router.py
│   ├── schemas.py
│   └── ...
│
├── middleware/                  # Custom middleware
│   ├── __init__.py
│   ├── logging.py
│   ├── timing.py
│   └── correlation_id.py
│
└── core/                        # Shared utilities
    ├── exceptions.py
    ├── security.py
    └── database.py
```

### Middleware vs Dependencies

| Concern                      | Use Middleware | Use Dependencies         |
| ---------------------------- | -------------- | ------------------------ |
| **Request logging**          | ✅             |                          |
| **Correlation ID injection** | ✅             |                          |
| **Response timing**          | ✅             |                          |
| **CORS**                     | ✅             |                          |
| **Authentication**           |                | ✅ (per-route control)   |
| **Authorization**            |                | ✅ (role-based)          |
| **Database sessions**        |                | ✅ (request-scoped)      |
| **Service injection**        |                | ✅                       |
| **Rate limiting**            | ✅ or ✅       | (depends on granularity) |

**Rule of thumb:**

- **Middleware**: Runs on ALL requests, no access to route-specific info
- **Dependencies**: Runs per-route, can be selective, supports DI

### Middleware Examples

```python
# src/middleware/correlation_id.py
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to all requests for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_var.set(correlation_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


# src/middleware/timing.py
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TimingMiddleware(BaseHTTPMiddleware):
    """Add request timing headers."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response
```

### Lifespan: Resource Allocation & Deallocation

The **lifespan** context manager handles resource initialization (startup) and cleanup (shutdown). This is the recommended pattern for:

| Resource             | Startup                  | Shutdown                |
| -------------------- | ------------------------ | ----------------------- |
| **Database pool**    | Create connection pool   | Close all connections   |
| **Redis/Cache**      | Connect to Redis         | Close connection        |
| **HTTP clients**     | Create httpx.AsyncClient | Close client            |
| **AWS clients**      | Initialize boto3 session | (stateless, no cleanup) |
| **Background tasks** | Start scheduler          | Cancel pending tasks    |
| **ML models**        | Load into memory         | Free memory             |

```python
# src/core/lifespan.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from redis.asyncio import Redis

from src.core.config import settings


# Global resources (initialized in lifespan, accessed via app.state)
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifecycle resources.

    Resources are stored in app.state for access in dependencies.
    """
    # =========================================================================
    # STARTUP: Initialize resources
    # =========================================================================

    # Database connection pool
    app.state.db_engine: AsyncEngine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,   # Recycle connections after 1 hour
    )

    # Redis connection
    app.state.redis: Redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )

    # HTTP client for external API calls
    app.state.http_client: httpx.AsyncClient = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_connections=100),
    )

    print("✅ Application startup complete")

    # =========================================================================
    # YIELD: Application runs here
    # =========================================================================
    yield

    # =========================================================================
    # SHUTDOWN: Cleanup resources (reverse order of initialization)
    # =========================================================================

    # Close HTTP client
    await app.state.http_client.aclose()

    # Close Redis connection
    await app.state.redis.close()

    # Dispose database engine (closes all pooled connections)
    await app.state.db_engine.dispose()

    print("✅ Application shutdown complete")
```

### Accessing Lifespan Resources in Dependencies

```python
# src/core/dependencies.py
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis
import httpx


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Get database session from the connection pool."""
    engine = request.app.state.db_engine
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_redis(request: Request) -> Redis:
    """Get Redis client from app state."""
    return request.app.state.redis


async def get_http_client(request: Request) -> httpx.AsyncClient:
    """Get HTTP client from app state."""
    return request.app.state.http_client


# Type aliases for cleaner route signatures
DBSession = Annotated[AsyncSession, Depends(get_db_session)]
RedisClient = Annotated[Redis, Depends(get_redis)]
HTTPClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
```

### Using Resources in Routes

```python
# src/placements/router.py
from src.core.dependencies import DBSession, RedisClient

@router.get("/{placement_id}")
async def get_placement(
    placement_id: UUID,
    db: DBSession,
    redis: RedisClient,
) -> PlacementResponse:
    # Check cache first
    cached = await redis.get(f"placement:{placement_id}")
    if cached:
        return PlacementResponse.model_validate_json(cached)

    # Query database
    result = await db.execute(
        select(Placement).where(Placement.id == placement_id)
    )
    placement = result.scalar_one_or_none()

    if placement:
        # Cache for 5 minutes
        await redis.setex(
            f"placement:{placement_id}",
            300,
            PlacementResponse.from_orm(placement).model_dump_json(),
        )

    return placement
```

### Best Practices for Resource Management

1. **Initialize once, reuse everywhere** - Create pools/clients in lifespan, not per-request
2. **Use connection pools** - Never create new DB connections per request
3. **Set timeouts** - Always configure timeouts for external resources
4. **Graceful shutdown** - Close resources in reverse order of initialization
5. **Health checks** - Verify resource health before marking app as ready

```python
# src/health/router.py
@router.get("/health/ready")
async def readiness_check(
    request: Request,
    db: DBSession,
    redis: RedisClient,
) -> dict:
    """Check if all resources are healthy."""
    checks = {}

    # Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Redis check
    try:
        await redis.ping()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    all_healthy = all(v == "healthy" for v in checks.values())

    if not all_healthy:
        raise HTTPException(status_code=503, detail=checks)

    return {"status": "ready", "checks": checks}
```

### App Entry Point with Lifespan

```python
# src/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.lifespan import lifespan
from src.middleware.correlation_id import CorrelationIdMiddleware
from src.middleware.timing import TimingMiddleware
from src.placements.router import router as placements_router
from src.videos.router import router as videos_router


app = FastAPI(
    title="Nedlia API",
    version="1.0.0",
    lifespan=lifespan,
)

# =============================================================================
# Middleware (order matters - first added = outermost)
# =============================================================================
app.add_middleware(TimingMiddleware)           # Outermost - times entire request
app.add_middleware(CorrelationIdMiddleware)    # Add correlation ID early
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.nedlia.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Routers
# =============================================================================
app.include_router(placements_router, prefix="/api/v1")
app.include_router(videos_router, prefix="/api/v1")
```

### Router Pattern (Separate Files + include_router)

Each feature has its own router file. The main app includes all routers:

```python
# src/main.py
from fastapi import FastAPI

from src.placements.router import router as placements_router
from src.videos.router import router as videos_router
from src.products.router import router as products_router

app = FastAPI(title="Nedlia API")

# Include all feature routers
app.include_router(placements_router, prefix="/api/v1")
app.include_router(videos_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
```

Each router file defines routes for ONE feature:

```python
# src/placements/router.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.placements.service import PlacementService
from src.placements.schemas import PlacementCreate, PlacementResponse
from src.placements.dependencies import get_placement_service

# Router for this feature only - prefix set here or in include_router
router = APIRouter(prefix="/placements", tags=["Placements"])


class PlacementCreate(BaseModel):
    """Request model for creating a placement."""

    video_id: UUID
    product_id: UUID
    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., gt=0, description="End time in seconds")
    description: str | None = Field(None, max_length=500)


class PlacementResponse(BaseModel):
    """Response model for a placement."""

    id: UUID
    video_id: UUID
    product_id: UUID
    start_time: float
    end_time: float
    status: str
    created_at: str

    model_config = {"from_attributes": True}


@router.post(
    "",
    response_model=PlacementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a placement",
    description="Create a new product placement for a video.",
)
async def create_placement(
    request: PlacementCreate,
    service: Annotated[PlacementService, Depends(get_placement_service)],
) -> Placement:
    """Create a new placement."""
    return await service.create(request)


@router.get(
    "/{placement_id}",
    response_model=PlacementResponse,
    summary="Get a placement",
)
async def get_placement(
    placement_id: UUID,
    service: Annotated[PlacementService, Depends(get_placement_service)],
) -> Placement:
    """Get a placement by ID."""
    placement = await service.get(placement_id)
    if not placement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Placement {placement_id} not found",
        )
    return placement


@router.get(
    "",
    response_model=list[PlacementResponse],
    summary="List placements",
)
async def list_placements(
    service: Annotated[PlacementService, Depends(get_placement_service)],
    video_id: UUID | None = Query(None, description="Filter by video"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[Placement]:
    """List placements with optional filters."""
    return await service.list(video_id=video_id, limit=limit, offset=offset)
```

### Dependency Injection

```python
# src/interface/dependencies.py
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.placement_service import PlacementService
from src.infrastructure.database import async_session_maker
from src.infrastructure.repositories.placement import PlacementRepository


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_maker() as session:
        yield session


async def get_placement_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PlacementRepository:
    """Get placement repository."""
    return PlacementRepository(session)


async def get_placement_service(
    repository: Annotated[PlacementRepository, Depends(get_placement_repository)],
) -> PlacementService:
    """Get placement service."""
    return PlacementService(repository)
```

### Error Handling

```python
# src/interface/exceptions.py
from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} {resource_id} not found",
        )


class ValidationError(HTTPException):
    """Validation error."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        )


class ConflictError(HTTPException):
    """Resource conflict."""

    def __init__(self, message: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        )
```

---

## Domain Layer Patterns

### Entities

```python
# src/domain/placement.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class PlacementStatus(str, Enum):
    """Placement status."""

    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class TimeRange:
    """Value object for time range."""

    start_time: float
    end_time: float

    def __post_init__(self) -> None:
        """Validate time range."""
        if self.start_time < 0:
            raise ValueError("start_time must be non-negative")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be greater than start_time")

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        return self.end_time - self.start_time


@dataclass
class Placement:
    """Placement aggregate root."""

    video_id: UUID
    product_id: UUID
    time_range: TimeRange
    id: UUID = field(default_factory=uuid4)
    status: PlacementStatus = PlacementStatus.DRAFT
    description: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def activate(self) -> None:
        """Activate the placement."""
        if self.status != PlacementStatus.DRAFT:
            raise ValueError("Can only activate draft placements")
        self.status = PlacementStatus.ACTIVE
        self.updated_at = datetime.utcnow()

    def archive(self) -> None:
        """Archive the placement."""
        self.status = PlacementStatus.ARCHIVED
        self.updated_at = datetime.utcnow()
```

### Repository Interface

```python
# src/domain/repositories.py
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.placement import Placement


class PlacementRepository(ABC):
    """Abstract repository for placements."""

    @abstractmethod
    async def save(self, placement: Placement) -> Placement:
        """Save a placement."""
        ...

    @abstractmethod
    async def find_by_id(self, placement_id: UUID) -> Placement | None:
        """Find placement by ID."""
        ...

    @abstractmethod
    async def find_by_video(
        self,
        video_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Placement]:
        """Find placements by video ID."""
        ...

    @abstractmethod
    async def delete(self, placement_id: UUID) -> bool:
        """Delete a placement."""
        ...
```

---

## Testing Patterns

```python
# tests/unit/test_placement.py
import pytest
from uuid import uuid4

from src.domain.placement import Placement, PlacementStatus, TimeRange


class TestTimeRange:
    """Tests for TimeRange value object."""

    def test_valid_time_range(self) -> None:
        """Test creating a valid time range."""
        time_range = TimeRange(start_time=10.0, end_time=20.0)

        assert time_range.start_time == 10.0
        assert time_range.end_time == 20.0
        assert time_range.duration == 10.0

    def test_negative_start_time_raises_error(self) -> None:
        """Test that negative start time raises ValueError."""
        with pytest.raises(ValueError, match="start_time must be non-negative"):
            TimeRange(start_time=-1.0, end_time=10.0)

    def test_end_before_start_raises_error(self) -> None:
        """Test that end before start raises ValueError."""
        with pytest.raises(ValueError, match="end_time must be greater"):
            TimeRange(start_time=20.0, end_time=10.0)


class TestPlacement:
    """Tests for Placement aggregate."""

    @pytest.fixture
    def placement(self) -> Placement:
        """Create a test placement."""
        return Placement(
            video_id=uuid4(),
            product_id=uuid4(),
            time_range=TimeRange(start_time=0.0, end_time=30.0),
        )

    def test_default_status_is_draft(self, placement: Placement) -> None:
        """Test that new placements are in draft status."""
        assert placement.status == PlacementStatus.DRAFT

    def test_activate_changes_status(self, placement: Placement) -> None:
        """Test activating a placement."""
        placement.activate()

        assert placement.status == PlacementStatus.ACTIVE

    def test_cannot_activate_non_draft(self, placement: Placement) -> None:
        """Test that only draft placements can be activated."""
        placement.activate()

        with pytest.raises(ValueError, match="Can only activate draft"):
            placement.activate()
```

---

## Running Checks

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### CI Pipeline

```yaml
# .github/workflows/python-lint.yml
name: Python Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync --dev
        working-directory: nedlia-back-end/api

      - name: Ruff check
        run: uv run ruff check .
        working-directory: nedlia-back-end/api

      - name: Ruff format check
        run: uv run ruff format --check .
        working-directory: nedlia-back-end/api

      - name: MyPy
        run: uv run mypy src/
        working-directory: nedlia-back-end/api
```

---

## IDE Setup

### VS Code Settings

```json
// .vscode/settings.json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "strict",
  "ruff.lint.args": ["--config=pyproject.toml"],
  "ruff.format.args": ["--config=pyproject.toml"]
}
```

### Required Extensions

- **Ruff** (`charliermarsh.ruff`) - Linting & formatting
- **Pylance** (`ms-python.vscode-pylance`) - Type checking
- **Python** (`ms-python.python`) - Python support

---

## Related Documentation

- [Code Quality](code-quality.md) – Overall quality standards
- [Testing Strategy](testing-strategy.md) – Testing patterns
- [API Standards](api-standards.md) – API design patterns
