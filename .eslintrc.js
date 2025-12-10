module.exports = {
  root: true,
  env: {
    node: true,
    browser: true,
    es2022: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
  },
  plugins: ['@typescript-eslint', 'import', '@nx', 'boundaries'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:import/recommended',
    'plugin:import/typescript',
    'plugin:boundaries/recommended',
    'prettier',
  ],
  rules: {
    // ===== EXISTING RULES =====
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'warn',
    'import/order': [
      'error',
      {
        groups: ['builtin', 'external', 'internal', 'parent', 'sibling', 'index'],
        'newlines-between': 'always',
        alphabetize: { order: 'asc', caseInsensitive: true },
      },
    ],
    'no-console': ['warn', { allow: ['warn', 'error'] }],

    // ===== SOLID: Single Responsibility Principle =====
    // Limit file size to encourage focused modules
    'max-lines': ['warn', { max: 300, skipBlankLines: true, skipComments: true }],
    // Limit function size
    'max-lines-per-function': ['warn', { max: 50, skipBlankLines: true, skipComments: true }],
    // Limit cyclomatic complexity
    complexity: ['warn', { max: 10 }],
    // Limit function parameters (too many = doing too much)
    'max-params': ['warn', { max: 4 }],
    // Limit nesting depth
    'max-depth': ['warn', { max: 4 }],

    // ===== SOLID: Open/Closed Principle =====
    // Prefer readonly to prevent mutation
    '@typescript-eslint/prefer-readonly': 'off', // Enable when using type-aware linting
    // Encourage explicit member accessibility
    '@typescript-eslint/explicit-member-accessibility': [
      'warn',
      { accessibility: 'explicit', overrides: { constructors: 'no-public' } },
    ],

    // ===== SOLID: Liskov Substitution Principle =====
    // Require explicit return types for better contract definition
    '@typescript-eslint/explicit-function-return-type': [
      'warn',
      { allowExpressions: true, allowTypedFunctionExpressions: true },
    ],
    // Consistent type assertions
    '@typescript-eslint/consistent-type-assertions': [
      'error',
      { assertionStyle: 'as', objectLiteralTypeAssertions: 'never' },
    ],

    // ===== SOLID: Interface Segregation Principle =====
    // Prefer interfaces over type aliases for object types
    '@typescript-eslint/consistent-type-definitions': ['warn', 'interface'],
    // No empty interfaces (sign of poor segregation)
    '@typescript-eslint/no-empty-interface': 'error',

    // ===== SOLID: Dependency Inversion Principle =====
    // Nx enforce module boundaries
    '@nx/enforce-module-boundaries': [
      'error',
      {
        allow: [],
        depConstraints: [
          {
            sourceTag: 'scope:shared',
            onlyDependOnLibsWithTags: ['scope:shared'],
          },
          {
            sourceTag: 'scope:backend',
            onlyDependOnLibsWithTags: ['scope:shared', 'scope:backend'],
          },
          {
            sourceTag: 'scope:frontend',
            onlyDependOnLibsWithTags: ['scope:shared', 'scope:frontend'],
          },
          {
            sourceTag: 'type:feature',
            onlyDependOnLibsWithTags: ['type:feature', 'type:ui', 'type:data-access', 'type:util'],
          },
          {
            sourceTag: 'type:ui',
            onlyDependOnLibsWithTags: ['type:ui', 'type:util'],
          },
          {
            sourceTag: 'type:data-access',
            onlyDependOnLibsWithTags: ['type:data-access', 'type:util'],
          },
          {
            sourceTag: 'type:util',
            onlyDependOnLibsWithTags: ['type:util'],
          },
        ],
      },
    ],
    // No circular dependencies
    'import/no-cycle': 'error',
    // No relative parent imports (use aliases)
    'import/no-relative-parent-imports': 'warn',
  },
  settings: {
    'import/resolver': {
      typescript: true,
      node: true,
    },
    'boundaries/elements': [
      { type: 'backend', pattern: 'nedlia-back-end/*' },
      { type: 'frontend', pattern: 'nedlia-front-end/*' },
      { type: 'sdk', pattern: 'nedlia-sdk/*' },
      { type: 'shared', pattern: 'libs/shared/*' },
    ],
    'boundaries/ignore': ['**/*.spec.ts', '**/*.test.ts'],
  },
  ignorePatterns: ['node_modules/', 'dist/', '.build/', 'coverage/'],
};
