# Idempotency

Idempotency patterns for Nedlia's API using the **[IETF Idempotency-Key Header](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)** standard.

## Table of Contents

- [What is Idempotency?](#what-is-idempotency)
- [Why Idempotency Matters](#why-idempotency-matters)
- [Benefits of Idempotency Keys](#benefits-of-idempotency-keys)
- [IETF Standard: Idempotency-Key Header](#ietf-standard-idempotency-key-header)
- [Server Behavior](#server-behavior)
- [Error Handling (RFC 9457)](#error-handling-rfc-9457)
- [Implementation](#implementation)
- [Client Implementation](#client-implementation)
- [Best Practices](#best-practices)
- [Security Considerations](#security-considerations)
- [Related Documentation](#related-documentation)
- [References](#references)

---

## What is Idempotency?

An **idempotent operation** produces the same result regardless of how many times it's executed. In HTTP APIs:

| Method | Idempotent | Safe | Notes                        |
| ------ | ---------- | ---- | ---------------------------- |
| GET    | ✅         | ✅   | Always idempotent            |
| HEAD   | ✅         | ✅   | Always idempotent            |
| PUT    | ✅         | ❌   | Replaces entire resource     |
| DELETE | ✅         | ❌   | Deleting twice = same result |
| POST   | ❌         | ❌   | **Requires Idempotency-Key** |
| PATCH  | ❌         | ❌   | **Requires Idempotency-Key** |

---

## Why Idempotency Matters

### The Problem: Network Uncertainty

```
Client                    Network                    Server
   |                         |                         |
   |-------- POST /orders ---|------------------------>|
   |                         |     ❌ Connection lost   |
   |<------ Timeout ---------|                         |
   |                         |                         |
   |  ❓ Did the order get created?                    |
   |  ❓ Is it safe to retry?                          |
```

Without idempotency, the client faces a dilemma:

- **Retry**: Risk creating duplicate orders
- **Don't retry**: Risk losing the order entirely

### The Solution: Idempotency Keys

```
Client                    Network                    Server
   |                         |                         |
   |-- POST /orders ---------|------------------------>|
   |   Idempotency-Key: abc  |     ❌ Connection lost   |
   |<------ Timeout ---------|                         |
   |                         |                         |
   |-- POST /orders ---------|------------------------>| ✅ Same key =
   |   Idempotency-Key: abc  |                         |    return cached result
   |<------------------------|-------- 201 Created ----|
```

---

## Benefits of Idempotency Keys

### 1. **Safe Retries**

Clients can safely retry failed requests without fear of duplicate operations.

```python
# Client code - safe to retry
async def create_order(order_data: dict) -> Order:
    idempotency_key = str(uuid.uuid4())

    for attempt in range(3):
        try:
            response = await client.post(
                "/orders",
                json=order_data,
                headers={"Idempotency-Key": idempotency_key}
            )
            return Order(**response.json())
        except TimeoutError:
            continue  # Safe to retry with same key

    raise OrderCreationFailed()
```

### 2. **Exactly-Once Semantics**

Critical for financial operations where duplicates are unacceptable:

| Operation             | Without Idempotency  | With Idempotency    |
| --------------------- | -------------------- | ------------------- |
| Payment processing    | Double charge risk   | Exactly one charge  |
| Order creation        | Duplicate orders     | Single order        |
| Inventory reservation | Over-reservation     | Correct reservation |
| Webhook delivery      | Duplicate processing | Process once        |

### 3. **Simplified Error Handling**

Clients don't need complex logic to determine if an operation succeeded:

```typescript
// Without idempotency - complex error handling
async function createPlacement(data: PlacementData): Promise<Placement> {
  try {
    return await api.post('/placements', data);
  } catch (error) {
    if (error instanceof TimeoutError) {
      // Did it succeed? Need to query and check...
      const existing = await api.get('/placements', {
        filter: { video_id: data.video_id, start_time: data.start_time },
      });
      if (existing.length > 0) {
        return existing[0]; // Maybe this one? Maybe a different one?
      }
      // Still uncertain...
    }
    throw error;
  }
}

// With idempotency - simple retry
async function createPlacement(data: PlacementData): Promise<Placement> {
  const idempotencyKey = generateKey(data);
  return await api.post('/placements', data, {
    headers: { 'Idempotency-Key': idempotencyKey },
    retry: { maxAttempts: 3 }, // Safe to retry
  });
}
```

### 4. **Distributed System Resilience**

In microservices, requests may be processed by different instances:

```
                    ┌─────────────┐
                    │ Load        │
    Request ───────►│ Balancer    │
    Key: abc        └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐   ┌────────┐   ┌────────┐
         │ API-1  │   │ API-2  │   │ API-3  │
         └────┬───┘   └────┬───┘   └────┬───┘
              │            │            │
              └────────────┼────────────┘
                           ▼
                    ┌─────────────┐
                    │   Redis     │  ← Shared idempotency store
                    │ (Key: abc)  │
                    └─────────────┘
```

### 5. **Audit Trail**

Idempotency keys provide natural correlation for debugging:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "idempotency_key": "8e03978e-40d5-43e8-bc93-6894a57f9324",
  "action": "placement_created",
  "placement_id": "pl_abc123",
  "duplicate_request": false
}
```

---

## IETF Standard: Idempotency-Key Header

Nedlia implements the **[IETF Idempotency-Key Header draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/)**.

### Header Format

```http
POST /v1/placements HTTP/1.1
Host: api.nedlia.com
Content-Type: application/json
Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"

{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "time_range": { "start_time": 30.5, "end_time": 45.0 }
}
```

### Key Requirements

| Requirement     | Description                                   |
| --------------- | --------------------------------------------- |
| **Format**      | String (RFC 8941 Structured Field)            |
| **Uniqueness**  | Must be unique per operation                  |
| **Recommended** | UUID v4 or similar high-entropy random string |
| **Expiry**      | Keys expire after 24 hours (configurable)     |
| **Scope**       | Per-user or per-API-key                       |

### Industry Adoption

The Idempotency-Key header is used by major APIs:

- **Stripe** - Payment processing
- **PayPal** - Financial transactions
- **Adyen** - Payment gateway
- **Square** - Commerce platform
- **Twilio** - Communications
- **Google Standard Payments** - Payment processing

---

## Server Behavior

### Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Request Received                          │
│                   Idempotency-Key: "abc123"                      │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Key exists in cache?   │
                    └───────────┬─────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
        ┌───────────────┐               ┌───────────────┐
        │      NO       │               │      YES      │
        │  First time   │               │   Duplicate   │
        └───────┬───────┘               └───────┬───────┘
                │                               │
                ▼                               ▼
        ┌───────────────┐               ┌───────────────┐
        │ Process       │               │ Check status  │
        │ request       │               └───────┬───────┘
        └───────┬───────┘                       │
                │                   ┌───────────┴───────────┐
                ▼                   │                       │
        ┌───────────────┐           ▼                       ▼
        │ Store result  │   ┌───────────────┐       ┌───────────────┐
        │ with key      │   │  Completed    │       │  In Progress  │
        └───────┬───────┘   │  Return cached│       │  Return 409   │
                │           │  response     │       │  Conflict     │
                ▼           └───────────────┘       └───────────────┘
        ┌───────────────┐
        │ Return result │
        └───────────────┘
```

### Response Scenarios

#### First Request (New Key)

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "data": {
    "id": "pl_abc123",
    "video_id": "...",
    "status": "active"
  }
}
```

#### Duplicate Request (Same Key, Completed)

```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "data": {
    "id": "pl_abc123",
    "video_id": "...",
    "status": "active"
  }
}
```

> Same response as original - client can't tell it's a duplicate.

#### Concurrent Request (Same Key, In Progress)

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/idempotency-conflict",
  "title": "Request In Progress",
  "status": 409,
  "detail": "A request with this Idempotency-Key is currently being processed."
}
```

---

## Error Handling (RFC 9457)

### Missing Idempotency-Key

When required but not provided:

```http
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/idempotency-key-missing",
  "title": "Idempotency-Key Required",
  "status": 400,
  "detail": "This operation requires an Idempotency-Key header."
}
```

### Key Reused with Different Payload

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/idempotency-key-reused",
  "title": "Idempotency-Key Already Used",
  "status": 422,
  "detail": "This Idempotency-Key was used with a different request payload."
}
```

### Concurrent Request Conflict

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/idempotency-conflict",
  "title": "Request In Progress",
  "status": 409,
  "detail": "A request with this Idempotency-Key is currently being processed."
}
```

---

## Implementation

### Server-Side (FastAPI)

```python
# src/middleware/idempotency.py
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response
from redis.asyncio import Redis

from src.core.exceptions import ProblemException

IDEMPOTENCY_TTL = 86400  # 24 hours


@dataclass
class IdempotencyRecord:
    status: str  # "processing" | "completed"
    response_status: int | None = None
    response_body: str | None = None
    fingerprint: str | None = None


class IdempotencyMiddleware:
    """IETF Idempotency-Key header implementation."""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def process_request(
        self,
        request: Request,
        idempotency_key: str,
    ) -> Response | None:
        """
        Check idempotency key and return cached response if available.
        Returns None if request should be processed normally.
        """
        cache_key = self._cache_key(request, idempotency_key)
        fingerprint = await self._compute_fingerprint(request)

        # Try to get existing record
        record_data = await self.redis.get(cache_key)

        if record_data:
            record = IdempotencyRecord(**json.loads(record_data))

            # Check if request is still being processed
            if record.status == "processing":
                raise IdempotencyConflictException()

            # Check fingerprint matches
            if record.fingerprint != fingerprint:
                raise IdempotencyKeyReusedException()

            # Return cached response
            return Response(
                content=record.response_body,
                status_code=record.response_status,
                media_type="application/json",
            )

        # Mark as processing
        await self.redis.setex(
            cache_key,
            IDEMPOTENCY_TTL,
            json.dumps({"status": "processing", "fingerprint": fingerprint}),
        )

        return None  # Process request normally

    async def store_response(
        self,
        request: Request,
        idempotency_key: str,
        response: Response,
    ) -> None:
        """Store response for future duplicate requests."""
        cache_key = self._cache_key(request, idempotency_key)
        fingerprint = await self._compute_fingerprint(request)

        record = IdempotencyRecord(
            status="completed",
            response_status=response.status_code,
            response_body=response.body.decode(),
            fingerprint=fingerprint,
        )

        await self.redis.setex(
            cache_key,
            IDEMPOTENCY_TTL,
            json.dumps(record.__dict__),
        )

    def _cache_key(self, request: Request, idempotency_key: str) -> str:
        """Generate cache key scoped to user/API key."""
        user_id = getattr(request.state, "user_id", "anonymous")
        return f"idempotency:{user_id}:{idempotency_key}"

    async def _compute_fingerprint(self, request: Request) -> str:
        """Compute fingerprint of request payload."""
        body = await request.body()
        return hashlib.sha256(body).hexdigest()


# Exception classes
@dataclass
class IdempotencyKeyMissingException(ProblemException):
    type: str = "https://api.nedlia.com/problems/idempotency-key-missing"
    title: str = "Idempotency-Key Required"
    status: int = 400
    detail: str = "This operation requires an Idempotency-Key header."


@dataclass
class IdempotencyKeyReusedException(ProblemException):
    type: str = "https://api.nedlia.com/problems/idempotency-key-reused"
    title: str = "Idempotency-Key Already Used"
    status: int = 422
    detail: str = "This Idempotency-Key was used with a different request payload."


@dataclass
class IdempotencyConflictException(ProblemException):
    type: str = "https://api.nedlia.com/problems/idempotency-conflict"
    title: str = "Request In Progress"
    status: int = 409
    detail: str = "A request with this Idempotency-Key is currently being processed."
```

### Decorator for Idempotent Endpoints

```python
# src/core/idempotency.py
from functools import wraps

from fastapi import Request, Response

def idempotent(func):
    """Mark endpoint as requiring idempotency key."""

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key:
            raise IdempotencyKeyMissingException()

        # Remove quotes if present (RFC 8941 string format)
        idempotency_key = idempotency_key.strip('"')

        middleware = request.app.state.idempotency_middleware

        # Check for cached response
        cached = await middleware.process_request(request, idempotency_key)
        if cached:
            return cached

        try:
            # Process request
            response = await func(request, *args, **kwargs)

            # Store response
            await middleware.store_response(request, idempotency_key, response)

            return response

        except Exception as e:
            # Clear processing status on error
            await middleware.clear_processing(request, idempotency_key)
            raise

    return wrapper
```

### Usage in Routes

```python
# src/placements/router.py
from src.core.idempotency import idempotent

@router.post("", status_code=201)
@idempotent
async def create_placement(
    request: Request,
    data: PlacementCreate,
    service: PlacementServiceDep,
) -> PlacementResponse:
    """Create a new placement. Requires Idempotency-Key header."""
    return await service.create(data)
```

---

## Client Implementation

### Python SDK

```python
# nedlia-sdk/python/src/client.py
import uuid

class NedliaClient:
    async def create_placement(
        self,
        data: PlacementCreate,
        idempotency_key: str | None = None,
    ) -> Placement:
        """
        Create a placement with automatic idempotency.

        Args:
            data: Placement data
            idempotency_key: Optional custom key. Auto-generated if not provided.
        """
        key = idempotency_key or str(uuid.uuid4())

        return await self._request(
            "POST",
            "/placements",
            json=data.model_dump(),
            headers={"Idempotency-Key": f'"{key}"'},
        )
```

### TypeScript SDK

```typescript
// nedlia-sdk/javascript/src/client.ts
import { v4 as uuidv4 } from 'uuid';

export class NedliaClient {
  async createPlacement(
    data: PlacementCreate,
    options?: { idempotencyKey?: string }
  ): Promise<Placement> {
    const idempotencyKey = options?.idempotencyKey ?? uuidv4();

    return this.request('POST', '/placements', {
      body: data,
      headers: {
        'Idempotency-Key': `"${idempotencyKey}"`,
      },
    });
  }
}
```

---

## Best Practices

### Key Generation

```python
# ✅ Good - UUID v4 (recommended)
idempotency_key = str(uuid.uuid4())
# "8e03978e-40d5-43e8-bc93-6894a57f9324"

# ✅ Good - High-entropy random string
idempotency_key = secrets.token_urlsafe(32)
# "clkyoesmbgybucifusbbtdsbohtyuuwz"

# ✅ Good - Deterministic from business data (for retries)
idempotency_key = hashlib.sha256(
    f"{user_id}:{order_id}:{timestamp}".encode()
).hexdigest()

# ❌ Bad - Sequential or predictable
idempotency_key = str(counter)  # Attackers can guess
idempotency_key = str(int(time.time()))  # Collisions likely
```

### When to Use Idempotency Keys

| Operation              | Idempotency Key? | Reason                         |
| ---------------------- | ---------------- | ------------------------------ |
| Create placement       | ✅ Required      | Duplicate placements = bad     |
| Process payment        | ✅ Required      | Double charge = very bad       |
| Send notification      | ✅ Required      | Duplicate notifications = spam |
| Update placement (PUT) | ❌ Optional      | PUT is naturally idempotent    |
| Delete placement       | ❌ Optional      | DELETE is naturally idempotent |
| Get placement          | ❌ Not needed    | GET is safe and idempotent     |

### Retry Strategy

```python
async def create_with_retry(data: dict, max_retries: int = 3) -> dict:
    """Create resource with idempotent retries."""
    idempotency_key = str(uuid.uuid4())  # Generate ONCE

    for attempt in range(max_retries):
        try:
            return await client.post(
                "/placements",
                json=data,
                headers={"Idempotency-Key": idempotency_key},
            )
        except (TimeoutError, ConnectionError):
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    raise MaxRetriesExceeded()
```

---

## Security Considerations

### Key Validation

```python
def validate_idempotency_key(key: str) -> bool:
    """Validate idempotency key format and entropy."""
    # Must be string
    if not isinstance(key, str):
        return False

    # Reasonable length (UUID = 36 chars)
    if not 16 <= len(key) <= 128:
        return False

    # Only safe characters
    if not re.match(r'^[a-zA-Z0-9_-]+$', key):
        return False

    return True
```

### Scope Keys to Users

```python
def cache_key(user_id: str, idempotency_key: str) -> str:
    """Scope idempotency key to user to prevent cross-user attacks."""
    return f"idempotency:{user_id}:{idempotency_key}"
```

### Prevent Information Disclosure

- Don't reveal if a key exists for another user
- Return same error for invalid/missing keys
- Log key usage for audit

---

## Related Documentation

- [API Standards](api-standards.md) – HTTP methods and idempotency
- [Error Handling](error-handling.md) – RFC 9457 Problem Details
- [Rate Limiting](rate-limiting.md) – Request throttling
- [Resilience Patterns](resilience-patterns.md) – Retry strategies

## References

- [IETF Idempotency-Key Header Draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) – Standard specification
- [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html) – HTTP Semantics (idempotent methods)
- [RFC 4122](https://www.rfc-editor.org/rfc/rfc4122.html) – UUID specification
- [Stripe Idempotency](https://stripe.com/docs/idempotency) – Industry implementation
