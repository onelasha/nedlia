# JavaScript/TypeScript Tooling Configuration

This directory contains all JavaScript and TypeScript tooling configuration for the Nedlia monorepo.

## Configuration Files

| File                       | Purpose                                                |
| -------------------------- | ------------------------------------------------------ |
| **`eslint.config.js`**     | ESLint configuration with SOLID principles enforcement |
| **`prettier.config.js`**   | Prettier code formatting rules                         |
| **`tsconfig.base.json`**   | Base TypeScript configuration for all JS/TS projects   |
| **`commitlint.config.js`** | Conventional commit message validation                 |
| **`.nvmrc`**               | Node.js version specification                          |

## Usage

### ESLint

Projects can extend this config. The root `.eslintrc.cjs` redirects to this file for Nx compatibility.

```javascript
// In project eslint config
module.exports = {
  extends: ['../../tools/js/eslint.config.js'],
  // project-specific overrides
};
```

### TypeScript

Projects can extend the base tsconfig:

```json
{
  "extends": "../../tools/js/tsconfig.base.json",
  "compilerOptions": {
    // project-specific options
  }
}
```

### Prettier

Prettier automatically discovers config from root. Projects inherit these settings.

### Commitlint

Configured via `package.json` at repository root:

```json
{
  "commitlint": {
    "extends": ["./tools/js/commitlint.config.js"]
  }
}
```

### Node Version

Use `.nvmrc` with nvm:

```bash
cd tools/js && nvm use
# or from root
nvm use tools/js/.nvmrc
```

## SOLID Principles Enforcement

The ESLint configuration enforces SOLID principles:

- **Single Responsibility**: `max-lines`, `max-lines-per-function`, `complexity`
- **Open/Closed**: `explicit-member-accessibility`
- **Liskov Substitution**: `explicit-function-return-type`
- **Interface Segregation**: `consistent-type-definitions`, `no-empty-interface`
- **Dependency Inversion**: `@nx/enforce-module-boundaries`, `import/no-cycle`

See [SOLID Principles](../../docs/SOLID-PRINCIPLES.md) for details.
