# ADR-003: Event-Driven Architecture

## Status

Accepted

## Context

Nedlia's product placement platform needs to:

- Generate placement files asynchronously (after placements are created)
- Validate placements without blocking the API response
- Notify advertisers when campaigns or placements change
- Sync data between plugins and server
- Scale different components independently
- Handle failures gracefully

## Decision

We adopt an **event-driven architecture** with **eventual consistency**.

### Event Flow

```
Command → Handler → Persist → Publish Event → Subscribers
```

1. API receives command (e.g., "create placement")
2. Lambda handler validates and persists to Aurora
3. Handler publishes event to EventBridge (e.g., `placement.created`)
4. SQS queues receive event and trigger downstream Lambdas
5. Consumers process event (generate files, send notifications, etc.)

### Key Patterns

- **CQRS**: Separate command (write) and query (read) paths
- **Eventual Consistency**: Reads may lag writes; design for it
- **Idempotency**: All handlers must handle duplicate events
- **Dead Letter Queues**: Failed events go to DLQ for inspection

### Event Format

We use [CloudEvents](https://cloudevents.io/) specification:

```json
{
  "specversion": "1.0",
  "type": "com.nedlia.placement.created",
  "source": "/placements",
  "id": "uuid",
  "time": "2024-01-01T00:00:00Z",
  "data": {
    "placementId": "123",
    "videoId": "456",
    "productId": "789"
  }
}
```

### Key Events

| Event                        | Publisher        | Consumers                |
| ---------------------------- | ---------------- | ------------------------ |
| `placement.created`          | API              | File Generator, Notifier |
| `placement.updated`          | API              | File Generator, Notifier |
| `placement.deleted`          | API              | File Generator, Notifier |
| `video.validation_requested` | API              | Validator                |
| `video.validation_completed` | Validator        | Notifier, API (cache)    |
| `campaign.created`           | API              | Notifier                 |
| `plugin.sync_requested`      | Plugin (via API) | Sync Worker              |

## Consequences

### Positive

- Services are decoupled; can evolve independently
- Natural fit for async processing (file generation, validation)
- Easy to add new consumers without changing producers
- Built-in retry and failure handling via SQS

### Negative

- Eventual consistency requires careful UI design
- Debugging distributed flows is harder
- Event schema evolution needs governance
- More infrastructure to manage

### Mitigations

- Use X-Ray for distributed tracing
- Implement correlation IDs across all events
- Document event schemas in a registry
- Design UI to handle "processing" states gracefully
