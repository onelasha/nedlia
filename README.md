# Nedlia

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub](https://img.shields.io/github/stars/onelasha/Nedlia?style=social)](https://github.com/onelasha/Nedlia)

<!-- Uncomment when CI/SonarCloud is set up:
[![Build](https://github.com/onelasha/Nedlia/actions/workflows/ci.yml/badge.svg)](https://github.com/onelasha/Nedlia/actions)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=onelasha_Nedlia&metric=coverage)](https://sonarcloud.io/summary/new_code?id=onelasha_Nedlia)
-->

**AI-powered code review platform** that helps teams ship better code faster through automated PR analysis, intelligent suggestions, and seamless integrations.

> **Project Status**: 🚧 **Alpha** – Under active development. Not yet production-ready.

---

## Quick Start

```bash
# Clone
git clone https://github.com/onelasha/Nedlia.git
cd Nedlia

# Install dependencies
pnpm install
cd nedlia-back-end/python && uv sync && cd ../..

# Set up environment
cp .env.example .env

# Run linting
make lint
```

See [Getting Started](docs/getting-started.md) for detailed setup instructions.

---

## Tech Stack

| Layer              | Technologies                               |
| ------------------ | ------------------------------------------ |
| **Backend**        | Python, NestJS, PostgreSQL                 |
| **Frontend**       | React, TypeScript, Vite                    |
| **Infrastructure** | Terraform / Pulumi, Docker, GitHub Actions |
| **Plugins**        | SwiftUI (macOS/iOS)                        |
| **SDKs**           | Python, TypeScript, Swift                  |

---

## Documentation

### Guides

- [Getting Started](docs/getting-started.md) – Prerequisites, installation, environment setup
- [Local Development](docs/local-development.md) – Running services locally
- [Branching Strategy](docs/branching-strategy.md) – Trunk-based development, feature flags (LaunchDarkly)
- [Code Quality](docs/code-quality.md) – SonarCloud, linting, formatting standards
- [Testing](docs/testing.md) – Test strategy, running tests, coverage
- [Deployment](docs/deployment.md) – CI/CD, environments, release process

### Reference

- [Architecture](ARCHITECTURE.md) – Clean architecture, AWS serverless, event-driven design
- [Contributing](CONTRIBUTING.md) – Branch naming, PR workflow, conventional commits
- [Pull Request Guidelines](docs/pull-request-guidelines.md) – PR title, description, review process
- [ADRs](docs/adr/) – Architecture Decision Records

### Policies

- [Security](SECURITY.md) – Security policy and vulnerability reporting
- [Code of Conduct](CODE_OF_CONDUCT.md) – Community standards
- [Changelog](CHANGELOG.md) – Release history and version notes

---

## Structure

```text
nedlia-back-end/      Python and NestJS backend services
nedlia-front-end/     React web frontend
nedlia-IaC/           Infrastructure as Code (Terraform/CDK/Pulumi)
nedlia-plugin/        Native plugins (SwiftUI, etc.)
nedlia-sdk/           Public SDKs (Python, JS, Swift, ...)
```

### Back-end

```text
nedlia-back-end/
  python/             Python backend components
  nestjs/             NestJS backend services (API, workers, etc.)
```

### Front-end

```text
nedlia-front-end/
  web/                React web application
```

### SDKs

```text
nedlia-sdk/
  python/             Python SDK for Nedlia APIs
  js/                 JavaScript/TypeScript SDK
  swift/              Swift SDK (optional, future)
```

### Plugins

```text
nedlia-plugin/
  ios/                iOS / SwiftUI plugin(s)
```

### Infrastructure

```text
nedlia-IaC/
  terraform/          Terraform modules (optional)
  cdk/ or pulumi/     Alternative IaC stacks (optional)
```

## Tooling

- Package manager (JS): pnpm with workspaces
- Monorepo orchestration (JS): Nx
- Python: uv or compatible tooling via `pyproject.toml` per project
- CI/CD: GitHub Actions (planned)

Root `package.json` defines a workspace that includes:

- `nedlia-back-end/nestjs`
- `nedlia-front-end/web`
- `nedlia-sdk/js`

## Getting Started

### Prerequisites

- Node.js (LTS)
- pnpm (`corepack enable` recommended)
- Python 3.11+

### Install JS dependencies

From the repository root:

```bash
pnpm install
```

Once Nx projects are fully wired, you will be able to run:

```bash
pnpm lint
pnpm test
pnpm build
```

### Python projects

Each Python project has its own `pyproject.toml`:

- `nedlia-back-end/python/pyproject.toml`
- `nedlia-sdk/python/pyproject.toml`

Tooling is configured via `[tool.uv]` sections and can be extended per project.

## Conventions

- One repo for all core components (backends, frontends, SDKs, plugins, IaC).
- Per-language best practices inside each subfolder.
- Shared configuration at the root:
  - `.editorconfig` for formatting basics
  - `.gitignore` covering Node, Python, IDE, and OS artifacts

## Roadmap

- [ ] Add Nx configuration and initial NestJS + React + JS SDK projects
- [ ] Flesh out Python backend and SDK package layout and tests
- [ ] Add GitHub Actions workflows for linting, testing, and building all projects
- [ ] Introduce SwiftUI plugin project(s) and iOS build pipeline
- [ ] Define infrastructure layout and provisioning workflows in `nedlia-IaC/`
- [ ] Implement core code review analysis engine
- [ ] Build PR integration with GitHub/GitLab
- [ ] Create dashboard for review insights

---

## License

This project is licensed under the [MIT License](LICENSE).
