# Nedlia Portal

React web application for marketing agencies and advertisers.

## Structure

```
src/
  domain/           # Business entities
  application/      # Use cases, state management
  infrastructure/   # API clients, storage
  ui/               # React components, pages
```

## Features

| Feature             | Description                           |
| ------------------- | ------------------------------------- |
| Campaign Management | Create and manage ad campaigns        |
| Placement Tracking  | View product placements across videos |
| Analytics           | Performance metrics and reporting     |
| Budget Management   | Track and manage placement budgets    |
| Validation Reports  | View placement validation results     |

## Setup

```bash
cd nedlia-front-end/portal
pnpm install
pnpm dev
```

## Tech Stack

- **Framework**: React + TypeScript
- **Build**: Vite
- **Styling**: TailwindCSS
- **State**: TanStack Query
- **UI Components**: shadcn/ui
