# Observability

Comprehensive observability strategy for Nedlia covering logging, metrics, tracing, and alerting.

## Three Pillars of Observability

```
┌─────────────────────────────────────────────────────────────────┐
│                        Observability                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│     Logs        │    Metrics      │         Traces              │
│                 │                 │                             │
│ What happened   │ How much/many   │ Request flow across         │
│ (events)        │ (aggregates)    │ services                    │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ CloudWatch Logs │ CloudWatch      │ AWS X-Ray                   │
│                 │ Metrics         │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

---

## Structured Logging

### Log Format

All logs use JSON format for machine parsing:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "message": "Placement created",
  "service": "nedlia-api",
  "environment": "production",
  "version": "1.2.3",
  "request_id": "req_abc123",
  "trace_id": "1-5f8d3b2a-abc123def456",
  "user_id": "user_xyz789",
  "data": {
    "placement_id": "placement_123",
    "video_id": "video_456"
  }
}
```

### Log Levels

| Level      | When to Use                | Example                         |
| ---------- | -------------------------- | ------------------------------- |
| `DEBUG`    | Detailed debugging info    | Variable values, flow tracing   |
| `INFO`     | Normal operations          | Request received, job completed |
| `WARN`     | Potential issues           | Retry attempt, deprecated usage |
| `ERROR`    | Errors that need attention | Failed operation, exception     |
| `CRITICAL` | System failures            | Database down, out of memory    |

### Python Logging Setup

```python
# src/infrastructure/logging.py
import structlog
import logging

def configure_logging(environment: str, service: str, version: str):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # Add global context
    structlog.contextvars.bind_contextvars(
        service=service,
        environment=environment,
        version=version,
    )

# Usage
logger = structlog.get_logger()

def create_placement(request):
    logger.info(
        "Creating placement",
        video_id=request.video_id,
        product_id=request.product_id,
    )
```

### Request Context

Bind request context at the start of each request:

```python
# src/interface/middleware.py
from structlog.contextvars import bind_contextvars, clear_contextvars

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    trace_id = request.headers.get("X-Amzn-Trace-Id", "")

    clear_contextvars()
    bind_contextvars(
        request_id=request_id,
        trace_id=trace_id,
        path=request.url.path,
        method=request.method,
    )

    response = await call_next(request)
    return response
```

### Sensitive Data

Never log sensitive data:

```python
# Bad
logger.info("User login", password=user.password)

# Good
logger.info("User login", user_id=user.id)

# Mask sensitive fields
def mask_sensitive(data: dict) -> dict:
    sensitive_keys = {"password", "token", "secret", "api_key"}
    return {
        k: "***MASKED***" if k in sensitive_keys else v
        for k, v in data.items()
    }
```

---

## Metrics

### Key Metrics

#### API Metrics

| Metric                   | Type      | Description                                |
| ------------------------ | --------- | ------------------------------------------ |
| `api.requests.total`     | Counter   | Total requests by endpoint, method, status |
| `api.requests.duration`  | Histogram | Request latency in ms                      |
| `api.requests.in_flight` | Gauge     | Current active requests                    |
| `api.errors.total`       | Counter   | Errors by type                             |

#### Business Metrics

| Metric                       | Type      | Description           |
| ---------------------------- | --------- | --------------------- |
| `placements.created.total`   | Counter   | Placements created    |
| `placements.validated.total` | Counter   | Validations completed |
| `validations.duration`       | Histogram | Validation time       |
| `campaigns.active`           | Gauge     | Active campaigns      |

#### Infrastructure Metrics

| Metric                  | Type      | Description           |
| ----------------------- | --------- | --------------------- |
| `lambda.invocations`    | Counter   | Lambda invocations    |
| `lambda.duration`       | Histogram | Lambda execution time |
| `lambda.errors`         | Counter   | Lambda errors         |
| `sqs.messages.received` | Counter   | Messages received     |
| `sqs.messages.dlq`      | Counter   | Messages sent to DLQ  |
| `db.connections.active` | Gauge     | Active DB connections |
| `db.query.duration`     | Histogram | Query latency         |

### CloudWatch Metrics

```python
# src/infrastructure/metrics.py
import boto3
from datetime import datetime

cloudwatch = boto3.client('cloudwatch')

def put_metric(name: str, value: float, unit: str, dimensions: dict = None):
    cloudwatch.put_metric_data(
        Namespace='Nedlia',
        MetricData=[{
            'MetricName': name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.utcnow(),
            'Dimensions': [
                {'Name': k, 'Value': v}
                for k, v in (dimensions or {}).items()
            ],
        }]
    )

# Usage
put_metric(
    name='PlacementsCreated',
    value=1,
    unit='Count',
    dimensions={'Environment': 'production'}
)
```

### Embedded Metric Format (EMF)

For Lambda, use EMF for efficient metric publishing:

```python
# src/infrastructure/emf.py
import json

def emit_metric(name: str, value: float, unit: str, dimensions: dict):
    print(json.dumps({
        "_aws": {
            "Timestamp": int(datetime.utcnow().timestamp() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": "Nedlia",
                "Dimensions": [list(dimensions.keys())],
                "Metrics": [{"Name": name, "Unit": unit}]
            }]
        },
        **dimensions,
        name: value,
    }))
```

---

## Distributed Tracing

### AWS X-Ray Integration

```python
# src/infrastructure/tracing.py
from aws_xray_sdk.core import xray_recorder, patch_all

# Patch all supported libraries
patch_all()

# Configure X-Ray
xray_recorder.configure(
    service='nedlia-api',
    sampling=True,
    context_missing='LOG_ERROR',
)

# Create subsegments for custom operations
def create_placement(request):
    with xray_recorder.in_subsegment('create_placement') as subsegment:
        subsegment.put_annotation('video_id', request.video_id)
        subsegment.put_metadata('request', request.dict())

        placement = Placement.create(request)

        subsegment.put_annotation('placement_id', placement.id)
        return placement
```

### Trace Context Propagation

Pass trace context between services:

```python
# API → EventBridge → Worker
def publish_event(event: DomainEvent):
    trace_id = xray_recorder.current_segment().trace_id

    eventbridge.put_events(
        Entries=[{
            'Source': 'nedlia.api',
            'DetailType': event.type,
            'Detail': json.dumps({
                **event.data,
                '_trace_id': trace_id,  # Propagate trace
            }),
        }]
    )

# Worker receives and continues trace
def handle_event(sqs_event):
    for record in sqs_event['Records']:
        body = json.loads(record['body'])
        trace_id = body.get('_trace_id')

        # Continue trace
        xray_recorder.begin_segment(
            name='file-generator',
            traceid=trace_id,
        )
        # ... process
        xray_recorder.end_segment()
```

### Trace Sampling

```yaml
# xray-sampling-rules.json
{
  'version': 2,
  'rules':
    [
      {
        'description': 'Health checks - minimal sampling',
        'host': '*',
        'http_method': 'GET',
        'url_path': '/health',
        'fixed_target': 0,
        'rate': 0.01,
      },
      {
        'description': 'Default - 5% sampling',
        'host': '*',
        'http_method': '*',
        'url_path': '*',
        'fixed_target': 1,
        'rate': 0.05,
      },
    ],
}
```

---

## Alerting

### Alert Categories

| Category     | Severity | Response Time     | Example                               |
| ------------ | -------- | ----------------- | ------------------------------------- |
| **Critical** | P1       | 15 min            | Service down, data loss               |
| **High**     | P2       | 1 hour            | High error rate, degraded performance |
| **Medium**   | P3       | 4 hours           | Elevated latency, queue backlog       |
| **Low**      | P4       | Next business day | Warning thresholds, capacity planning |

### Key Alerts

```yaml
# alerts.yaml
alerts:
  # Critical
  - name: API Down
    condition: api.requests.total == 0 for 5 minutes
    severity: critical
    runbook: docs/runbooks/api-down.md

  - name: Database Connection Failed
    condition: db.connections.errors > 0
    severity: critical
    runbook: docs/runbooks/db-connection.md

  # High
  - name: High Error Rate
    condition: api.errors.total / api.requests.total > 0.05
    severity: high
    runbook: docs/runbooks/high-error-rate.md

  - name: High Latency
    condition: api.requests.duration.p99 > 5000
    severity: high
    runbook: docs/runbooks/high-latency.md

  # Medium
  - name: DLQ Messages
    condition: sqs.messages.dlq > 0
    severity: medium
    runbook: docs/runbooks/dlq-messages.md

  - name: Queue Backlog
    condition: sqs.messages.visible > 1000
    severity: medium
    runbook: docs/runbooks/queue-backlog.md
```

### CloudWatch Alarms

```hcl
# nedlia-IaC/modules/monitoring/alarms.tf
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "nedlia-${var.environment}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "High 5XX error rate"

  dimensions = {
    ApiName = "nedlia-api"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}
```

---

## Dashboards

### API Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Overview                              │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Requests/min    │ Error Rate      │ P99 Latency                 │
│     1,234       │     0.1%        │     245ms                   │
├─────────────────┴─────────────────┴─────────────────────────────┤
│                    Request Rate (last 24h)                       │
│  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄   │
├─────────────────────────────────────────────────────────────────┤
│                    Latency Distribution                          │
│  P50: 45ms  │  P90: 120ms  │  P99: 245ms  │  Max: 890ms        │
├─────────────────────────────────────────────────────────────────┤
│                    Top Endpoints by Request                      │
│  GET /placements         45%                                     │
│  POST /placements        25%                                     │
│  GET /videos             15%                                     │
│  POST /videos/validate   10%                                     │
│  Other                    5%                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Worker Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│                      Workers Overview                            │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Messages/min    │ DLQ Count       │ Avg Processing Time         │
│      567        │       0         │      1.2s                   │
├─────────────────┴─────────────────┴─────────────────────────────┤
│                    Queue Depth (last 24h)                        │
│  ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄   │
├─────────────────────────────────────────────────────────────────┤
│                    Worker Performance                            │
│  file-generator:  avg 0.8s  │  errors: 0                        │
│  validator:       avg 2.1s  │  errors: 0                        │
│  notifier:        avg 0.3s  │  errors: 0                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Runbooks

### Structure

```
docs/runbooks/
  api-down.md
  high-error-rate.md
  high-latency.md
  db-connection.md
  dlq-messages.md
  queue-backlog.md
```

### Runbook Template

````markdown
# Runbook: High Error Rate

## Alert

- **Name**: High Error Rate
- **Severity**: High (P2)
- **Condition**: Error rate > 5% for 5 minutes

## Impact

- Users may experience failed requests
- Data may not be saved

## Diagnosis

1. Check CloudWatch Logs for errors:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/nedlia-api \
     --filter-pattern "ERROR"
   ```
````

2. Check X-Ray for failing traces:

   - Open X-Ray console
   - Filter by `error = true`

3. Check downstream dependencies:
   - Database connectivity
   - S3 access
   - EventBridge publishing

## Resolution

### If database issue:

1. Check Aurora status in RDS console
2. Verify security group rules
3. Check connection pool exhaustion

### If S3 issue:

1. Verify bucket exists
2. Check IAM permissions
3. Verify bucket policy

### If EventBridge issue:

1. Check event bus exists
2. Verify IAM permissions
3. Check rule targets

## Escalation

- If unresolved after 30 minutes, escalate to on-call engineer
- Contact: #platform-oncall Slack channel

````

---

## Health Checks

### API Health Endpoint

```python
# src/interface/routes/health.py
@router.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "s3": await check_s3(),
        "eventbridge": await check_eventbridge(),
    }

    all_healthy = all(c["status"] == "healthy" for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }

async def check_database():
    try:
        await db.execute("SELECT 1")
        return {"status": "healthy", "latency_ms": 5}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
````

### Deep Health Check

```python
@router.get("/health/deep")
async def deep_health_check():
    """Full system check - use sparingly"""
    return {
        "database": {
            "status": "healthy",
            "connections": {"active": 5, "max": 20},
            "latency_ms": 5,
        },
        "s3": {
            "status": "healthy",
            "bucket": "nedlia-production",
        },
        "eventbridge": {
            "status": "healthy",
            "bus": "nedlia-events",
        },
        "sqs": {
            "file-generation-queue": {"messages": 12, "dlq": 0},
            "validation-queue": {"messages": 3, "dlq": 0},
        },
    }
```

---

## Related Documentation

- [Architecture](../ARCHITECTURE.md) – System overview
- [Resilience Patterns](resilience-patterns.md) – Error handling
- [Testing Strategy](testing-strategy.md) – Testing observability
