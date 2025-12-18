# Error Handling Strategy by Project Type

Comprehensive error handling strategies for all Nedlia project types using **industry standards**. This document provides project-specific guidance while referencing the core [Error Handling Guide](error-handling.md) and [Resilience Patterns](resilience-patterns.md).

## Table of Contents

- [Standards Reference](#standards-reference)
- [1. API Services (FastAPI)](#1-api-services-fastapi)
- [2. Lambda Workers (Event-Driven)](#2-lambda-workers-event-driven)
- [3. JavaScript SDK (TypeScript)](#3-javascript-sdk-typescript)
- [4. Python SDK](#4-python-sdk)
- [5. Swift SDK](#5-swift-sdk)
- [6. Editor Plugins (Swift)](#6-editor-plugins-swift)
- [7. Frontend (React Portal)](#7-frontend-react-portal)
- [Cross-Cutting Standards](#cross-cutting-standards)
- [Related Documentation](#related-documentation)
- [References](#references)

---

## Standards Reference

| Project Type      | Standard/Pattern                                            |
| ----------------- | ----------------------------------------------------------- |
| API Services      | **RFC 9457** Problem Details for HTTP APIs                  |
| Lambda Workers    | **AWS Lambda Partial Batch Response** + CloudEvents         |
| JavaScript SDK    | **Typed Exceptions** + Exponential Backoff (AWS SDK style)  |
| Python SDK        | **Exception Hierarchy** + Tenacity (standard retry lib)     |
| Swift SDK         | **Swift Result Type** + Structured Concurrency              |
| Editor Plugins    | **Apple Human Interface Guidelines** for error presentation |
| Frontend (Portal) | **React Error Boundaries** + React Query error handling     |

---

## 1. API Services (FastAPI)

**Location**: `nedlia-back-end/services/`, `nedlia-back-end/api/`

### Standard: RFC 9457 Problem Details for HTTP APIs

Nedlia APIs implement **[RFC 9457](https://www.rfc-editor.org/rfc/rfc9457.html)** (successor to RFC 7807) — the IETF standard for machine-readable error responses.

#### Why RFC 9457?

- **IETF Standard**: Industry-recognized specification
- **Interoperability**: Supported by API gateways, monitoring tools, and client libraries
- **Extensibility**: Custom fields via extension members
- **Multiple errors**: JSON Pointer support for field-level validation errors
- **Content negotiation**: `application/problem+json` media type

#### Response Format

```http
HTTP/1.1 403 Forbidden
Content-Type: application/problem+json
Content-Language: en

{
  "type": "https://api.nedlia.com/problems/insufficient-credit",
  "title": "Insufficient Credit",
  "status": 403,
  "detail": "Your current balance is 30, but that costs 50.",
  "instance": "/v1/placements/123e4567-e89b-12d3-a456-426614174000",
  "balance": 30,
  "cost": 50
}
```

#### Required Fields

| Field      | Type    | Required | Description                                       |
| ---------- | ------- | -------- | ------------------------------------------------- |
| `type`     | URI     | Yes      | URI identifying the problem type                  |
| `title`    | string  | Yes      | Short, human-readable summary (constant per type) |
| `status`   | integer | Yes      | HTTP status code                                  |
| `detail`   | string  | No       | Human-readable explanation of this occurrence     |
| `instance` | URI     | No       | URI identifying this specific occurrence          |

#### Problem Type Registry

Define problem types at `https://api.nedlia.com/problems/`:

| Problem Type URI                                      | Title                 | Status | When to Use                     |
| ----------------------------------------------------- | --------------------- | ------ | ------------------------------- |
| `https://api.nedlia.com/problems/validation-error`    | Validation Error      | 400    | Request validation failed       |
| `https://api.nedlia.com/problems/unauthorized`        | Unauthorized          | 401    | Authentication required/invalid |
| `https://api.nedlia.com/problems/forbidden`           | Forbidden             | 403    | Insufficient permissions        |
| `https://api.nedlia.com/problems/not-found`           | Resource Not Found    | 404    | Resource does not exist         |
| `https://api.nedlia.com/problems/conflict`            | Conflict              | 409    | Business rule conflict          |
| `https://api.nedlia.com/problems/placement-overlap`   | Placement Overlap     | 409    | Placement time range overlaps   |
| `https://api.nedlia.com/problems/campaign-expired`    | Campaign Expired      | 409    | Campaign has ended              |
| `https://api.nedlia.com/problems/rate-limited`        | Rate Limit Exceeded   | 429    | Too many requests               |
| `https://api.nedlia.com/problems/internal-error`      | Internal Server Error | 500    | Unexpected server error         |
| `https://api.nedlia.com/problems/service-unavailable` | Service Unavailable   | 503    | Downstream service unavailable  |
| `about:blank`                                         | (HTTP status title)   | varies | Generic HTTP errors             |

> **Note**: Use `about:blank` as `type` when the HTTP status code alone is sufficient context.

#### Validation Errors with JSON Pointer (RFC 6901)

For validation errors, use the `errors` extension with JSON Pointers:

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Your request contains invalid fields.",
  "errors": [
    {
      "pointer": "#/time_range/start_time",
      "detail": "must be a non-negative number"
    },
    {
      "pointer": "#/time_range/end_time",
      "detail": "must be greater than start_time"
    }
  ]
}
```

#### FastAPI Implementation

```python
# src/core/problem_details.py
from dataclasses import dataclass, field
from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse

PROBLEM_CONTENT_TYPE = "application/problem+json"

@dataclass
class ProblemDetail:
    """RFC 9457 Problem Details response."""
    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_response(self) -> JSONResponse:
        body = {
            "type": self.type,
            "title": self.title,
            "status": self.status,
        }
        if self.detail:
            body["detail"] = self.detail
        if self.instance:
            body["instance"] = self.instance
        body.update(self.extensions)

        return JSONResponse(
            status_code=self.status,
            content=body,
            media_type=PROBLEM_CONTENT_TYPE,
        )


# Problem type constants
class ProblemTypes:
    BASE_URI = "https://api.nedlia.com/problems"
    VALIDATION_ERROR = f"{BASE_URI}/validation-error"
    UNAUTHORIZED = f"{BASE_URI}/unauthorized"
    FORBIDDEN = f"{BASE_URI}/forbidden"
    NOT_FOUND = f"{BASE_URI}/not-found"
    CONFLICT = f"{BASE_URI}/conflict"
    PLACEMENT_OVERLAP = f"{BASE_URI}/placement-overlap"
    CAMPAIGN_EXPIRED = f"{BASE_URI}/campaign-expired"
    RATE_LIMITED = f"{BASE_URI}/rate-limited"
    INTERNAL_ERROR = f"{BASE_URI}/internal-error"
    SERVICE_UNAVAILABLE = f"{BASE_URI}/service-unavailable"
```

#### Exception Hierarchy

```python
# src/core/exceptions.py
from dataclasses import dataclass, field
from typing import Any

@dataclass
class ProblemException(Exception):
    """Base exception that maps to RFC 9457 Problem Details."""
    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationException(ProblemException):
    type: str = ProblemTypes.VALIDATION_ERROR
    title: str = "Validation Error"
    status: int = 422
    errors: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        if self.errors:
            self.extensions["errors"] = self.errors

@dataclass
class NotFoundException(ProblemException):
    type: str = ProblemTypes.NOT_FOUND
    title: str = "Resource Not Found"
    status: int = 404
    resource_type: str = ""
    resource_id: str = ""

    def __post_init__(self):
        if not self.detail and self.resource_type:
            self.detail = f"{self.resource_type} '{self.resource_id}' not found"

@dataclass
class ConflictException(ProblemException):
    type: str = ProblemTypes.CONFLICT
    title: str = "Conflict"
    status: int = 409

@dataclass
class PlacementOverlapException(ConflictException):
    type: str = ProblemTypes.PLACEMENT_OVERLAP
    title: str = "Placement Overlap"
    existing_placement_id: str | None = None
    overlap_start: float = 0.0
    overlap_end: float = 0.0

    def __post_init__(self):
        self.detail = "Placement overlaps with an existing placement"
        if self.existing_placement_id:
            self.extensions["existing_placement_id"] = self.existing_placement_id
            self.extensions["overlap_range"] = {
                "start_time": self.overlap_start,
                "end_time": self.overlap_end,
            }

@dataclass
class RateLimitException(ProblemException):
    type: str = ProblemTypes.RATE_LIMITED
    title: str = "Rate Limit Exceeded"
    status: int = 429
    retry_after: int = 60

    def __post_init__(self):
        self.detail = f"Rate limit exceeded. Retry after {self.retry_after} seconds."
        self.extensions["retry_after"] = self.retry_after
```

#### Global Exception Handler

```python
# src/core/exception_handlers.py
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from src.core.exceptions import ProblemException
from src.core.problem_details import ProblemDetail, ProblemTypes, PROBLEM_CONTENT_TYPE

logger = logging.getLogger(__name__)

async def problem_exception_handler(request: Request, exc: ProblemException):
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

    problem = ProblemDetail(
        type=exc.type,
        title=exc.title,
        status=exc.status,
        detail=exc.detail,
        instance=str(request.url.path),
        extensions=exc.extensions,
    )
    return problem.to_response()

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors as RFC 9457."""
    errors = []
    for error in exc.errors():
        # Convert Pydantic loc to JSON Pointer
        pointer = "#/" + "/".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "pointer": pointer,
            "detail": error["msg"],
        })

    problem = ProblemDetail(
        type=ProblemTypes.VALIDATION_ERROR,
        title="Validation Error",
        status=422,
        detail="Your request contains invalid fields.",
        instance=str(request.url.path),
        extensions={"errors": errors},
    )
    return problem.to_response()

async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions as RFC 9457."""
    logger.exception("Unhandled exception: %s", str(exc))

    problem = ProblemDetail(
        type=ProblemTypes.INTERNAL_ERROR,
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred.",
        instance=str(request.url.path),
    )
    return problem.to_response()

def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers."""
    app.add_exception_handler(ProblemException, problem_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

#### OpenAPI Documentation

Document problem responses in OpenAPI:

```python
# src/core/openapi.py
from fastapi import FastAPI

PROBLEM_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"}
            }
        },
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"}
            }
        },
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"}
            }
        },
    },
    422: {
        "description": "Validation Error",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ValidationProblemDetail"}
            }
        },
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/problem+json": {
                "schema": {"$ref": "#/components/schemas/ProblemDetail"}
            }
        },
    },
}
```

---

## 2. Lambda Workers (Event-Driven)

**Location**: `nedlia-back-end/workers/`

### Standard: AWS Lambda Partial Batch Response

Implements **[AWS Lambda Partial Batch Response](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)** for SQS event sources.

#### Configuration

Enable partial batch response in event source mapping:

```hcl
# Terraform configuration
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = aws_sqs_queue.main.arn
  function_name    = aws_lambda_function.worker.arn
  batch_size       = 10

  function_response_types = ["ReportBatchItemFailures"]
}
```

#### Handler Pattern (AWS Standard)

```python
# src/handlers/file_generator.py
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    SQS Lambda handler with AWS Partial Batch Response.

    Returns:
        dict with batchItemFailures containing failed message identifiers.
        AWS will only retry the failed messages, not the entire batch.
    """
    batch_item_failures: list[dict[str, str]] = []

    for record in event.get("Records", []):
        message_id = record["messageId"]

        try:
            # Parse CloudEvents envelope (if using EventBridge)
            body = json.loads(record["body"])
            detail = body.get("detail", body)

            # Process the message
            process_record(detail)

            logger.info(
                "Successfully processed message",
                extra={"message_id": message_id},
            )

        except Exception as e:
            logger.exception(
                "Failed to process message",
                extra={"message_id": message_id, "error": str(e)},
            )
            # Report this item as failed - AWS will retry it
            batch_item_failures.append({"itemIdentifier": message_id})

    # AWS Lambda Partial Batch Response format
    return {"batchItemFailures": batch_item_failures}
```

#### Idempotency with AWS Lambda Powertools

Use **[AWS Lambda Powertools](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)** for standard idempotency:

```python
# src/handlers/file_generator.py
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    idempotent_function,
    IdempotencyConfig,
)

persistence_layer = DynamoDBPersistenceLayer(table_name="IdempotencyTable")
config = IdempotencyConfig(
    expires_after_seconds=86400,  # 24 hours
    event_key_jmespath="detail.placement_id",
)

@idempotent_function(
    data_keyword_argument="event",
    persistence_store=persistence_layer,
    config=config,
)
def process_placement(event: dict) -> dict:
    """Idempotent placement processing."""
    placement_id = event["detail"]["placement_id"]
    # Process placement...
    return {"status": "processed", "placement_id": placement_id}
```

#### Dead Letter Queue (DLQ) Configuration

```hcl
# Terraform - Standard AWS DLQ pattern
resource "aws_sqs_queue" "main" {
  name = "nedlia-${var.environment}-${var.queue_name}"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3  # Move to DLQ after 3 failures
  })

  visibility_timeout_seconds = 300  # 5 minutes
}

resource "aws_sqs_queue" "dlq" {
  name = "nedlia-${var.environment}-${var.queue_name}-dlq"
  message_retention_seconds = 1209600  # 14 days (max)
}

# CloudWatch alarm for DLQ monitoring
resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "nedlia-${var.environment}-${var.queue_name}-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }
}
```

#### Error Categories

| Category            | Action                               | Retry? | DLQ?      |
| ------------------- | ------------------------------------ | ------ | --------- |
| Transient (network) | Return in `batchItemFailures`        | Yes    | After max |
| Business rule       | Return in `batchItemFailures`        | Yes    | After max |
| Invalid message     | Log and skip (don't add to failures) | No     | No        |
| Poison message      | Return in `batchItemFailures`        | Yes    | After max |

---

## 3. JavaScript SDK (TypeScript)

**Location**: `nedlia-sdk/javascript/`

### Standard: Typed Exceptions + AWS SDK-style Retry

Follows patterns from **AWS SDK for JavaScript v3** and **Stripe Node SDK**.

#### Error Classes

```typescript
// src/errors.ts

/**
 * Base error class for all Nedlia SDK errors.
 * Follows RFC 9457 Problem Details structure from API.
 */
export class NedliaError extends Error {
  readonly type: string;
  readonly title: string;
  readonly status: number;
  readonly detail?: string;
  readonly instance?: string;
  readonly retryable: boolean;

  constructor(problem: ProblemDetail) {
    super(problem.detail ?? problem.title);
    this.name = 'NedliaError';
    this.type = problem.type;
    this.title = problem.title;
    this.status = problem.status;
    this.detail = problem.detail;
    this.instance = problem.instance;
    this.retryable = this.isRetryableStatus(problem.status);
  }

  private isRetryableStatus(status: number): boolean {
    return status === 429 || status >= 500;
  }

  static fromResponse(response: Response, body: ProblemDetail): NedliaError {
    switch (body.type) {
      case ProblemTypes.VALIDATION_ERROR:
        return new ValidationError(body);
      case ProblemTypes.NOT_FOUND:
        return new NotFoundError(body);
      case ProblemTypes.UNAUTHORIZED:
        return new UnauthorizedError(body);
      case ProblemTypes.FORBIDDEN:
        return new ForbiddenError(body);
      case ProblemTypes.RATE_LIMITED:
        return new RateLimitError(body);
      default:
        return new NedliaError(body);
    }
  }
}

export class ValidationError extends NedliaError {
  readonly errors?: Array<{ pointer: string; detail: string }>;

  constructor(problem: ProblemDetail & { errors?: Array<{ pointer: string; detail: string }> }) {
    super(problem);
    this.name = 'ValidationError';
    this.errors = problem.errors;
  }
}

export class NotFoundError extends NedliaError {
  constructor(problem: ProblemDetail) {
    super(problem);
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends NedliaError {
  constructor(problem: ProblemDetail) {
    super(problem);
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends NedliaError {
  constructor(problem: ProblemDetail) {
    super(problem);
    this.name = 'ForbiddenError';
  }
}

export class RateLimitError extends NedliaError {
  readonly retryAfter: number;

  constructor(problem: ProblemDetail & { retry_after?: number }) {
    super(problem);
    this.name = 'RateLimitError';
    this.retryAfter = problem.retry_after ?? 60;
    this.retryable = true;
  }
}

export class NetworkError extends Error {
  readonly retryable = true;

  constructor(message: string = 'Network request failed', public readonly cause?: Error) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends Error {
  readonly retryable = true;

  constructor(public readonly timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = 'TimeoutError';
  }
}
```

#### Retry with Exponential Backoff (AWS SDK Standard)

```typescript
// src/retry.ts

export interface RetryStrategy {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
  jitterType: 'full' | 'decorrelated' | 'none';
}

export const DEFAULT_RETRY_STRATEGY: RetryStrategy = {
  maxAttempts: 3,
  baseDelayMs: 100,
  maxDelayMs: 20000,
  jitterType: 'full',
};

/**
 * Calculate delay with exponential backoff and jitter.
 * Based on AWS SDK retry behavior.
 */
function calculateDelay(attempt: number, strategy: RetryStrategy): number {
  const exponentialDelay = Math.min(
    strategy.baseDelayMs * Math.pow(2, attempt),
    strategy.maxDelayMs
  );

  switch (strategy.jitterType) {
    case 'full':
      return Math.random() * exponentialDelay;
    case 'decorrelated':
      return Math.min(strategy.maxDelayMs, Math.random() * exponentialDelay * 3);
    case 'none':
    default:
      return exponentialDelay;
  }
}

function isRetryable(error: unknown): boolean {
  if (error instanceof NedliaError) return error.retryable;
  if (error instanceof NetworkError) return true;
  if (error instanceof TimeoutError) return true;
  return false;
}

export async function withRetry<T>(
  fn: () => Promise<T>,
  strategy: Partial<RetryStrategy> = {}
): Promise<T> {
  const config = { ...DEFAULT_RETRY_STRATEGY, ...strategy };
  let lastError: Error | undefined;

  for (let attempt = 0; attempt < config.maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (!isRetryable(error) || attempt === config.maxAttempts - 1) {
        throw error;
      }

      const delay = calculateDelay(attempt, config);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}
```

#### Client Implementation

```typescript
// src/client.ts

export interface NedliaClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
  retryStrategy?: Partial<RetryStrategy>;
}

export class NedliaClient {
  private readonly config: Required<NedliaClientConfig>;

  constructor(config: NedliaClientConfig) {
    this.config = {
      baseUrl: 'https://api.nedlia.com/v1',
      timeout: 30000,
      retryStrategy: DEFAULT_RETRY_STRATEGY,
      ...config,
    };
  }

  async getPlacement(placementId: string): Promise<Placement> {
    return this.request('GET', `/placements/${placementId}`);
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    return withRetry(async () => {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

      try {
        const response = await fetch(`${this.config.baseUrl}${path}`, {
          method,
          headers: {
            Authorization: `Bearer ${this.config.apiKey}`,
            'Content-Type': 'application/json',
            Accept: 'application/json, application/problem+json',
          },
          body: body ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const problemDetail = await response.json();
          throw NedliaError.fromResponse(response, problemDetail);
        }

        return response.json();
      } catch (error) {
        clearTimeout(timeoutId);

        if (error instanceof NedliaError) throw error;
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw new TimeoutError(this.config.timeout);
        }
        throw new NetworkError('Network request failed', error as Error);
      }
    }, this.config.retryStrategy);
  }
}
```

---

## 4. Python SDK

**Location**: `nedlia-sdk/python/`

### Standard: Exception Hierarchy + Tenacity

Uses **[Tenacity](https://tenacity.readthedocs.io/)** (standard Python retry library) and mirrors RFC 9457 Problem Details.

#### Exception Classes

```python
# nedlia/exceptions.py
from dataclasses import dataclass, field
from typing import Any

@dataclass
class NedliaError(Exception):
    """
    Base exception for Nedlia SDK.
    Maps to RFC 9457 Problem Details from API.
    """
    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return self.detail or self.title

@dataclass
class ValidationError(NedliaError):
    """Validation error with field-level details."""
    errors: list[dict[str, str]] = field(default_factory=list)

@dataclass
class NotFoundError(NedliaError):
    """Resource not found."""
    pass

@dataclass
class UnauthorizedError(NedliaError):
    """Authentication required or invalid."""
    pass

@dataclass
class ForbiddenError(NedliaError):
    """Insufficient permissions."""
    pass

@dataclass
class RateLimitError(NedliaError):
    """Rate limit exceeded."""
    retry_after: int = 60
    retryable: bool = True

@dataclass
class NetworkError(NedliaError):
    """Network-level error."""
    type: str = "about:blank"
    title: str = "Network Error"
    status: int = 0
    retryable: bool = True

@dataclass
class TimeoutError(NedliaError):
    """Request timeout."""
    type: str = "about:blank"
    title: str = "Timeout"
    status: int = 0
    retryable: bool = True
```

#### Client with Tenacity Retry

```python
# nedlia/client.py
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception,
)

from nedlia.exceptions import (
    NedliaError,
    ValidationError,
    NotFoundError,
    UnauthorizedError,
    ForbiddenError,
    RateLimitError,
    NetworkError,
    TimeoutError,
)

def is_retryable(exc: BaseException) -> bool:
    """Check if exception is retryable."""
    return isinstance(exc, NedliaError) and exc.retryable

class NedliaClient:
    """Nedlia API client with automatic retry."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.nedlia.com/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, application/problem+json",
            },
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.1, max=20),
        retry=retry_if_exception(is_retryable),
        reraise=True,
    )
    async def get_placement(self, placement_id: str) -> dict:
        """Get a placement by ID."""
        return await self._request("GET", f"/placements/{placement_id}")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make HTTP request with error handling."""
        try:
            response = await self._client.request(method, path, **kwargs)

            if response.status_code >= 400:
                raise self._parse_error(response)

            return response.json()

        except httpx.ConnectError as e:
            raise NetworkError(detail=str(e))
        except httpx.TimeoutException as e:
            raise TimeoutError(detail=f"Request timed out after {self.timeout}s")

    def _parse_error(self, response: httpx.Response) -> NedliaError:
        """Parse RFC 9457 Problem Details response."""
        try:
            problem = response.json()
        except Exception:
            problem = {
                "type": "about:blank",
                "title": response.reason_phrase,
                "status": response.status_code,
            }

        error_type = problem.get("type", "about:blank")
        base_kwargs = {
            "type": error_type,
            "title": problem.get("title", "Error"),
            "status": problem.get("status", response.status_code),
            "detail": problem.get("detail"),
            "instance": problem.get("instance"),
        }

        # Map to specific exception classes
        if "validation-error" in error_type:
            return ValidationError(**base_kwargs, errors=problem.get("errors", []))
        elif "not-found" in error_type:
            return NotFoundError(**base_kwargs)
        elif "unauthorized" in error_type:
            return UnauthorizedError(**base_kwargs)
        elif "forbidden" in error_type:
            return ForbiddenError(**base_kwargs)
        elif "rate-limited" in error_type:
            return RateLimitError(
                **base_kwargs,
                retry_after=problem.get("retry_after", 60),
            )
        elif response.status_code >= 500:
            return NedliaError(**base_kwargs, retryable=True)
        else:
            return NedliaError(**base_kwargs)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
```

---

## 5. Swift SDK

**Location**: `nedlia-sdk/swift/`

### Standard: Swift Result Type + Structured Concurrency

Follows **Swift API Design Guidelines** and **Apple's async/await patterns**.

#### Error Types

```swift
// Sources/NedliaSDK/Errors.swift
import Foundation

/// RFC 9457 Problem Details mapped to Swift.
public struct ProblemDetail: Decodable, Sendable {
    public let type: String
    public let title: String
    public let status: Int
    public let detail: String?
    public let instance: String?

    // Extension fields
    public let errors: [ValidationFieldError]?
    public let retryAfter: Int?

    enum CodingKeys: String, CodingKey {
        case type, title, status, detail, instance, errors
        case retryAfter = "retry_after"
    }
}

public struct ValidationFieldError: Decodable, Sendable {
    public let pointer: String
    public let detail: String
}

/// Nedlia SDK error types.
public enum NedliaError: Error, Sendable {
    case validation(ProblemDetail, errors: [ValidationFieldError])
    case notFound(ProblemDetail)
    case unauthorized(ProblemDetail)
    case forbidden(ProblemDetail)
    case rateLimited(ProblemDetail, retryAfter: Int)
    case serverError(ProblemDetail)
    case networkError(Error)
    case timeout(TimeInterval)
    case decodingError(Error)

    public var isRetryable: Bool {
        switch self {
        case .rateLimited, .serverError, .networkError, .timeout:
            return true
        default:
            return false
        }
    }

    public var problemDetail: ProblemDetail? {
        switch self {
        case .validation(let p, _), .notFound(let p), .unauthorized(let p),
             .forbidden(let p), .rateLimited(let p, _), .serverError(let p):
            return p
        default:
            return nil
        }
    }

    static func from(problemDetail: ProblemDetail) -> NedliaError {
        if problemDetail.type.contains("validation-error") {
            return .validation(problemDetail, errors: problemDetail.errors ?? [])
        } else if problemDetail.type.contains("not-found") {
            return .notFound(problemDetail)
        } else if problemDetail.type.contains("unauthorized") {
            return .unauthorized(problemDetail)
        } else if problemDetail.type.contains("forbidden") {
            return .forbidden(problemDetail)
        } else if problemDetail.type.contains("rate-limited") {
            return .rateLimited(problemDetail, retryAfter: problemDetail.retryAfter ?? 60)
        } else {
            return .serverError(problemDetail)
        }
    }
}

extension NedliaError: LocalizedError {
    public var errorDescription: String? {
        switch self {
        case .validation(let p, _):
            return p.detail ?? p.title
        case .notFound(let p), .unauthorized(let p), .forbidden(let p),
             .rateLimited(let p, _), .serverError(let p):
            return p.detail ?? p.title
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .timeout(let seconds):
            return "Request timed out after \(seconds) seconds"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        }
    }
}
```

#### Client with Structured Concurrency

```swift
// Sources/NedliaSDK/Client.swift
import Foundation

public actor NedliaClient {
    private let baseURL: URL
    private let apiKey: String
    private let session: URLSession
    private let timeout: TimeInterval
    private let retryConfig: RetryConfig

    public init(
        apiKey: String,
        baseURL: URL = URL(string: "https://api.nedlia.com/v1")!,
        timeout: TimeInterval = 30,
        retryConfig: RetryConfig = .default
    ) {
        self.apiKey = apiKey
        self.baseURL = baseURL
        self.timeout = timeout
        self.retryConfig = retryConfig

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = timeout
        self.session = URLSession(configuration: config)
    }

    public func getPlacement(id: String) async throws -> Placement {
        try await withRetry(config: retryConfig) {
            try await self.request(
                method: "GET",
                path: "/placements/\(id)"
            )
        }
    }

    private func request<T: Decodable>(
        method: String,
        path: String,
        body: Encodable? = nil
    ) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json, application/problem+json", forHTTPHeaderField: "Accept")

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch let error as URLError where error.code == .timedOut {
            throw NedliaError.timeout(timeout)
        } catch {
            throw NedliaError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NedliaError.networkError(URLError(.badServerResponse))
        }

        if httpResponse.statusCode >= 400 {
            let problemDetail = try JSONDecoder().decode(ProblemDetail.self, from: data)
            throw NedliaError.from(problemDetail: problemDetail)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw NedliaError.decodingError(error)
        }
    }
}
```

#### Retry with Structured Concurrency

```swift
// Sources/NedliaSDK/Retry.swift
import Foundation

public struct RetryConfig: Sendable {
    public let maxAttempts: Int
    public let baseDelay: TimeInterval
    public let maxDelay: TimeInterval

    public static let `default` = RetryConfig(
        maxAttempts: 3,
        baseDelay: 0.1,
        maxDelay: 20.0
    )

    public init(maxAttempts: Int, baseDelay: TimeInterval, maxDelay: TimeInterval) {
        self.maxAttempts = maxAttempts
        self.baseDelay = baseDelay
        self.maxDelay = maxDelay
    }
}

func withRetry<T: Sendable>(
    config: RetryConfig,
    operation: @Sendable () async throws -> T
) async throws -> T {
    var lastError: Error?

    for attempt in 0..<config.maxAttempts {
        do {
            return try await operation()
        } catch let error as NedliaError {
            lastError = error

            guard error.isRetryable && attempt < config.maxAttempts - 1 else {
                throw error
            }

            // Exponential backoff with jitter
            let delay = min(
                config.baseDelay * pow(2.0, Double(attempt)),
                config.maxDelay
            )
            let jitter = Double.random(in: 0...delay)
            try await Task.sleep(nanoseconds: UInt64((delay + jitter) * 1_000_000_000))

        } catch {
            throw NedliaError.networkError(error)
        }
    }

    throw lastError ?? NedliaError.networkError(URLError(.unknown))
}
```

---

## 6. Editor Plugins (Swift)

**Location**: `nedlia-plugin/finalcut/`, `nedlia-plugin/davinci/`, `nedlia-plugin/lumafusion/`

### Standard: Apple Human Interface Guidelines

Follows **[Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/patterns/entering-data#alerts)** for error presentation.

#### Error Presentation

```swift
// Sources/NedliaPlugin/UI/ErrorPresenter.swift
import AppKit

public final class ErrorPresenter {
    /// Present error following Apple HIG.
    /// - Alerts should be used sparingly for critical errors
    /// - Use inline feedback for validation errors
    /// - Provide actionable recovery options
    public func present(
        _ error: Error,
        in window: NSWindow?,
        recoveryHandler: ((Bool) -> Void)? = nil
    ) {
        let alert = NSAlert()

        switch error {
        case let nedliaError as NedliaError:
            configureAlert(alert, for: nedliaError)
        case let pluginError as PluginError:
            configureAlert(alert, for: pluginError)
        default:
            alert.messageText = "An Error Occurred"
            alert.informativeText = error.localizedDescription
            alert.alertStyle = .warning
        }

        if let window = window {
            alert.beginSheetModal(for: window) { response in
                recoveryHandler?(response == .alertFirstButtonReturn)
            }
        } else {
            let response = alert.runModal()
            recoveryHandler?(response == .alertFirstButtonReturn)
        }
    }

    private func configureAlert(_ alert: NSAlert, for error: NedliaError) {
        switch error {
        case .networkError, .timeout:
            alert.messageText = "Connection Error"
            alert.informativeText = "Unable to connect to Nedlia. Check your internet connection and try again."
            alert.alertStyle = .warning
            alert.addButton(withTitle: "Try Again")
            alert.addButton(withTitle: "Cancel")

        case .unauthorized:
            alert.messageText = "Sign In Required"
            alert.informativeText = "Your session has expired. Please sign in again."
            alert.alertStyle = .informational
            alert.addButton(withTitle: "Sign In")
            alert.addButton(withTitle: "Cancel")

        case .rateLimited(_, let retryAfter):
            alert.messageText = "Too Many Requests"
            alert.informativeText = "Please wait \(retryAfter) seconds before trying again."
            alert.alertStyle = .informational
            alert.addButton(withTitle: "OK")

        case .validation(_, let errors):
            alert.messageText = "Invalid Input"
            let details = errors.map { "• \($0.detail)" }.joined(separator: "\n")
            alert.informativeText = "Please fix the following:\n\(details)"
            alert.alertStyle = .warning
            alert.addButton(withTitle: "OK")

        default:
            alert.messageText = "Error"
            alert.informativeText = error.localizedDescription
            alert.alertStyle = .warning
            alert.addButton(withTitle: "OK")
        }
    }
}
```

#### Offline Support with Local-First Pattern

```swift
// Sources/NedliaPlugin/Sync/OfflineManager.swift
import Foundation

/// Manages offline operations following local-first principles.
public actor OfflineManager {
    private var pendingOperations: [PendingOperation] = []
    private let storage: LocalStorage
    private let client: NedliaClient

    public enum SyncState {
        case synced
        case pending(count: Int)
        case syncing
        case error(Error)
    }

    @Published public private(set) var state: SyncState = .synced

    /// Queue operation for later sync.
    public func enqueue(_ operation: Operation) async {
        let pending = PendingOperation(
            id: UUID(),
            operation: operation,
            createdAt: Date()
        )
        pendingOperations.append(pending)
        await storage.save(pendingOperations)
        state = .pending(count: pendingOperations.count)
    }

    /// Attempt to sync all pending operations.
    public func sync() async -> [SyncResult] {
        guard !pendingOperations.isEmpty else { return [] }

        state = .syncing
        var results: [SyncResult] = []
        var succeeded: [UUID] = []

        for operation in pendingOperations {
            do {
                try await execute(operation)
                succeeded.append(operation.id)
                results.append(.success(operation.id))
            } catch {
                results.append(.failure(operation.id, error))
            }
        }

        // Remove successful operations
        pendingOperations.removeAll { succeeded.contains($0.id) }
        await storage.save(pendingOperations)

        if pendingOperations.isEmpty {
            state = .synced
        } else {
            state = .pending(count: pendingOperations.count)
        }

        return results
    }
}
```

---

## 7. Frontend (React Portal)

**Location**: `nedlia-front-end/portal/`

### Standard: React Error Boundaries + TanStack Query

Follows **[React Error Boundaries](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)** and **[TanStack Query](https://tanstack.com/query/latest/docs/framework/react/guides/query-retries)** patterns.

#### Error Boundary (React Standard)

```tsx
// src/components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
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
    // Log to error reporting service
    console.error('Error boundary caught:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error, this.reset);
      }
      return (
        this.props.fallback ?? (
          <DefaultErrorFallback error={this.state.error} onRetry={this.reset} />
        )
      );
    }
    return this.props.children;
  }
}

function DefaultErrorFallback({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <div role="alert" className="error-fallback">
      <h2>Something went wrong</h2>
      <pre>{error.message}</pre>
      <button onClick={onRetry}>Try again</button>
    </div>
  );
}
```

#### TanStack Query Configuration

```tsx
// src/lib/query-client.ts
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { NedliaError, UnauthorizedError } from './errors';
import { toast } from '@/components/ui/toast';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Retry configuration (TanStack Query standard)
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors (except 429)
        if (error instanceof NedliaError) {
          if (error.status >= 400 && error.status < 500 && error.status !== 429) {
            return false;
          }
        }
        return failureCount < 3;
      },
      retryDelay: attemptIndex => Math.min(1000 * 2 ** attemptIndex, 30000),
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
    mutations: {
      retry: false, // Don't retry mutations by default
    },
  },
  queryCache: new QueryCache({
    onError: error => {
      // Global error handling for queries
      if (error instanceof UnauthorizedError) {
        // Redirect to login
        window.location.href = '/login';
        return;
      }

      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof NedliaError ? error.detail : 'An error occurred',
      });
    },
  }),
  mutationCache: new MutationCache({
    onError: error => {
      // Global error handling for mutations
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error instanceof NedliaError ? error.detail : 'An error occurred',
      });
    },
  }),
});
```

#### API Hooks with Error Handling

```tsx
// src/hooks/usePlacement.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { placementApi } from '@/lib/api';
import { toast } from '@/components/ui/toast';

export function usePlacement(placementId: string) {
  return useQuery({
    queryKey: ['placement', placementId],
    queryFn: () => placementApi.get(placementId),
    // Error handled by global queryCache.onError
  });
}

export function useCreatePlacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: placementApi.create,
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['placements'] });
      toast({ title: 'Placement created successfully' });
    },
    // Error handled by global mutationCache.onError
  });
}
```

#### Form Validation with RFC 9457 Errors

```tsx
// src/components/PlacementForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ValidationError } from '@/lib/errors';

export function PlacementForm() {
  const form = useForm({
    resolver: zodResolver(placementSchema),
  });

  const mutation = useCreatePlacement();

  const onSubmit = async (data: PlacementInput) => {
    try {
      await mutation.mutateAsync(data);
    } catch (error) {
      // Map RFC 9457 validation errors to form fields
      if (error instanceof ValidationError && error.errors) {
        error.errors.forEach(({ pointer, detail }) => {
          // Convert JSON Pointer to field name: "#/time_range/start_time" -> "time_range.start_time"
          const fieldName = pointer.replace('#/', '').replace(/\//g, '.');
          form.setError(fieldName as keyof PlacementInput, {
            type: 'server',
            message: detail,
          });
        });
      }
    }
  };

  return <form onSubmit={form.handleSubmit(onSubmit)}>{/* Form fields */}</form>;
}
```

---

## Cross-Cutting Standards

### Correlation IDs

All components propagate correlation IDs using the **W3C Trace Context** standard:

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
```

### Structured Logging

Follow **[OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/)** for error logging:

```python
logger.warning(
    "Request failed",
    extra={
        "error.type": exc.type,
        "error.message": exc.detail,
        "http.status_code": exc.status,
        "http.url": str(request.url),
    },
)
```

### Error Monitoring

| Component | Standard                    | Tool       |
| --------- | --------------------------- | ---------- |
| API       | OpenTelemetry + Sentry      | CloudWatch |
| Workers   | AWS X-Ray                   | CloudWatch |
| SDKs      | Client-side error reporting | Sentry     |
| Frontend  | React Error Boundaries      | Sentry     |

---

## Related Documentation

- [Error Handling Guide](error-handling.md) – Core error patterns
- [Resilience Patterns](resilience-patterns.md) – Circuit breakers, retries, fallbacks
- [API Standards](api-standards.md) – API design standards
- [Logging Standards](logging-standards.md) – Structured logging
- [Observability](observability.md) – Monitoring and alerting

## References

- [RFC 9457 - Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)
- [RFC 6901 - JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901)
- [AWS Lambda Partial Batch Response](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [AWS Lambda Powertools - Idempotency](https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/)
- [TanStack Query - Error Handling](https://tanstack.com/query/latest/docs/framework/react/guides/query-retries)
- [Apple Human Interface Guidelines - Alerts](https://developer.apple.com/design/human-interface-guidelines/alerts)
