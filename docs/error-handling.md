# Error Handling Guide

Standardized error handling patterns for Nedlia's Python backend (FastAPI, Lambda workers) and TypeScript frontend using **industry standards**.

## Table of Contents

- [Principles](#principles)
- [Error Response Format (RFC 9457)](#error-response-format-rfc-9457)
- [Problem Type Registry](#problem-type-registry)
- [Python Exception Hierarchy (RFC 9457)](#python-exception-hierarchy-rfc-9457)
- [FastAPI Exception Handlers (RFC 9457)](#fastapi-exception-handlers-rfc-9457)
- [Usage Patterns](#usage-patterns)
- [Lambda Worker Error Handling (AWS Standard)](#lambda-worker-error-handling-aws-standard)
- [TypeScript Error Handling (RFC 9457)](#typescript-error-handling-rfc-9457)
- [Error Logging](#error-logging)
- [Testing Errors](#testing-errors)
- [Related Documentation](#related-documentation)

---

## Principles

1. **Fail Fast**: Validate early, fail with clear messages
2. **No Silent Failures**: Always log errors, never swallow exceptions
3. **User-Friendly Messages**: External errors are human-readable; internal details stay in logs
4. **Standards-Based**: Use RFC 9457 Problem Details for API errors
5. **Traceable**: Every error includes correlation ID via W3C Trace Context

---

## Error Response Format (RFC 9457)

All API errors follow **[RFC 9457 Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)**:

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Your request contains invalid fields.",
  "instance": "/v1/placements",
  "errors": [
    {
      "pointer": "#/time_range/start_time",
      "detail": "must be a non-negative number"
    }
  ]
}
```

| Field      | Type    | Required | Description                                       |
| ---------- | ------- | -------- | ------------------------------------------------- |
| `type`     | URI     | ✅       | URI identifying the problem type                  |
| `title`    | string  | ✅       | Short, human-readable summary (constant per type) |
| `status`   | integer | ✅       | HTTP status code                                  |
| `detail`   | string  | ❌       | Human-readable explanation of this occurrence     |
| `instance` | URI     | ❌       | URI identifying this specific occurrence          |

---

## Problem Type Registry

Problem types are defined at `https://api.nedlia.com/problems/`:

### Standard Problem Types

| Problem Type URI                                      | Title                 | Status |
| ----------------------------------------------------- | --------------------- | ------ |
| `https://api.nedlia.com/problems/validation-error`    | Validation Error      | 422    |
| `https://api.nedlia.com/problems/unauthorized`        | Unauthorized          | 401    |
| `https://api.nedlia.com/problems/forbidden`           | Forbidden             | 403    |
| `https://api.nedlia.com/problems/not-found`           | Resource Not Found    | 404    |
| `https://api.nedlia.com/problems/conflict`            | Conflict              | 409    |
| `https://api.nedlia.com/problems/rate-limited`        | Rate Limit Exceeded   | 429    |
| `https://api.nedlia.com/problems/internal-error`      | Internal Server Error | 500    |
| `https://api.nedlia.com/problems/service-unavailable` | Service Unavailable   | 503    |
| `about:blank`                                         | (HTTP status title)   | varies |

### Domain-Specific Problem Types

| Problem Type URI                                         | Title                  | Status |
| -------------------------------------------------------- | ---------------------- | ------ |
| `https://api.nedlia.com/problems/placement-overlap`      | Placement Overlap      | 409    |
| `https://api.nedlia.com/problems/video-not-found`        | Video Not Found        | 404    |
| `https://api.nedlia.com/problems/product-not-found`      | Product Not Found      | 404    |
| `https://api.nedlia.com/problems/campaign-expired`       | Campaign Expired       | 409    |
| `https://api.nedlia.com/problems/validation-in-progress` | Validation In Progress | 409    |
| `https://api.nedlia.com/problems/quota-exceeded`         | Quota Exceeded         | 429    |

---

## Python Exception Hierarchy (RFC 9457)

### Base Exceptions

```python
# src/core/exceptions.py
from dataclasses import dataclass, field
from typing import Any

# Problem type base URI
PROBLEM_BASE_URI = "https://api.nedlia.com/problems"


@dataclass
class ProblemException(Exception):
    """Base exception mapping to RFC 9457 Problem Details."""

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.detail or self.title


@dataclass
class ValidationException(ProblemException):
    """Request validation failed."""

    type: str = f"{PROBLEM_BASE_URI}/validation-error"
    title: str = "Validation Error"
    status: int = 422
    errors: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.errors:
            self.extensions["errors"] = self.errors


@dataclass
class NotFoundException(ProblemException):
    """Resource not found."""

    type: str = f"{PROBLEM_BASE_URI}/not-found"
    title: str = "Resource Not Found"
    status: int = 404
    resource_type: str = ""
    resource_id: str = ""

    def __post_init__(self) -> None:
        if not self.detail and self.resource_type:
            self.detail = f"{self.resource_type} '{self.resource_id}' not found"


@dataclass
class ConflictException(ProblemException):
    """Business rule conflict."""

    type: str = f"{PROBLEM_BASE_URI}/conflict"
    title: str = "Conflict"
    status: int = 409


@dataclass
class UnauthorizedException(ProblemException):
    """Authentication required."""

    type: str = f"{PROBLEM_BASE_URI}/unauthorized"
    title: str = "Unauthorized"
    status: int = 401
    detail: str = "Authentication required"


@dataclass
class ForbiddenException(ProblemException):
    """Insufficient permissions."""

    type: str = f"{PROBLEM_BASE_URI}/forbidden"
    title: str = "Forbidden"
    status: int = 403
    detail: str = "Insufficient permissions"


@dataclass
class RateLimitException(ProblemException):
    """Rate limit exceeded."""

    type: str = f"{PROBLEM_BASE_URI}/rate-limited"
    title: str = "Rate Limit Exceeded"
    status: int = 429
    retry_after: int = 60

    def __post_init__(self) -> None:
        if not self.detail:
            self.detail = f"Rate limit exceeded. Retry after {self.retry_after} seconds."
        self.extensions["retry_after"] = self.retry_after
```

### Domain Exceptions

```python
# src/domain/exceptions.py
from dataclasses import dataclass
from uuid import UUID

from src.core.exceptions import ConflictException, NotFoundException, PROBLEM_BASE_URI


@dataclass
class PlacementOverlapException(ConflictException):
    """Placement overlaps with existing placement."""

    type: str = f"{PROBLEM_BASE_URI}/placement-overlap"
    title: str = "Placement Overlap"
    existing_placement_id: UUID | None = None
    overlap_start: float = 0.0
    overlap_end: float = 0.0

    def __post_init__(self) -> None:
        self.detail = "Placement overlaps with an existing placement"
        if self.existing_placement_id:
            self.extensions["existing_placement_id"] = str(self.existing_placement_id)
            self.extensions["overlap_range"] = {
                "start_time": self.overlap_start,
                "end_time": self.overlap_end,
            }


@dataclass
class VideoNotFoundException(NotFoundException):
    """Video not found."""

    type: str = f"{PROBLEM_BASE_URI}/video-not-found"
    title: str = "Video Not Found"
    resource_type: str = "Video"


@dataclass
class ProductNotFoundException(NotFoundException):
    """Product not found."""

    type: str = f"{PROBLEM_BASE_URI}/product-not-found"
    title: str = "Product Not Found"
    resource_type: str = "Product"


@dataclass
class CampaignExpiredException(ConflictException):
    """Campaign has expired."""

    type: str = f"{PROBLEM_BASE_URI}/campaign-expired"
    title: str = "Campaign Expired"
    detail: str = "Campaign has ended and cannot be modified"
```

---

## FastAPI Exception Handlers (RFC 9457)

### Global Exception Handler

```python
# src/core/exception_handlers.py
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.exceptions import ProblemException

logger = logging.getLogger(__name__)

PROBLEM_CONTENT_TYPE = "application/problem+json"


def create_problem_response(
    type: str,
    title: str,
    status: int,
    detail: str | None = None,
    instance: str | None = None,
    extensions: dict[str, Any] | None = None,
) -> JSONResponse:
    """Create RFC 9457 Problem Details response."""
    body: dict[str, Any] = {
        "type": type,
        "title": title,
        "status": status,
    }
    if detail:
        body["detail"] = detail
    if instance:
        body["instance"] = instance
    if extensions:
        body.update(extensions)

    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_CONTENT_TYPE,
    )


async def problem_exception_handler(request: Request, exc: ProblemException) -> JSONResponse:
    """Handle ProblemException and return RFC 9457 response."""
    logger.warning(
        "Problem: %s",
        exc.title,
        extra={
            "problem_type": exc.type,
            "status": exc.status,
            "detail": exc.detail,
            "path": str(request.url.path),
        },
    )
    return create_problem_response(
        type=exc.type,
        title=exc.title,
        status=exc.status,
        detail=exc.detail,
        instance=str(request.url.path),
        extensions=exc.extensions if exc.extensions else None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors as RFC 9457 with JSON Pointers."""
    errors = []
    for error in exc.errors():
        # Convert Pydantic loc to JSON Pointer (RFC 6901)
        pointer = "#/" + "/".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "pointer": pointer,
            "detail": error["msg"],
        })

    logger.info(
        "Validation error",
        extra={"validation_errors": errors},
    )

    return create_problem_response(
        type="https://api.nedlia.com/problems/validation-error",
        title="Validation Error",
        status=422,
        detail="Your request contains invalid fields.",
        instance=str(request.url.path),
        extensions={"errors": errors},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions as RFC 9457."""
    logger.exception(
        "Unhandled exception: %s",
        str(exc),
        extra={"exception_type": type(exc).__name__},
    )

    return create_problem_response(
        type="https://api.nedlia.com/problems/internal-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred.",
        instance=str(request.url.path),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers."""
    app.add_exception_handler(ProblemException, problem_exception_handler)
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

from src.domain.exceptions import (
    PlacementOverlapException,
    VideoNotFoundException,
)


class PlacementService:
    async def create(self, data: PlacementCreate) -> Placement:
        # Validate video exists
        video = await self.video_repo.find_by_id(data.video_id)
        if not video:
            raise VideoNotFoundException(resource_id=str(data.video_id))

        # Check for overlaps
        existing = await self.repo.find_overlapping(
            video_id=data.video_id,
            start_time=data.start_time,
            end_time=data.end_time,
        )
        if existing:
            raise PlacementOverlapException(
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
            raise VideoNotFoundException(resource_id=str(video_id))
        raise  # Re-raise other HTTP errors


# ❌ Bad - Catching and re-raising without transformation
async def get_placement(placement_id: UUID) -> Placement:
    try:
        return await self.repo.find_by_id(placement_id)
    except NotFoundException:
        raise  # Pointless - let it bubble up
```

---

## Lambda Worker Error Handling (AWS Standard)

Uses **[AWS Lambda Partial Batch Response](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)** for SQS event sources.

### SQS Handler Pattern

```python
# src/handlers/file_generator.py
import json
import logging
from typing import Any

from src.core.exceptions import ProblemException
from src.tasks.file_generation import generate_placement_file

logger = logging.getLogger(__name__)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    SQS Lambda handler with AWS Partial Batch Response.

    Returns batchItemFailures - AWS will only retry failed messages.
    """
    batch_item_failures: list[dict[str, str]] = []

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

        except ProblemException as e:
            # Business errors - log and fail the message
            logger.warning(
                "Business error in file generation",
                extra={
                    "problem_type": e.type,
                    "detail": e.detail,
                    "message_id": message_id,
                },
            )
            batch_item_failures.append({"itemIdentifier": message_id})

        except Exception as e:
            # Unexpected errors - log and fail the message
            logger.exception(
                "Unexpected error in file generation",
                extra={"message_id": message_id},
            )
            batch_item_failures.append({"itemIdentifier": message_id})

    # AWS Lambda Partial Batch Response format
    return {"batchItemFailures": batch_item_failures}
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

## TypeScript Error Handling (RFC 9457)

### Error Classes

```typescript
// src/core/errors.ts

/** RFC 9457 Problem Details structure */
interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  [key: string]: unknown; // Extension fields
}

export class NedliaError extends Error {
  constructor(
    public readonly type: string,
    public readonly title: string,
    public readonly status: number,
    public readonly detail?: string,
    public readonly instance?: string,
    public readonly extensions?: Record<string, unknown>
  ) {
    super(detail ?? title);
    this.name = 'NedliaError';
  }

  get isRetryable(): boolean {
    return this.status === 429 || this.status >= 500;
  }

  static fromProblemDetail(problem: ProblemDetail): NedliaError {
    const { type, title, status, detail, instance, ...extensions } = problem;

    if (type.includes('validation-error')) {
      return new ValidationError(problem);
    }
    if (type.includes('not-found')) {
      return new NotFoundError(type, title, status, detail, instance);
    }
    if (type.includes('unauthorized')) {
      return new UnauthorizedError(detail);
    }
    if (type.includes('rate-limited')) {
      return new RateLimitError(problem);
    }

    return new NedliaError(type, title, status, detail, instance, extensions);
  }
}

export class ValidationError extends NedliaError {
  readonly errors?: Array<{ pointer: string; detail: string }>;

  constructor(problem: ProblemDetail & { errors?: Array<{ pointer: string; detail: string }> }) {
    super(problem.type, problem.title, problem.status, problem.detail, problem.instance);
    this.name = 'ValidationError';
    this.errors = problem.errors;
  }
}

export class NotFoundError extends NedliaError {
  constructor(
    type: string = 'https://api.nedlia.com/problems/not-found',
    title: string = 'Resource Not Found',
    status: number = 404,
    detail?: string,
    instance?: string
  ) {
    super(type, title, status, detail, instance);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends NedliaError {
  constructor(detail: string = 'Authentication required') {
    super('https://api.nedlia.com/problems/unauthorized', 'Unauthorized', 401, detail);
    this.name = 'UnauthorizedError';
  }
}

export class RateLimitError extends NedliaError {
  readonly retryAfter: number;

  constructor(problem: ProblemDetail & { retry_after?: number }) {
    super(problem.type, problem.title, problem.status, problem.detail, problem.instance);
    this.name = 'RateLimitError';
    this.retryAfter = problem.retry_after ?? 60;
  }
}
```

### API Client Error Handling

```typescript
// src/infrastructure/api-client.ts
import { NedliaError } from '../core/errors';

const PROBLEM_CONTENT_TYPE = 'application/problem+json';

export async function handleApiError(response: Response): Promise<never> {
  const contentType = response.headers.get('content-type') ?? '';

  if (contentType.includes(PROBLEM_CONTENT_TYPE) || contentType.includes('application/json')) {
    const problemDetail = await response.json();
    throw NedliaError.fromProblemDetail(problemDetail);
  }

  // Fallback for non-JSON errors
  throw new NedliaError('about:blank', response.statusText, response.status, await response.text());
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

from src.domain.exceptions import PlacementOverlapException, VideoNotFoundException
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

        with pytest.raises(VideoNotFoundException) as exc_info:
            await service.create(data)

        error = exc_info.value
        assert "video-not-found" in error.type
        assert error.status == 404

    async def test_create_raises_overlap_error(
        self, service: PlacementService, existing_placement: Placement
    ) -> None:
        """Test that overlapping placement raises error with RFC 9457 extensions."""
        data = PlacementCreate(
            video_id=existing_placement.video_id,
            product_id=uuid4(),
            start_time=5.0,  # Overlaps with existing 0-10
            end_time=15.0,
        )

        with pytest.raises(PlacementOverlapException) as exc_info:
            await service.create(data)

        error = exc_info.value
        assert "placement-overlap" in error.type
        assert error.status == 409
        assert error.extensions["existing_placement_id"] == str(existing_placement.id)
```

---

## Related Documentation

- [Error Handling Strategy by Project Type](error-handling-strategy.md) – Project-specific error handling (APIs, Workers, SDKs, Plugins, Frontend)
- [API Standards](api-standards.md) – Error response format
- [Logging Standards](logging-standards.md) – Error logging patterns
- [Testing Strategy](testing-strategy.md) – Testing error cases
- [Observability](observability.md) – Error monitoring and alerting
- [Resilience Patterns](resilience-patterns.md) – Circuit breakers, retries, fallbacks
