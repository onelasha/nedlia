# Dependency Injection Patterns

Dependency Injection (DI) patterns for Nedlia's Python backend (FastAPI) and TypeScript frontend (React).

## Principles

1. **Inversion of Control**: High-level modules don't depend on low-level modules; both depend on abstractions
2. **Testability**: Dependencies can be easily mocked for testing
3. **Flexibility**: Swap implementations without changing business logic
4. **Single Responsibility**: Each component has one reason to change

---

## Python (FastAPI)

FastAPI has built-in dependency injection via the `Depends` function.

### Basic Pattern

```python
# src/placements/dependencies.py
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.placements.repository import PlacementRepository
from src.placements.service import PlacementService


async def get_db_session(request: Request) -> AsyncSession:
    """Get database session from app state (initialized in lifespan)."""
    async with request.app.state.async_session() as session:
        yield session


async def get_placement_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PlacementRepository:
    """Get placement repository with injected session."""
    return PlacementRepository(session)


async def get_placement_service(
    repository: Annotated[PlacementRepository, Depends(get_placement_repository)],
) -> PlacementService:
    """Get placement service with injected repository."""
    return PlacementService(repository)


# Type alias for cleaner route signatures
PlacementServiceDep = Annotated[PlacementService, Depends(get_placement_service)]
```

### Using in Routes

```python
# src/placements/router.py
from fastapi import APIRouter
from src.placements.dependencies import PlacementServiceDep

router = APIRouter(prefix="/placements", tags=["Placements"])


@router.post("", status_code=201)
async def create_placement(
    request: PlacementCreate,
    service: PlacementServiceDep,  # Injected automatically
) -> PlacementResponse:
    return await service.create(request)


@router.get("/{placement_id}")
async def get_placement(
    placement_id: UUID,
    service: PlacementServiceDep,
) -> PlacementResponse:
    return await service.get(placement_id)
```

### Dependency Chain

```
Route Handler
    └── PlacementService (Depends)
            └── PlacementRepository (Depends)
                    └── AsyncSession (Depends)
                            └── Request.app.state (lifespan)
```

### Abstract Interfaces (Ports)

Define abstract interfaces for infrastructure dependencies:

```python
# src/domain/ports.py
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.placement import Placement


class PlacementRepositoryPort(ABC):
    """Abstract repository interface (port)."""

    @abstractmethod
    async def save(self, placement: Placement) -> Placement:
        """Save a placement."""
        ...

    @abstractmethod
    async def find_by_id(self, placement_id: UUID) -> Placement | None:
        """Find placement by ID."""
        ...

    @abstractmethod
    async def find_by_video(self, video_id: UUID) -> list[Placement]:
        """Find placements by video ID."""
        ...


class EventPublisherPort(ABC):
    """Abstract event publisher interface."""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event."""
        ...
```

### Concrete Implementations (Adapters)

```python
# src/infrastructure/repositories/placement.py
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.ports import PlacementRepositoryPort
from src.domain.placement import Placement


class PostgresPlacementRepository(PlacementRepositoryPort):
    """PostgreSQL implementation of placement repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, placement: Placement) -> Placement:
        model = PlacementModel.from_entity(placement)
        self.session.add(model)
        await self.session.flush()
        return model.to_entity()

    async def find_by_id(self, placement_id: UUID) -> Placement | None:
        result = await self.session.get(PlacementModel, placement_id)
        return result.to_entity() if result else None
```

### Wiring Dependencies

```python
# src/core/dependencies.py
from typing import Annotated

from fastapi import Depends, Request

from src.domain.ports import PlacementRepositoryPort, EventPublisherPort
from src.infrastructure.repositories.placement import PostgresPlacementRepository
from src.infrastructure.events.eventbridge import EventBridgePublisher


async def get_placement_repository(
    request: Request,
) -> PlacementRepositoryPort:
    """Get placement repository implementation."""
    session = await get_db_session(request)
    return PostgresPlacementRepository(session)


async def get_event_publisher(
    request: Request,
) -> EventPublisherPort:
    """Get event publisher implementation."""
    return EventBridgePublisher(request.app.state.eventbridge_client)


# Type aliases
PlacementRepo = Annotated[PlacementRepositoryPort, Depends(get_placement_repository)]
EventPublisher = Annotated[EventPublisherPort, Depends(get_event_publisher)]
```

### Service with Multiple Dependencies

```python
# src/application/placement_service.py
from src.domain.ports import PlacementRepositoryPort, EventPublisherPort
from src.domain.events import PlacementCreated


class PlacementService:
    """Application service for placement operations."""

    def __init__(
        self,
        repository: PlacementRepositoryPort,
        event_publisher: EventPublisherPort,
    ) -> None:
        self.repository = repository
        self.event_publisher = event_publisher

    async def create(self, data: PlacementCreate) -> Placement:
        placement = Placement(**data.model_dump())
        saved = await self.repository.save(placement)
        await self.event_publisher.publish(PlacementCreated(placement_id=saved.id))
        return saved
```

```python
# src/placements/dependencies.py
async def get_placement_service(
    repository: PlacementRepo,
    event_publisher: EventPublisher,
) -> PlacementService:
    return PlacementService(repository, event_publisher)
```

### Testing with Mocks

```python
# tests/unit/test_placement_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.placement_service import PlacementService
from src.domain.placement import Placement


@pytest.fixture
def mock_repository() -> AsyncMock:
    repo = AsyncMock()
    repo.save.return_value = Placement(
        id=uuid4(),
        video_id=uuid4(),
        product_id=uuid4(),
        time_range=TimeRange(0, 10),
    )
    return repo


@pytest.fixture
def mock_event_publisher() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def service(mock_repository, mock_event_publisher) -> PlacementService:
    return PlacementService(mock_repository, mock_event_publisher)


async def test_create_publishes_event(
    service: PlacementService,
    mock_event_publisher: AsyncMock,
) -> None:
    data = PlacementCreate(video_id=uuid4(), product_id=uuid4(), start_time=0, end_time=10)

    await service.create(data)

    mock_event_publisher.publish.assert_called_once()
```

### Override Dependencies in Tests

```python
# tests/integration/conftest.py
from fastapi.testclient import TestClient

from src.main import app
from src.core.dependencies import get_db_session


@pytest.fixture
def test_client(test_db_session):
    """Create test client with overridden dependencies."""

    async def override_get_db_session():
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
```

---

## TypeScript (React)

React uses Context API for dependency injection.

### Context Pattern

```typescript
// src/contexts/ServicesContext.tsx
import { createContext, useContext, ReactNode } from 'react';
import { PlacementService } from '../services/PlacementService';
import { ApiClient } from '../infrastructure/ApiClient';

interface Services {
  placementService: PlacementService;
  apiClient: ApiClient;
}

const ServicesContext = createContext<Services | null>(null);

interface ServicesProviderProps {
  children: ReactNode;
  services?: Partial<Services>;
}

export function ServicesProvider({ children, services }: ServicesProviderProps) {
  const apiClient = services?.apiClient ?? new ApiClient();

  const defaultServices: Services = {
    apiClient,
    placementService: services?.placementService ?? new PlacementService(apiClient),
  };

  return <ServicesContext.Provider value={defaultServices}>{children}</ServicesContext.Provider>;
}

export function useServices(): Services {
  const context = useContext(ServicesContext);
  if (!context) {
    throw new Error('useServices must be used within ServicesProvider');
  }
  return context;
}

export function usePlacementService(): PlacementService {
  return useServices().placementService;
}
```

### Service Implementation

```typescript
// src/services/PlacementService.ts
import { ApiClient } from '../infrastructure/ApiClient';
import { Placement, PlacementCreate } from '../types/placement';

export class PlacementService {
  constructor(private apiClient: ApiClient) {}

  async create(data: PlacementCreate): Promise<Placement> {
    return this.apiClient.post<Placement>('/placements', data);
  }

  async getById(id: string): Promise<Placement> {
    return this.apiClient.get<Placement>(`/placements/${id}`);
  }

  async listByVideo(videoId: string): Promise<Placement[]> {
    return this.apiClient.get<Placement[]>(`/videos/${videoId}/placements`);
  }
}
```

### Using in Components

```typescript
// src/components/PlacementList.tsx
import { usePlacementService } from '../contexts/ServicesContext';
import { useQuery } from '@tanstack/react-query';

interface PlacementListProps {
  videoId: string;
}

export function PlacementList({ videoId }: PlacementListProps) {
  const placementService = usePlacementService();

  const { data: placements, isLoading } = useQuery({
    queryKey: ['placements', videoId],
    queryFn: () => placementService.listByVideo(videoId),
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <ul>
      {placements?.map(p => (
        <li key={p.id}>{p.description}</li>
      ))}
    </ul>
  );
}
```

### App Setup

```typescript
// src/App.tsx
import { ServicesProvider } from './contexts/ServicesContext';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ServicesProvider>
        <Router />
      </ServicesProvider>
    </QueryClientProvider>
  );
}
```

### Testing with Mock Services

```typescript
// src/components/__tests__/PlacementList.test.tsx
import { render, screen } from '@testing-library/react';
import { ServicesProvider } from '../../contexts/ServicesContext';
import { PlacementList } from '../PlacementList';

const mockPlacementService = {
  listByVideo: jest.fn().mockResolvedValue([{ id: '1', description: 'Test placement' }]),
};

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ServicesProvider services={{ placementService: mockPlacementService as any }}>
        {ui}
      </ServicesProvider>
    </QueryClientProvider>
  );
}

test('renders placements', async () => {
  renderWithProviders(<PlacementList videoId="video-1" />);

  expect(await screen.findByText('Test placement')).toBeInTheDocument();
  expect(mockPlacementService.listByVideo).toHaveBeenCalledWith('video-1');
});
```

---

## Lambda Workers

For Lambda functions, use simple constructor injection:

```python
# src/handlers/file_generator.py
from src.tasks.file_generation import FileGenerationTask
from src.infrastructure.s3 import S3Client
from src.infrastructure.repositories.placement import PostgresPlacementRepository


def create_handler():
    """Factory function to create handler with dependencies."""
    s3_client = S3Client()
    db_session = create_session()
    repository = PostgresPlacementRepository(db_session)
    task = FileGenerationTask(repository, s3_client)

    async def handler(event, context):
        for record in event["Records"]:
            await task.process(record)

    return handler


# Export handler
handler = create_handler()
```

---

## Related Documentation

- [Architecture](../ARCHITECTURE.md) – Clean architecture layers
- [Python Style Guide](python-style-guide.md) – FastAPI patterns
- [Testing Strategy](testing-strategy.md) – Mocking dependencies
- [SOLID Principles](SOLID-PRINCIPLES.md) – Dependency Inversion Principle
