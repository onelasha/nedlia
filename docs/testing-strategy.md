# Testing Strategy

Comprehensive testing strategy for Nedlia, covering all layers and integration patterns.

## Testing Pyramid

```
                         ╱╲
                        ╱  ╲
                       ╱ E2E╲          Few, slow, high confidence (5%)
                      ╱──────╲
                     ╱Contract╲        API contracts between services (10%)
                    ╱──────────╲
                   ╱ Integration╲      Real dependencies, boundaries (20%)
                  ╱──────────────╲
                 ╱                ╲
                ╱    Unit Tests    ╲   Fast, isolated, focused (65%)
               ╱────────────────────╲
              ╱══════════════════════╲
```

---

## Test Categories

### Unit Tests

Test individual functions, classes, and modules in isolation.

**Characteristics**:

- No I/O (network, disk, database)
- No external dependencies
- Fast (< 100ms per test)
- Deterministic

**What to Test**:

- Domain entities and value objects
- Business logic and validation
- Pure functions
- State machines

**Example**:

```python
# tests/unit/domain/test_placement.py
import pytest
from src.domain.placement import Placement, TimeRange, InvalidTimeRange

class TestPlacement:
    def test_create_valid_placement(self):
        placement = Placement(
            video_id="video-123",
            product_id="product-456",
            time_range=TimeRange(start_time=30.0, end_time=45.0),
        )
        assert placement.duration == 15.0

    def test_reject_negative_start_time(self):
        with pytest.raises(InvalidTimeRange):
            TimeRange(start_time=-1.0, end_time=10.0)

    def test_reject_end_before_start(self):
        with pytest.raises(InvalidTimeRange):
            TimeRange(start_time=50.0, end_time=30.0)
```

### Integration Tests

Test interactions between components and external systems.

**Characteristics**:

- Real database (containerized)
- Real message queues (containerized)
- Real file storage (local/mocked S3)
- Slower (seconds per test)

**What to Test**:

- Repository implementations
- API endpoints
- Message handlers
- External service clients

**Example**:

```python
# tests/integration/test_placement_repository.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="module")
def postgres():
    with PostgresContainer("postgres:15") as pg:
        yield pg

@pytest.fixture
def repository(postgres):
    return PostgresPlacementRepository(postgres.get_connection_url())

class TestPlacementRepository:
    def test_save_and_retrieve(self, repository):
        placement = Placement(
            video_id="video-123",
            product_id="product-456",
            time_range=TimeRange(30.0, 45.0),
        )

        repository.save(placement)
        retrieved = repository.find_by_id(placement.id)

        assert retrieved.video_id == placement.video_id
        assert retrieved.time_range == placement.time_range

    def test_find_by_video(self, repository):
        # Create multiple placements for same video
        for i in range(3):
            repository.save(Placement(
                video_id="video-123",
                product_id=f"product-{i}",
                time_range=TimeRange(i * 10, i * 10 + 5),
            ))

        placements = repository.find_by_video("video-123")
        assert len(placements) == 3
```

### Contract Tests

Verify API contracts between services using Consumer-Driven Contract Testing.

**Tool**: [Pact](https://pact.io/)

**Flow**:

1. Consumer defines expected interactions
2. Pact generates contract file
3. Provider verifies against contract
4. Contracts stored in Pact Broker

**Consumer Side (SDK)**:

```python
# tests/contract/test_placement_api_consumer.py
from pact import Consumer, Provider

pact = Consumer('NedliaSDK').has_pact_with(Provider('NedliaAPI'))

def test_get_placement():
    expected = {
        "data": {
            "id": "abc123",
            "video_id": "video-123",
            "status": "active",
        }
    }

    pact.given("a placement exists").upon_receiving(
        "a request for a placement"
    ).with_request(
        method="GET",
        path="/v1/placements/abc123",
    ).will_respond_with(
        status=200,
        body=expected,
    )

    with pact:
        result = sdk_client.get_placement("abc123")
        assert result.id == "abc123"
```

**Provider Side (API)**:

```python
# tests/contract/test_placement_api_provider.py
from pact import Verifier

def test_provider_against_consumer_contracts():
    verifier = Verifier(provider="NedliaAPI", provider_base_url="http://localhost:8000")

    verifier.verify_with_broker(
        broker_url="https://pact-broker.nedlia.com",
        publish_verification_results=True,
    )
```

### End-to-End Tests

Test complete user flows through the entire system.

**Tool**: [Playwright](https://playwright.dev/)

**Characteristics**:

- Real browser (Portal)
- Real API calls
- Real database
- Slowest (minutes per test)
- Run in staging environment

**Example**:

```typescript
// tests/e2e/placement-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Placement Management', () => {
  test('advertiser can create a placement', async ({ page }) => {
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'advertiser@example.com');
    await page.fill('[name="password"]', 'password');
    await page.click('button[type="submit"]');

    // Navigate to video
    await page.goto('/videos/video-123');

    // Add placement
    await page.click('[data-testid="add-placement"]');
    await page.fill('[name="start_time"]', '30');
    await page.fill('[name="end_time"]', '45');
    await page.selectOption('[name="product_id"]', 'product-456');
    await page.click('button[type="submit"]');

    // Verify
    await expect(page.locator('[data-testid="placement-list"]')).toContainText('30s - 45s');
  });
});
```

---

## Test Infrastructure

### Local Development

```bash
# Run all tests
make test

# Run specific categories
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-coverage
```

### Docker Compose for Integration Tests

```yaml
# docker-compose.test.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: nedlia_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports:
      - '5433:5432'

  localstack:
    image: localstack/localstack
    environment:
      SERVICES: s3,sqs,events
    ports:
      - '4566:4566'

  redis:
    image: redis:7
    ports:
      - '6380:6379'
```

### Testcontainers (Preferred)

```python
# conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.localstack import LocalStackContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as pg:
        yield pg

@pytest.fixture(scope="session")
def localstack():
    with LocalStackContainer() as ls:
        ls.with_services("s3", "sqs", "events")
        yield ls
```

---

## Test Data Management

### Factories

Use factories for consistent test data:

```python
# tests/factories.py
from factory import Factory, Faker, SubFactory
from src.domain.placement import Placement, TimeRange

class TimeRangeFactory(Factory):
    class Meta:
        model = TimeRange

    start_time = Faker('pyfloat', min_value=0, max_value=100)
    end_time = Faker('pyfloat', min_value=101, max_value=200)

class PlacementFactory(Factory):
    class Meta:
        model = Placement

    id = Faker('uuid4')
    video_id = Faker('uuid4')
    product_id = Faker('uuid4')
    time_range = SubFactory(TimeRangeFactory)
    description = Faker('sentence')
    status = 'active'
```

Usage:

```python
def test_something():
    placement = PlacementFactory()
    placement_with_custom = PlacementFactory(status='draft')
    placements = PlacementFactory.build_batch(10)
```

### Fixtures

```python
# tests/fixtures/placements.py
VALID_PLACEMENT = {
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "time_range": {"start_time": 30.0, "end_time": 45.0},
    "description": "Test placement",
}

INVALID_PLACEMENT_NEGATIVE_TIME = {
    **VALID_PLACEMENT,
    "time_range": {"start_time": -10.0, "end_time": 45.0},
}
```

### Database Seeding

```python
# tests/seed.py
def seed_test_database(session):
    # Create advertiser
    advertiser = Advertiser(name="Test Advertiser")
    session.add(advertiser)

    # Create campaign
    campaign = Campaign(advertiser_id=advertiser.id, name="Test Campaign")
    session.add(campaign)

    # Create products
    for i in range(5):
        product = Product(advertiser_id=advertiser.id, name=f"Product {i}")
        session.add(product)

    session.commit()
```

---

## Mocking Strategies

### Domain Layer: No Mocks

Domain logic should be tested with real objects:

```python
# Good: Real objects
def test_placement_overlap():
    p1 = Placement(time_range=TimeRange(0, 30))
    p2 = Placement(time_range=TimeRange(20, 50))
    assert p1.overlaps(p2)

# Bad: Mocking domain objects
def test_placement_overlap_bad():
    p1 = Mock(spec=Placement)
    p1.time_range = Mock()  # Don't do this
```

### Application Layer: Mock Ports

```python
# Good: Mock the port (interface)
def test_create_placement_use_case():
    mock_repo = Mock(spec=PlacementRepository)
    mock_repo.save.return_value = None

    use_case = CreatePlacementUseCase(repository=mock_repo)
    result = use_case.execute(CreatePlacementRequest(...))

    mock_repo.save.assert_called_once()
```

### Infrastructure Layer: Fakes over Mocks

```python
# Good: In-memory fake
class InMemoryPlacementRepository(PlacementRepository):
    def __init__(self):
        self._placements = {}

    def save(self, placement: Placement):
        self._placements[placement.id] = placement

    def find_by_id(self, id: str) -> Optional[Placement]:
        return self._placements.get(id)

# Use in tests
def test_with_fake():
    repo = InMemoryPlacementRepository()
    use_case = CreatePlacementUseCase(repository=repo)
    # ...
```

---

## Event Testing

### Testing Event Publishers

```python
def test_placement_created_event_published():
    mock_publisher = Mock(spec=EventPublisher)
    use_case = CreatePlacementUseCase(
        repository=InMemoryPlacementRepository(),
        event_publisher=mock_publisher,
    )

    use_case.execute(CreatePlacementRequest(...))

    mock_publisher.publish.assert_called_once()
    event = mock_publisher.publish.call_args[0][0]
    assert event.type == "placement.created"
```

### Testing Event Handlers

```python
def test_file_generator_handler():
    # Arrange
    mock_s3 = Mock(spec=S3Client)
    handler = FileGeneratorHandler(s3_client=mock_s3)

    event = {
        "Records": [{
            "body": json.dumps({
                "type": "placement.created",
                "data": {"placement_id": "abc123"}
            })
        }]
    }

    # Act
    handler.handle(event, None)

    # Assert
    mock_s3.put_object.assert_called_once()
```

### Testing Eventual Consistency

```python
@pytest.mark.integration
def test_placement_file_generated_eventually():
    # Create placement via API
    response = client.post("/v1/placements", json={...})
    placement_id = response.json()["data"]["id"]

    # Wait for file generation (eventual consistency)
    file_url = None
    for _ in range(10):  # Retry up to 10 times
        time.sleep(1)
        placement = client.get(f"/v1/placements/{placement_id}").json()
        if placement["data"].get("file_url"):
            file_url = placement["data"]["file_url"]
            break

    assert file_url is not None
```

---

## Coverage Requirements

| Layer          | Minimum | Target  |
| -------------- | ------- | ------- |
| Domain         | 90%     | 95%     |
| Application    | 80%     | 90%     |
| Infrastructure | 70%     | 80%     |
| Interface      | 60%     | 70%     |
| **Overall**    | **80%** | **85%** |

### Coverage Configuration

```toml
# pyproject.toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
]
```

---

## CI Integration

```yaml
# .github/workflows/ci.yml
test:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:15
      env:
        POSTGRES_DB: test
        POSTGRES_PASSWORD: test
      ports:
        - 5432:5432

  steps:
    - uses: actions/checkout@v4

    - name: Run unit tests
      run: pytest tests/unit -v --cov

    - name: Run integration tests
      run: pytest tests/integration -v

    - name: Run contract tests
      run: pytest tests/contract -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## Test Naming Conventions

```python
# Pattern: test_<action>_<condition>_<expected_result>

def test_create_placement_with_valid_data_returns_placement():
    pass

def test_create_placement_with_negative_time_raises_validation_error():
    pass

def test_get_placement_when_not_found_returns_404():
    pass
```

---

## Performance Testing

### Performance Testing Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱Chaos╲         Resilience under failure
                 ╱───────╲
                ╱  Stress  ╲      Breaking point, recovery
               ╱────────────╲
              ╱    Load      ╲    Expected production load
             ╱────────────────╲
            ╱   Spike / Soak   ╲  Sudden bursts, sustained load
           ╱────────────────────╲
          ╱    Baseline / Smoke  ╲  Single user, sanity check
         ╱════════════════════════╲
```

### Test Types

| Type         | Purpose                                   | When to Run        |
| ------------ | ----------------------------------------- | ------------------ |
| **Baseline** | Establish single-user response times      | Every PR           |
| **Load**     | Validate performance under expected load  | Nightly            |
| **Stress**   | Find breaking point and recovery behavior | Weekly             |
| **Spike**    | Test sudden traffic bursts                | Weekly             |
| **Soak**     | Detect memory leaks, resource exhaustion  | Weekly (4-8 hours) |
| **Chaos**    | Validate resilience under failure         | Monthly            |

### Performance Targets (SLOs)

| Metric          | Target       | Critical    |
| --------------- | ------------ | ----------- |
| API P50 latency | < 100ms      | < 200ms     |
| API P99 latency | < 500ms      | < 1s        |
| Throughput      | > 1000 req/s | > 500 req/s |
| Error rate      | < 0.1%       | < 1%        |
| Availability    | 99.9%        | 99%         |

### Tools

| Tool          | Best For                      | Language   | Pros                          | Cons                        |
| ------------- | ----------------------------- | ---------- | ----------------------------- | --------------------------- |
| **k6**        | Modern APIs, CI/CD            | JavaScript | Fast, scriptable, great DX    | No GUI                      |
| **JMeter**    | Complex scenarios, enterprise | Java/GUI   | Feature-rich, plugins, mature | Heavy, steep learning curve |
| **Gatling**   | High throughput, reports      | Scala/Java | Excellent reports, efficient  | Scala DSL learning curve    |
| **Locust**    | Python teams                  | Python     | Easy scripting, distributed   | Less performant than k6     |
| **Artillery** | Node.js teams                 | YAML/JS    | Simple config, good for APIs  | Limited advanced features   |
| **Vegeta**    | Quick HTTP load               | Go         | Simple CLI, fast              | Basic features only         |
| **wrk/wrk2**  | Raw HTTP benchmarks           | Lua        | Extremely fast                | Limited scripting           |
| **AWS FIS**   | Chaos engineering             | -          | Native AWS integration        | AWS only                    |

### Tool Selection Guide

```
                 What's your priority?
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
 ┌───────────┐    ┌───────────┐    ┌───────────┐
 │  CI/CD &  │    │  Complex  │    │ Beautiful │
 │ Developer │    │Enterprise │    │  Reports  │
 │Experience │    │ Scenarios │    │           │
 └─────┬─────┘    └─────┬─────┘    └─────┬─────┘
       │                │                │
       ▼                ▼                ▼
    ┌────┐          ┌────────┐       ┌─────────┐
    │ k6 │          │ JMeter │       │ Gatling │
    └────┘          └────────┘       └─────────┘
```

### Recommended Stack for Nedlia

| Use Case            | Primary Tool | Alternative  |
| ------------------- | ------------ | ------------ |
| API load testing    | k6           | Gatling      |
| Complex scenarios   | JMeter       | Gatling      |
| CI/CD integration   | k6           | Artillery    |
| Python team scripts | Locust       | k6           |
| Quick benchmarks    | wrk2         | Vegeta       |
| Chaos engineering   | AWS FIS      | Chaos Monkey |

### JMeter Example

For complex enterprise scenarios:

```bash
# Run JMeter headless
jmeter -n -t test-plan.jmx -l results.jtl -e -o report/

# With parameters
jmeter -n -t test-plan.jmx \
  -Jbase_url=https://api.staging.nedlia.com \
  -Jthreads=100 \
  -Jduration=300
```

### Gatling Example (Scala)

For high-throughput with detailed HTML reports:

```scala
// src/test/scala/PlacementSimulation.scala
class PlacementSimulation extends Simulation {
  val httpProtocol = http
    .baseUrl("http://localhost:8000")
    .acceptHeader("application/json")

  val scn = scenario("Placements")
    .exec(http("List").get("/v1/placements").check(status.is(200)))
    .pause(1)
    .exec(http("Create").post("/v1/placements")
      .body(StringBody("""{"video_id":"...","product_id":"..."}"""))
      .check(status.is(201)))

  setUp(
    scn.inject(rampUsers(50).during(2.minutes))
  ).assertions(global.responseTime.percentile(95).lt(500))
}
```

### Locust Example (Python)

For Python teams:

```python
# tools/performance-tests/locustfile.py
from locust import HttpUser, task, between

class PlacementUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_placements(self):
        self.client.get("/v1/placements?limit=20")

    @task(1)
    def create_placement(self):
        self.client.post("/v1/placements", json={
            "video_id": "550e8400-e29b-41d4-a716-446655440000",
            "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "time_range": {"start_time": 30.0, "end_time": 45.0},
        })
```

```bash
# Run with web UI
locust -f locustfile.py --host=http://localhost:8000

# Headless
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 5m
```

### k6 Load Test Example

```javascript
// tools/performance-tests/k6/load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const placementDuration = new Trend('placement_duration');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 }, // Ramp up
    { duration: '5m', target: 50 }, // Steady state
    { duration: '2m', target: 100 }, // Peak load
    { duration: '5m', target: 100 }, // Sustained peak
    { duration: '2m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    errors: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export default function () {
  // GET placements
  const listStart = Date.now();
  const listRes = http.get(`${BASE_URL}/v1/placements?limit=20`);
  placementDuration.add(Date.now() - listStart);

  check(listRes, {
    'list status is 200': r => r.status === 200,
    'list has data': r => JSON.parse(r.body).data !== undefined,
  });
  errorRate.add(listRes.status !== 200);

  sleep(1);

  // POST placement
  const createRes = http.post(
    `${BASE_URL}/v1/placements`,
    JSON.stringify({
      video_id: '550e8400-e29b-41d4-a716-446655440000',
      product_id: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
      time_range: { start_time: 30.0, end_time: 45.0 },
    }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(createRes, {
    'create status is 201': r => r.status === 201,
  });
  errorRate.add(createRes.status !== 201);

  sleep(1);
}

export function handleSummary(data) {
  return {
    'summary.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}
```

### Running Performance Tests

```bash
# Baseline (single VU)
k6 run --vus 1 --duration 30s tools/performance-tests/k6/load-test.js

# Load test
k6 run tools/performance-tests/k6/load-test.js

# Stress test (find breaking point)
k6 run --vus 200 --duration 10m tools/performance-tests/k6/load-test.js

# Spike test
k6 run --stage 1m:10,10s:200,1m:200,10s:10 tools/performance-tests/k6/load-test.js

# With environment
k6 run -e BASE_URL=https://api.staging.nedlia.com tools/performance-tests/k6/load-test.js
```

### Soak Test Configuration

```javascript
// tools/performance-tests/k6/soak-test.js
export const options = {
  stages: [
    { duration: '5m', target: 50 }, // Ramp up
    { duration: '4h', target: 50 }, // Sustained load
    { duration: '5m', target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    errors: ['rate<0.01'],
  },
};
```

### Chaos Engineering

Test system resilience under failure conditions:

```yaml
# AWS Fault Injection Simulator experiments
experiments:
  - name: Database failover
    action: Trigger Aurora failover
    duration: 5 minutes
    expected: Service continues with < 30s disruption

  - name: Lambda throttling
    action: Reduce Lambda concurrency to 10
    duration: 10 minutes
    expected: Graceful degradation, no errors

  - name: Network latency
    action: Add 500ms latency to database calls
    duration: 5 minutes
    expected: Requests complete within SLO

  - name: SQS unavailable
    action: Block SQS access
    duration: 5 minutes
    expected: Events queued locally, processed after recovery
```

### CI Integration

```yaml
# .github/workflows/performance.yml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *' # Nightly at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run k6 load test
        uses: grafana/k6-action@v0.3.1
        with:
          filename: tools/performance-tests/k6/load-test.js
        env:
          BASE_URL: ${{ secrets.STAGING_API_URL }}

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: k6-results
          path: summary.json

      - name: Check thresholds
        run: |
          if grep -q '"thresholds":.*"failed":true' summary.json; then
            echo "Performance thresholds failed!"
            exit 1
          fi
```

### Performance Monitoring Dashboard

Track performance trends over time:

| Metric               | Source     | Alert Threshold     |
| -------------------- | ---------- | ------------------- |
| P50 latency trend    | CloudWatch | +20% week-over-week |
| P99 latency trend    | CloudWatch | +50% week-over-week |
| Error rate trend     | CloudWatch | > 0.5%              |
| Throughput           | CloudWatch | -20% from baseline  |
| Lambda duration      | CloudWatch | > 10s average       |
| Database connections | RDS        | > 80% pool          |

### Performance Test Checklist

Before release:

- [ ] Baseline tests pass
- [ ] Load test at 2x expected traffic passes
- [ ] No memory leaks in soak test
- [ ] P99 latency within SLO
- [ ] Error rate < 0.1%
- [ ] Database query times < 100ms
- [ ] No N+1 queries detected
- [ ] Cache hit rate > 80%

---

## Event-Driven Performance Testing

For Nedlia's serverless, event-driven architecture, standard API load testing isn't enough. We need to measure **end-to-end flow latency** and **eventual consistency windows**.

### What to Measure

| Metric                 | Description                                           | Target      |
| ---------------------- | ----------------------------------------------------- | ----------- |
| **End-to-end latency** | Event produced → all consumers processed → consistent | P99 < 5s    |
| **Consistency window** | Time until read model reflects write                  | 95% < 2s    |
| **Queue backlog**      | SQS ApproximateNumberOfMessagesVisible                | < 100       |
| **Consumer lag**       | Time messages sit in queue                            | P99 < 1s    |
| **Cold start latency** | Lambda cold start under load                          | < 500ms     |
| **Scale-up time**      | Fargate task spin-up                                  | < 60s       |
| **Throughput ceiling** | Events/sec before degradation                         | > 500/s     |
| **Cost per 1K events** | Lambda + Fargate + DB cost                            | Track trend |

### End-to-End Flow Latency

Track latency across the entire event flow, not just per-service:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│   API   │───▶│  Event  │───▶│  Queue  │───▶│ Worker  │───▶│   DB    │
│ Gateway │    │ Bridge  │    │  (SQS)  │    │(Lambda) │    │(Aurora) │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │              │
   t=0ms         t=5ms         t=10ms        t=50ms         t=100ms
     │              │              │              │              │
     └──────────────┴──────────────┴──────────────┴──────────────┘
                    End-to-end latency = 100ms
```

### Correlation ID Strategy

Every event MUST carry a correlation ID for tracing:

```python
# Event structure with correlation
{
    "id": "evt_abc123",
    "correlation_id": "corr_xyz789",  # Trace across all services
    "test_run_id": "perf_test_001",   # Group by test run
    "timestamps": {
        "produced_at": "2024-01-15T10:00:00.000Z",
        "published_at": "2024-01-15T10:00:00.005Z",
        "consumed_at": "2024-01-15T10:00:00.050Z",
        "processed_at": "2024-01-15T10:00:00.100Z"
    },
    "data": { ... }
}
```

### Consistency Validation Test

Don't just fire events—verify the system reaches consistent state:

```python
# tools/performance-tests/consistency/consistency_test.py
import asyncio
import time
from uuid import uuid4

class ConsistencyTester:
    """Validates eventual consistency SLOs."""

    def __init__(self, api_client, db_client, slo_seconds: float = 5.0):
        self.api = api_client
        self.db = db_client
        self.slo = slo_seconds
        self.results = []

    async def test_placement_consistency(self, num_events: int = 100):
        """
        1. Create placement via API
        2. Poll read model until consistent
        3. Record consistency latency
        """
        tasks = [self._single_consistency_test() for _ in range(num_events)]
        self.results = await asyncio.gather(*tasks)
        return self._analyze_results()

    async def _single_consistency_test(self) -> dict:
        correlation_id = str(uuid4())
        start_time = time.time()

        # 1. Write via API
        response = await self.api.post("/v1/placements", json={
            "video_id": "test-video",
            "product_id": "test-product",
            "time_range": {"start_time": 0, "end_time": 10},
            "_correlation_id": correlation_id,
        })
        placement_id = response.json()["data"]["id"]
        write_time = time.time()

        # 2. Poll read model until consistent
        consistent = False
        poll_count = 0
        max_polls = int(self.slo * 10)  # Poll every 100ms

        while not consistent and poll_count < max_polls:
            await asyncio.sleep(0.1)
            poll_count += 1

            # Check if file_url is populated (set by async worker)
            placement = await self.api.get(f"/v1/placements/{placement_id}")
            if placement.json()["data"].get("file_url"):
                consistent = True

        end_time = time.time()

        return {
            "correlation_id": correlation_id,
            "placement_id": placement_id,
            "write_latency_ms": (write_time - start_time) * 1000,
            "consistency_latency_ms": (end_time - start_time) * 1000,
            "consistent": consistent,
            "within_slo": (end_time - start_time) <= self.slo,
            "poll_count": poll_count,
        }

    def _analyze_results(self) -> dict:
        latencies = [r["consistency_latency_ms"] for r in self.results if r["consistent"]]
        return {
            "total_events": len(self.results),
            "consistent_count": sum(1 for r in self.results if r["consistent"]),
            "within_slo_count": sum(1 for r in self.results if r["within_slo"]),
            "slo_percentage": sum(1 for r in self.results if r["within_slo"]) / len(self.results) * 100,
            "p50_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None,
            "p90_latency_ms": sorted(latencies)[int(len(latencies) * 0.9)] if latencies else None,
            "p99_latency_ms": sorted(latencies)[int(len(latencies) * 0.99)] if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
        }
```

### Event Producer for Load Testing

Custom producer for controlled event injection:

```python
# tools/performance-tests/producers/event_producer.py
import asyncio
import boto3
import json
import time
from dataclasses import dataclass
from uuid import uuid4

@dataclass
class ProducerConfig:
    events_per_second: int
    duration_seconds: int
    event_type: str
    ramp_up_seconds: int = 60

class EventProducer:
    """Produces events at controlled rate for load testing."""

    def __init__(self, config: ProducerConfig):
        self.config = config
        self.eventbridge = boto3.client('events')
        self.test_run_id = f"perf_{int(time.time())}"
        self.produced_events = []

    async def run(self):
        """Run the load test."""
        total_events = self.config.events_per_second * self.config.duration_seconds
        interval = 1.0 / self.config.events_per_second

        print(f"Starting load test: {self.config.events_per_second} events/sec for {self.config.duration_seconds}s")
        print(f"Test run ID: {self.test_run_id}")

        start_time = time.time()
        events_sent = 0

        while events_sent < total_events:
            # Ramp up logic
            elapsed = time.time() - start_time
            if elapsed < self.config.ramp_up_seconds:
                current_rate = self.config.events_per_second * (elapsed / self.config.ramp_up_seconds)
                interval = 1.0 / max(current_rate, 1)

            event = self._create_event()
            await self._publish_event(event)
            self.produced_events.append(event)
            events_sent += 1

            await asyncio.sleep(interval)

        return self._generate_report()

    def _create_event(self) -> dict:
        return {
            "id": str(uuid4()),
            "correlation_id": str(uuid4()),
            "test_run_id": self.test_run_id,
            "type": self.config.event_type,
            "produced_at": time.time(),
            "data": {
                "video_id": str(uuid4()),
                "product_id": str(uuid4()),
                "time_range": {"start_time": 0, "end_time": 30},
            }
        }

    async def _publish_event(self, event: dict):
        self.eventbridge.put_events(
            Entries=[{
                "Source": "nedlia.perf-test",
                "DetailType": event["type"],
                "Detail": json.dumps(event),
                "EventBusName": "nedlia-events",
            }]
        )

    def _generate_report(self) -> dict:
        return {
            "test_run_id": self.test_run_id,
            "total_events": len(self.produced_events),
            "target_rate": self.config.events_per_second,
            "duration_seconds": self.config.duration_seconds,
        }

# Usage
async def main():
    config = ProducerConfig(
        events_per_second=100,
        duration_seconds=300,
        event_type="placement.created",
        ramp_up_seconds=60,
    )
    producer = EventProducer(config)
    report = await producer.run()
    print(json.dumps(report, indent=2))
```

### AWS Metrics to Monitor During Tests

| Service     | Metric                               | What It Tells You              |
| ----------- | ------------------------------------ | ------------------------------ |
| **Lambda**  | `Duration`                           | Processing time per invocation |
| **Lambda**  | `ConcurrentExecutions`               | Scale-out behavior             |
| **Lambda**  | `Throttles`                          | Hitting concurrency limits     |
| **Lambda**  | `IteratorAge`                        | Consumer lag (stream-based)    |
| **Lambda**  | `ColdStarts` (custom)                | Cold start frequency           |
| **Fargate** | `CPUUtilization`                     | CPU pressure                   |
| **Fargate** | `MemoryUtilization`                  | Memory pressure                |
| **Fargate** | `RunningTaskCount`                   | Scale-out behavior             |
| **SQS**     | `ApproximateNumberOfMessagesVisible` | Queue backlog                  |
| **SQS**     | `ApproximateAgeOfOldestMessage`      | Consumer lag                   |
| **SQS**     | `NumberOfMessagesReceived`           | Throughput                     |
| **SQS**     | `NumberOfMessagesSent` (DLQ)         | Failed messages                |
| **Aurora**  | `DatabaseConnections`                | Connection pool pressure       |
| **Aurora**  | `ReadLatency` / `WriteLatency`       | DB performance                 |

### Cold Start & Scale-Up Testing

```python
# tools/performance-tests/chaos/cold_start_test.py
async def test_lambda_cold_starts():
    """
    Force cold starts by:
    1. Waiting for Lambda to scale down (5-15 min idle)
    2. Sending burst of concurrent requests
    3. Measuring first response times
    """
    # Wait for scale-down
    await asyncio.sleep(900)  # 15 minutes

    # Burst 50 concurrent requests
    start = time.time()
    tasks = [api.get("/v1/placements") for _ in range(50)]
    responses = await asyncio.gather(*tasks)
    end = time.time()

    latencies = [r.elapsed.total_seconds() * 1000 for r in responses]

    return {
        "cold_start_p50_ms": sorted(latencies)[25],
        "cold_start_p99_ms": sorted(latencies)[49],
        "cold_start_max_ms": max(latencies),
        "total_burst_time_ms": (end - start) * 1000,
    }

async def test_fargate_scale_up():
    """
    Test Fargate scaling by:
    1. Starting with minimum tasks (2)
    2. Ramping load until scale-out triggers
    3. Measuring time to new tasks running
    """
    # Record initial task count
    initial_tasks = await get_running_task_count()

    # Ramp load
    for rate in [50, 100, 200, 500]:
        await send_requests_at_rate(rate, duration=60)

        # Check if scaled
        current_tasks = await get_running_task_count()
        if current_tasks > initial_tasks:
            scale_time = time.time()
            break

    return {
        "initial_tasks": initial_tasks,
        "final_tasks": current_tasks,
        "scale_trigger_rate": rate,
        "scale_up_time_seconds": scale_time - start_time,
    }
```

### Backpressure & Failure Testing

```python
# tools/performance-tests/chaos/backpressure_test.py
async def test_slow_consumer():
    """
    Simulate slow downstream consumer:
    1. Inject artificial delay in worker
    2. Send events at normal rate
    3. Monitor queue buildup and recovery
    """
    # Enable slow mode (via feature flag or env var)
    await set_worker_delay_ms(500)

    # Send events
    await send_events(rate=100, duration=300)

    # Monitor queue
    metrics = await collect_queue_metrics(duration=600)

    return {
        "max_queue_depth": max(metrics["queue_depth"]),
        "queue_drain_time_seconds": metrics["drain_time"],
        "dlq_messages": metrics["dlq_count"],
    }

async def test_downstream_failure():
    """
    Test behavior when downstream service fails:
    1. Make DB unavailable
    2. Send events
    3. Verify retry behavior and DLQ usage
    """
    # Simulate DB failure
    await block_db_access()

    # Send events
    await send_events(rate=50, duration=60)

    # Wait for retries to exhaust
    await asyncio.sleep(300)

    # Check DLQ
    dlq_messages = await get_dlq_message_count()

    # Restore DB
    await restore_db_access()

    # Verify recovery
    await asyncio.sleep(60)
    final_dlq = await get_dlq_message_count()

    return {
        "events_sent": 3000,
        "dlq_messages": dlq_messages,
        "dlq_after_recovery": final_dlq,
        "retry_behavior": "verified" if dlq_messages > 0 else "failed",
    }
```

### Idempotency Testing Under Load

```python
# tools/performance-tests/chaos/idempotency_test.py
async def test_duplicate_event_handling():
    """
    Verify idempotency under load:
    1. Send same event multiple times
    2. Verify only one side effect
    """
    correlation_id = str(uuid4())
    event = create_placement_event(correlation_id=correlation_id)

    # Send same event 10 times (simulating SQS redelivery)
    for _ in range(10):
        await publish_event(event)

    # Wait for processing
    await asyncio.sleep(5)

    # Verify only one placement created
    placements = await db.query(
        "SELECT * FROM placements WHERE correlation_id = %s",
        correlation_id
    )

    return {
        "events_sent": 10,
        "placements_created": len(placements),
        "idempotent": len(placements) == 1,
    }
```

### Cost Estimation Under Load

```python
# tools/performance-tests/cost_estimator.py
def estimate_cost(metrics: dict) -> dict:
    """Estimate AWS cost based on load test metrics."""

    # Lambda pricing (us-east-1)
    lambda_price_per_ms = 0.0000166667 / 1000  # per GB-second
    lambda_memory_gb = 1  # 1GB configured

    lambda_cost = (
        metrics["lambda_invocations"] *
        metrics["avg_duration_ms"] *
        lambda_memory_gb *
        lambda_price_per_ms
    )

    # Fargate pricing
    fargate_vcpu_per_hour = 0.04048
    fargate_memory_per_gb_hour = 0.004445

    fargate_cost = (
        metrics["fargate_vcpu_hours"] * fargate_vcpu_per_hour +
        metrics["fargate_memory_gb_hours"] * fargate_memory_per_gb_hour
    )

    # Aurora pricing
    aurora_io_per_million = 0.20
    aurora_cost = metrics["aurora_io_requests"] / 1_000_000 * aurora_io_per_million

    total = lambda_cost + fargate_cost + aurora_cost

    return {
        "lambda_cost": f"${lambda_cost:.4f}",
        "fargate_cost": f"${fargate_cost:.4f}",
        "aurora_cost": f"${aurora_cost:.4f}",
        "total_cost": f"${total:.4f}",
        "cost_per_1k_events": f"${total / metrics['total_events'] * 1000:.4f}",
    }
```

### Performance Test Report Template

```markdown
# Performance Test Report

**Test Run ID**: perf_1705312800
**Date**: 2024-01-15
**Environment**: Staging
**Duration**: 30 minutes

## Summary

| Metric                     | Result       | Target  | Status |
| -------------------------- | ------------ | ------- | ------ |
| End-to-end P99 latency     | 1.2s         | < 5s    | ✅     |
| Consistency SLO (95% < 2s) | 97.3%        | > 95%   | ✅     |
| Max throughput             | 450 events/s | > 500/s | ⚠️     |
| Error rate                 | 0.02%        | < 0.1%  | ✅     |
| Cold start P99             | 380ms        | < 500ms | ✅     |

## Load Profile

- Ramp: 0 → 500 events/sec over 5 min
- Steady: 500 events/sec for 20 min
- Ramp down: 500 → 0 over 5 min

## Findings

### Bottleneck Identified

- Queue backlog started growing at 450 events/sec
- Root cause: Lambda concurrency limit (100)
- Recommendation: Increase reserved concurrency to 200

### Cold Starts

- 12 cold starts observed during ramp-up
- Average cold start: 320ms
- No cold starts during steady state

## Cost Projection

At 500 events/sec sustained:

- Lambda: $45/day
- Fargate: $28/day
- Aurora: $12/day
- **Total: $85/day (~$2,550/month)**
```

### Performance Test Checklist (Updated)

Before release:

- [ ] Baseline tests pass
- [ ] Load test at 2x expected traffic passes
- [ ] No memory leaks in soak test
- [ ] P99 latency within SLO
- [ ] Error rate < 0.1%
- [ ] Database query times < 100ms
- [ ] No N+1 queries detected
- [ ] Cache hit rate > 80%
- [ ] **End-to-end consistency SLO met (95% < 2s)**
- [ ] **Queue backlog stays bounded under load**
- [ ] **Cold start latency acceptable**
- [ ] **Fargate scale-up time < 60s**
- [ ] **No duplicate side effects (idempotency verified)**
- [ ] **DLQ behavior validated**
- [ ] **Cost projection reviewed**

---

## Related Documentation

- [Domain Model](domain-model.md) – What to test
- [API Standards](api-standards.md) – API testing patterns
- [Observability](observability.md) – Performance monitoring
- [Resilience Patterns](resilience-patterns.md) – Chaos engineering
