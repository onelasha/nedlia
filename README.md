# Nedlia

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![GitHub Stars](https://img.shields.io/github/stars/onelasha/Nedlia?style=social)](https://github.com/onelasha/Nedlia)

**Product placement validation platform** for video content.

> 🚧 **Alpha** – Under active development

---

## Table of Contents

- [Developer Setup](#-developer-setup)
- [Quick Start](#-quick-start)
- [Projects](#-projects)
- [Tech Stack](#-tech-stack)
- [Documentation](#-documentation)
- [Repository Structure](#-repository-structure)
- [Roadmap](#-roadmap)

---

## 🛠️ Developer Setup

> **⚠️ Complete this section before running any project.**

### 1. Prerequisites

| Tool    | Version | Install                                                      |
| ------- | ------- | ------------------------------------------------------------ |
| Node.js | 20.x    | `nvm install 20 or higher`                                   |
| pnpm    | 10.x    | `corepack enable && corepack prepare pnpm@latest --activate` |
| Python  | 3.13.5  | `pyenv install 3.13.5`                                       |
| uv      | latest  | `curl -LsSf https://astral.sh/uv/install.sh \| sh`           |

### 2. Verify Tools

```bash
node -v && pnpm -v && python -V && uv --version
```

### 3. Clone & Install

```bash
git clone https://github.com/onelasha/Nedlia.git
cd Nedlia
pnpm install
cp .env.example .env

# Note: For Python projects, always use `uv sync --extra dev` to install linting tools.
```

### 4. Verify Git Hooks ⚠️

```bash
pnpm verify-hooks   # Must show: ✅ Git hooks installed
```

> **🔒 Git hooks are MANDATORY.** All commits are validated with **Shift-Left Parity**: the pre-commit hook runs the exact same linting, type-checking, and tests as the CI. This ensures a green build before you even push.

📖 **Detailed guides:** [Getting Started](docs/getting-started.md) • [Local Development](docs/local-development.md)

---

## 🚀 Quick Start

```bash
nx run portal:serve              # Frontend    → http://localhost:5173
nx run api:serve                 # Backend API → http://localhost:8000
nx run placement-service:serve   # Service     → http://localhost:8001
```

### Common Commands

| Command                  | Description                    |
| ------------------------ | ------------------------------ |
| `nx run <project>:serve` | Start a project                |
| `nx run-many -t lint`    | Lint all projects              |
| `nx run-many -t test`    | Test all projects              |
| `nx run-many -t build`   | Build all projects             |
| `nx affected -t lint`    | Lint changed projects only     |
| `nx graph`               | Visualize project dependencies |

---

## 📦 Projects

| Project               | Type    | Language   | Description                       |
| --------------------- | ------- | ---------- | --------------------------------- |
| **portal**            | App     | TypeScript | React web portal for advertisers  |
| **api**               | App     | Python     | FastAPI REST API                  |
| **placement-service** | App     | Python     | Placement management microservice |
| **workers**           | App     | Python     | Event-driven background workers   |
| **sdk-js**            | Library | TypeScript | Video player SDK                  |

---

## 🔧 Tech Stack

| Layer              | Technologies                                  |
| ------------------ | --------------------------------------------- |
| **Frontend**       | React, TypeScript, Vite, TailwindCSS          |
| **Backend**        | FastAPI (Python), PostgreSQL                  |
| **Infrastructure** | AWS (Lambda, API Gateway, S3, SQS), Terraform |
| **Plugins**        | Swift, SwiftUI (macOS/iOS)                    |
| **Monorepo**       | Nx, pnpm workspaces                           |
| **Quality**        | ESLint, Ruff, Prettier, Husky                 |

---

## 📚 Documentation

<table>
<tr>
<td width="50%" valign="top">

### Getting Started

- [Getting Started](docs/getting-started.md)
- [Local Development](docs/local-development.md)

### Architecture

- [Architecture Overview](ARCHITECTURE.md)
- [Frontend Architecture](docs/frontend-architecture.md)
- [Domain Model](docs/domain-model.md)
- [API Standards](docs/api-standards.md)
- [Security Architecture](docs/security-architecture.md)

### Design Principles

- [SOLID Principles](docs/SOLID-PRINCIPLES.md)
- [DRY Principles](docs/dry-principles.md)

</td>
<td width="50%" valign="top">

### Development

- [Python Style Guide](docs/python-style-guide.md)
- [TypeScript Style Guide](docs/typescript-style-guide.md)
- [Error Handling](docs/error-handling.md)
- [Logging Standards](docs/logging-standards.md)

### Operations

- [Deployment](docs/deployment.md)
- [Branching Strategy](docs/branching-strategy.md)
- [Testing Strategy](docs/testing-strategy.md)

### Contributing

- [Contributing Guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

</td>
</tr>
</table>

---

## 📁 Repository Structure

```
nedlia/
├── tools/                    # Tooling configuration
│   ├── js/                   # ESLint, Prettier, TSConfig
│   ├── python/               # Ruff, MyPy configs
│   └── security/             # Gitleaks config
│
├── nedlia-back-end/
│   ├── api/                  # FastAPI REST API
│   ├── workers/              # Background workers
│   ├── services/
│   │   └── placement-service/
│   └── shared/               # Shared domain models
│
├── nedlia-front-end/
│   └── portal/               # React web portal
│
├── nedlia-sdk/
│   ├── js/                   # Web SDK
│   ├── python/               # Server SDK
│   └── swift/                # iOS/macOS SDK
│
├── nedlia-plugin/            # Video editor plugins
│   ├── finalcut/
│   ├── davinci/
│   └── lumafusion/
│
└── nedlia-IaC/               # Terraform infrastructure
```

---

## 🗺️ Roadmap

- [x] Monorepo with clean architecture
- [x] Nx build orchestration
- [x] Git hooks & conventional commits
- [x] CI/CD pipeline
- [x] Infrastructure as Code
- [ ] FastAPI backend
- [ ] React portal
- [ ] Video editor plugins
- [ ] SDKs

---

## 📄 License

[MIT License](LICENSE)
