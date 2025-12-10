# Rate Limiting & Throttling

Rate limiting patterns for Nedlia's API to protect against abuse and ensure fair usage.

## Principles

1. **Protect Resources**: Prevent abuse and ensure availability
2. **Fair Usage**: Distribute capacity fairly among users
3. **Graceful Degradation**: Return helpful errors, not crashes
4. **Transparency**: Communicate limits via headers

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

## Response Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 600
X-RateLimit-Remaining: 599
X-RateLimit-Reset: 1705312800
```

### Rate Limit Exceeded Response

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 30

{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Retry after 30 seconds.",
    "retry_after": 30
  }
}
```

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

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_at)

        return response

    def _rate_limit_response(self, result: RateLimitResult) -> Response:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": f"Rate limit exceeded. Retry after {result.retry_after} seconds.",
                    "retry_after": result.retry_after,
                }
            },
            headers={
                "Retry-After": str(result.retry_after),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(result.reset_at),
            },
        )
```

---

## Per-Endpoint Limits

Some endpoints need different limits:

```python
# src/core/rate_limiter.py
from functools import wraps


def rate_limit(limit: int, window: int = 60):
    """Decorator for per-endpoint rate limiting."""

    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            rate_limiter = request.app.state.rate_limiter
            user_id = request.state.user.id if hasattr(request.state, "user") else request.client.host
            key = f"endpoint:{func.__name__}:{user_id}"

            result = await rate_limiter.check(key, limit, window)

            if not result.allowed:
                raise RateLimitError(
                    message=f"Endpoint rate limit exceeded. Retry after {result.retry_after} seconds.",
                    retry_after=result.retry_after,
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
- [Error Handling](error-handling.md) – RateLimitError
- [Caching Strategy](caching-strategy.md) – Redis usage
- [Observability](observability.md) – Monitoring rate limits
