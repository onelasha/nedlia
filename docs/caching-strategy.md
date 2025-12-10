# Caching Strategy

Caching patterns and Redis implementation for Nedlia's API and services.

## Principles

1. **Cache What's Expensive**: Database queries, external API calls, computed results
2. **Invalidate Correctly**: Stale data is worse than no cache
3. **Fail Gracefully**: Cache failures shouldn't break the application
4. **Monitor Hit Rates**: Low hit rates indicate wasted resources

---

## Cache Layers

| Layer           | Technology   | TTL        | Use Case                     |
| --------------- | ------------ | ---------- | ---------------------------- |
| **Application** | Redis        | 5-60 min   | API responses, computed data |
| **Database**    | Aurora cache | Automatic  | Query result caching         |
| **CDN**         | CloudFront   | 1-24 hours | Static assets, public API    |
| **Client**      | Browser/SDK  | Varies     | HTTP cache headers           |

---

## Redis Setup

### Connection (Lifespan)

```python
# src/core/lifespan.py
from contextlib import asynccontextmanager
from redis.asyncio import Redis

from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis
    app.state.redis = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
    )

    yield

    # Cleanup
    await app.state.redis.close()
```

### Dependency

```python
# src/core/dependencies.py
from typing import Annotated
from fastapi import Depends, Request
from redis.asyncio import Redis


async def get_redis(request: Request) -> Redis:
    return request.app.state.redis


RedisClient = Annotated[Redis, Depends(get_redis)]
```

---

## Caching Patterns

### Cache-Aside (Lazy Loading)

Most common pattern: check cache first, load from DB on miss.

```python
# src/placements/service.py
import json
from uuid import UUID

from src.core.dependencies import RedisClient


class PlacementService:
    def __init__(self, repository: PlacementRepository, redis: Redis) -> None:
        self.repository = repository
        self.redis = redis
        self.cache_ttl = 300  # 5 minutes

    async def get_by_id(self, placement_id: UUID) -> Placement | None:
        cache_key = f"placement:{placement_id}"

        # Try cache first
        cached = await self.redis.get(cache_key)
        if cached:
            return Placement.model_validate_json(cached)

        # Cache miss - load from database
        placement = await self.repository.find_by_id(placement_id)
        if placement:
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                placement.model_dump_json(),
            )

        return placement
```

### Write-Through

Update cache when writing to database.

```python
async def update(self, placement_id: UUID, data: PlacementUpdate) -> Placement:
    # Update database
    placement = await self.repository.update(placement_id, data)

    # Update cache
    cache_key = f"placement:{placement_id}"
    await self.redis.setex(
        cache_key,
        self.cache_ttl,
        placement.model_dump_json(),
    )

    return placement
```

### Cache Invalidation

Delete cache when data changes.

```python
async def delete(self, placement_id: UUID) -> None:
    # Delete from database
    await self.repository.delete(placement_id)

    # Invalidate cache
    await self.redis.delete(f"placement:{placement_id}")

    # Also invalidate related caches
    placement = await self.repository.find_by_id(placement_id)
    if placement:
        await self.redis.delete(f"video:{placement.video_id}:placements")
```

### Pattern-Based Invalidation

```python
async def invalidate_video_caches(self, video_id: UUID) -> None:
    """Invalidate all caches related to a video."""
    pattern = f"video:{video_id}:*"

    # Use SCAN to find keys (don't use KEYS in production)
    cursor = 0
    while True:
        cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
        if keys:
            await self.redis.delete(*keys)
        if cursor == 0:
            break
```

---

## Cache Key Conventions

```python
# Key format: {entity}:{id}:{optional_suffix}

# Single entity
"placement:550e8400-e29b-41d4-a716-446655440000"
"video:6ba7b810-9dad-11d1-80b4-00c04fd430c8"

# Related collection
"video:6ba7b810-9dad-11d1-80b4-00c04fd430c8:placements"

# Query results (hash the query params)
"placements:list:abc123hash"

# User-specific
"user:123:preferences"

# Rate limiting
"ratelimit:user:123:api"
```

### Key Builder

```python
# src/core/cache.py
from typing import Any
import hashlib
import json


class CacheKey:
    @staticmethod
    def placement(placement_id: UUID) -> str:
        return f"placement:{placement_id}"

    @staticmethod
    def video_placements(video_id: UUID) -> str:
        return f"video:{video_id}:placements"

    @staticmethod
    def query(prefix: str, params: dict[str, Any]) -> str:
        """Generate cache key for query with parameters."""
        param_hash = hashlib.md5(
            json.dumps(params, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]
        return f"{prefix}:query:{param_hash}"
```

---

## TTL Guidelines

| Data Type            | TTL     | Reason                          |
| -------------------- | ------- | ------------------------------- |
| User session         | 30 min  | Security, frequent access       |
| Placement details    | 5 min   | May change, frequently accessed |
| Video metadata       | 15 min  | Rarely changes                  |
| List/search results  | 1-2 min | Quickly stale with new data     |
| Static configuration | 1 hour  | Rarely changes                  |
| Rate limit counters  | 1 min   | Short window                    |
| Validation results   | 10 min  | Expensive to compute            |

---

## Caching Decorator

```python
# src/core/cache.py
from functools import wraps
from typing import Callable, TypeVar
import json

T = TypeVar("T")


def cached(
    key_prefix: str,
    ttl: int = 300,
    key_builder: Callable[..., str] | None = None,
):
    """Decorator for caching function results."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(self, *args, **kwargs) -> T:
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"{key_prefix}:{args[0] if args else 'default'}"

            # Try cache
            cached_value = await self.redis.get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            # Execute function
            result = await func(self, *args, **kwargs)

            # Cache result
            if result is not None:
                await self.redis.setex(
                    cache_key,
                    ttl,
                    json.dumps(result, default=str),
                )

            return result

        return wrapper

    return decorator
```

```python
# Usage
class PlacementService:
    @cached("placement", ttl=300)
    async def get_by_id(self, placement_id: UUID) -> Placement | None:
        return await self.repository.find_by_id(placement_id)
```

---

## Cache Stampede Prevention

When cache expires, multiple requests may hit the database simultaneously.

### Lock-Based Prevention

```python
async def get_with_lock(self, placement_id: UUID) -> Placement | None:
    cache_key = f"placement:{placement_id}"
    lock_key = f"lock:{cache_key}"

    # Try cache first
    cached = await self.redis.get(cache_key)
    if cached:
        return Placement.model_validate_json(cached)

    # Try to acquire lock
    acquired = await self.redis.set(lock_key, "1", nx=True, ex=10)

    if acquired:
        try:
            # We have the lock - load from DB
            placement = await self.repository.find_by_id(placement_id)
            if placement:
                await self.redis.setex(
                    cache_key,
                    self.cache_ttl,
                    placement.model_dump_json(),
                )
            return placement
        finally:
            await self.redis.delete(lock_key)
    else:
        # Another request is loading - wait and retry
        await asyncio.sleep(0.1)
        return await self.get_with_lock(placement_id)
```

### Probabilistic Early Expiration

```python
import random
import time


async def get_with_early_expiry(self, placement_id: UUID) -> Placement | None:
    cache_key = f"placement:{placement_id}"

    cached = await self.redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        expiry_time = data.get("_expiry", 0)

        # Probabilistically refresh before expiry
        time_left = expiry_time - time.time()
        if time_left > 0 and random.random() > (time_left / self.cache_ttl):
            # Refresh in background
            asyncio.create_task(self._refresh_cache(placement_id))

        return Placement.model_validate(data["value"])

    return await self._load_and_cache(placement_id)
```

---

## Graceful Degradation

Cache failures shouldn't break the application.

```python
async def get_by_id(self, placement_id: UUID) -> Placement | None:
    cache_key = f"placement:{placement_id}"

    try:
        cached = await self.redis.get(cache_key)
        if cached:
            return Placement.model_validate_json(cached)
    except RedisError as e:
        logger.warning("Cache read failed", extra={"error": str(e)})
        # Continue to database

    # Load from database
    placement = await self.repository.find_by_id(placement_id)

    # Try to cache, but don't fail if Redis is down
    if placement:
        try:
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                placement.model_dump_json(),
            )
        except RedisError as e:
            logger.warning("Cache write failed", extra={"error": str(e)})

    return placement
```

---

## HTTP Caching

### Cache Headers

```python
# src/placements/router.py
from fastapi import Response


@router.get("/{placement_id}")
async def get_placement(
    placement_id: UUID,
    response: Response,
    service: PlacementServiceDep,
) -> PlacementResponse:
    placement = await service.get_by_id(placement_id)

    # Set cache headers
    response.headers["Cache-Control"] = "private, max-age=60"
    response.headers["ETag"] = f'"{placement.version}"'

    return placement


@router.get("/public/products")
async def list_products(response: Response) -> list[ProductResponse]:
    # Public data can be cached by CDN
    response.headers["Cache-Control"] = "public, max-age=3600"
    return await product_service.list_all()
```

### Conditional Requests

```python
from fastapi import Header, HTTPException


@router.get("/{placement_id}")
async def get_placement(
    placement_id: UUID,
    if_none_match: str | None = Header(None),
    service: PlacementServiceDep,
) -> PlacementResponse:
    placement = await service.get_by_id(placement_id)
    etag = f'"{placement.version}"'

    if if_none_match == etag:
        raise HTTPException(status_code=304)  # Not Modified

    return placement
```

---

## Monitoring

### Cache Metrics

```python
# src/core/cache.py
from prometheus_client import Counter, Histogram

cache_hits = Counter("cache_hits_total", "Cache hits", ["cache_name"])
cache_misses = Counter("cache_misses_total", "Cache misses", ["cache_name"])
cache_latency = Histogram("cache_latency_seconds", "Cache operation latency")


async def get_cached(self, key: str, cache_name: str) -> str | None:
    with cache_latency.time():
        result = await self.redis.get(key)

    if result:
        cache_hits.labels(cache_name=cache_name).inc()
    else:
        cache_misses.labels(cache_name=cache_name).inc()

    return result
```

### CloudWatch Metrics

```python
# Log cache stats for CloudWatch
logger.info(
    "Cache operation",
    extra={
        "cache_key": cache_key,
        "hit": cached is not None,
        "latency_ms": latency_ms,
    },
)
```

---

## Related Documentation

- [Data Architecture](data-architecture.md) – Database design
- [Performance Guidelines](performance-guidelines.md) – Optimization
- [Observability](observability.md) – Monitoring cache metrics
- [Resilience Patterns](resilience-patterns.md) – Fallback strategies
