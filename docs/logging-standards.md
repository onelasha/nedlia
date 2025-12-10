# Logging Standards

Structured logging standards for Nedlia's Python backend (FastAPI, Lambda workers) and TypeScript frontend.

## Principles

1. **Structured Logging**: JSON format for machine parsing
2. **Contextual**: Include correlation IDs, user IDs, resource IDs
3. **Leveled**: Use appropriate log levels consistently
4. **Secure**: Never log secrets, tokens, or PII
5. **Actionable**: Logs should help diagnose issues

---

## Log Levels

| Level      | When to Use                                        | Examples                                   |
| ---------- | -------------------------------------------------- | ------------------------------------------ |
| `DEBUG`    | Detailed diagnostic info (disabled in production)  | SQL queries, cache hits, internal state    |
| `INFO`     | Normal operations, business events                 | Request received, placement created        |
| `WARNING`  | Unexpected but handled situations                  | Retry attempt, deprecated API usage        |
| `ERROR`    | Errors that need attention but don't crash the app | External service failure, validation error |
| `CRITICAL` | System is unusable, immediate action required      | Database connection lost, out of memory    |

### Level Guidelines

```python
# DEBUG - Detailed diagnostics (disabled in prod)
logger.debug("Cache lookup", extra={"key": cache_key, "hit": True})

# INFO - Normal business operations
logger.info("Placement created", extra={"placement_id": str(placement.id)})

# WARNING - Handled issues, potential problems
logger.warning("Retry attempt", extra={"attempt": 2, "max_attempts": 3})

# ERROR - Failures requiring investigation
logger.error("External API failed", extra={"service": "video-processor", "status": 503})

# CRITICAL - System-level failures
logger.critical("Database connection pool exhausted")
```

---

## Python Logging Configuration

### Structured JSON Logger

```python
# src/core/logging.py
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from src.middleware.correlation_id import correlation_id_var


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get(""),
        }

        # Add location info
        if record.levelno >= logging.WARNING:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Add extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in {
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "pathname", "process", "processName", "relativeCreated",
                    "stack_info", "exc_info", "exc_text", "thread", "threadName",
                    "taskName", "message",
                }:
                    log_data[key] = value

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure application logging."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
```

### Usage in Application

```python
# src/main.py
from src.core.logging import configure_logging
from src.core.config import settings

# Configure at startup
configure_logging(level=settings.log_level)
```

---

## Contextual Logging

### Always Include Context

```python
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class PlacementService:
    async def create(self, data: PlacementCreate) -> Placement:
        logger.info(
            "Creating placement",
            extra={
                "video_id": str(data.video_id),
                "product_id": str(data.product_id),
                "time_range": {
                    "start": data.start_time,
                    "end": data.end_time,
                },
            },
        )

        placement = await self.repo.save(Placement(**data.model_dump()))

        logger.info(
            "Placement created",
            extra={
                "placement_id": str(placement.id),
                "video_id": str(placement.video_id),
                "status": placement.status.value,
            },
        )

        return placement
```

### Standard Context Fields

Always include these fields when available:

| Field            | Description                   | Example                               |
| ---------------- | ----------------------------- | ------------------------------------- |
| `correlation_id` | Request trace ID (auto-added) | `"req_abc123"`                        |
| `user_id`        | Authenticated user            | `"usr_xyz789"`                        |
| `placement_id`   | Placement being operated on   | `"550e8400-..."`                      |
| `video_id`       | Video being operated on       | `"6ba7b810-..."`                      |
| `campaign_id`    | Campaign context              | `"123e4567-..."`                      |
| `action`         | What operation is happening   | `"create"`, `"validate"`, `"archive"` |
| `duration_ms`    | Operation timing              | `150.5`                               |
| `status`         | Result status                 | `"success"`, `"failure"`              |

---

## Request Logging Middleware

### HTTP Request/Response Logging

```python
# src/middleware/logging.py
import logging
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.middleware.correlation_id import correlation_id_var

logger = logging.getLogger("nedlia.http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Log request
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        response = await call_next(request)

        # Log response
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response
```

### Registration

```python
# src/main.py
from src.middleware.logging import RequestLoggingMiddleware

app.add_middleware(RequestLoggingMiddleware)
```

---

## Lambda Worker Logging

### Handler Logging Pattern

```python
# src/handlers/file_generator.py
import json
import logging
from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

# Use Lambda Powertools for structured logging
logger = Logger(service="file-generator")


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """SQS Lambda handler for file generation."""
    failed_records = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        body = json.loads(record["body"])

        # Add message context to all logs in this iteration
        logger.append_keys(
            message_id=message_id,
            placement_id=body.get("detail", {}).get("placement_id"),
        )

        try:
            logger.info("Processing file generation")
            generate_placement_file(body)
            logger.info("File generation completed")

        except Exception as e:
            logger.exception("File generation failed")
            failed_records.append({"itemIdentifier": message_id})

        finally:
            # Clear message-specific keys
            logger.remove_keys(["message_id", "placement_id"])

    return {"batchItemFailures": failed_records}
```

### Lambda Powertools Configuration

```python
# src/core/logging_lambda.py
from aws_lambda_powertools import Logger

# Create logger with service name
logger = Logger(
    service="nedlia-api",
    level="INFO",
    log_uncaught_exceptions=True,
)
```

---

## What to Log

### ✅ Do Log

```python
# Business events
logger.info("Placement created", extra={"placement_id": str(id)})
logger.info("Video validation started", extra={"video_id": str(id)})
logger.info("Campaign activated", extra={"campaign_id": str(id)})

# State changes
logger.info("Placement status changed", extra={
    "placement_id": str(id),
    "old_status": "draft",
    "new_status": "active",
})

# External service calls
logger.info("Calling external API", extra={
    "service": "video-processor",
    "endpoint": "/process",
    "timeout_ms": 30000,
})

# Performance metrics
logger.info("Database query completed", extra={
    "query": "find_placements_by_video",
    "duration_ms": 45.2,
    "result_count": 15,
})

# Errors with context
logger.error("External service failed", extra={
    "service": "video-processor",
    "status_code": 503,
    "retry_count": 2,
})
```

### ❌ Don't Log

```python
# ❌ Secrets and credentials
logger.info(f"Using API key: {api_key}")  # NEVER

# ❌ PII (Personally Identifiable Information)
logger.info(f"User email: {user.email}")  # NEVER
logger.info(f"User name: {user.full_name}")  # NEVER

# ❌ Full request/response bodies (may contain secrets)
logger.debug(f"Request body: {request.body}")  # AVOID

# ❌ Passwords, tokens, session IDs
logger.info(f"Session: {session_id}")  # NEVER

# ❌ Credit card numbers, SSNs, etc.
logger.info(f"Payment: {card_number}")  # NEVER
```

### Safe PII Handling

```python
# If you must reference users, use IDs only
logger.info("User action", extra={
    "user_id": str(user.id),  # ✅ OK - just the ID
    # "email": user.email,    # ❌ NO - PII
})

# Mask sensitive data if needed for debugging
def mask_email(email: str) -> str:
    """Mask email for logging: john@example.com -> j***@e***.com"""
    local, domain = email.split("@")
    return f"{local[0]}***@{domain[0]}***.{domain.split('.')[-1]}"

logger.debug("Email sent", extra={"recipient": mask_email(user.email)})
```

---

## Log Output Examples

### JSON Format (Production)

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "nedlia.placements.service",
  "message": "Placement created",
  "correlation_id": "req_abc123",
  "placement_id": "550e8400-e29b-41d4-a716-446655440000",
  "video_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "status": "draft"
}
```

### Error with Stack Trace

```json
{
  "timestamp": "2024-01-15T10:30:00.456Z",
  "level": "ERROR",
  "logger": "nedlia.infrastructure.video_client",
  "message": "External API failed",
  "correlation_id": "req_abc123",
  "service": "video-processor",
  "status_code": 503,
  "location": {
    "file": "/app/src/infrastructure/video_client.py",
    "line": 45,
    "function": "fetch_metadata"
  },
  "exception": "Traceback (most recent call last):\n  File ..."
}
```

---

## TypeScript Logging

### Logger Setup

```typescript
// src/core/logger.ts
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogContext {
  [key: string]: unknown;
}

class Logger {
  private context: LogContext = {};

  constructor(private name: string) {}

  withContext(context: LogContext): Logger {
    const logger = new Logger(this.name);
    logger.context = { ...this.context, ...context };
    return logger;
  }

  private log(level: LogLevel, message: string, extra?: LogContext): void {
    const entry = {
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      logger: this.name,
      message,
      ...this.context,
      ...extra,
    };

    const output = JSON.stringify(entry);

    switch (level) {
      case 'debug':
        console.debug(output);
        break;
      case 'info':
        console.info(output);
        break;
      case 'warn':
        console.warn(output);
        break;
      case 'error':
        console.error(output);
        break;
    }
  }

  debug(message: string, extra?: LogContext): void {
    this.log('debug', message, extra);
  }

  info(message: string, extra?: LogContext): void {
    this.log('info', message, extra);
  }

  warn(message: string, extra?: LogContext): void {
    this.log('warn', message, extra);
  }

  error(message: string, error?: Error, extra?: LogContext): void {
    this.log('error', message, {
      ...extra,
      error: error
        ? {
            name: error.name,
            message: error.message,
            stack: error.stack,
          }
        : undefined,
    });
  }
}

export function getLogger(name: string): Logger {
  return new Logger(name);
}
```

### Usage

```typescript
// src/placements/service.ts
import { getLogger } from '../core/logger';

const logger = getLogger('placements.service');

export async function createPlacement(data: PlacementCreate): Promise<Placement> {
  logger.info('Creating placement', {
    videoId: data.videoId,
    productId: data.productId,
  });

  try {
    const placement = await repository.save(data);
    logger.info('Placement created', { placementId: placement.id });
    return placement;
  } catch (error) {
    logger.error('Failed to create placement', error as Error, {
      videoId: data.videoId,
    });
    throw error;
  }
}
```

---

## CloudWatch Integration

### Log Groups

| Service        | Log Group                      |
| -------------- | ------------------------------ |
| API (Fargate)  | `/ecs/nedlia-api`              |
| File Generator | `/aws/lambda/nedlia-file-gen`  |
| Validator      | `/aws/lambda/nedlia-validator` |
| Notifier       | `/aws/lambda/nedlia-notifier`  |

### CloudWatch Insights Queries

```sql
-- Find all errors for a correlation ID
fields @timestamp, @message
| filter correlation_id = "req_abc123"
| sort @timestamp asc

-- Error rate by service
fields @timestamp, level, logger
| filter level = "ERROR"
| stats count() by bin(1h), logger

-- Slow requests (>1s)
fields @timestamp, path, duration_ms
| filter duration_ms > 1000
| sort duration_ms desc
| limit 50

-- Failed placements
fields @timestamp, message, placement_id, error_code
| filter message like /failed/i and logger like /placement/
| sort @timestamp desc
```

### Metric Filters

Create CloudWatch metric filters for alerting:

```hcl
# terraform
resource "aws_cloudwatch_log_metric_filter" "error_count" {
  name           = "nedlia-api-errors"
  log_group_name = "/ecs/nedlia-api"
  pattern        = "{ $.level = \"ERROR\" }"

  metric_transformation {
    name      = "ErrorCount"
    namespace = "Nedlia/API"
    value     = "1"
  }
}
```

---

## Environment Configuration

| Environment | Log Level | Format | Destination |
| ----------- | --------- | ------ | ----------- |
| Development | DEBUG     | JSON   | stdout      |
| Testing     | INFO      | JSON   | stdout      |
| Staging     | INFO      | JSON   | CloudWatch  |
| Production  | INFO      | JSON   | CloudWatch  |

```python
# src/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    log_level: str = "INFO"
    environment: str = "development"

    model_config = {"env_file": ".env"}


settings = Settings()
```

---

## Related Documentation

- [Error Handling](error-handling.md) – Error logging patterns
- [Observability](observability.md) – Metrics and tracing
- [Security Architecture](security-architecture.md) – PII handling
