# Error Handling Strategy by Project Type

Comprehensive error handling strategies for all Nedlia project types. This document provides project-specific guidance while referencing the core [Error Handling Guide](error-handling.md) and [Resilience Patterns](resilience-patterns.md).

---

## Overview

| Project Type      | Language   | Error Strategy                                      |
| ----------------- | ---------- | --------------------------------------------------- |
| API Services      | Python     | Exception hierarchy + global handlers               |
| Lambda Workers    | Python     | Partial batch failure + DLQ + idempotency           |
| JavaScript SDK    | TypeScript | Result types + typed errors + retry                 |
| Python SDK        | Python     | Exception hierarchy + retry + timeout               |
| Swift SDK         | Swift      | Result type + typed errors + async/await            |
| Editor Plugins    | Swift      | Result type + user-facing alerts + offline handling |
| Frontend (Portal) | TypeScript | Error boundaries + toast notifications + retry      |

---

## 1. API Services (FastAPI)

**Location**: `nedlia-back-end/services/`, `nedlia-back-end/api/`

### Error Format: Custom JSON Envelope

Nedlia uses a **Custom JSON Envelope** pattern rather than RFC 7807 Problem Details.

#### Why Custom Envelope over RFC 7807?

| Aspect                 | Custom Envelope                           | RFC 7807 Problem Details         |
| ---------------------- | ----------------------------------------- | -------------------------------- |
| **Consistency**        | Matches success envelope (`data`/`error`) | Different structure from success |
| **Simplicity**         | Flat, predictable structure               | Requires `type` URI management   |
| **SDK ergonomics**     | Easy to parse in all languages            | `type` URIs add complexity       |
| **Field-level errors** | Native `details` array                    | Requires extension               |
| **Adoption**           | Stripe, GitHub, Twilio pattern            | IETF standard, less common       |

#### Format Comparison

```json
// ✅ Nedlia Custom Envelope (chosen)
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "req_abc123",
    "details": [
      { "field": "time_range.start_time", "code": "INVALID_VALUE", "message": "Start time cannot be negative" }
    ]
  }
}

// ❌ RFC 7807 Problem Details (not used)
{
  "type": "https://api.nedlia.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Request validation failed",
  "instance": "/v1/placements",
  "request_id": "req_abc123",
  "errors": [...]
}
```

#### Content-Type

```
Content-Type: application/json
```

> **Note**: RFC 7807 uses `application/problem+json`. We use standard `application/json` for consistency.

### Strategy

- **Global exception handlers** catch all errors and return standardized responses
- **Domain exceptions** for business rule violations
- **No try/except in routes** — let errors bubble up to global handlers
- **Correlation IDs** for tracing across services

### Exception Hierarchy

```python
NedliaError (base)
├── ValidationError (400)
├── NotFoundError (404)
│   ├── VideoNotFoundError
│   ├── ProductNotFoundError
│   └── PlacementNotFoundError
├── ConflictError (409)
│   ├── PlacementOverlapError
│   └── CampaignExpiredError
├── UnauthorizedError (401)
├── ForbiddenError (403)
└── RateLimitError (429)
```

### Implementation Checklist

- [ ] Register global exception handlers in `main.py`
- [ ] Use domain exceptions in service layer
- [ ] Include `request_id` in all error responses
- [ ] Log errors with structured context
- [ ] Never expose internal details in error messages

### Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "request_id": "req_abc123",
    "details": [{ "field": "name", "code": "REQUIRED", "message": "Name is required" }]
  }
}
```

### Error Logging

```python
# ✅ Correct: Structured logging with context
logger.warning(
    "Placement creation failed",
    extra={
        "error_code": "PLACEMENT_OVERLAP",
        "video_id": str(video_id),
        "user_id": str(user_id),
    },
)

# ❌ Wrong: Unstructured logging
logger.warning(f"Placement overlap for video {video_id}")
```

### HTTP Status Code Mapping

| Scenario                   | Status | Error Code            |
| -------------------------- | ------ | --------------------- |
| Invalid request body       | 400    | `VALIDATION_ERROR`    |
| Missing authentication     | 401    | `UNAUTHORIZED`        |
| Insufficient permissions   | 403    | `FORBIDDEN`           |
| Resource not found         | 404    | `NOT_FOUND`           |
| Business rule violation    | 409    | `CONFLICT`            |
| Rate limit exceeded        | 429    | `RATE_LIMITED`        |
| Unexpected server error    | 500    | `INTERNAL_ERROR`      |
| Downstream service failure | 503    | `SERVICE_UNAVAILABLE` |

---

## 2. Lambda Workers (Event-Driven)

**Location**: `nedlia-back-end/workers/`

### Strategy

- **Partial batch failure** — return failed message IDs, not entire batch
- **Idempotency** — check if work already done before processing
- **Dead Letter Queue (DLQ)** — failed messages go to DLQ after max retries
- **No exceptions escape** — always catch and report failures

### Handler Pattern

```python
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """SQS Lambda handler with partial batch failure support."""
    failed_records = []

    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            body = json.loads(record["body"])
            event_id = body.get("id") or message_id

            # Idempotency check
            if await idempotency_store.exists(event_id):
                logger.info("Already processed", extra={"event_id": event_id})
                continue

            # Process the message
            await process_message(body)

            # Mark as processed
            await idempotency_store.mark_processed(event_id)

        except NedliaError as e:
            # Business error — log and fail the message
            logger.warning(
                "Business error in worker",
                extra={"error_code": e.code, "message_id": message_id},
            )
            failed_records.append({"itemIdentifier": message_id})

        except Exception as e:
            # Unexpected error — log and fail the message
            logger.exception("Unexpected error", extra={"message_id": message_id})
            failed_records.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failed_records}
```

### Error Categories

| Category            | Action                      | Retry? | DLQ? |
| ------------------- | --------------------------- | ------ | ---- |
| Transient (network) | Fail message, let SQS retry | Yes    | Yes  |
| Business rule       | Fail message, log warning   | Yes    | Yes  |
| Invalid message     | Log error, delete message   | No     | No   |
| Poison message      | Fail message                | Yes    | Yes  |

### Idempotency Implementation

```python
class IdempotencyStore:
    """Redis-based idempotency store."""

    def __init__(self, redis: Redis, ttl: int = 86400):
        self.redis = redis
        self.ttl = ttl  # 24 hours default

    async def exists(self, event_id: str) -> bool:
        return await self.redis.exists(f"idempotency:{event_id}")

    async def mark_processed(self, event_id: str) -> None:
        await self.redis.setex(f"idempotency:{event_id}", self.ttl, "1")
```

### DLQ Monitoring

```python
# CloudWatch alarm for DLQ messages
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "nedlia-${var.environment}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

### Worker-Specific Strategies

| Worker           | Idempotency Key   | Retry Strategy         | Fallback                |
| ---------------- | ----------------- | ---------------------- | ----------------------- |
| `file_generator` | `placement_id`    | 3 retries, exp backoff | Queue for manual review |
| `validator`      | `validation_id`   | 3 retries              | Mark as pending         |
| `notifier`       | `notification_id` | 5 retries              | Log and skip            |
| `sync`           | `sync_request_id` | 3 retries              | Queue for retry         |

---

## 3. JavaScript SDK (TypeScript)

**Location**: `nedlia-sdk/javascript/`

### Strategy

- **Typed error classes** with discriminated unions
- **Automatic retry** with exponential backoff for transient errors
- **Timeout handling** with configurable limits
- **Offline detection** and queuing

### Error Classes

```typescript
// src/errors.ts
export type NedliaErrorCode =
  | 'VALIDATION_ERROR'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'RATE_LIMITED'
  | 'NETWORK_ERROR'
  | 'TIMEOUT'
  | 'INTERNAL_ERROR';

export class NedliaError extends Error {
  constructor(
    message: string,
    public readonly code: NedliaErrorCode,
    public readonly statusCode?: number,
    public readonly requestId?: string,
    public readonly details?: ErrorDetail[],
    public readonly retryable: boolean = false
  ) {
    super(message);
    this.name = 'NedliaError';
  }

  static fromResponse(response: ApiErrorResponse): NedliaError {
    const { code, message, request_id, details } = response.error;
    const retryable = ['RATE_LIMITED', 'SERVICE_UNAVAILABLE'].includes(code);
    return new NedliaError(
      message,
      code as NedliaErrorCode,
      response.status,
      request_id,
      details,
      retryable
    );
  }
}

export class NetworkError extends NedliaError {
  constructor(message: string = 'Network request failed') {
    super(message, 'NETWORK_ERROR', undefined, undefined, undefined, true);
    this.name = 'NetworkError';
  }
}

export class TimeoutError extends NedliaError {
  constructor(timeoutMs: number) {
    super(
      `Request timed out after ${timeoutMs}ms`,
      'TIMEOUT',
      undefined,
      undefined,
      undefined,
      true
    );
    this.name = 'TimeoutError';
  }
}
```

### Retry Logic

```typescript
// src/retry.ts
export interface RetryConfig {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
  retryableErrors: NedliaErrorCode[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  baseDelayMs: 1000,
  maxDelayMs: 30000,
  retryableErrors: ['NETWORK_ERROR', 'TIMEOUT', 'RATE_LIMITED', 'SERVICE_UNAVAILABLE'],
};

export async function withRetry<T>(
  fn: () => Promise<T>,
  config: Partial<RetryConfig> = {}
): Promise<T> {
  const { maxAttempts, baseDelayMs, maxDelayMs, retryableErrors } = {
    ...DEFAULT_RETRY_CONFIG,
    ...config,
  };

  let lastError: Error | undefined;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      const isRetryable = error instanceof NedliaError && retryableErrors.includes(error.code);

      if (!isRetryable || attempt === maxAttempts) {
        throw error;
      }

      const delay = Math.min(baseDelayMs * Math.pow(2, attempt - 1), maxDelayMs);
      const jitter = delay * 0.1 * Math.random();
      await sleep(delay + jitter);
    }
  }

  throw lastError;
}
```

### Client Usage

```typescript
// src/client.ts
export class NedliaClient {
  async getPlacement(placementId: string): Promise<Placement> {
    return withRetry(async () => {
      const response = await this.fetch(`/placements/${placementId}`);

      if (!response.ok) {
        throw NedliaError.fromResponse(await response.json());
      }

      return response.json();
    });
  }
}
```

### Error Handling in Consumer Code

```typescript
// Consumer usage
try {
  const placement = await client.getPlacement(id);
} catch (error) {
  if (error instanceof NedliaError) {
    switch (error.code) {
      case 'NOT_FOUND':
        // Handle missing placement
        break;
      case 'UNAUTHORIZED':
        // Redirect to login
        break;
      case 'RATE_LIMITED':
        // Show rate limit message
        break;
      default:
        // Generic error handling
        console.error('API error:', error.message);
    }
  } else {
    // Unexpected error
    console.error('Unexpected error:', error);
  }
}
```

---

## 4. Python SDK

**Location**: `nedlia-sdk/python/`

### Strategy

- **Exception hierarchy** mirroring API errors
- **Automatic retry** with tenacity
- **Timeout configuration** per operation
- **Structured logging** for debugging

### Exception Classes

```python
# nedlia/exceptions.py
from dataclasses import dataclass
from typing import Any

@dataclass
class NedliaError(Exception):
    """Base exception for Nedlia SDK."""
    message: str
    code: str = "INTERNAL_ERROR"
    status_code: int | None = None
    request_id: str | None = None
    details: list[dict[str, Any]] | None = None
    retryable: bool = False

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

@dataclass
class ValidationError(NedliaError):
    code: str = "VALIDATION_ERROR"
    status_code: int = 400

@dataclass
class NotFoundError(NedliaError):
    code: str = "NOT_FOUND"
    status_code: int = 404

@dataclass
class UnauthorizedError(NedliaError):
    code: str = "UNAUTHORIZED"
    status_code: int = 401

@dataclass
class RateLimitError(NedliaError):
    code: str = "RATE_LIMITED"
    status_code: int = 429
    retryable: bool = True
    retry_after: int = 60

@dataclass
class NetworkError(NedliaError):
    code: str = "NETWORK_ERROR"
    retryable: bool = True

@dataclass
class TimeoutError(NedliaError):
    code: str = "TIMEOUT"
    retryable: bool = True
```

### Retry with Tenacity

```python
# nedlia/client.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)

def is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, NedliaError) and exc.retryable

class NedliaClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception(is_retryable),
    )
    async def get_placement(self, placement_id: str) -> Placement:
        response = await self._request("GET", f"/placements/{placement_id}")
        return Placement(**response)

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                timeout=self.timeout,
                **kwargs,
            ) as response:
                if response.status >= 400:
                    error_body = await response.json()
                    raise self._parse_error(response.status, error_body)
                return await response.json()

        except aiohttp.ClientError as e:
            raise NetworkError(message=str(e))
        except asyncio.TimeoutError:
            raise TimeoutError(message=f"Request timed out after {self.timeout}s")

    def _parse_error(self, status: int, body: dict) -> NedliaError:
        error = body.get("error", {})
        code = error.get("code", "INTERNAL_ERROR")
        message = error.get("message", "Unknown error")
        request_id = error.get("request_id")
        details = error.get("details")

        error_classes = {
            "VALIDATION_ERROR": ValidationError,
            "NOT_FOUND": NotFoundError,
            "UNAUTHORIZED": UnauthorizedError,
            "RATE_LIMITED": RateLimitError,
        }

        error_class = error_classes.get(code, NedliaError)
        return error_class(
            message=message,
            status_code=status,
            request_id=request_id,
            details=details,
        )
```

### Consumer Usage

```python
from nedlia import NedliaClient
from nedlia.exceptions import NotFoundError, RateLimitError

client = NedliaClient(api_key="...")

try:
    placement = await client.get_placement(placement_id)
except NotFoundError:
    print("Placement not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except NedliaError as e:
    print(f"API error: {e}")
```

---

## 5. Swift SDK

**Location**: `nedlia-sdk/swift/`

### Strategy

- **Result type** for all async operations
- **Typed errors** with associated values
- **Async/await** with structured concurrency
- **Automatic retry** for transient failures

### Error Types

```swift
// Sources/NedliaSDK/Errors.swift
import Foundation

public enum NedliaError: Error, Equatable {
    case validation(message: String, details: [ValidationDetail]?)
    case unauthorized(message: String)
    case forbidden(message: String)
    case notFound(resource: String, id: String)
    case conflict(message: String)
    case rateLimited(retryAfter: Int)
    case networkError(underlying: Error)
    case timeout(seconds: TimeInterval)
    case serverError(message: String, requestId: String?)
    case decodingError(underlying: Error)

    public var isRetryable: Bool {
        switch self {
        case .networkError, .timeout, .rateLimited, .serverError:
            return true
        default:
            return false
        }
    }

    public var localizedDescription: String {
        switch self {
        case .validation(let message, _):
            return "Validation error: \(message)"
        case .unauthorized(let message):
            return "Unauthorized: \(message)"
        case .forbidden(let message):
            return "Forbidden: \(message)"
        case .notFound(let resource, let id):
            return "\(resource) '\(id)' not found"
        case .conflict(let message):
            return "Conflict: \(message)"
        case .rateLimited(let retryAfter):
            return "Rate limited. Retry after \(retryAfter) seconds"
        case .networkError(let underlying):
            return "Network error: \(underlying.localizedDescription)"
        case .timeout(let seconds):
            return "Request timed out after \(seconds) seconds"
        case .serverError(let message, _):
            return "Server error: \(message)"
        case .decodingError(let underlying):
            return "Decoding error: \(underlying.localizedDescription)"
        }
    }
}

public struct ValidationDetail: Codable, Equatable {
    public let field: String
    public let code: String
    public let message: String
}
```

### Result-Based API

```swift
// Sources/NedliaSDK/Client.swift
import Foundation

public actor NedliaClient {
    private let baseURL: URL
    private let apiKey: String
    private let session: URLSession
    private let retryConfig: RetryConfig

    public func getPlacement(id: String) async -> Result<Placement, NedliaError> {
        await withRetry(config: retryConfig) {
            try await self.request(
                method: "GET",
                path: "/placements/\(id)",
                responseType: Placement.self
            )
        }
    }

    private func request<T: Decodable>(
        method: String,
        path: String,
        body: Encodable? = nil,
        responseType: T.Type
    ) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(path))
        request.httpMethod = method
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw NedliaError.networkError(underlying: URLError(.badServerResponse))
        }

        if httpResponse.statusCode >= 400 {
            throw try parseError(statusCode: httpResponse.statusCode, data: data)
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw NedliaError.decodingError(underlying: error)
        }
    }

    private func parseError(statusCode: Int, data: Data) throws -> NedliaError {
        let errorResponse = try JSONDecoder().decode(APIErrorResponse.self, from: data)
        let error = errorResponse.error

        switch error.code {
        case "VALIDATION_ERROR":
            return .validation(message: error.message, details: error.details)
        case "UNAUTHORIZED":
            return .unauthorized(message: error.message)
        case "FORBIDDEN":
            return .forbidden(message: error.message)
        case "NOT_FOUND":
            return .notFound(resource: "Resource", id: "unknown")
        case "CONFLICT":
            return .conflict(message: error.message)
        case "RATE_LIMITED":
            return .rateLimited(retryAfter: 60)
        default:
            return .serverError(message: error.message, requestId: error.requestId)
        }
    }
}
```

### Retry Logic

```swift
// Sources/NedliaSDK/Retry.swift
public struct RetryConfig {
    public let maxAttempts: Int
    public let baseDelay: TimeInterval
    public let maxDelay: TimeInterval

    public static let `default` = RetryConfig(
        maxAttempts: 3,
        baseDelay: 1.0,
        maxDelay: 30.0
    )
}

func withRetry<T>(
    config: RetryConfig,
    operation: @escaping () async throws -> T
) async -> Result<T, NedliaError> {
    var lastError: NedliaError?

    for attempt in 1...config.maxAttempts {
        do {
            let result = try await operation()
            return .success(result)
        } catch let error as NedliaError {
            lastError = error

            guard error.isRetryable && attempt < config.maxAttempts else {
                return .failure(error)
            }

            let delay = min(
                config.baseDelay * pow(2.0, Double(attempt - 1)),
                config.maxDelay
            )
            try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))

        } catch {
            return .failure(.networkError(underlying: error))
        }
    }

    return .failure(lastError ?? .serverError(message: "Unknown error", requestId: nil))
}
```

### Consumer Usage

```swift
let client = NedliaClient(apiKey: "...")

let result = await client.getPlacement(id: placementId)

switch result {
case .success(let placement):
    // Use placement
    print("Got placement: \(placement.id)")

case .failure(let error):
    switch error {
    case .notFound:
        // Handle not found
        showAlert("Placement not found")

    case .unauthorized:
        // Redirect to login
        navigateToLogin()

    case .rateLimited(let retryAfter):
        // Show rate limit message
        showAlert("Please wait \(retryAfter) seconds")

    default:
        // Generic error
        showAlert(error.localizedDescription)
    }
}
```

---

## 6. Editor Plugins (Swift)

**Location**: `nedlia-plugin/finalcut/`, `nedlia-plugin/davinci/`, `nedlia-plugin/lumafusion/`

### Strategy

- **User-facing error alerts** with actionable messages
- **Offline mode** with local queue
- **Graceful degradation** when server unavailable
- **Automatic sync retry** when connection restored

### Error Types

```swift
// Sources/NedliaPlugin/Errors.swift
public enum PluginError: Error {
    // API Errors (from SDK)
    case apiError(NedliaError)

    // Local Errors
    case invalidTimeRange(start: TimeInterval, end: TimeInterval)
    case placementOverlap(existingId: String)
    case projectNotLoaded
    case unsupportedVideoFormat(format: String)

    // Sync Errors
    case syncFailed(reason: String)
    case offlineMode
    case conflictDetected(local: Placement, remote: Placement)

    public var userMessage: String {
        switch self {
        case .apiError(let nedliaError):
            return nedliaError.localizedDescription

        case .invalidTimeRange(let start, let end):
            return "Invalid time range: \(formatTime(start)) - \(formatTime(end))"

        case .placementOverlap(let existingId):
            return "This placement overlaps with an existing one"

        case .projectNotLoaded:
            return "Please open a project first"

        case .unsupportedVideoFormat(let format):
            return "Video format '\(format)' is not supported"

        case .syncFailed(let reason):
            return "Sync failed: \(reason)"

        case .offlineMode:
            return "Working offline. Changes will sync when connected."

        case .conflictDetected:
            return "Conflict detected. Please resolve before continuing."
        }
    }

    public var isRecoverable: Bool {
        switch self {
        case .offlineMode, .syncFailed:
            return true
        default:
            return false
        }
    }
}
```

### Offline Queue

```swift
// Sources/NedliaPlugin/OfflineQueue.swift
public actor OfflineQueue {
    private var pendingOperations: [PendingOperation] = []
    private let storage: LocalStorage
    private let client: NedliaClient

    public func enqueue(_ operation: Operation) async {
        let pending = PendingOperation(
            id: UUID().uuidString,
            operation: operation,
            createdAt: Date(),
            retryCount: 0
        )
        pendingOperations.append(pending)
        await storage.savePendingOperations(pendingOperations)
    }

    public func sync() async -> [SyncResult] {
        var results: [SyncResult] = []

        for operation in pendingOperations {
            let result = await executeOperation(operation)
            results.append(result)

            if case .success = result {
                pendingOperations.removeAll { $0.id == operation.id }
            }
        }

        await storage.savePendingOperations(pendingOperations)
        return results
    }

    private func executeOperation(_ operation: PendingOperation) async -> SyncResult {
        switch operation.operation {
        case .createPlacement(let placement):
            let result = await client.createPlacement(placement)
            return result.map { .created($0) }
                         .mapError { .apiError($0) }

        case .updatePlacement(let id, let updates):
            let result = await client.updatePlacement(id: id, updates: updates)
            return result.map { .updated($0) }
                         .mapError { .apiError($0) }

        case .deletePlacement(let id):
            let result = await client.deletePlacement(id: id)
            return result.map { _ in .deleted(id) }
                         .mapError { .apiError($0) }
        }
    }
}
```

### User-Facing Error Handling

```swift
// Sources/NedliaPlugin/UI/ErrorPresenter.swift
public class ErrorPresenter {
    public func present(_ error: PluginError, in viewController: NSViewController) {
        let alert = NSAlert()
        alert.messageText = "Error"
        alert.informativeText = error.userMessage
        alert.alertStyle = error.isRecoverable ? .warning : .critical

        if error.isRecoverable {
            alert.addButton(withTitle: "Retry")
            alert.addButton(withTitle: "Cancel")
        } else {
            alert.addButton(withTitle: "OK")
        }

        // Add "Report Issue" for unexpected errors
        if case .apiError(.serverError) = error {
            alert.addButton(withTitle: "Report Issue")
        }

        let response = alert.runModal()

        switch response {
        case .alertFirstButtonReturn where error.isRecoverable:
            // Retry action
            NotificationCenter.default.post(name: .retryLastOperation, object: nil)
        case .alertThirdButtonReturn:
            // Report issue
            openIssueReporter(error: error)
        default:
            break
        }
    }

    private func openIssueReporter(error: PluginError) {
        // Open issue reporter with error context
    }
}
```

### Connection State Management

```swift
// Sources/NedliaPlugin/ConnectionManager.swift
public actor ConnectionManager {
    public enum State {
        case connected
        case disconnected
        case reconnecting
    }

    @Published public private(set) var state: State = .disconnected
    private let client: NedliaClient
    private let offlineQueue: OfflineQueue

    public func checkConnection() async {
        let result = await client.healthCheck()

        switch result {
        case .success:
            if state != .connected {
                state = .connected
                // Sync pending operations
                await offlineQueue.sync()
            }
        case .failure:
            state = .disconnected
        }
    }

    public func handleOperation<T>(
        _ operation: @escaping () async -> Result<T, NedliaError>,
        fallback: @escaping () async -> T?
    ) async -> Result<T, PluginError> {
        if state == .disconnected {
            if let fallbackResult = await fallback() {
                return .success(fallbackResult)
            }
            return .failure(.offlineMode)
        }

        let result = await operation()

        switch result {
        case .success(let value):
            return .success(value)
        case .failure(let error):
            if error.isRetryable {
                state = .disconnected
                if let fallbackResult = await fallback() {
                    return .success(fallbackResult)
                }
            }
            return .failure(.apiError(error))
        }
    }
}
```

---

## 7. Frontend (React Portal)

**Location**: `nedlia-front-end/portal/`

### Strategy

- **Error boundaries** for component-level error isolation
- **Toast notifications** for user feedback
- **Retry UI** for transient failures
- **Form validation** with inline errors

### Error Boundary

```tsx
// src/components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';
import { ErrorFallback } from './ErrorFallback';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
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
    console.error('Error boundary caught:', error, errorInfo);
    this.props.onError?.(error, errorInfo);

    // Send to error tracking
    trackError(error, { componentStack: errorInfo.componentStack });
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <ErrorFallback
            error={this.state.error}
            onRetry={() => this.setState({ hasError: false })}
          />
        )
      );
    }
    return this.props.children;
  }
}
```

### API Error Handling Hook

```tsx
// src/hooks/useApiError.ts
import { useState, useCallback } from 'react';
import { NedliaError } from '@/lib/errors';
import { toast } from '@/components/ui/toast';

interface UseApiErrorOptions {
  showToast?: boolean;
  onUnauthorized?: () => void;
}

export function useApiError(options: UseApiErrorOptions = {}) {
  const { showToast = true, onUnauthorized } = options;
  const [error, setError] = useState<NedliaError | null>(null);

  const handleError = useCallback(
    (error: unknown) => {
      if (error instanceof NedliaError) {
        setError(error);

        if (error.code === 'UNAUTHORIZED') {
          onUnauthorized?.();
          return;
        }

        if (showToast) {
          toast({
            variant: 'destructive',
            title: getErrorTitle(error.code),
            description: error.message,
          });
        }
      } else {
        const genericError = new NedliaError('An unexpected error occurred', 'INTERNAL_ERROR');
        setError(genericError);

        if (showToast) {
          toast({
            variant: 'destructive',
            title: 'Error',
            description: 'An unexpected error occurred. Please try again.',
          });
        }
      }
    },
    [showToast, onUnauthorized]
  );

  const clearError = useCallback(() => setError(null), []);

  return { error, handleError, clearError };
}

function getErrorTitle(code: string): string {
  const titles: Record<string, string> = {
    VALIDATION_ERROR: 'Validation Error',
    UNAUTHORIZED: 'Authentication Required',
    FORBIDDEN: 'Access Denied',
    NOT_FOUND: 'Not Found',
    CONFLICT: 'Conflict',
    RATE_LIMITED: 'Too Many Requests',
    INTERNAL_ERROR: 'Server Error',
  };
  return titles[code] ?? 'Error';
}
```

### Query Error Handling (React Query)

```tsx
// src/hooks/usePlacement.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useApiError } from './useApiError';
import { placementApi } from '@/lib/api';

export function usePlacement(placementId: string) {
  const { handleError } = useApiError();

  return useQuery({
    queryKey: ['placement', placementId],
    queryFn: () => placementApi.get(placementId),
    retry: (failureCount, error) => {
      // Only retry retryable errors, max 3 times
      if (error instanceof NedliaError && error.retryable) {
        return failureCount < 3;
      }
      return false;
    },
    onError: handleError,
  });
}

export function useCreatePlacement() {
  const queryClient = useQueryClient();
  const { handleError } = useApiError();

  return useMutation({
    mutationFn: placementApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['placements'] });
      toast({ title: 'Placement created successfully' });
    },
    onError: handleError,
  });
}
```

### Form Validation Errors

```tsx
// src/components/PlacementForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { placementSchema } from '@/lib/schemas';

export function PlacementForm() {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(placementSchema),
  });

  const mutation = useCreatePlacement();

  const onSubmit = async (data: PlacementInput) => {
    try {
      await mutation.mutateAsync(data);
    } catch (error) {
      if (error instanceof NedliaError && error.code === 'VALIDATION_ERROR') {
        // Map server validation errors to form fields
        error.details?.forEach(detail => {
          setError(detail.field as keyof PlacementInput, {
            type: 'server',
            message: detail.message,
          });
        });
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Input {...register('name')} error={errors.name?.message} />
      <Input {...register('startTime')} type="number" error={errors.startTime?.message} />
      <Input {...register('endTime')} type="number" error={errors.endTime?.message} />
      <Button type="submit" loading={mutation.isPending}>
        Create Placement
      </Button>
    </form>
  );
}
```

---

## Cross-Cutting Concerns

### Correlation IDs

All components should propagate correlation IDs for distributed tracing:

```python
# API: Extract from header or generate
correlation_id = request.headers.get("X-Request-ID") or str(uuid4())

# Worker: Extract from event
correlation_id = event.get("detail", {}).get("correlation_id")

# SDK: Include in requests
headers = {"X-Request-ID": self.correlation_id}
```

### Error Monitoring

| Component | Tool                | Alert Threshold      |
| --------- | ------------------- | -------------------- |
| API       | CloudWatch + Sentry | 5xx > 1% of requests |
| Workers   | CloudWatch          | DLQ messages > 0     |
| SDKs      | Client-side Sentry  | Error rate > 0.1%    |
| Plugins   | Crash reporting     | Any crash            |
| Frontend  | Sentry              | Error rate > 0.5%    |

### Testing Error Scenarios

```python
# API: Test exception handling
@pytest.mark.parametrize("exception,expected_status,expected_code", [
    (ValidationError("Invalid"), 400, "VALIDATION_ERROR"),
    (NotFoundError("Video", "123"), 404, "NOT_FOUND"),
    (ConflictError("Overlap"), 409, "CONFLICT"),
])
async def test_exception_handler(exception, expected_status, expected_code):
    response = await client.get("/test-error", params={"error": exception.__class__.__name__})
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
```

```typescript
// SDK: Test retry behavior
describe('retry', () => {
  it('retries on network error', async () => {
    const fn = jest
      .fn()
      .mockRejectedValueOnce(new NetworkError())
      .mockResolvedValueOnce({ data: 'success' });

    const result = await withRetry(fn);

    expect(fn).toHaveBeenCalledTimes(2);
    expect(result).toEqual({ data: 'success' });
  });

  it('does not retry on validation error', async () => {
    const fn = jest.fn().mockRejectedValue(new NedliaError('Invalid', 'VALIDATION_ERROR', 400));

    await expect(withRetry(fn)).rejects.toThrow('Invalid');
    expect(fn).toHaveBeenCalledTimes(1);
  });
});
```

---

## Related Documentation

- [Error Handling Guide](error-handling.md) – Core error patterns
- [Resilience Patterns](resilience-patterns.md) – Circuit breakers, retries, fallbacks
- [API Standards](api-standards.md) – Error response format
- [Logging Standards](logging-standards.md) – Error logging
- [Testing Strategy](testing-strategy.md) – Testing error cases
- [Observability](observability.md) – Error monitoring and alerting
