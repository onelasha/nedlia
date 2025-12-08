# Nedlia Backend

Backend services for the Nedlia product placement platform.

## Components

| Component  | Technology      | Purpose                                 |
| ---------- | --------------- | --------------------------------------- |
| `api/`     | FastAPI         | REST API (sync requests)                |
| `workers/` | Python + Lambda | Event-driven workers (async processing) |
| `shared/`  | Python          | Shared domain models                    |

## Event-Driven Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Plugin    │────▶│     API     │────▶│   Aurora    │
│   (Swift)   │     │  (FastAPI)  │     │ (PostgreSQL)│
└─────────────┘     └─────────────┘     └─────────────┘
                          │
┌─────────────┐           │ publish        ┌─────────────┐
│   Portal    │───────────┤───────────────▶│ EventBridge │
│   (React)   │           │                └──────┬──────┘
└─────────────┘           │                       │
                          │              ┌────────┼────────┐
┌─────────────┐           │              ▼        ▼        ▼
│  Video SDK  │───────────┘         ┌────────┐ ┌────────┐ ┌────────┐
│   (JS)      │                     │  SQS   │ │  SQS   │ │  SQS   │
└─────────────┘                     │ Queue  │ │ Queue  │ │ Queue  │
                                    └───┬────┘ └───┬────┘ └───┬────┘
                                        ▼          ▼          ▼
                                    ┌────────┐ ┌────────┐ ┌────────┐
                                    │ File   │ │Validate│ │Notify  │
                                    │ Gen    │ │ Worker │ │ Worker │
                                    └────────┘ └────────┘ └────────┘
```

## Event Flow

### Synchronous (API)

1. Client sends request → API Gateway → Lambda (API)
2. API validates, persists to Aurora
3. API publishes event to EventBridge
4. API returns response immediately

### Asynchronous (Workers)

1. EventBridge routes event to SQS queue
2. SQS triggers Lambda (Worker)
3. Worker processes event (file generation, validation, etc.)
4. Worker may publish new events (eventual consistency)

## Key Events

| Event                        | Publisher | Consumers                |
| ---------------------------- | --------- | ------------------------ |
| `placement.created`          | API       | File Generator, Notifier |
| `placement.updated`          | API       | File Generator, Notifier |
| `video.validation_requested` | API       | Validator                |
| `video.validation_completed` | Validator | Notifier                 |
| `campaign.created`           | API       | Notifier                 |

## Eventual Consistency

- **Writes**: Synchronous to Aurora via API
- **Reads**: May lag behind writes (query read models)
- **Validation**: Async - returns `202 Accepted`, poll for result
- **File Generation**: Async - files available after processing

## Setup (Local Development)

```bash
# API
cd api && uv sync && uv run uvicorn src.main:app --reload

# Workers (local simulation)
cd workers && uv sync && uv run python -m src.main
```

## Clean Architecture

Each component follows clean architecture:

- **Domain**: Business entities (Placement, Video, Campaign)
- **Application**: Use cases and orchestration
- **Infrastructure**: Aurora, S3, EventBridge, SQS
- **Interface**: API routes, Lambda handlers
