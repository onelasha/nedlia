# Nedlia API

FastAPI REST API for the Nedlia product placement platform.

## Structure

```
src/
  domain/           # Business entities (Placement, Video, Campaign)
  application/      # Use cases and business logic
  infrastructure/   # Database, S3, external services
  interface/        # API routes and controllers
tests/              # Unit and integration tests
```

## Setup

```bash
cd nedlia-back-end/api
uv sync
uv run uvicorn src.main:app --reload
```

## API Endpoints

| Endpoint                     | Description                   |
| ---------------------------- | ----------------------------- |
| `POST /placements`           | Create product placement      |
| `GET /placements/{id}`       | Get placement details         |
| `POST /videos/{id}/validate` | Validate placements for video |
| `GET /campaigns`             | List advertiser campaigns     |

## Environment Variables

See `.env.example` for required configuration.
