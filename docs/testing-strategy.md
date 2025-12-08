# Testing Strategy

Comprehensive testing strategy for Nedlia, covering all layers and integration patterns.

## Testing Pyramid

```
                    ┌───────────┐
                    │    E2E    │  Few, slow, high confidence
                    │   Tests   │  (5%)
                    ├───────────┤
                    │ Contract  │  API contracts between services
                    │   Tests   │  (10%)
                    ├───────────┤
                    │Integration│  Real dependencies, boundaries
                    │   Tests   │  (20%)
                    ├───────────┤
                    │   Unit    │  Fast, isolated, focused
                    │   Tests   │  (65%)
                    └───────────┘
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

## Related Documentation

- [Domain Model](domain-model.md) – What to test
- [API Standards](api-standards.md) – API testing patterns
- [Observability](observability.md) – Test observability
