# Placement Service

Domain-driven microservice for managing product placements.

## Responsibilities

- CRUD operations for placements
- Placement file generation
- Placement overlap detection
- Time range validation

## API Endpoints

| Method | Endpoint                  | Description                  |
| ------ | ------------------------- | ---------------------------- |
| GET    | `/placements`             | List placements (paginated)  |
| POST   | `/placements`             | Create placement             |
| GET    | `/placements/{id}`        | Get placement by ID          |
| PUT    | `/placements/{id}`        | Update placement             |
| DELETE | `/placements/{id}`        | Delete placement             |
| GET    | `/placements/{id}/file`   | Get generated placement file |
| POST   | `/videos/{id}/placements` | List placements for video    |

## Domain Model

```python
# Aggregate Root
class Placement:
    id: PlacementId
    video_id: VideoId
    product_id: ProductId
    time_range: TimeRange
    position: Optional[PlacementPosition]
    status: PlacementStatus
    file_url: Optional[str]

# Value Objects
class TimeRange:
    start_time: float  # seconds
    end_time: float

class PlacementPosition:
    x: float  # 0.0-1.0
    y: float
    width: float
    height: float
```

## Events Published

| Event                      | Trigger                  |
| -------------------------- | ------------------------ |
| `placement.created`        | New placement created    |
| `placement.updated`        | Placement modified       |
| `placement.deleted`        | Placement removed        |
| `placement.file_generated` | File generation complete |

## Events Consumed

| Event                  | Action                            |
| ---------------------- | --------------------------------- |
| `video.registered`     | Index video for placement queries |
| `campaign.deactivated` | Pause related placements          |

## Configuration

```bash
# Environment variables
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
S3_BUCKET=nedlia-placements
EVENTBRIDGE_BUS=nedlia-events
```

## Local Development

```bash
cd nedlia-back-end/services/placement-service

# Install dependencies
uv sync

# Run locally
uv run uvicorn src.main:app --reload --port 8001

# Run tests
uv run pytest

# Build Docker image
docker build -t placement-service .
```

## Structure

```
src/
  domain/           # Placement, TimeRange, PlacementPosition
  application/      # Use cases, DTOs, ports
  infrastructure/   # PostgreSQL repo, S3 client, EventBridge
  interface/        # FastAPI routes, health checks
  main.py           # Application entry point
tests/
  unit/
  integration/
Dockerfile
pyproject.toml
```
