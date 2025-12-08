# TypeScript & React Style Guide

Coding standards and best practices for Nedlia's TypeScript codebase (Portal, SDKs).

## Overview

| Tool           | Purpose       | Config             |
| -------------- | ------------- | ------------------ |
| **ESLint**     | Linting       | `eslint.config.js` |
| **Prettier**   | Formatting    | `.prettierrc`      |
| **TypeScript** | Type checking | `tsconfig.json`    |

---

## Quick Start

```bash
# Install dependencies
cd nedlia-front-end/portal
pnpm install

# Lint
pnpm lint

# Fix lint issues
pnpm lint --fix

# Format
pnpm format

# Type check
pnpm typecheck
```

---

## TypeScript Standards

### Strict Mode

Always enable strict mode in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true
  }
}
```

### Type Definitions

```typescript
// ✅ Good - Explicit types
interface Placement {
  id: string;
  videoId: string;
  productId: string;
  timeRange: TimeRange;
  status: PlacementStatus;
  createdAt: Date;
}

type PlacementStatus = 'draft' | 'active' | 'archived';

interface TimeRange {
  startTime: number;
  endTime: number;
}

// ✅ Good - Function types
type PlacementHandler = (placement: Placement) => Promise<void>;

// ✅ Good - Generic types
interface ApiResponse<T> {
  data: T;
  meta: {
    total: number;
    page: number;
  };
}

// ❌ Bad - Using `any`
function processData(data: any): any {
  return data;
}

// ❌ Bad - Missing types
function processData(data) {
  return data;
}
```

### Prefer `interface` over `type` for Objects

```typescript
// ✅ Good - Use interface for object shapes
interface User {
  id: string;
  name: string;
  email: string;
}

// ✅ Good - Use type for unions, primitives, tuples
type Status = 'pending' | 'active' | 'inactive';
type Coordinates = [number, number];
type ID = string | number;

// ✅ Good - Extend interfaces
interface AdminUser extends User {
  permissions: string[];
}
```

### Enums vs Union Types

```typescript
// ✅ Preferred - Union types (tree-shakeable)
type PlacementStatus = 'draft' | 'active' | 'archived';

// ✅ Also good - const objects for runtime values
const PlacementStatus = {
  Draft: 'draft',
  Active: 'active',
  Archived: 'archived',
} as const;

type PlacementStatus = (typeof PlacementStatus)[keyof typeof PlacementStatus];

// ⚠️ Avoid - TypeScript enums (not tree-shakeable)
enum PlacementStatusEnum {
  Draft = 'draft',
  Active = 'active',
  Archived = 'archived',
}
```

### Null Handling

```typescript
// ✅ Good - Explicit null checks
function getPlacement(id: string): Placement | null {
  const placement = placements.get(id);
  return placement ?? null;
}

// ✅ Good - Optional chaining
const name = user?.profile?.name ?? 'Unknown';

// ✅ Good - Type guards
function isPlacement(value: unknown): value is Placement {
  return typeof value === 'object' && value !== null && 'id' in value && 'videoId' in value;
}

// ❌ Bad - Non-null assertion without validation
const name = user!.profile!.name;
```

---

## React Standards

### Component Structure

```typescript
// ✅ Good - Functional component with TypeScript
import { useState, useCallback } from 'react';

interface PlacementCardProps {
  placement: Placement;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  isLoading?: boolean;
}

export function PlacementCard({
  placement,
  onEdit,
  onDelete,
  isLoading = false,
}: PlacementCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleEdit = useCallback(() => {
    onEdit(placement.id);
  }, [onEdit, placement.id]);

  const handleDelete = useCallback(() => {
    onDelete(placement.id);
  }, [onDelete, placement.id]);

  if (isLoading) {
    return <PlacementCardSkeleton />;
  }

  return (
    <div className="placement-card">
      <h3>{placement.description}</h3>
      <p>Status: {placement.status}</p>
      <div className="actions">
        <button onClick={handleEdit}>Edit</button>
        <button onClick={handleDelete}>Delete</button>
      </div>
    </div>
  );
}
```

### File Naming Conventions

```
src/
├── components/
│   ├── PlacementCard/
│   │   ├── PlacementCard.tsx        # Component
│   │   ├── PlacementCard.test.tsx   # Tests
│   │   ├── PlacementCard.styles.ts  # Styles (if using CSS-in-JS)
│   │   └── index.ts                 # Re-export
│   └── ui/
│       ├── Button.tsx
│       └── Input.tsx
├── hooks/
│   ├── usePlacements.ts
│   └── useAuth.ts
├── services/
│   ├── api.ts
│   └── placement.service.ts
├── types/
│   ├── placement.ts
│   └── api.ts
└── utils/
    ├── format.ts
    └── validation.ts
```

### Naming Conventions

| Type                 | Convention                  | Example                    |
| -------------------- | --------------------------- | -------------------------- |
| **Components**       | PascalCase                  | `PlacementCard.tsx`        |
| **Hooks**            | camelCase with `use` prefix | `usePlacements.ts`         |
| **Utilities**        | camelCase                   | `formatDate.ts`            |
| **Types/Interfaces** | PascalCase                  | `Placement`, `ApiResponse` |
| **Constants**        | UPPER_SNAKE_CASE            | `MAX_PLACEMENTS`           |
| **CSS classes**      | kebab-case                  | `placement-card`           |

### Hooks

```typescript
// ✅ Good - Custom hook with proper typing
import { useState, useEffect, useCallback } from 'react';

interface UsePlacementsOptions {
  videoId?: string;
  limit?: number;
}

interface UsePlacementsReturn {
  placements: Placement[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function usePlacements(options: UsePlacementsOptions = {}): UsePlacementsReturn {
  const { videoId, limit = 20 } = options;

  const [placements, setPlacements] = useState<Placement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchPlacements = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await placementService.list({ videoId, limit });
      setPlacements(response.data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [videoId, limit]);

  useEffect(() => {
    fetchPlacements();
  }, [fetchPlacements]);

  return {
    placements,
    isLoading,
    error,
    refetch: fetchPlacements,
  };
}
```

### State Management (Zustand)

```typescript
// ✅ Good - Zustand store with TypeScript
import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface PlacementState {
  placements: Placement[];
  selectedId: string | null;
  isLoading: boolean;
  error: string | null;
}

interface PlacementActions {
  setPlacements: (placements: Placement[]) => void;
  selectPlacement: (id: string | null) => void;
  addPlacement: (placement: Placement) => void;
  updatePlacement: (id: string, updates: Partial<Placement>) => void;
  deletePlacement: (id: string) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

type PlacementStore = PlacementState & PlacementActions;

export const usePlacementStore = create<PlacementStore>()(
  devtools(
    persist(
      set => ({
        // State
        placements: [],
        selectedId: null,
        isLoading: false,
        error: null,

        // Actions
        setPlacements: placements => set({ placements }),
        selectPlacement: id => set({ selectedId: id }),
        addPlacement: placement =>
          set(state => ({
            placements: [...state.placements, placement],
          })),
        updatePlacement: (id, updates) =>
          set(state => ({
            placements: state.placements.map(p => (p.id === id ? { ...p, ...updates } : p)),
          })),
        deletePlacement: id =>
          set(state => ({
            placements: state.placements.filter(p => p.id !== id),
          })),
        setLoading: isLoading => set({ isLoading }),
        setError: error => set({ error }),
      }),
      { name: 'placement-store' }
    )
  )
);
```

### API Calls (React Query)

```typescript
// ✅ Good - React Query with TypeScript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Query keys
export const placementKeys = {
  all: ['placements'] as const,
  lists: () => [...placementKeys.all, 'list'] as const,
  list: (filters: PlacementFilters) => [...placementKeys.lists(), filters] as const,
  details: () => [...placementKeys.all, 'detail'] as const,
  detail: (id: string) => [...placementKeys.details(), id] as const,
};

// Queries
export function usePlacementsQuery(filters: PlacementFilters = {}) {
  return useQuery({
    queryKey: placementKeys.list(filters),
    queryFn: () => placementService.list(filters),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function usePlacementQuery(id: string) {
  return useQuery({
    queryKey: placementKeys.detail(id),
    queryFn: () => placementService.get(id),
    enabled: !!id,
  });
}

// Mutations
export function useCreatePlacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: placementService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: placementKeys.lists() });
    },
  });
}

export function useUpdatePlacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: PlacementUpdate }) =>
      placementService.update(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: placementKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: placementKeys.lists() });
    },
  });
}
```

### Error Boundaries

```typescript
// ✅ Good - Error boundary component
import { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div className="error-fallback">
            <h2>Something went wrong</h2>
            <p>{this.state.error?.message}</p>
          </div>
        )
      );
    }

    return this.props.children;
  }
}
```

---

## Styling (TailwindCSS)

### Class Organization

```tsx
// ✅ Good - Organized Tailwind classes
<div
  className={cn(
    // Layout
    "flex flex-col gap-4",
    // Sizing
    "w-full max-w-md",
    // Spacing
    "p-6",
    // Colors
    "bg-white dark:bg-gray-800",
    // Border
    "rounded-lg border border-gray-200",
    // Shadow
    "shadow-sm",
    // Transitions
    "transition-all duration-200",
    // Conditional
    isActive && "ring-2 ring-blue-500"
  )}
>
```

### Component Variants (CVA)

```typescript
// ✅ Good - Class Variance Authority for variants
import { cva, type VariantProps } from 'class-variance-authority';

const buttonVariants = cva(
  // Base styles
  'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

export function Button({ className, variant, size, isLoading, children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={isLoading}
      {...props}
    >
      {isLoading ? <Spinner className="mr-2" /> : null}
      {children}
    </button>
  );
}
```

---

## Testing

### Component Testing (Vitest + Testing Library)

```typescript
// ✅ Good - Component test
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { PlacementCard } from './PlacementCard';

const mockPlacement: Placement = {
  id: '1',
  videoId: 'video-1',
  productId: 'product-1',
  timeRange: { startTime: 0, endTime: 30 },
  status: 'active',
  description: 'Test placement',
  createdAt: new Date(),
};

describe('PlacementCard', () => {
  it('renders placement information', () => {
    render(<PlacementCard placement={mockPlacement} onEdit={vi.fn()} onDelete={vi.fn()} />);

    expect(screen.getByText('Test placement')).toBeInTheDocument();
    expect(screen.getByText(/active/i)).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn();

    render(<PlacementCard placement={mockPlacement} onEdit={onEdit} onDelete={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /edit/i }));

    expect(onEdit).toHaveBeenCalledWith('1');
  });

  it('shows loading skeleton when isLoading is true', () => {
    render(
      <PlacementCard placement={mockPlacement} onEdit={vi.fn()} onDelete={vi.fn()} isLoading />
    );

    expect(screen.getByTestId('placement-skeleton')).toBeInTheDocument();
  });
});
```

### Hook Testing

```typescript
// ✅ Good - Hook test
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import { usePlacements } from './usePlacements';
import * as placementService from '@/services/placement.service';

vi.mock('@/services/placement.service');

describe('usePlacements', () => {
  it('fetches placements on mount', async () => {
    const mockPlacements = [{ id: '1', description: 'Test' }];
    vi.mocked(placementService.list).mockResolvedValue({
      data: mockPlacements,
    });

    const { result } = renderHook(() => usePlacements());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.placements).toEqual(mockPlacements);
  });

  it('handles errors', async () => {
    vi.mocked(placementService.list).mockRejectedValue(new Error('API Error'));

    const { result } = renderHook(() => usePlacements());

    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });

    expect(result.current.error?.message).toBe('API Error');
  });
});
```

---

## ESLint Configuration

```javascript
// eslint.config.js
import js from '@eslint/js';
import typescript from '@typescript-eslint/eslint-plugin';
import typescriptParser from '@typescript-eslint/parser';
import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import importPlugin from 'eslint-plugin-import';

export default [
  js.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: { jsx: true },
      },
    },
    plugins: {
      '@typescript-eslint': typescript,
      react,
      'react-hooks': reactHooks,
      import: importPlugin,
    },
    rules: {
      // TypeScript
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/consistent-type-imports': ['error', { prefer: 'type-imports' }],

      // React
      'react/react-in-jsx-scope': 'off',
      'react/prop-types': 'off',
      'react/jsx-no-target-blank': 'error',
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',

      // Imports
      'import/order': [
        'error',
        {
          groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
          'newlines-between': 'always',
          alphabetize: { order: 'asc' },
        },
      ],
      'import/no-duplicates': 'error',

      // General
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'prefer-const': 'error',
      eqeqeq: ['error', 'always'],
    },
    settings: {
      react: { version: 'detect' },
    },
  },
];
```

---

## Prettier Configuration

```json
// .prettierrc
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 80,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

---

## VS Code Settings

```json
// .vscode/settings.json
{
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": "explicit"
    }
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "typescript.suggest.autoImports": true
}
```

---

## Related Documentation

- [Code Quality](code-quality.md) – Overall quality standards
- [Testing Strategy](testing-strategy.md) – Testing patterns
- [API Standards](api-standards.md) – API integration patterns
