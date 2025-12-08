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

### Python Backend (`nedlia-back-end/python`)

```text
src/nedlia_backend_py/
  domain/           # Entities, value objects, domain services
  application/      # Use cases, ports (interfaces), DTOs
  infrastructure/   # Repositories, external clients, ORM models
  interface/        # FastAPI/Flask routes, CLI commands
```

### NestJS Backend (`nedlia-back-end/nestjs`)

```text
src/
  core/
    domain/         # Entities, value objects
    application/    # Use cases, ports (TS interfaces)
  infrastructure/   # TypeORM/Prisma repos, external clients
  interface/        # Nest controllers, resolvers, guards
```

### React Frontend (`nedlia-front-end/web`)

```text
src/
  domain/           # Domain models, validation, pure logic
  application/      # Use cases, state orchestration, facades
  infrastructure/   # API clients, storage adapters
  ui/               # React components, hooks, pages
```

### SDKs (`nedlia-sdk/python`, `nedlia-sdk/js`)

```text
src/
  domain/           # Core types exposed to SDK users
  application/      # High-level client methods
  infrastructure/   # HTTP transport, auth, retries
```

### SwiftUI Plugin (`nedlia-plugin/ios`)

```text
Sources/
  Domain/           # Models, business rules
  Application/      # Use cases, view models
  Infrastructure/   # Networking, persistence
  UI/               # SwiftUI views
```

## Testing Strategy

- **Domain**: Unit tests, no mocks needed.
- **Application**: Unit tests with mocked ports.
- **Infrastructure**: Integration tests against real or containerized services.
- **Interface**: End-to-end or contract tests.

## Enforcement

- Code reviews must verify layer boundaries.
- Linters and import rules (e.g., eslint-plugin-boundaries, Python import-linter) can automate checks.
- CI will fail if forbidden imports are detected (once configured).
