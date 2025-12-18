# Nedlia

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Stars](https://img.shields.io/github/stars/onelasha/Nedlia?style=social)](https://github.com/onelasha/Nedlia)

<!-- CI Badge - uncomment when workflows are running -->
<!-- [![CI](https://github.com/onelasha/Nedlia/actions/workflows/ci.yml/badge.svg)](https://github.com/onelasha/Nedlia/actions/workflows/ci.yml) -->

<!-- SonarCloud Badges - uncomment after SonarCloud project is created -->
<!-- [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=coverage)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Bugs](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=bugs)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Technical Debt](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=sqale_index)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->
<!-- [![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia) -->

**Product placement validation platform** for video content. Integrate, manage, and validate product placements across video editing platforms and streaming players.

> **Project Status**: 🚧 **Alpha** – Under active development. Not yet production-ready.

---

## Quick Start

```bash
# Clone
git clone https://github.com/onelasha/Nedlia.git
cd Nedlia

# Install dependencies
pnpm install
cd nedlia-back-end/api && uv sync && cd ../..

# Set up environment
cp .env.example .env

# Run linting
make lint
```

See [Getting Started](docs/getting-started.md) for detailed setup instructions.

---

## Development Commands

This monorepo uses [Nx](https://nx.dev) for build orchestration.

```bash
# Run specific project
nx serve portal                    # Start portal dev server
nx test api                        # Run API tests

# Run tasks across projects
nx run-many -t lint                # Lint all projects
nx run-many -t test                # Test all projects
nx run-many -t build               # Build all projects

# Run only affected (changed) projects
nx affected -t test                # Test affected projects
nx affected -t lint                # Lint affected projects

# Visualize project graph
nx graph

# See available targets for a project
nx show project portal
```

---

## Components

| Component     | Description                                                       |
| ------------- | ----------------------------------------------------------------- |
| **Plugin**    | Video editor plugins (Final Cut Pro, DaVinci Resolve, LumaFusion) |
| **SDK & API** | Streaming video player integration for placement validation       |
| **Portal**    | Web portal for marketing agencies and advertisers                 |

## Tech Stack

| Layer              | Technologies                                     |
| ------------------ | ------------------------------------------------ |
| **Backend**        | FastAPI (Python), PostgreSQL (Aurora Serverless) |
| **Frontend**       | React, TypeScript, Vite, TailwindCSS             |
| **Infrastructure** | AWS (Lambda, API Gateway, S3, SQS), Terraform    |
| **Plugins**        | Swift, SwiftUI (macOS/iOS)                       |
| **SDKs**           | JavaScript, Python, Swift                        |
| **Monorepo**       | Nx, pnpm workspaces                              |
| **Code Quality**   | ESLint (SOLID enforcement), Ruff, Prettier       |

---

## Documentation

### 🚀 Getting Started

- [Getting Started](docs/getting-started.md) – Prerequisites, installation, environment setup
- [Local Development](docs/local-development.md) – Running services locally

### 🏗️ Architecture

- [Architecture Overview](ARCHITECTURE.md) – Clean architecture, AWS serverless, event-driven
- [Frontend Architecture](docs/frontend-architecture.md) – React Clean Architecture, layers, folder structure
- [Domain Model](docs/domain-model.md) – Bounded contexts, aggregates, domain events
- [Data Architecture](docs/data-architecture.md) – Schema design, ACID principles, event registry
- [API Standards](docs/api-standards.md) – Versioning, errors, pagination, OpenAPI
- [Security Architecture](docs/security-architecture.md) – Auth flows, RBAC, secrets management
- [ADRs](docs/adr/) – Architecture Decision Records

### 📐 Design Principles

- [SOLID Principles](docs/SOLID-PRINCIPLES.md) – ESLint rules enforcing SOLID design
- [DRY Principles](docs/dry-principles.md) – Don't Repeat Yourself patterns

### 💻 Development Standards

- [Python Style Guide](docs/python-style-guide.md) – PEP 8, FastAPI patterns, type hints
- [TypeScript Style Guide](docs/typescript-style-guide.md) – React, ESLint, Prettier, strict mode
- [Code Quality](docs/code-quality.md) – SonarCloud, linting, formatting
- [Error Handling](docs/error-handling.md) – RFC 9457 Problem Details, exception hierarchy
- [Error Handling Strategy](docs/error-handling-strategy.md) – Project-specific strategies (RFC 9457, AWS Lambda, React Error Boundaries)
- [Logging Standards](docs/logging-standards.md) – Structured logging, log levels, PII handling
- [Dependency Injection](docs/dependency-injection.md) – DI patterns for Python and TypeScript

### 🗄️ Data & Infrastructure

- [Database Migrations](docs/database-migrations.md) – Alembic patterns, rollback procedures
- [Caching Strategy](docs/caching-strategy.md) – Redis patterns, cache invalidation, TTLs
- [Feature Flags](docs/feature-flags.md) – Gradual rollouts, kill switches

### ⚡ Performance & Reliability

- [Performance Guidelines](docs/performance-guidelines.md) – N+1 prevention, pagination, optimization
- [Rate Limiting](docs/rate-limiting.md) – IETF RateLimit headers, quota policies
- [Idempotency](docs/idempotency.md) – IETF Idempotency-Key header, safe retries
- [Resilience Patterns](docs/resilience-patterns.md) – Circuit breakers, retries, fallbacks
- [Observability](docs/observability.md) – Logging, metrics, tracing, alerting

### 🧪 Testing & Quality

- [Testing Strategy](docs/testing-strategy.md) – Testing pyramid, contract tests, coverage

### 🚢 Deployment & Operations

- [Deployment](docs/deployment.md) – CI/CD, environments, release process
- [Deployment Orchestration](docs/deployment-orchestration.md) – Multi-team deployment, change detection
- [Release Management](docs/release-management.md) – Release trains, sign-offs, production governance
- [Branching Strategy](docs/branching-strategy.md) – Trunk-based development
- [Incident Response](docs/incident-response.md) – On-call procedures, escalation, postmortems

### 🌐 Frontend

- [Accessibility](docs/accessibility.md) – WCAG 2.1 AA compliance, screen readers
- [Internationalization](docs/internationalization.md) – i18n patterns, locale formatting

### 🔒 Compliance

- [Data Retention & GDPR](docs/data-retention.md) – Data lifecycle, user rights, anonymization

### 🤝 Contributing

- [Contributing Guide](CONTRIBUTING.md) – Branch naming, PR workflow, conventional commits
- [Pull Request Guidelines](docs/pull-request-guidelines.md) – PR title, description, review

### 📋 Policies

- [Security Policy](SECURITY.md) – Vulnerability reporting
- [Code of Conduct](CODE_OF_CONDUCT.md) – Community standards
- [Changelog](CHANGELOG.md) – Release history

---

## Structure

```text
nedlia-back-end/
  api/                FastAPI REST API (Lambda)
  workers/            Event-driven workers (Lambda)
  services/           Domain microservices (Fargate)
    placement-service/
    validation-service/
    notification-service/
  shared/             Shared domain models

nedlia-front-end/
  portal/             Advertiser/Agency web portal

nedlia-sdk/
  javascript/         Video player SDK (web)
  python/             Server-side SDK
  swift/              iOS/macOS SDK

nedlia-plugin/
  finalcut/           Final Cut Pro plugin
  davinci/            DaVinci Resolve plugin
  lumafusion/         LumaFusion plugin

nedlia-IaC/           Terraform + Terragrunt infrastructure

tests/
  performance/        Performance & load testing
    k6/               k6 load test scripts
    consistency/      Eventual consistency tests
    chaos/            Chaos engineering tests
    producers/        Event producers for testing
```

---

## Roadmap

- [x] Monorepo structure with clean architecture
- [x] Developer best practices (linting, formatting, pre-commit hooks)
- [x] CI/CD pipeline (GitHub Actions)
- [x] Infrastructure as Code (Terraform + Terragrunt)
- [x] Nx monorepo with module boundary enforcement
- [x] SOLID principles enforcement via ESLint
- [ ] FastAPI backend implementation
- [ ] React portal implementation
- [ ] Video editor plugins (Final Cut Pro, DaVinci, LumaFusion)
- [ ] SDKs (JavaScript, Python, Swift)
- [ ] Production deployment

---

## License

This project is licensed under the [MIT License](LICENSE).
