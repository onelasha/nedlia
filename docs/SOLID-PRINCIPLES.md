# SOLID Principles Enforcement

This project enforces SOLID principles through ESLint rules and Nx module boundaries.

## Rules by Principle

### S - Single Responsibility Principle

| Rule                     | Limit | Purpose                                   |
| ------------------------ | ----- | ----------------------------------------- |
| `max-lines`              | 300   | Files should have one focused purpose     |
| `max-lines-per-function` | 50    | Functions should do one thing             |
| `complexity`             | 10    | Low cyclomatic complexity = focused logic |
| `max-params`             | 4     | Many params = function doing too much     |
| `max-depth`              | 4     | Deep nesting = complex responsibility     |

### O - Open/Closed Principle

| Rule                            | Purpose                       |
| ------------------------------- | ----------------------------- |
| `explicit-member-accessibility` | Clear public API contracts    |
| TypeScript `strict` mode        | Prevents unexpected mutations |

**Best Practices:**

- Use abstract classes/interfaces for extension points
- Prefer composition over inheritance
- Use strategy pattern for varying behavior

### L - Liskov Substitution Principle

| Rule                                  | Purpose                              |
| ------------------------------------- | ------------------------------------ |
| `explicit-function-return-type`       | Clear contracts for substitutability |
| `consistent-type-assertions`          | Safe type narrowing                  |
| TypeScript `noUncheckedIndexedAccess` | Prevents undefined access            |

**Best Practices:**

- Subtypes must honor parent contracts
- Don't throw unexpected exceptions in overrides
- Maintain invariants in derived classes

### I - Interface Segregation Principle

| Rule                          | Purpose                           |
| ----------------------------- | --------------------------------- |
| `consistent-type-definitions` | Prefer interfaces for composition |
| `no-empty-interface`          | Interfaces must have purpose      |

**Best Practices:**

- Create small, focused interfaces
- Clients shouldn't depend on methods they don't use
- Split large interfaces into role-specific ones

### D - Dependency Inversion Principle

| Rule                                | Purpose                         |
| ----------------------------------- | ------------------------------- |
| `@nx/enforce-module-boundaries`     | Architectural layer enforcement |
| `import/no-cycle`                   | Prevents circular dependencies  |
| `import/no-relative-parent-imports` | Use path aliases                |

## Project Tags

Add tags to your `project.json` files:

```json
{
  "tags": ["scope:backend", "type:feature"]
}
```

### Scope Tags

- `scope:shared` - Can only depend on shared
- `scope:backend` - Can depend on shared + backend
- `scope:frontend` - Can depend on shared + frontend

### Type Tags

- `type:feature` - Business logic, can use all types
- `type:ui` - Presentation only, uses ui + util
- `type:data-access` - Data layer, uses data-access + util
- `type:util` - Pure utilities, only uses util

## Dependency Flow

```
┌─────────────┐     ┌─────────────┐
│  Frontend   │     │   Backend   │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 │
          ┌──────▼──────┐
          │   Shared    │
          │    (SDK)    │
          └─────────────┘
```

## Running Lint

```bash
# Lint all projects
pnpm nx run-many -t lint

# Lint specific project
pnpm nx lint <project-name>

# Lint affected projects
pnpm nx affected -t lint
```
