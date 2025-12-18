# Rate Limiting & Throttling

Rate limiting patterns for Nedlia's API using **[IETF RateLimit Headers](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)** standard.

## Table of Contents

- [Principles](#principles)
- [Rate Limit Tiers](#rate-limit-tiers)
- [Response Headers (IETF Standard)](#response-headers-ietf-standard)
- [Implementation](#implementation)
- [FastAPI Middleware](#fastapi-middleware)
- [Per-Endpoint Limits](#per-endpoint-limits)
- [Client Retry Strategies](#client-retry-strategies)
- [API Gateway Rate Limiting](#api-gateway-rate-limiting)
- [Monitoring](#monitoring)
- [Related Documentation](#related-documentation)
- [References](#references)

---

## Principles

1. **Protect Resources**: Prevent abuse and ensure availability
2. **Fair Usage**: Distribute capacity fairly among users
3. **Graceful Degradation**: Return helpful errors, not crashes
4. **Standards-Based**: Use IETF RateLimit headers + RFC 9457 Problem Details

---

## Rate Limit Tiers

| Tier           | Requests/min | Burst | Use Case                 |
| -------------- | ------------ | ----- | ------------------------ |
| **Anonymous**  | 30           | 5     | Unauthenticated requests |
| **Free**       | 60           | 10    | Free tier users          |
| **Pro**        | 600          | 100   | Paid users               |
| **Enterprise** | 6000         | 1000  | Enterprise customers     |
| **Internal**   | Unlimited    | -     | Internal services        |

---

## Response Headers (IETF Standard)

Nedlia uses the **[IETF RateLimit Headers draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/)** standard.

### RateLimit-Policy Header

Advertises the quota policy:

```
RateLimit-Policy: "default";q=600;w=60
```

| Parameter | Description              | Example         |
| --------- | ------------------------ | --------------- |
| `q`       | Quota (requests allowed) | `q=600`         |
| `w`       | Window (seconds)         | `w=60`          |
| `qu`      | Quota unit (optional)    | `qu="requests"` |
| `pk`      | Partition key (optional) | `pk=:base64:`   |

### RateLimit Header

Communicates current service limits:

```
RateLimit: "default";r=599;t=45
```

| Parameter | Description                      | Example   |
| --------- | -------------------------------- | --------- |
| `r`       | Remaining quota units            | `r=599`   |
| `t`       | Time until quota reset (seconds) | `t=45`    |
| `pk`      | Partition key (optional)         | `pk=:..:` |

### Complete Response Example

```http
HTTP/1.1 200 OK
Content-Type: application/json
RateLimit-Policy: "default";q=600;w=60
RateLimit: "default";r=599;t=45

{"data": {...}}
```

### Rate Limit Exceeded Response (RFC 9457)

Uses RFC 9457 Problem Details with IETF-defined problem type:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/problem+json
Retry-After: 30
RateLimit-Policy: "default";q=600;w=60
RateLimit: "default";r=0;t=30

{
  "type": "https://iana.org/assignments/http-problem-types#quota-exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Request quota exceeded. Retry after 30 seconds.",
  "instance": "/v1/placements",
  "violated-policies": ["default"],
  "retry_after": 30
}
```

> **Note**: The `type` URI `https://iana.org/assignments/http-problem-types#quota-exceeded` is the IETF-registered problem type for rate limiting.

---

## Implementation

### Token Bucket Algorithm

```python
# src/core/rate_limiter.py
import time
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_at: int
    retry_after: int | None = None


class TokenBucketRateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = int(now // window_seconds) * window_seconds
        window_key = f"ratelimit:{key}:{window_start}"

        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds + 1)
        results = await pipe.execute()

        current_count = results[0]
        remaining = max(0, limit - current_count)
        reset_at = window_start + window_seconds

        if current_count > limit:
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=reset_at,
                retry_after=int(reset_at - now),
            )

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
        )
```

### Sliding Window Algorithm

More accurate but slightly more complex:

```python
class SlidingWindowRateLimiter:
    """Sliding window rate limiter for smoother limiting."""

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        now = time.time()
        window_key = f"ratelimit:sliding:{key}"

        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(window_key, 0, now - window_seconds)

        # Count current entries
        pipe.zcard(window_key)

        # Add current request
        pipe.zadd(window_key, {str(now): now})

        # Set expiry
        pipe.expire(window_key, window_seconds + 1)

        results = await pipe.execute()
        current_count = results[1]

        if current_count >= limit:
            # Get oldest entry to calculate retry time
            oldest = await self.redis.zrange(window_key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + window_seconds - now) if oldest else window_seconds

            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                reset_at=int(now + retry_after),
                retry_after=retry_after,
            )

        return RateLimitResult(
            allowed=True,
            limit=limit,
            remaining=limit - current_count - 1,
            reset_at=int(now + window_seconds),
        )
```

---

## FastAPI Middleware

```python
# src/middleware/rate_limit.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.rate_limiter import TokenBucketRateLimiter, RateLimitResult
from src.core.exceptions import RateLimitError


TIER_LIMITS = {
    "anonymous": 30,
    "free": 60,
    "pro": 600,
    "enterprise": 6000,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/health/ready"]:
            return await call_next(request)

        # Get rate limiter from app state
        rate_limiter: TokenBucketRateLimiter = request.app.state.rate_limiter

        # Determine user tier and key
        user = getattr(request.state, "user", None)
        if user:
            tier = user.subscription_tier
            key = f"user:{user.id}"
        else:
            tier = "anonymous"
            key = f"ip:{request.client.host}"

        limit = TIER_LIMITS.get(tier, 30)

        # Check rate limit
        result = await rate_limiter.check(key, limit)

        if not result.allowed:
            return self._rate_limit_response(result)

        # Process request
        response = await call_next(request)

        # Add IETF RateLimit headers
        policy_name = tier
        response.headers["RateLimit-Policy"] = f'"{policy_name}";q={result.limit};w=60'
        response.headers["RateLimit"] = f'"{policy_name}";r={result.remaining};t={result.reset_at - int(time.time())}'

        return response

    def _rate_limit_response(self, result: RateLimitResult, policy_name: str = "default") -> Response:
        """Return RFC 9457 Problem Details response for rate limiting."""
        return JSONResponse(
            status_code=429,
            content={
                "type": "https://iana.org/assignments/http-problem-types#quota-exceeded",
                "title": "Rate Limit Exceeded",
                "status": 429,
                "detail": f"Request quota exceeded. Retry after {result.retry_after} seconds.",
                "violated-policies": [policy_name],
                "retry_after": result.retry_after,
            },
            media_type="application/problem+json",
            headers={
                "Retry-After": str(result.retry_after),
                "RateLimit-Policy": f'"{policy_name}";q={result.limit};w=60',
                "RateLimit": f'"{policy_name}";r=0;t={result.retry_after}',
            },
        )
```

---

## Per-Endpoint Limits

Some endpoints need different limits:

```python
# src/core/rate_limiter.py
from functools import wraps


def rate_limit(limit: int, window: int = 60, policy_name: str = "endpoint"):
    """Decorator for per-endpoint rate limiting with IETF headers."""

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = request.app.state.rate_limiter
            user_id = request.state.user.id if hasattr(request.state, "user") else request.client.host
            key = f"endpoint:{func.__name__}:{user_id}"

            result = await rate_limiter.check(key, limit, window)

            if not result.allowed:
                # Raise RFC 9457 compliant rate limit exception
                raise RateLimitException(
                    detail=f"Endpoint rate limit exceeded. Retry after {result.retry_after} seconds.",
                    retry_after=result.retry_after,
                    extensions={"violated-policies": [policy_name]},
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
```

```python
# src/placements/router.py
from src.core.rate_limiter import rate_limit


@router.post("/validate")
@rate_limit(limit=10, window=60)  # 10 validations per minute
async def validate_placement(
    placement_id: UUID,
    service: PlacementServiceDep,
) -> ValidationResult:
    return await service.validate(placement_id)
```

---

## Client Retry Strategies

### SDK Implementation

```python
# nedlia-sdk/python/src/client.py
import time
import random
from typing import TypeVar

import httpx

T = TypeVar("T")


class NedliaClient:
    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(
            base_url="https://api.nedlia.com/v1",
            headers={"X-API-Key": api_key},
        )

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make request with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(method, path, **kwargs)

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.max_retries:
                        await self._wait_with_jitter(retry_after)
                        continue
                    raise RateLimitError(retry_after=retry_after)

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self.max_retries:
                    await self._wait_with_jitter(2 ** attempt)
                    last_exception = e
                    continue
                raise

        raise last_exception

    async def _wait_with_jitter(self, base_seconds: float) -> None:
        """Wait with exponential backoff and jitter."""
        jitter = random.uniform(0, 0.1 * base_seconds)
        await asyncio.sleep(base_seconds + jitter)
```

### TypeScript SDK

```typescript
// nedlia-sdk/javascript/src/client.ts
export class NedliaClient {
  private maxRetries = 3;

  async request<T>(method: string, path: string, options?: RequestInit): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const response = await fetch(`${this.baseUrl}${path}`, {
          method,
          headers: {
            'X-API-Key': this.apiKey,
            'Content-Type': 'application/json',
          },
          ...options,
        });

        if (response.status === 429) {
          const retryAfter = parseInt(response.headers.get('Retry-After') || '60');
          if (attempt < this.maxRetries) {
            await this.sleep(retryAfter * 1000);
            continue;
          }
          throw new RateLimitError(retryAfter);
        }

        if (!response.ok) {
          throw new ApiError(response.status, await response.json());
        }

        return response.json();
      } catch (error) {
        if (error instanceof ApiError && error.status >= 500 && attempt < this.maxRetries) {
          await this.sleep(Math.pow(2, attempt) * 1000);
          lastError = error;
          continue;
        }
        throw error;
      }
    }

    throw lastError;
  }

  private sleep(ms: number): Promise<void> {
    const jitter = Math.random() * ms * 0.1;
    return new Promise(resolve => setTimeout(resolve, ms + jitter));
  }
}
```

---

## API Gateway Rate Limiting

AWS API Gateway provides additional rate limiting:

```hcl
# nedlia-IaC/modules/api-gateway/main.tf
resource "aws_api_gateway_usage_plan" "pro" {
  name = "pro-tier"

  throttle_settings {
    rate_limit  = 600   # requests per second
    burst_limit = 100   # burst capacity
  }

  quota_settings {
    limit  = 100000     # requests per month
    period = "MONTH"
  }
}

resource "aws_api_gateway_usage_plan" "enterprise" {
  name = "enterprise-tier"

  throttle_settings {
    rate_limit  = 6000
    burst_limit = 1000
  }

  # No monthly quota for enterprise
}
```

---

## Monitoring

### Metrics

```python
from prometheus_client import Counter, Histogram

rate_limit_hits = Counter(
    "rate_limit_hits_total",
    "Rate limit hits",
    ["tier", "endpoint"],
)

rate_limit_remaining = Histogram(
    "rate_limit_remaining",
    "Remaining rate limit when request made",
    ["tier"],
)
```

### Alerts

```yaml
# CloudWatch alarm for high rate limit hits
- name: HighRateLimitHits
  metric: rate_limit_hits_total
  threshold: 1000
  period: 300 # 5 minutes
  action: notify-oncall
```

---

## Related Documentation

- [API Standards](api-standards.md) – Error response format
- [Error Handling](error-handling.md) – RateLimitException (RFC 9457)
- [Error Handling Strategy](error-handling-strategy.md) – Project-specific error handling
- [Caching Strategy](caching-strategy.md) – Redis usage
- [Observability](observability.md) – Monitoring rate limits

## References

- [IETF RateLimit Headers Draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/) – Standard for rate limit headers
- [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) – Standard error format
- [IANA HTTP Problem Types](https://www.iana.org/assignments/http-problem-types/) – Registered problem types including `quota-exceeded`
