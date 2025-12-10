# Performance Guidelines

Performance optimization patterns for Nedlia's API, database queries, and frontend.

## Principles

1. **Measure First**: Profile before optimizing
2. **Optimize Hot Paths**: Focus on frequently executed code
3. **Avoid Premature Optimization**: Clarity over micro-optimizations
4. **Set Budgets**: Define performance targets and monitor them

---

## Performance Targets

| Metric              | Target  | Alert Threshold |
| ------------------- | ------- | --------------- |
| API p50 latency     | < 100ms | > 200ms         |
| API p99 latency     | < 500ms | > 1000ms        |
| Database query time | < 50ms  | > 200ms         |
| Time to First Byte  | < 200ms | > 500ms         |
| Frontend LCP        | < 2.5s  | > 4s            |
| Frontend FID        | < 100ms | > 300ms         |

---

## Database Performance

### N+1 Query Prevention

The most common performance issue. Always eager-load related data.

```python
# ❌ Bad: N+1 queries
async def get_placements_with_products(video_id: UUID) -> list[dict]:
    placements = await session.execute(
        select(Placement).where(Placement.video_id == video_id)
    )
    results = []
    for placement in placements.scalars():
        # This executes a query for EACH placement!
        product = await session.get(Product, placement.product_id)
        results.append({"placement": placement, "product": product})
    return results


# ✅ Good: Eager loading with joinedload
from sqlalchemy.orm import joinedload

async def get_placements_with_products(video_id: UUID) -> list[Placement]:
    result = await session.execute(
        select(Placement)
        .options(joinedload(Placement.product))
        .where(Placement.video_id == video_id)
    )
    return result.scalars().unique().all()


# ✅ Good: Explicit join
async def get_placements_with_products(video_id: UUID) -> list[dict]:
    result = await session.execute(
        select(Placement, Product)
        .join(Product, Placement.product_id == Product.id)
        .where(Placement.video_id == video_id)
    )
    return [{"placement": p, "product": pr} for p, pr in result.all()]
```

### Pagination

Never load unbounded result sets.

```python
# ❌ Bad: Loading all records
async def get_all_placements() -> list[Placement]:
    result = await session.execute(select(Placement))
    return result.scalars().all()  # Could be millions!


# ✅ Good: Cursor-based pagination
async def get_placements(
    cursor: UUID | None = None,
    limit: int = 20,
) -> tuple[list[Placement], UUID | None]:
    query = select(Placement).order_by(Placement.created_at.desc())

    if cursor:
        cursor_placement = await session.get(Placement, cursor)
        if cursor_placement:
            query = query.where(Placement.created_at < cursor_placement.created_at)

    query = query.limit(limit + 1)  # Fetch one extra to check for more
    result = await session.execute(query)
    placements = result.scalars().all()

    next_cursor = None
    if len(placements) > limit:
        placements = placements[:limit]
        next_cursor = placements[-1].id

    return placements, next_cursor
```

### Index Optimization

```sql
-- Check slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

-- Check missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;

-- Analyze query plan
EXPLAIN ANALYZE
SELECT * FROM placements
WHERE video_id = '...' AND status = 'active'
ORDER BY created_at DESC
LIMIT 20;
```

**Index Guidelines**:

- Index columns used in WHERE, JOIN, ORDER BY
- Use composite indexes for multi-column queries
- Consider partial indexes for filtered queries
- Don't over-index (slows writes)

```sql
-- Composite index for common query pattern
CREATE INDEX idx_placements_video_status_created
ON placements (video_id, status, created_at DESC)
WHERE deleted_at IS NULL;

-- Partial index for active records only
CREATE INDEX idx_placements_active
ON placements (video_id)
WHERE status = 'active' AND deleted_at IS NULL;
```

### Query Optimization

```python
# ❌ Bad: SELECT * when you only need a few columns
result = await session.execute(select(Placement))

# ✅ Good: Select only needed columns
result = await session.execute(
    select(Placement.id, Placement.status, Placement.created_at)
    .where(Placement.video_id == video_id)
)


# ❌ Bad: Multiple queries for counts
total = await session.execute(select(func.count(Placement.id)))
active = await session.execute(
    select(func.count(Placement.id)).where(Placement.status == 'active')
)

# ✅ Good: Single query with conditional counts
result = await session.execute(
    select(
        func.count(Placement.id).label('total'),
        func.count(Placement.id).filter(Placement.status == 'active').label('active'),
    )
)
```

### Connection Pool Tuning

```python
# src/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.database_url,
    pool_size=10,           # Base pool size
    max_overflow=20,        # Additional connections when needed
    pool_pre_ping=True,     # Verify connections before use
    pool_recycle=3600,      # Recycle connections after 1 hour
    pool_timeout=30,        # Wait max 30s for connection
)
```

---

## API Performance

### Async All the Way

```python
# ❌ Bad: Blocking call in async context
import requests

async def fetch_video_metadata(video_id: str) -> dict:
    response = requests.get(f"https://api.example.com/videos/{video_id}")
    return response.json()


# ✅ Good: Async HTTP client
import httpx

async def fetch_video_metadata(video_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.example.com/videos/{video_id}")
        return response.json()
```

### Parallel Requests

```python
import asyncio

# ❌ Bad: Sequential requests
async def get_placement_details(placement_ids: list[UUID]) -> list[dict]:
    results = []
    for pid in placement_ids:
        placement = await get_placement(pid)
        product = await get_product(placement.product_id)
        results.append({"placement": placement, "product": product})
    return results


# ✅ Good: Parallel requests
async def get_placement_details(placement_ids: list[UUID]) -> list[dict]:
    placements = await asyncio.gather(*[
        get_placement(pid) for pid in placement_ids
    ])

    products = await asyncio.gather(*[
        get_product(p.product_id) for p in placements
    ])

    return [
        {"placement": p, "product": pr}
        for p, pr in zip(placements, products)
    ]
```

### Response Streaming

For large responses, stream instead of buffering:

```python
from fastapi.responses import StreamingResponse
import json


@router.get("/placements/export")
async def export_placements(video_id: UUID) -> StreamingResponse:
    async def generate():
        yield "["
        first = True
        async for placement in stream_placements(video_id):
            if not first:
                yield ","
            yield json.dumps(placement.model_dump())
            first = False
        yield "]"

    return StreamingResponse(
        generate(),
        media_type="application/json",
    )
```

### Request Timeouts

```python
# Set timeouts on external calls
async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
    response = await client.get(url)

# Set database query timeout
from sqlalchemy import text

await session.execute(text("SET statement_timeout = '5000'"))  # 5 seconds
```

---

## Caching Performance

See [Caching Strategy](caching-strategy.md) for detailed patterns.

```python
# Cache expensive computations
@cached("validation_result", ttl=600)
async def validate_video(video_id: UUID) -> ValidationResult:
    # Expensive validation logic
    ...

# Cache database queries
async def get_placement(placement_id: UUID) -> Placement:
    cache_key = f"placement:{placement_id}"

    cached = await redis.get(cache_key)
    if cached:
        return Placement.model_validate_json(cached)

    placement = await repository.find_by_id(placement_id)
    if placement:
        await redis.setex(cache_key, 300, placement.model_dump_json())

    return placement
```

---

## Frontend Performance

### Bundle Optimization

```typescript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
  },
});
```

### Lazy Loading

```typescript
// Lazy load routes
const PlacementEditor = lazy(() => import('./pages/PlacementEditor'));
const Analytics = lazy(() => import('./pages/Analytics'));

function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/editor" element={<PlacementEditor />} />
        <Route path="/analytics" element={<Analytics />} />
      </Routes>
    </Suspense>
  );
}
```

### Image Optimization

```typescript
// Use next/image or similar for automatic optimization
import Image from 'next/image';

<Image src="/product-thumbnail.jpg" width={200} height={200} loading="lazy" placeholder="blur" />;
```

### React Performance

```typescript
// Memoize expensive components
const PlacementList = memo(function PlacementList({ placements }: Props) {
  return (
    <ul>
      {placements.map(p => (
        <PlacementItem key={p.id} placement={p} />
      ))}
    </ul>
  );
});

// Memoize expensive computations
const sortedPlacements = useMemo(
  () => placements.sort((a, b) => a.startTime - b.startTime),
  [placements]
);

// Memoize callbacks
const handleClick = useCallback(
  (id: string) => {
    onSelect(id);
  },
  [onSelect]
);
```

### Virtual Lists

For long lists, use virtualization:

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function PlacementList({ placements }: { placements: Placement[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: placements.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
  });

  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(virtualItem => (
          <div
            key={virtualItem.key}
            style={{
              position: 'absolute',
              top: virtualItem.start,
              height: virtualItem.size,
            }}
          >
            <PlacementItem placement={placements[virtualItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Monitoring Performance

### API Metrics

```python
# src/middleware/timing.py
import time
from prometheus_client import Histogram

request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        request_duration.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        ).observe(duration)

        response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
        return response
```

### Database Query Logging

```python
# Log slow queries
import logging
from sqlalchemy import event

logger = logging.getLogger("sqlalchemy.engine")


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.perf_counter() - conn.info["query_start_time"].pop()
    if total > 0.1:  # Log queries > 100ms
        logger.warning(
            "Slow query",
            extra={
                "duration_ms": total * 1000,
                "statement": statement[:500],
            },
        )
```

---

## Performance Testing

### Load Testing with k6

```javascript
// tests/performance/k6/api-load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 }, // Ramp up
    { duration: '3m', target: 50 }, // Stay at 50 users
    { duration: '1m', target: 100 }, // Ramp up more
    { duration: '3m', target: 100 }, // Stay at 100 users
    { duration: '1m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'], // Error rate < 1%
  },
};

export default function () {
  const res = http.get('https://api.nedlia.com/v1/placements');

  check(res, {
    'status is 200': r => r.status === 200,
    'response time < 500ms': r => r.timings.duration < 500,
  });

  sleep(1);
}
```

---

## Related Documentation

- [Caching Strategy](caching-strategy.md) – Redis caching patterns
- [Data Architecture](data-architecture.md) – Database design
- [Observability](observability.md) – Performance monitoring
- [Testing Strategy](testing-strategy.md) – Performance testing
