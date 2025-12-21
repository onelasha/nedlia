# Nedlia Architecture

This document describes the clean architecture principles and layer structure used across all Nedlia projects.

## Core Principles

1. **Dependency Rule**: Dependencies point inward. Outer layers depend on inner layers, never the reverse.
2. **Framework Independence**: Business logic does not depend on frameworks, databases, or UI.
3. **Testability**: Core logic can be tested without external systems.
4. **Flexibility**: Swap infrastructure (DB, API, UI) without changing business rules.

## Layer Diagram

```text
┌─────────────────────────────────────────────────────────┐
│                      Interface                          │
│         (Controllers, Views, CLI, GraphQL)              │
├─────────────────────────────────────────────────────────┤
│                    Infrastructure                       │
│      (Repositories, API Clients, DB, Messaging)         │
├─────────────────────────────────────────────────────────┤
│                     Application                         │
│          (Use Cases, Ports, DTOs, Services)             │
├─────────────────────────────────────────────────────────┤
│                       Domain                            │
│       (Entities, Value Objects, Domain Services)        │
└─────────────────────────────────────────────────────────┘
```

## Dependency Rules

| Layer          | Can Import          | Cannot Import          |
| -------------- | ------------------- | ---------------------- |
| Domain         | Nothing             | Application, Infra, UI |
| Application    | Domain              | Infrastructure, UI     |
| Infrastructure | Application, Domain | UI                     |
| Interface      | Application, Domain | (uses Infra via DI)    |

## Per-Stack Structure

### API Service (`nedlia-back-end/api`)

FastAPI REST API - handles synchronous requests from plugins, SDKs, and portal.

```text
src/
  domain/           # Placement, Video, Campaign entities
  application/      # Use cases, ports (interfaces), DTOs
  infrastructure/   # Repositories, S3 client, EventBridge publisher
  interface/        # FastAPI routes, middleware
```

### Workers (`nedlia-back-end/workers`)

Event-driven workers - consume messages from SQS queues.

```text
src/
  handlers/         # SQS message handlers (Lambda entry points)
  tasks/            # Business logic for async processing
```

**Worker Types**:
| Worker | Trigger | Purpose |
|--------|---------|--------|
| `file_generator` | `placement.created` | Generate placement data files |
| `validator` | `video.validation_requested` | Async placement validation |
| `notifier` | `placement.*`, `campaign.*` | Send notifications |
| `sync` | `plugin.sync_requested` | Sync plugin data to server |

### Shared Domain (`nedlia-back-end/shared`)

Shared domain models used by both API and Workers.

```text
src/
  domain/           # Placement, Video, Campaign, Product entities
  utils/            # Common utilities
```

### Portal (`nedlia-front-end/portal`)

React web application for advertisers and agencies.

```text
src/
  domain/           # Domain models, validation
  application/      # Use cases, state management
  infrastructure/   # API clients, storage
  ui/               # React components, pages
```

### SDKs (`nedlia-sdk/`)

| SDK           | Purpose                            |
| ------------- | ---------------------------------- |
| `javascript/` | Video player integration (web)     |
| `python/`     | Server-side API integration        |
| `swift/`      | iOS/macOS video player integration |

```text
src/
  domain/           # Core types exposed to SDK users
  application/      # High-level client methods
  infrastructure/   # HTTP transport, auth, retries
```

### Plugins (`nedlia-plugin/`)

Video editor plugins for adding product placements.

| Plugin        | Platform         |
| ------------- | ---------------- |
| `finalcut/`   | Final Cut Pro    |
| `davinci/`    | DaVinci Resolve  |
| `lumafusion/` | LumaFusion (iOS) |

```text
Sources/
  Domain/           # Placement models, validation
  Application/      # Use cases, view models
  Infrastructure/   # API client, local storage
  UI/               # SwiftUI/AppKit views
```

## AWS Serverless Architecture

Nedlia uses an **event-driven, serverless architecture** on AWS with **eventual consistency**.

### Infrastructure Stack

| Component     | AWS Service                          |
| ------------- | ------------------------------------ |
| Compute       | Lambda (Python, Node.js)             |
| API           | API Gateway (REST)                   |
| Database      | Aurora Serverless v2 (PostgreSQL)    |
| Messaging     | EventBridge + SQS                    |
| Cache         | ElastiCache (Redis)                  |
| Auth          | Cognito                              |
| Storage       | S3                                   |
| Secrets       | Secrets Manager, SSM Parameter Store |
| Observability | CloudWatch Logs, X-Ray               |

### Event-Driven Design

```text
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   API GW     │────▶│   Lambda     │────▶│ EventBridge  │
│  (Commands)  │     │  (Handler)   │     │   (Events)   │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                     ┌───────────────────────────┼───────────────────────────┐
                     ▼                           ▼                           ▼
              ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
              │     SQS      │           │     SQS      │           │     SQS      │
              │  (Queue A)   │           │  (Queue B)   │           │  (Queue C)   │
              └──────┬───────┘           └──────┬───────┘           └──────┬───────┘
                     ▼                           ▼                           ▼
              ┌──────────────┐           ┌──────────────┐           ┌──────────────┐
              │   Lambda     │           │   Lambda     │           │   Lambda     │
              │ (Consumer A) │           │ (Consumer B) │           │ (Consumer C) │
              └──────────────┘           └──────────────┘           └──────────────┘
```

### Key Patterns

- **CQRS**: Separate command (write) and query (read) paths
- **Eventual Consistency**: Events propagate asynchronously; reads may lag writes
- **Idempotency**: All handlers must be idempotent (use idempotency keys)
- **Dead Letter Queues**: Failed events go to DLQ for retry/inspection
- **Event Schemas**: Use CloudEvents format for interoperability

### Event Flow Example: Create Placement

1. **Command**: Plugin calls `POST /placements` → API Gateway → Lambda
2. **Persist**: API Lambda writes placement to Aurora
3. **Publish**: API Lambda emits `placement.created` to EventBridge
4. **Subscribe**: SQS queues receive event:
   - `file-generation-queue` → File Generator Worker
   - `notification-queue` → Notifier Worker
5. **Process**: Workers generate files, send notifications

### Event Flow Example: Validate Video

1. **Command**: SDK calls `POST /videos/{id}/validate` → API Gateway → Lambda
2. **Publish**: API Lambda emits `video.validation_requested` to EventBridge
3. **Response**: API returns `202 Accepted` with validation ID (async)
4. **Process**: Validator Worker processes placements, checks timing
5. **Complete**: Worker emits `video.validation_completed`
6. **Query**: SDK polls `GET /validations/{id}` for result (eventual consistency)

---

## Infrastructure as Code

### Tooling

- **Terraform**: Infrastructure definitions
- **Terragrunt**: DRY configuration, environment management

### Environments

| Environment  | Purpose                      |
| ------------ | ---------------------------- |
| `dev`        | Local/individual development |
| `testing`    | Automated test runs, CI      |
| `staging`    | Pre-production validation    |
| `production` | Live system                  |

### IaC Structure (`nedlia-IaC/`)

```text
nedlia-IaC/
  terragrunt.hcl              # Root Terragrunt config
  environments/
    dev/
      terragrunt.hcl
      env.hcl
    testing/
      terragrunt.hcl
      env.hcl
    staging/
      terragrunt.hcl
      env.hcl
    production/
      terragrunt.hcl
      env.hcl
  modules/
    vpc/
    aurora/
    lambda/
    api-gateway/
    eventbridge/
    sqs/
    cognito/
    s3/
```

### Deployment Flow

```text
terragrunt run-all plan   # Preview changes across all modules
terragrunt run-all apply  # Apply changes
```

---

## Testing Strategy

- **Domain**: Unit tests, no mocks needed.
- **Application**: Unit tests with mocked ports.
- **Infrastructure**: Integration tests against real or containerized services.
- **Interface**: End-to-end or contract tests.

## Enforcement

### Nx Monorepo

This project uses **Nx** for monorepo management with enforced module boundaries.

```bash
# Run lint across all projects
pnpm nx run-many -t lint

# Lint affected projects only
pnpm nx affected -t lint

# View project graph
pnpm nx graph
```

### ESLint Module Boundaries

The `@nx/enforce-module-boundaries` rule enforces dependency constraints via project tags:

**Scope Tags** (which layers can depend on which):

- `scope:shared` → Can only depend on `scope:shared`
- `scope:backend` → Can depend on `scope:shared`, `scope:backend`
- `scope:frontend` → Can depend on `scope:shared`, `scope:frontend`

**Type Tags** (architectural layer constraints):

- `type:feature` → Can use `type:feature`, `type:ui`, `type:data-access`, `type:util`
- `type:ui` → Can use `type:ui`, `type:util`
- `type:data-access` → Can use `type:data-access`, `type:util`
- `type:util` → Can only use `type:util`

Add tags to each project's `project.json`:

```json
{
  "name": "my-project",
  "tags": ["scope:frontend", "type:feature"]
}
```

### SOLID Principles

ESLint rules enforce SOLID principles. See [SOLID Principles](docs/SOLID-PRINCIPLES.md) for details.

### Automated Checks

- **ESLint**: `@nx/enforce-module-boundaries`, `import/no-cycle`, `eslint-plugin-boundaries` (see `tools/js/eslint.config.js`)
- **Python**: `ruff` with import rules (see `pyproject.toml`)
- **CI**: Lint checks run on every PR and will fail on violations

### Tooling Configuration

Language-specific tooling is organized under `tools/`:

```text
tools/
  js/                    # JavaScript/TypeScript tooling
    eslint.config.js     # ESLint with SOLID enforcement
    prettier.config.js   # Code formatting
    tsconfig.base.json   # Base TypeScript config
    commitlint.config.js # Commit message validation
    .nvmrc               # Node.js version
  python/                # Python tooling
    ruff.toml            # Shared Ruff linting/formatting config
    mypy.ini             # Shared MyPy type checking config
    .python-version      # Python version
```

Each Python project extends the shared config via `[tool.ruff] extend = "../../tools/python/ruff.toml"`.
