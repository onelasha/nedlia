# Error Handling Guide

Standardized error handling patterns for Nedlia's Python backend (FastAPI, Lambda workers) and TypeScript frontend.

## Principles

1. **Fail Fast**: Validate early, fail with clear messages
2. **No Silent Failures**: Always log errors, never swallow exceptions
3. **User-Friendly Messages**: External errors are human-readable; internal details stay in logs
4. **Consistent Format**: All APIs return the same error structure
5. **Traceable**: Every error includes a request/correlation ID

---

## Error Response Format

All API errors follow this structure (defined in [API Standards](api-standards.md)):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "request_id": "req_abc123",
    "details": [
      {
        "field": "time_range.start_time",
        "code": "INVALID_VALUE",
        "message": "Start time cannot be negative"
      }
    ]
  }
}
```

| Field        | Type   | Required | Description                          |
| ------------ | ------ | -------- | ------------------------------------ |
| `code`       | string | ✅       | Machine-readable error code          |
| `message`    | string | ✅       | Human-readable description           |
| `request_id` | string | ✅       | Correlation ID for tracing           |
| `details`    | array  | ❌       | Field-level errors (validation only) |

---

## Error Codes

### Standard Codes

| Code                  | HTTP | Description                        |
| --------------------- | ---- | ---------------------------------- |
| `VALIDATION_ERROR`    | 400  | Request validation failed          |
| `INVALID_JSON`        | 400  | Malformed JSON body                |
| `UNAUTHORIZED`        | 401  | Authentication required or invalid |
| `FORBIDDEN`           | 403  | Insufficient permissions           |
| `NOT_FOUND`           | 404  | Resource does not exist            |
| `METHOD_NOT_ALLOWED`  | 405  | HTTP method not supported          |
| `CONFLICT`            | 409  | Business rule conflict             |
| `GONE`                | 410  | Resource permanently deleted       |
| `RATE_LIMITED`        | 429  | Too many requests                  |
| `INTERNAL_ERROR`      | 500  | Unexpected server error            |
| `SERVICE_UNAVAILABLE` | 503  | Downstream service unavailable     |

### Domain-Specific Codes

| Code                     | HTTP | Description                          |
| ------------------------ | ---- | ------------------------------------ |
| `PLACEMENT_OVERLAP`      | 409  | Placement overlaps with existing one |
| `VIDEO_NOT_FOUND`        | 404  | Referenced video does not exist      |
| `PRODUCT_NOT_FOUND`      | 404  | Referenced product does not exist    |
| `CAMPAIGN_EXPIRED`       | 409  | Campaign has ended                   |
| `VALIDATION_IN_PROGRESS` | 409  | Video validation already running     |
| `QUOTA_EXCEEDED`         | 429  | Account quota exceeded               |

---

## Python Exception Hierarchy

### Base Exceptions

```python
# src/core/exceptions.py
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NedliaError(Exception):
    """Base exception for all Nedlia errors."""

    message: str
    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    details: list[dict[str, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        return self.message


@dataclass
class ValidationError(NedliaError):
    """Request validation failed."""

    code: str = "VALIDATION_ERROR"
    status_code: int = 400


@dataclass
class NotFoundError(NedliaError):
    """Resource not found."""

    resource: str = ""
    resource_id: str = ""
    code: str = "NOT_FOUND"
    status_code: int = 404

    def __post_init__(self) -> None:
        if not self.message and self.resource:
            self.message = f"{self.resource} '{self.resource_id}' not found"


@dataclass
class ConflictError(NedliaError):
    """Business rule conflict."""

    code: str = "CONFLICT"
    status_code: int = 409


@dataclass
class UnauthorizedError(NedliaError):
    """Authentication required."""

    message: str = "Authentication required"
    code: str = "UNAUTHORIZED"
    status_code: int = 401


@dataclass
class ForbiddenError(NedliaError):
    """Insufficient permissions."""

    message: str = "Insufficient permissions"
    code: str = "FORBIDDEN"
    status_code: int = 403


@dataclass
class RateLimitError(NedliaError):
    """Rate limit exceeded."""

    retry_after: int = 60
    code: str = "RATE_LIMITED"
    status_code: int = 429

    def __post_init__(self) -> None:
        if not self.message:
            self.message = f"Rate limit exceeded. Retry after {self.retry_after} seconds."
```

### Domain Exceptions

```python
# src/domain/exceptions.py
from dataclasses import dataclass
from uuid import UUID

from src.core.exceptions import ConflictError, NotFoundError


@dataclass
class PlacementOverlapError(ConflictError):
    """Placement overlaps with existing placement."""

    existing_placement_id: UUID | None = None
    overlap_start: float = 0.0
    overlap_end: float = 0.0
    code: str = "PLACEMENT_OVERLAP"

    def __post_init__(self) -> None:
        self.message = "Placement overlaps with existing placement"
        if self.existing_placement_id:
            self.details = [
                {
                    "existing_placement_id": str(self.existing_placement_id),
                    "overlap_range": {
                        "start_time": self.overlap_start,
                        "end_time": self.overlap_end,
                    },
                }
            ]


@dataclass
class VideoNotFoundError(NotFoundError):
    """Video not found."""

    resource: str = "Video"
    code: str = "VIDEO_NOT_FOUND"


@dataclass
class ProductNotFoundError(NotFoundError):
    """Product not found."""

    resource: str = "Product"
    code: str = "PRODUCT_NOT_FOUND"


@dataclass
class CampaignExpiredError(ConflictError):
    """Campaign has expired."""

    code: str = "CAMPAIGN_EXPIRED"
    message: str = "Campaign has ended and cannot be modified"
```

---

## FastAPI Exception Handlers

### Global Exception Handler

```python
# src/core/exception_handlers.py
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from src.core.exceptions import NedliaError
from src.middleware.correlation_id import correlation_id_var

logger = logging.getLogger(__name__)


def create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Create standardized error response."""
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": correlation_id_var.get(""),
        }
    }
    if details:
        body["error"]["details"] = details

    return JSONResponse(status_code=status_code, content=body)


async def nedlia_exception_handler(request: Request, exc: NedliaError) -> JSONResponse:
    """Handle NedliaError exceptions."""
    logger.warning(
        "Business error: %s",
        exc.message,
        extra={
            "error_code": exc.code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )
    return create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details if exc.details else None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        details.append(
            {
                "field": field,
                "code": error["type"].upper().replace(".", "_"),
                "message": error["msg"],
            }
        )

    logger.info(
        "Validation error",
        extra={"validation_errors": details},
    )

    return create_error_response(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        status_code=400,
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(
        "Unhandled exception: %s",
        str(exc),
        extra={"exception_type": type(exc).__name__},
    )

    return create_error_response(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        status_code=500,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers."""
    app.add_exception_handler(NedliaError, nedlia_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

### Registration in Main App

```python
# src/main.py
from fastapi import FastAPI

from src.core.exception_handlers import register_exception_handlers

app = FastAPI(title="Nedlia API")

# Register exception handlers
register_exception_handlers(app)
```

---

## Usage Patterns

### Service Layer

```python
# src/placements/service.py
from uuid import UUID

from src.core.exceptions import NotFoundError
from src.domain.exceptions import PlacementOverlapError, VideoNotFoundError


class PlacementService:
    async def create(self, data: PlacementCreate) -> Placement:
        # Validate video exists
        video = await self.video_repo.find_by_id(data.video_id)
        if not video:
            raise VideoNotFoundError(resource_id=str(data.video_id))

        # Check for overlaps
        existing = await self.repo.find_overlapping(
            video_id=data.video_id,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        if existing:
            raise PlacementOverlapError(
                existing_placement_id=existing.id,
                overlap_start=max(data.start_time, existing.time_range.start_time),
                overlap_end=min(data.end_time, existing.time_range.end_time),
            )

        return await self.repo.save(Placement(**data.model_dump()))
```

### Route Handlers

Routes don't need try/except for business errors—the global handler catches them:

```python
# src/placements/router.py
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/placements", tags=["Placements"])


@router.post("", status_code=201)
async def create_placement(
    request: PlacementCreate,
    service: PlacementService = Depends(get_placement_service),
) -> PlacementResponse:
    # No try/except needed - exceptions bubble up to global handler
    return await service.create(request)
```

### When to Use Try/Except

Use explicit try/except only for:

1. **Recovery logic**: When you can handle the error and continue
2. **Transformation**: Converting external errors to domain errors
3. **Cleanup**: Ensuring resources are released

```python
# ✅ Good - Converting external error to domain error
async def fetch_video_metadata(video_id: UUID) -> VideoMetadata:
    try:
        response = await self.http_client.get(f"/videos/{video_id}")
        response.raise_for_status()
        return VideoMetadata(**response.json())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise VideoNotFoundError(resource_id=str(video_id))
        raise  # Re-raise other HTTP errors


# ❌ Bad - Catching and re-raising without transformation
async def get_placement(placement_id: UUID) -> Placement:
    try:
        return await self.repo.find_by_id(placement_id)
    except NotFoundError:
        raise  # Pointless - let it bubble up
```

---

## Lambda Worker Error Handling

### SQS Handler Pattern

```python
# src/handlers/file_generator.py
import json
import logging
from typing import Any

from src.core.exceptions import NedliaError
from src.tasks.file_generation import generate_placement_file

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """SQS Lambda handler for file generation."""
    failed_records = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            placement_id = body["detail"]["placement_id"]

            logger.info(
                "Processing file generation",
                extra={"placement_id": placement_id, "message_id": message_id},
            )

            generate_placement_file(placement_id)

        except NedliaError as e:
            # Business errors - log and fail the message
            logger.warning(
                "Business error in file generation",
                extra={
                    "error_code": e.code,
                    "message": e.message,
                    "message_id": message_id,
                },
            )
            failed_records.append({"itemIdentifier": message_id})

        except Exception as e:
            # Unexpected errors - log and fail the message
            logger.exception(
                "Unexpected error in file generation",
                extra={"message_id": message_id},
            )
            failed_records.append({"itemIdentifier": message_id})

    # Partial batch failure response
    return {"batchItemFailures": failed_records}
```

### Idempotency

Workers must be idempotent. Use idempotency keys to prevent duplicate processing:

```python
async def process_event(event_id: str, payload: dict) -> None:
    # Check if already processed
    if await self.idempotency_store.exists(event_id):
        logger.info("Event already processed", extra={"event_id": event_id})
        return

    try:
        await self.do_work(payload)
        await self.idempotency_store.mark_processed(event_id)
    except Exception:
        # Don't mark as processed - allow retry
        raise
```

---

## TypeScript Error Handling

### Error Classes

```typescript
// src/core/errors.ts
export class NedliaError extends Error {
  constructor(
    message: string,
    public readonly code: string = 'INTERNAL_ERROR',
    public readonly statusCode: number = 500,
    public readonly details?: Record<string, unknown>[]
  ) {
    super(message);
    this.name = 'NedliaError';
  }
}

export class ValidationError extends NedliaError {
  constructor(message: string, details?: Record<string, unknown>[]) {
    super(message, 'VALIDATION_ERROR', 400, details);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends NedliaError {
  constructor(resource: string, resourceId: string) {
    super(`${resource} '${resourceId}' not found`, 'NOT_FOUND', 404);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends NedliaError {
  constructor(message = 'Authentication required') {
    super(message, 'UNAUTHORIZED', 401);
    this.name = 'UnauthorizedError';
  }
}
```

### API Client Error Handling

```typescript
// src/infrastructure/api-client.ts
import { NedliaError, UnauthorizedError, NotFoundError } from '../core/errors';

interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    request_id: string;
    details?: Record<string, unknown>[];
  };
}

export async function handleApiError(response: Response): Promise<never> {
  const body: ApiErrorResponse = await response.json();
  const { code, message, details } = body.error;

  switch (response.status) {
    case 401:
      throw new UnauthorizedError(message);
    case 404:
      throw new NotFoundError('Resource', 'unknown');
    default:
      throw new NedliaError(message, code, response.status, details);
  }
}
```

### React Error Boundary

```tsx
// src/ui/components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
    // Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? <DefaultErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

---

## Error Logging

All errors should be logged with structured context. See [Logging Standards](logging-standards.md) for details.

```python
# ✅ Good - Structured error logging
logger.warning(
    "Placement creation failed: overlap detected",
    extra={
        "error_code": "PLACEMENT_OVERLAP",
        "video_id": str(video_id),
        "existing_placement_id": str(existing.id),
        "requested_range": {"start": start_time, "end": end_time},
    },
)

# ❌ Bad - Unstructured logging
logger.warning(f"Placement overlap for video {video_id}")
```

---

## Testing Errors

```python
# tests/unit/test_placement_service.py
import pytest
from uuid import uuid4

from src.domain.exceptions import PlacementOverlapError, VideoNotFoundError
from src.placements.service import PlacementService


class TestPlacementService:
    async def test_create_raises_video_not_found(
        self, service: PlacementService
    ) -> None:
        """Test that creating placement for non-existent video raises error."""
        data = PlacementCreate(
            video_id=uuid4(),  # Non-existent
            product_id=uuid4(),
            start_time=0.0,
            end_time=10.0,
        )

        with pytest.raises(VideoNotFoundError) as exc_info:
            await service.create(data)

        assert exc_info.value.code == "VIDEO_NOT_FOUND"
        assert str(data.video_id) in exc_info.value.message

    async def test_create_raises_overlap_error(
        self, service: PlacementService, existing_placement: Placement
    ) -> None:
        """Test that overlapping placement raises error with details."""
        data = PlacementCreate(
            video_id=existing_placement.video_id,
            product_id=uuid4(),
            start_time=5.0,  # Overlaps with existing 0-10
            end_time=15.0,
        )

        with pytest.raises(PlacementOverlapError) as exc_info:
            await service.create(data)

        error = exc_info.value
        assert error.code == "PLACEMENT_OVERLAP"
        assert error.existing_placement_id == existing_placement.id
        assert len(error.details) == 1
```

---

## Related Documentation

- [API Standards](api-standards.md) – Error response format
- [Logging Standards](logging-standards.md) – Error logging patterns
- [Testing Strategy](testing-strategy.md) – Testing error cases
- [Observability](observability.md) – Error monitoring and alerting
