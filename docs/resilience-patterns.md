# Resilience Patterns

This document defines resilience patterns for building fault-tolerant systems in Nedlia.

## Resilience Principles

1. **Expect Failure**: Design for failure, not just success
2. **Fail Fast**: Detect failures quickly, don't wait for timeouts
3. **Fail Gracefully**: Degrade functionality rather than crash
4. **Recover Automatically**: Self-healing systems
5. **Learn from Failures**: Post-mortems and improvements

---

## Circuit Breaker

Prevent cascading failures by stopping requests to failing services.

### States

```
┌─────────┐     failure threshold     ┌─────────┐
│ CLOSED  │ ─────────────────────────▶│  OPEN   │
│(normal) │                           │ (fail)  │
└────┬────┘                           └────┬────┘
     │                                     │
     │ success                             │ timeout
     │                                     │
     │         ┌─────────────┐             │
     └─────────│ HALF-OPEN   │◀────────────┘
               │  (testing)  │
               └─────────────┘
```

### Implementation

```python
# src/infrastructure/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from threading import Lock

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self._lock = Lock()

    def can_execute(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                if datetime.now() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise CircuitOpenError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        return wrapper

# Usage
db_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

@db_circuit
def query_database(sql: str):
    return db.execute(sql)
```

### Per-Service Circuit Breakers

```python
# Circuit breakers for external services
circuit_breakers = {
    "database": CircuitBreaker(failure_threshold=5, recovery_timeout=30),
    "s3": CircuitBreaker(failure_threshold=3, recovery_timeout=60),
    "eventbridge": CircuitBreaker(failure_threshold=3, recovery_timeout=60),
    "external_api": CircuitBreaker(failure_threshold=10, recovery_timeout=120),
}
```

---

## Retry with Exponential Backoff

Retry transient failures with increasing delays.

### Implementation

```python
# src/infrastructure/retry.py
import asyncio
import random
from functools import wraps
from typing import Type, Tuple

def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        raise

                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts}",
                        delay=delay,
                        error=str(e),
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        raise

                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    if jitter:
                        delay = delay * (0.5 + random.random())

                    time.sleep(delay)

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

# Usage
@retry(
    max_attempts=3,
    base_delay=1.0,
    retryable_exceptions=(ConnectionError, TimeoutError),
)
async def call_external_api(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
```

### Retry Policies by Service

| Service          | Max Attempts   | Base Delay | Max Delay |
| ---------------- | -------------- | ---------- | --------- |
| Database         | 3              | 0.5s       | 5s        |
| S3               | 3              | 1s         | 10s       |
| EventBridge      | 5              | 1s         | 30s       |
| External API     | 3              | 2s         | 60s       |
| SQS (via Lambda) | Handled by SQS | -          | -         |

---

## Timeout

Prevent requests from hanging indefinitely.

### Implementation

```python
# src/infrastructure/timeout.py
import asyncio
from functools import wraps

def timeout(seconds: float):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation timed out after {seconds}s")
        return wrapper
    return decorator

# Usage
@timeout(5.0)
async def fetch_placement(placement_id: str):
    return await repository.find_by_id(placement_id)
```

### Timeout Configuration

| Operation         | Timeout                  |
| ----------------- | ------------------------ |
| Database query    | 5s                       |
| S3 upload         | 30s                      |
| External API call | 10s                      |
| Lambda execution  | 30s (API), 300s (Worker) |
| API Gateway       | 29s                      |

---

## Bulkhead

Isolate failures to prevent resource exhaustion.

### Connection Pool Bulkhead

```python
# src/infrastructure/database.py
from sqlalchemy.pool import QueuePool

# Separate pools for different workloads
read_pool = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
)

write_pool = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
)

# Critical operations get dedicated pool
critical_pool = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=3,
    max_overflow=0,
    pool_timeout=10,
)
```

### Semaphore Bulkhead

```python
# src/infrastructure/bulkhead.py
import asyncio

class Bulkhead:
    def __init__(self, max_concurrent: int, name: str = "default"):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.name = name
        self.waiting = 0
        self.active = 0

    async def __aenter__(self):
        self.waiting += 1
        await self.semaphore.acquire()
        self.waiting -= 1
        self.active += 1
        return self

    async def __aexit__(self, *args):
        self.active -= 1
        self.semaphore.release()

# Usage
external_api_bulkhead = Bulkhead(max_concurrent=10, name="external_api")

async def call_external_api():
    async with external_api_bulkhead:
        # Only 10 concurrent calls allowed
        return await httpx.get("https://api.example.com")
```

---

## Fallback

Provide alternative behavior when primary fails.

### Implementation

```python
# src/infrastructure/fallback.py
from functools import wraps
from typing import Callable, Any

def fallback(fallback_func: Callable[..., Any]):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "Primary failed, using fallback",
                    error=str(e),
                    function=func.__name__,
                )
                return await fallback_func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
async def get_placement_from_cache(placement_id: str):
    """Fallback: return cached data"""
    cached = await cache.get(f"placement:{placement_id}")
    if cached:
        return Placement.from_cache(cached)
    raise PlacementNotFound(placement_id)

@fallback(get_placement_from_cache)
async def get_placement(placement_id: str):
    """Primary: fetch from database"""
    return await repository.find_by_id(placement_id)
```

### Fallback Strategies

| Scenario          | Primary   | Fallback               |
| ----------------- | --------- | ---------------------- |
| Get placement     | Database  | Cache                  |
| Validate video    | Real-time | Return pending status  |
| Send notification | Email     | Queue for retry        |
| Generate file     | S3        | Return placeholder URL |

---

## Rate Limiting

Protect services from overload.

### Token Bucket Algorithm

```python
# src/infrastructure/rate_limiter.py
import time
from threading import Lock

class TokenBucket:
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = Lock()

    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

# Usage
api_rate_limiter = TokenBucket(rate=100, capacity=200)  # 100 req/s, burst 200

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if not api_rate_limiter.acquire():
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"},
            headers={"Retry-After": "1"},
        )
    return await call_next(request)
```

### Per-User Rate Limiting

```python
# Redis-based rate limiting
class RedisRateLimiter:
    def __init__(self, redis: Redis, key_prefix: str, limit: int, window: int):
        self.redis = redis
        self.key_prefix = key_prefix
        self.limit = limit
        self.window = window

    async def is_allowed(self, identifier: str) -> tuple[bool, int]:
        key = f"{self.key_prefix}:{identifier}"
        pipe = self.redis.pipeline()

        pipe.incr(key)
        pipe.expire(key, self.window)
        results = await pipe.execute()

        current = results[0]
        remaining = max(0, self.limit - current)

        return current <= self.limit, remaining

# Usage
user_limiter = RedisRateLimiter(
    redis=redis_client,
    key_prefix="rate:user",
    limit=1000,
    window=60,  # 1000 requests per minute
)

async def check_rate_limit(user_id: str):
    allowed, remaining = await user_limiter.is_allowed(user_id)
    if not allowed:
        raise RateLimitExceeded(remaining=remaining)
```

---

## Dead Letter Queue (DLQ)

Handle messages that fail processing.

### SQS DLQ Configuration

```hcl
# nedlia-IaC/modules/sqs/main.tf
resource "aws_sqs_queue" "main" {
  name = "nedlia-${var.environment}-${var.queue_name}"

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3  # Move to DLQ after 3 failures
  })
}

resource "aws_sqs_queue" "dlq" {
  name = "nedlia-${var.environment}-${var.queue_name}-dlq"

  message_retention_seconds = 1209600  # 14 days
}
```

### DLQ Processing

```python
# src/workers/dlq_processor.py
async def process_dlq():
    """Process messages from DLQ for investigation or replay"""
    messages = await sqs.receive_messages(
        QueueUrl=DLQ_URL,
        MaxNumberOfMessages=10,
    )

    for message in messages:
        try:
            # Log for investigation
            logger.error(
                "DLQ message",
                message_id=message["MessageId"],
                body=message["Body"],
                attributes=message.get("Attributes", {}),
            )

            # Optionally replay
            if should_replay(message):
                await sqs.send_message(
                    QueueUrl=MAIN_QUEUE_URL,
                    MessageBody=message["Body"],
                )

            # Delete from DLQ
            await sqs.delete_message(
                QueueUrl=DLQ_URL,
                ReceiptHandle=message["ReceiptHandle"],
            )

        except Exception as e:
            logger.error("Failed to process DLQ message", error=str(e))
```

---

## Graceful Degradation

Reduce functionality to maintain core service.

### Feature Flags for Degradation

```python
# src/infrastructure/degradation.py
class DegradationManager:
    def __init__(self, feature_flags: FeatureFlagService):
        self.feature_flags = feature_flags

    async def is_feature_available(self, feature: str) -> bool:
        # Check if feature is manually disabled
        if await self.feature_flags.is_disabled(f"degradation:{feature}"):
            return False

        # Check circuit breaker
        circuit = circuit_breakers.get(feature)
        if circuit and circuit.state == CircuitState.OPEN:
            return False

        return True

# Usage
degradation = DegradationManager(feature_flags)

async def get_placement_with_validation(placement_id: str):
    placement = await get_placement(placement_id)

    # Skip validation if service is degraded
    if await degradation.is_feature_available("validation"):
        placement.validation_status = await validate(placement)
    else:
        placement.validation_status = "pending"  # Degrade gracefully

    return placement
```

### Degradation Levels

| Level         | Description             | Actions                            |
| ------------- | ----------------------- | ---------------------------------- |
| **Normal**    | All systems operational | Full functionality                 |
| **Degraded**  | Non-critical failures   | Disable analytics, caching         |
| **Critical**  | Major component down    | Read-only mode, queue writes       |
| **Emergency** | Multiple failures       | Static responses, maintenance page |

---

## Health Checks

Detect failures early.

### Liveness vs Readiness

```python
# Liveness: Is the process alive?
@router.get("/health/live")
async def liveness():
    return {"status": "alive"}

# Readiness: Can the service handle requests?
@router.get("/health/ready")
async def readiness():
    checks = {
        "database": await check_database(),
        "cache": await check_cache(),
    }

    all_ready = all(c["status"] == "ready" for c in checks.values())

    if not all_ready:
        raise HTTPException(status_code=503, detail=checks)

    return {"status": "ready", "checks": checks}
```

### Dependency Health Checks

```python
async def check_database() -> dict:
    try:
        start = time.time()
        await db.execute("SELECT 1")
        latency = (time.time() - start) * 1000

        return {
            "status": "ready" if latency < 100 else "degraded",
            "latency_ms": latency,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_cache() -> dict:
    try:
        await redis.ping()
        return {"status": "ready"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

---

## Chaos Engineering

Test resilience in production.

### Principles

1. Start with a hypothesis
2. Vary real-world events
3. Run experiments in production
4. Automate experiments
5. Minimize blast radius

### Experiments

| Experiment        | Tool         | Purpose               |
| ----------------- | ------------ | --------------------- |
| Kill Lambda       | AWS FIS      | Test auto-recovery    |
| Network latency   | AWS FIS      | Test timeout handling |
| Database failover | RDS          | Test failover time    |
| S3 errors         | Chaos Monkey | Test fallback         |

### AWS Fault Injection Simulator

```hcl
resource "aws_fis_experiment_template" "lambda_failure" {
  description = "Inject failures into Lambda"

  action {
    name      = "inject-lambda-error"
    action_id = "aws:lambda:invoke-function"

    parameter {
      key   = "functionArn"
      value = aws_lambda_function.api.arn
    }
  }

  stop_condition {
    source = "aws:cloudwatch:alarm"
    value  = aws_cloudwatch_metric_alarm.error_rate.arn
  }

  target {
    name           = "lambda-functions"
    resource_type  = "aws:lambda:function"
    selection_mode = "ALL"
  }
}
```

---

## Related Documentation

- [Observability](observability.md) – Monitoring failures
- [Architecture](../ARCHITECTURE.md) – System design
- [ADR-003: Event-Driven](adr/003-event-driven.md) – Async patterns
