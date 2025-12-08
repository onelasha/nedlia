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

---

## Documentation

### Guides

- [Getting Started](docs/getting-started.md) – Prerequisites, installation, environment setup
- [Local Development](docs/local-development.md) – Running services locally
- [Branching Strategy](docs/branching-strategy.md) – Trunk-based development, feature flags
- [Code Quality](docs/code-quality.md) – SonarCloud, linting, formatting
- [Testing Strategy](docs/testing-strategy.md) – Testing pyramid, contract tests, coverage
- [Deployment](docs/deployment.md) – CI/CD, environments, release process
- [Deployment Orchestration](docs/deployment-orchestration.md) – Multi-team deployment, change detection

### Architecture

- [Architecture Overview](ARCHITECTURE.md) – Clean architecture, AWS serverless, event-driven
- [Domain Model](docs/domain-model.md) – Bounded contexts, aggregates, domain events
- [API Standards](docs/api-standards.md) – Versioning, errors, pagination, OpenAPI
- [Data Architecture](docs/data-architecture.md) – Schema design, event registry, migrations
- [Security Architecture](docs/security-architecture.md) – Auth flows, RBAC, secrets management
- [Observability](docs/observability.md) – Logging, metrics, tracing, alerting
- [Resilience Patterns](docs/resilience-patterns.md) – Circuit breakers, retries, fallbacks
- [ADRs](docs/adr/) – Architecture Decision Records

### Contributing

- [Contributing Guide](CONTRIBUTING.md) – Branch naming, PR workflow, conventional commits
- [Pull Request Guidelines](docs/pull-request-guidelines.md) – PR title, description, review

### Policies

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
- [ ] FastAPI backend implementation
- [ ] React portal implementation
- [ ] Video editor plugins (Final Cut Pro, DaVinci, LumaFusion)
- [ ] SDKs (JavaScript, Python, Swift)
- [ ] Production deployment

---

## License

This project is licensed under the [MIT License](LICENSE).
