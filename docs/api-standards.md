# API Standards

This document defines API design standards for Nedlia services.

## Principles

1. **Consistency**: All APIs follow the same patterns
2. **Discoverability**: APIs are self-documenting via OpenAPI
3. **Evolvability**: APIs can evolve without breaking clients
4. **Security**: Authentication and authorization on all endpoints

---

## Versioning

### URL-Based Versioning

```
https://api.nedlia.com/v1/placements
https://api.nedlia.com/v2/placements
```

### Version Lifecycle

| Phase          | Duration | Description                     |
| -------------- | -------- | ------------------------------- |
| **Current**    | Ongoing  | Latest stable version           |
| **Deprecated** | 6 months | Still works, migration warnings |
| **Sunset**     | 3 months | Read-only, then removed         |

### Breaking vs Non-Breaking Changes

**Non-Breaking (no version bump)**:

- Adding new optional fields
- Adding new endpoints
- Adding new enum values (if clients handle unknown)
- Relaxing validation

**Breaking (requires new version)**:

- Removing fields
- Renaming fields
- Changing field types
- Changing URL structure
- Tightening validation

---

## URL Structure

### Resource Naming

```
# Collections (plural nouns)
GET    /v1/placements
POST   /v1/placements

# Individual resources
GET    /v1/placements/{id}
PUT    /v1/placements/{id}
PATCH  /v1/placements/{id}
DELETE /v1/placements/{id}

# Sub-resources
GET    /v1/videos/{id}/placements
POST   /v1/videos/{id}/placements

# Actions (verbs for non-CRUD operations)
POST   /v1/videos/{id}/validate
POST   /v1/placements/{id}/archive
```

### Naming Conventions

- Use **kebab-case** for URLs: `/validation-runs`
- Use **snake_case** for JSON fields: `created_at`
- Use **plural nouns** for collections: `/placements` not `/placement`
- Use **UUIDs** for resource IDs: `/placements/550e8400-e29b-41d4-a716-446655440000`

---

## Request/Response Format

### Content Type

```
Content-Type: application/json
Accept: application/json
```

### Request Body

```json
POST /v1/placements
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "time_range": {
    "start_time": 30.5,
    "end_time": 45.0
  },
  "description": "Product visible on table"
}
```

### Success Response

```json
HTTP/1.1 201 Created
Location: /v1/placements/123e4567-e89b-12d3-a456-426614174000

{
  "data": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "product_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "time_range": {
      "start_time": 30.5,
      "end_time": 45.0
    },
    "description": "Product visible on table",
    "status": "active",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### Envelope Structure

All responses use a consistent envelope:

```json
// Success
{
  "data": { ... },           // Single resource or array
  "meta": { ... }            // Optional metadata (pagination, etc.)
}

// Error
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "details": [ ... ]       // Optional field-level errors
  }
}
```

---

## HTTP Methods

| Method | Idempotent | Safe | Use Case                        |
| ------ | ---------- | ---- | ------------------------------- |
| GET    | ✅         | ✅   | Retrieve resource(s)            |
| POST   | ❌         | ❌   | Create resource, trigger action |
| PUT    | ✅         | ❌   | Full update (replace)           |
| PATCH  | ❌         | ❌   | Partial update                  |
| DELETE | ✅         | ❌   | Remove resource                 |

### Idempotency Keys

For non-idempotent operations, clients should send an idempotency key:

```
POST /v1/placements
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

{
  "video_id": "...",
  ...
}
```

Server behavior:

- First request: Process and store result with key
- Duplicate request: Return stored result (no reprocessing)
- Key expires after 24 hours

---

## Status Codes

### Success

| Code | Meaning    | When to Use               |
| ---- | ---------- | ------------------------- |
| 200  | OK         | GET, PUT, PATCH success   |
| 201  | Created    | POST created new resource |
| 202  | Accepted   | Async operation started   |
| 204  | No Content | DELETE success, no body   |

### Client Errors

| Code | Meaning              | When to Use                          |
| ---- | -------------------- | ------------------------------------ |
| 400  | Bad Request          | Invalid JSON, validation error       |
| 401  | Unauthorized         | Missing or invalid auth              |
| 403  | Forbidden            | Valid auth, insufficient permissions |
| 404  | Not Found            | Resource doesn't exist               |
| 409  | Conflict             | Business rule violation              |
| 422  | Unprocessable Entity | Semantic validation error            |
| 429  | Too Many Requests    | Rate limit exceeded                  |

### Server Errors

| Code | Meaning               | When to Use            |
| ---- | --------------------- | ---------------------- |
| 500  | Internal Server Error | Unexpected error       |
| 502  | Bad Gateway           | Upstream service error |
| 503  | Service Unavailable   | Maintenance, overload  |
| 504  | Gateway Timeout       | Upstream timeout       |

---

## Error Handling

### Error Response Format

```json
HTTP/1.1 400 Bad Request

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "req_abc123",
    "details": [
      {
        "field": "time_range.start_time",
        "code": "INVALID_VALUE",
        "message": "Start time cannot be negative"
      },
      {
        "field": "product_id",
        "code": "NOT_FOUND",
        "message": "Product does not exist"
      }
    ]
  }
}
```

### Error Codes

| Code               | HTTP Status | Description               |
| ------------------ | ----------- | ------------------------- |
| `VALIDATION_ERROR` | 400         | Request validation failed |
| `INVALID_JSON`     | 400         | Malformed JSON body       |
| `UNAUTHORIZED`     | 401         | Authentication required   |
| `FORBIDDEN`        | 403         | Insufficient permissions  |
| `NOT_FOUND`        | 404         | Resource not found        |
| `CONFLICT`         | 409         | Business rule conflict    |
| `RATE_LIMITED`     | 429         | Too many requests         |
| `INTERNAL_ERROR`   | 500         | Unexpected server error   |

### Business Rule Errors

```json
HTTP/1.1 409 Conflict

{
  "error": {
    "code": "PLACEMENT_OVERLAP",
    "message": "Placement overlaps with existing placement",
    "details": [
      {
        "existing_placement_id": "abc123",
        "overlap_range": {
          "start_time": 32.0,
          "end_time": 40.0
        }
      }
    ]
  }
}
```

---

## Pagination

### Cursor-Based (Preferred)

```
GET /v1/placements?limit=20&cursor=eyJpZCI6IjEyMyJ9
```

Response:

```json
{
  "data": [ ... ],
  "meta": {
    "has_more": true,
    "next_cursor": "eyJpZCI6IjE0MyJ9",
    "prev_cursor": "eyJpZCI6IjEwMyJ9"
  }
}
```

### Offset-Based (Simple Cases)

```
GET /v1/placements?limit=20&offset=40
```

Response:

```json
{
  "data": [ ... ],
  "meta": {
    "total": 150,
    "limit": 20,
    "offset": 40
  }
}
```

### Default Limits

| Resource          | Default | Max |
| ----------------- | ------- | --- |
| Placements        | 20      | 100 |
| Videos            | 20      | 50  |
| Campaigns         | 20      | 100 |
| Validation Issues | 50      | 200 |

---

## Filtering & Sorting

### Filtering

```
GET /v1/placements?video_id=abc123&status=active
GET /v1/placements?created_at[gte]=2024-01-01&created_at[lt]=2024-02-01
```

Operators:

- `eq` (default): Equals
- `ne`: Not equals
- `gt`, `gte`: Greater than (or equal)
- `lt`, `lte`: Less than (or equal)
- `in`: In list (`status[in]=active,draft`)

### Sorting

```
GET /v1/placements?sort=created_at        # Ascending
GET /v1/placements?sort=-created_at       # Descending
GET /v1/placements?sort=-created_at,name  # Multiple fields
```

---

## Async Operations

For long-running operations, return `202 Accepted` with a status URL.

### Request

```
POST /v1/videos/abc123/validate
```

### Response

```json
HTTP/1.1 202 Accepted
Location: /v1/validation-runs/run_xyz789

{
  "data": {
    "id": "run_xyz789",
    "status": "pending",
    "video_id": "abc123",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Polling

```
GET /v1/validation-runs/run_xyz789
```

```json
{
  "data": {
    "id": "run_xyz789",
    "status": "completed", // pending, running, completed, failed
    "video_id": "abc123",
    "created_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:15Z",
    "result": {
      "is_valid": true,
      "issues_count": 0
    }
  }
}
```

---

## Authentication

### Bearer Token

```
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

### API Key (SDK/Plugin)

```
X-API-Key: nedlia_live_abc123xyz
```

### Token Format

| Prefix         | Environment | Use               |
| -------------- | ----------- | ----------------- |
| `nedlia_live_` | Production  | Live API access   |
| `nedlia_test_` | Sandbox     | Testing           |
| `nedlia_dev_`  | Development | Local development |

---

## Rate Limiting

### Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705312800
```

### Limits

| Tier       | Requests/min | Burst |
| ---------- | ------------ | ----- |
| Free       | 60           | 10    |
| Pro        | 600          | 100   |
| Enterprise | 6000         | 1000  |

### Rate Limit Response

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 30

{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Retry after 30 seconds.",
    "retry_after": 30
  }
}
```

---

## OpenAPI Specification

All APIs are documented with OpenAPI 3.1:

```yaml
# openapi.yaml
openapi: 3.1.0
info:
  title: Nedlia API
  version: 1.0.0
  description: Product placement validation platform API

servers:
  - url: https://api.nedlia.com/v1
    description: Production
  - url: https://api.staging.nedlia.com/v1
    description: Staging

paths:
  /placements:
    get:
      summary: List placements
      operationId: listPlacements
      tags: [Placements]
      parameters:
        - $ref: '#/components/parameters/limit'
        - $ref: '#/components/parameters/cursor'
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PlacementList'
```

### Generating Clients

```bash
# Generate TypeScript client
npx openapi-generator-cli generate -i openapi.yaml -g typescript-fetch -o sdk/

# Generate Python client
openapi-generator generate -i openapi.yaml -g python -o sdk/
```

---

## HATEOAS (Optional)

For discoverability, include links:

```json
{
  "data": {
    "id": "abc123",
    "video_id": "xyz789",
    ...
  },
  "links": {
    "self": "/v1/placements/abc123",
    "video": "/v1/videos/xyz789",
    "validate": "/v1/placements/abc123/validate"
  }
}
```

---

## Related Documentation

- [Domain Model](domain-model.md) – Domain entities and events
- [Security Architecture](security-architecture.md) – Authentication details
- [Testing Strategy](testing-strategy.md) – API testing
