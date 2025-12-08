# Nedlia Workers

Event-driven Lambda workers for async processing. Consume messages from SQS queues triggered by EventBridge.

## Structure

```
src/
  handlers/         # Lambda entry points (SQS message handlers)
  tasks/            # Business logic for each task type
tests/              # Unit and integration tests
```

## Workers

| Worker           | Event Trigger                                             | Purpose                             |
| ---------------- | --------------------------------------------------------- | ----------------------------------- |
| `file_generator` | `placement.created`, `placement.updated`                  | Generate placement data files to S3 |
| `validator`      | `video.validation_requested`                              | Async validation of placements      |
| `notifier`       | `placement.*`, `campaign.*`, `video.validation_completed` | Send notifications                  |
| `sync`           | `plugin.sync_requested`                                   | Sync plugin data to server          |

## Event Flow

```
EventBridge                    SQS Queue                    Lambda Worker
    │                              │                              │
    │  placement.created           │                              │
    ├─────────────────────────────▶│                              │
    │                              │  trigger                     │
    │                              ├─────────────────────────────▶│
    │                              │                              │ process
    │                              │                              │ generate file
    │                              │                              │ upload to S3
    │  file.generated              │                              │
    │◀─────────────────────────────┼──────────────────────────────┤
    │                              │                              │
```

## Eventual Consistency

Workers operate asynchronously:

1. **API publishes event** → returns immediately to client
2. **Worker processes** → may take seconds to minutes
3. **Client polls** → for result (or receives webhook/notification)

### Idempotency

All handlers MUST be idempotent:

- Use idempotency keys from event payload
- Check if work already done before processing
- SQS may deliver messages more than once

### Dead Letter Queues

Failed messages go to DLQ after max retries:

- Monitor DLQ for failures
- Investigate and replay or discard

## Local Development

```bash
cd nedlia-back-end/workers
uv sync

# Run worker locally (simulates SQS trigger)
uv run python -m src.main

# Run specific handler
uv run python -c "from src.handlers.file_generator import handler; handler(event, context)"
```

## Deployment

Workers deploy as Lambda functions via Terraform:

```hcl
# nedlia-IaC/modules/lambda/
module "file_generator_worker" {
  source        = "./lambda"
  function_name = "nedlia-${var.environment}-file-generator"
  handler       = "src.handlers.file_generator.handler"
  # ...
}
```

## Testing

```bash
uv run pytest tests/
```

Mock SQS events for testing:

```python
def test_file_generator_handler():
    event = {
        "Records": [{
            "body": json.dumps({
                "type": "placement.created",
                "data": {"placement_id": "123"}
            })
        }]
    }
    result = handler(event, None)
    assert result["statusCode"] == 200
```
