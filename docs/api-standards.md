# API Standards

This document defines API design standards for Nedlia services.

## Table of Contents

- [Principles](#principles)
- [Versioning](#versioning)
- [URL Structure](#url-structure)
- [Request/Response Format](#requestresponse-format)
- [HTTP Methods](#http-methods)
- [Status Codes](#status-codes)
- [Error Handling (RFC 9457)](#error-handling-rfc-9457)
- [Pagination](#pagination)
- [Filtering & Sorting](#filtering--sorting)
- [Async Operations](#async-operations)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [OpenAPI Specification](#openapi-specification)
- [HATEOAS (Optional)](#hateoas-optional)
- [Related Documentation](#related-documentation)

---

## Principles

1. **Consistency**: All APIs follow the same patterns
2. **Discoverability**: APIs are self-documenting via OpenAPI
3. **Evolvability**: APIs can evolve without breaking clients
4. **Security**: Authentication and authorization on all endpoints

---

## Versioning

Nedlia uses **URL-based versioning** — the most widely adopted approach (GitHub, Stripe, Twilio, Google APIs).

### URL-Based Versioning

```
https://api.nedlia.com/v1/placements
https://api.nedlia.com/v2/placements
```

### Why URL Versioning?

| Approach         | Pros                            | Cons                              |
| ---------------- | ------------------------------- | --------------------------------- |
| **URL (chosen)** | Discoverable, cacheable, simple | URL changes between versions      |
| Header           | Clean URLs, content negotiation | Less discoverable, caching issues |
| Media Type       | RESTful, fine-grained           | Complex, poor tooling support     |
| Query Parameter  | Easy to implement               | Not recommended, caching issues   |

### Version Lifecycle

| Phase          | Duration | Description                     | Headers                               |
| -------------- | -------- | ------------------------------- | ------------------------------------- |
| **Current**    | Ongoing  | Latest stable version           | —                                     |
| **Deprecated** | 6 months | Still works, migration warnings | `Deprecation: true`, `Sunset: <date>` |
| **Sunset**     | 3 months | Read-only, then removed         | `Sunset: <date>`                      |

### Deprecation Headers

When an API version is deprecated, include standard headers:

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 01 Jul 2025 00:00:00 GMT
Link: <https://api.nedlia.com/v2/placements>; rel="successor-version"

{"data": {...}}
```

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

### Semantic Versioning for APIs

While URL uses major version only (`v1`, `v2`), internal tracking uses semver:

```
v1.0.0 → v1.1.0 (new endpoint)
v1.1.0 → v1.2.0 (new optional field)
v1.2.0 → v2.0.0 (breaking change)
```

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
```

### Error Response Format (RFC 9457)

Errors use **[RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html)** format with `application/problem+json` content type:

```json
{
  "type": "https://api.nedlia.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Your request contains invalid fields.",
  "instance": "/v1/placements",
  "errors": [{ "pointer": "#/time_range/start_time", "detail": "must be non-negative" }]
}
```

See [Error Handling Strategy](error-handling-strategy.md) for full RFC 9457 implementation details.

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

## Error Handling (RFC 9457)

Nedlia APIs implement **[RFC 9457 Problem Details for HTTP APIs](https://www.rfc-editor.org/rfc/rfc9457.html)** — the IETF standard for machine-readable error responses.

### Content Type

```
Content-Type: application/problem+json
```

### Error Response Format

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Your request contains invalid fields.",
  "instance": "/v1/placements",
  "errors": [
    {
      "pointer": "#/time_range/start_time",
      "detail": "must be a non-negative number"
    },
    {
      "pointer": "#/product_id",
      "detail": "product does not exist"
    }
  ]
}
```

### Problem Type Registry

| Problem Type URI                                    | Title                 | Status |
| --------------------------------------------------- | --------------------- | ------ |
| `https://api.nedlia.com/problems/validation-error`  | Validation Error      | 422    |
| `https://api.nedlia.com/problems/unauthorized`      | Unauthorized          | 401    |
| `https://api.nedlia.com/problems/forbidden`         | Forbidden             | 403    |
| `https://api.nedlia.com/problems/not-found`         | Resource Not Found    | 404    |
| `https://api.nedlia.com/problems/conflict`          | Conflict              | 409    |
| `https://api.nedlia.com/problems/placement-overlap` | Placement Overlap     | 409    |
| `https://api.nedlia.com/problems/rate-limited`      | Rate Limit Exceeded   | 429    |
| `https://api.nedlia.com/problems/internal-error`    | Internal Server Error | 500    |
| `about:blank`                                       | (HTTP status title)   | varies |

### Business Rule Errors

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "https://api.nedlia.com/problems/placement-overlap",
  "title": "Placement Overlap",
  "status": 409,
  "detail": "Placement overlaps with an existing placement.",
  "instance": "/v1/placements",
  "existing_placement_id": "abc123",
  "overlap_range": {
    "start_time": 32.0,
    "end_time": 40.0
  }
}
```

### Validation Errors with JSON Pointer (RFC 6901)

For field-level validation errors, use the `errors` extension with [JSON Pointers](https://www.rfc-editor.org/rfc/rfc6901):

```json
{
  "type": "https://api.nedlia.com/problems/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Your request contains invalid fields.",
  "errors": [
    { "pointer": "#/time_range/start_time", "detail": "must be non-negative" },
    { "pointer": "#/time_range/end_time", "detail": "must be greater than start_time" }
  ]
}
```

See [Error Handling Strategy](error-handling-strategy.md) for complete implementation details.

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
