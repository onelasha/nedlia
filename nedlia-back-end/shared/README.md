# Nedlia Shared

Shared domain models and utilities used by API and Workers.

## Structure

```
src/
  domain/           # Shared business entities
  utils/            # Common utilities
```

## Usage

This package is installed as a dependency in both `api` and `workers`:

```toml
# In api/pyproject.toml or workers/pyproject.toml
dependencies = [
    "nedlia-shared @ file:///${PROJECT_ROOT}/nedlia-back-end/shared",
]
```

## Domain Models

| Entity      | Description                                    |
| ----------- | ---------------------------------------------- |
| `Placement` | Product placement with time range and metadata |
| `Video`     | Video content metadata                         |
| `Campaign`  | Advertiser campaign                            |
| `Product`   | Product being placed                           |
