# Nedlia Backend

Backend services for the Nedlia product placement platform.

## Components

| Component   | Technology | Compute | Purpose                                 |
| ----------- | ---------- | ------- | --------------------------------------- |
| `api/`      | FastAPI    | Lambda  | REST API gateway (sync requests)        |
| `workers/`  | Python     | Lambda  | Event-driven workers (async processing) |
| `services/` | FastAPI    | Fargate | Domain microservices (long-running)     |
| `shared/`   | Python     | -       | Shared domain models                    |

## Hybrid Compute Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────┐│
│  │   Plugin    │────▶│  API GW +   │────▶│         ECS Cluster             ││
│  │   (Swift)   │     │   Lambda    │     │  ┌───────────┐ ┌───────────┐    ││
│  └─────────────┘     │   (API)     │     │  │ Placement │ │Validation │    ││
│                      └──────┬──────┘     │  │  Service  │ │  Service  │    ││
│  ┌─────────────┐            │            │  │ (Fargate) │ │ (Fargate) │    ││
│  │   Portal    │────────────┤            │  └─────┬─────┘ └─────┬─────┘    ││
│  │   (React)   │            │            └────────┼─────────────┼──────────┘│
│  └─────────────┘            │                     │             │           │
│                             │ publish             ▼             ▼           │
│  ┌─────────────┐            │            ┌─────────────────────────────────┐│
│  │  Video SDK  │────────────┘            │           Aurora DB             ││
│  │   (JS)      │                         └─────────────────────────────────┘│
│  └─────────────┘                                                            │
│                                                                             │
│                      ┌─────────────┐     ┌─────────────┐     ┌─────────────┐│
│                      │ EventBridge │────▶│     SQS     │────▶│   Lambda    ││
│                      │   (Events)  │     │  (Queues)   │     │  (Workers)  ││
│                      └─────────────┘     └─────────────┘     └─────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## When to Use Lambda vs Fargate

| Criteria       | Lambda               | Fargate            |
| -------------- | -------------------- | ------------------ |
| Execution time | < 15 min             | Long-running       |
| Traffic        | Sporadic             | Steady             |
| Connections    | Stateless            | Connection pooling |
| Cold starts    | Acceptable           | Not acceptable     |
| Use case       | API Gateway, Workers | Domain services    |

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

## Python Package Management (uv)

This project uses **[uv](https://docs.astral.sh/uv/)** for Python dependency management. Poetry is explicitly blocked.

| Aspect          | uv                    | Poetry                      |
| --------------- | --------------------- | --------------------------- |
| Install speed   | 10-100x faster (Rust) | Slow resolver               |
| Lock file       | `uv.lock` (standard)  | `poetry.lock` (proprietary) |
| Python versions | Built-in management   | Requires pyenv              |
| PEP compliance  | Full (517/518/621)    | Partial                     |
| Monorepo        | Native workspaces     | Limited                     |

### Quick Reference

```bash
uv sync --extra dev  # Install all dependencies including dev tools (linter, tests)
uv add <package>     # Add a dependency
uv run ruff check    # Run linter
uv run pytest        # Run tests
uv lock              # Update lock file
```

> ⚠️ **Poetry is blocked** via pre-commit hooks and CI. See root `.pre-commit-config.yaml`.

## Setup (Local Development)

For development, ALWAYS use `--extra dev` to ensure linting and testing tools are installed.

````bash
# API (Lambda)
cd api && uv sync --extra dev && uv run uvicorn src.main:app --reload --port 8000

# Workers (Lambda - local simulation)
cd workers && uv sync --extra dev && uv run python -m src.main

# Microservices (Fargate - via Docker)
cd services && docker-compose up

# Or run individual service
cd services/placement-service && uv sync --extra dev && uv run uvicorn src.main:app --reload --port 8001

## Initial Project Setup (All Backend Services)

For a fresh install or to ensure all backend tools are ready:

```bash
pnpm install:python

## Docker Compose (Local Services)

```bash
# Start all services with dependencies
docker-compose -f services/docker-compose.yml up

# Rebuild after changes
docker-compose -f services/docker-compose.yml up --build
````

## Clean Architecture

Each component follows clean architecture:

- **Domain**: Business entities (Placement, Video, Campaign)
- **Application**: Use cases and orchestration
- **Infrastructure**: Aurora, S3, EventBridge, SQS
- **Interface**: API routes, Lambda handlers, gRPC (services)

## Related Documentation

- [ADR-007: Fargate Microservices](../docs/adr/007-fargate-microservices.md) – Lambda vs Fargate decisions
- [Services README](services/README.md) – Microservices documentation
