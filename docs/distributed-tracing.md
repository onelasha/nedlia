# Distributed Tracing with OpenTelemetry

End-to-end distributed tracing for Nedlia using **[OpenTelemetry](https://opentelemetry.io/)** — the industry standard for observability.

## Table of Contents

- [Overview](#overview)
- [Why OpenTelemetry?](#why-opentelemetry)
- [W3C Trace Context Standard](#w3c-trace-context-standard)
- [Installation](#installation)
- [Configuration](#configuration)
- [FastAPI Integration](#fastapi-integration)
- [Database Query Tracing](#database-query-tracing)
- [Lambda Worker Tracing](#lambda-worker-tracing)
- [SQS Message Trace Propagation](#sqs-message-trace-propagation)
- [Trace Visualization](#trace-visualization)
- [Sampling Strategies](#sampling-strategies)
- [Exporting to Backends](#exporting-to-backends)
- [Debugging Slow Queries](#debugging-slow-queries)
- [Best Practices](#best-practices)
- [Terraform Configuration](#terraform-configuration)
- [Related Documentation](#related-documentation)
- [References](#references)

---

## Overview

OpenTelemetry enables tracing requests across:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Complete Request Flow                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Client ──► API Gateway ──► FastAPI ──► PostgreSQL                          │
│                               │                                              │
│                               ▼                                              │
│                          EventBridge                                         │
│                               │                                              │
│                    ┌──────────┼──────────┐                                  │
│                    ▼          ▼          ▼                                  │
│               SQS Queue  SQS Queue  SQS Queue                               │
│                    │          │          │                                  │
│                    ▼          ▼          ▼                                  │
│               Lambda     Lambda     Lambda                                  │
│            (file-gen)  (validator) (notifier)                               │
│                    │          │          │                                  │
│                    ▼          ▼          ▼                                  │
│                   S3     PostgreSQL   External                              │
│                                        Service                              │
│                                                                              │
│  ════════════════════════════════════════════════════════════════════════   │
│  All connected by a single trace_id: 4bf92f3577b34da6a3ce929d0e0e4736      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why OpenTelemetry?

| Feature                 | AWS X-Ray Only    | OpenTelemetry                     |
| ----------------------- | ----------------- | --------------------------------- |
| **Vendor lock-in**      | AWS only          | Vendor-neutral                    |
| **Standards**           | Proprietary       | W3C Trace Context, OTLP           |
| **Instrumentation**     | Limited libraries | 100+ auto-instrumentations        |
| **Export destinations** | X-Ray only        | Any backend (Jaeger, Zipkin, etc) |
| **Database tracing**    | Basic             | Full query visibility             |
| **Community**           | AWS               | CNCF, broad industry support      |

---

## W3C Trace Context Standard

OpenTelemetry uses **[W3C Trace Context](https://www.w3.org/TR/trace-context/)** for trace propagation:

```http
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             │   │                                │                  │
             │   │                                │                  └─ Flags (sampled)
             │   │                                └─ Parent Span ID (16 hex)
             │   └─ Trace ID (32 hex) ─ Same across all services
             └─ Version
```

This header propagates through:

- HTTP requests between services
- SQS messages (via message attributes)
- EventBridge events (via detail)

---

## Installation

```bash
# Core OpenTelemetry
pip install opentelemetry-api opentelemetry-sdk

# Exporters
pip install opentelemetry-exporter-otlp  # For OTLP (Jaeger, Tempo, etc.)
pip install opentelemetry-exporter-aws-xray  # For AWS X-Ray

# Auto-instrumentation
pip install opentelemetry-instrumentation-fastapi
pip install opentelemetry-instrumentation-sqlalchemy
pip install opentelemetry-instrumentation-httpx
pip install opentelemetry-instrumentation-botocore
pip install opentelemetry-instrumentation-redis
pip install opentelemetry-instrumentation-logging
```

---

## Configuration

### Environment Variables

```bash
# Service identification
OTEL_SERVICE_NAME=nedlia-api
OTEL_SERVICE_VERSION=1.2.3
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production,service.namespace=nedlia

# Exporter configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc

# Sampling (production: sample 10% of traces)
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1

# Exclude health checks from tracing
OTEL_PYTHON_FASTAPI_EXCLUDED_URLS=health,health/ready,health/live
```

### Programmatic Setup

```python
# src/infrastructure/telemetry.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.aws import AwsXRayPropagator
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Instrumentation imports
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor


def configure_telemetry(
    service_name: str,
    service_version: str,
    environment: str,
    otlp_endpoint: str | None = None,
) -> None:
    """Configure OpenTelemetry with all instrumentations."""

    # Create resource with service info
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": environment,
        "service.namespace": "nedlia",
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set as global provider
    trace.set_tracer_provider(provider)

    # Configure propagators (W3C + X-Ray for AWS compatibility)
    set_global_textmap(CompositePropagator([
        TraceContextTextMapPropagator(),  # W3C standard
        AwsXRayPropagator(),              # AWS X-Ray compatibility
    ]))


def instrument_all(app=None, engine=None):
    """Apply all auto-instrumentations."""

    # FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health,health/ready,health/live",
        )

    # SQLAlchemy with query capture
    if engine:
        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            enable_commenter=True,  # Add trace context to SQL comments
        )

    # HTTP clients
    HTTPXClientInstrumentor().instrument()

    # AWS SDK (boto3)
    BotocoreInstrumentor().instrument()

    # Redis
    RedisInstrumentor().instrument()
```

---

## FastAPI Integration

### Main Application Setup

```python
# src/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.infrastructure.telemetry import configure_telemetry, instrument_all
from src.infrastructure.database import engine
from src.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure telemetry on startup
    configure_telemetry(
        service_name="nedlia-api",
        service_version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        otlp_endpoint=settings.OTLP_ENDPOINT,
    )
    instrument_all(app=app, engine=engine)

    yield

    # Cleanup on shutdown
    trace.get_tracer_provider().shutdown()


app = FastAPI(
    title="Nedlia API",
    lifespan=lifespan,
)
```

### Custom Spans

```python
# src/placements/service.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class PlacementService:
    async def create(self, data: PlacementCreate) -> Placement:
        # Create custom span for business logic
        with tracer.start_as_current_span(
            "placement.create",
            attributes={
                "placement.video_id": str(data.video_id),
                "placement.product_id": str(data.product_id),
            }
        ) as span:
            # Validate video exists
            with tracer.start_as_current_span("placement.validate_video"):
                video = await self.video_repo.find_by_id(data.video_id)
                if not video:
                    span.set_status(trace.StatusCode.ERROR, "Video not found")
                    raise VideoNotFoundException(resource_id=str(data.video_id))

            # Check for overlaps
            with tracer.start_as_current_span("placement.check_overlaps"):
                existing = await self.repo.find_overlapping(
                    video_id=data.video_id,
                    start_time=data.start_time,
                    end_time=data.end_time,
                )
                if existing:
                    span.set_status(trace.StatusCode.ERROR, "Overlap detected")
                    raise PlacementOverlapException(
                        existing_placement_id=existing.id,
                    )

            # Create placement
            placement = await self.repo.save(Placement(**data.model_dump()))

            # Add result to span
            span.set_attribute("placement.id", str(placement.id))
            span.set_status(trace.StatusCode.OK)

            return placement
```

---

## Database Query Tracing

### SQLAlchemy Instrumentation

OpenTelemetry automatically traces all database queries:

```python
# Automatic span created for each query:
# Name: "SELECT nedlia.placements"
# Attributes:
#   db.system: postgresql
#   db.name: nedlia
#   db.statement: SELECT * FROM placements WHERE video_id = $1
#   db.operation: SELECT
#   db.sql.table: placements
```

### SQL Commenter (Trace Context in Queries)

Enable SQL commenter to add trace context to queries:

```python
SQLAlchemyInstrumentor().instrument(
    engine=engine,
    enable_commenter=True,
)
```

Your queries will include trace context:

```sql
SELECT * FROM placements WHERE video_id = '123'
/*traceparent='00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01'*/
```

**Benefits**:

- Correlate slow queries in database logs with traces
- Debug N+1 queries by seeing all queries in a trace
- Identify which request caused a slow query

### Query Performance Analysis

```python
# src/infrastructure/database.py
from opentelemetry import trace
from sqlalchemy import event
from sqlalchemy.engine import Engine
import time

tracer = trace.get_tracer(__name__)


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time = time.perf_counter() - conn.info["query_start_time"].pop()

    # Get current span
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("db.query.duration_ms", total_time * 1000)

        # Flag slow queries
        if total_time > 0.1:  # 100ms threshold
            span.set_attribute("db.query.slow", True)
            span.add_event("slow_query", {
                "duration_ms": total_time * 1000,
                "statement": statement[:500],  # Truncate long queries
            })
```

---

## Lambda Worker Tracing

### Handler with Trace Propagation

```python
# src/handlers/file_generator.py
import json
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind

from src.infrastructure.telemetry import configure_telemetry

# Configure on cold start
configure_telemetry(
    service_name="nedlia-file-generator",
    service_version="1.0.0",
    environment=os.environ.get("ENVIRONMENT", "development"),
    otlp_endpoint=os.environ.get("OTLP_ENDPOINT"),
)

tracer = trace.get_tracer(__name__)


def handler(event: dict, context) -> dict:
    """SQS Lambda handler with distributed tracing."""
    batch_item_failures = []

    for record in event.get("Records", []):
        message_id = record["messageId"]

        # Extract trace context from SQS message attributes
        carrier = {}
        if "messageAttributes" in record:
            attrs = record["messageAttributes"]
            if "traceparent" in attrs:
                carrier["traceparent"] = attrs["traceparent"]["stringValue"]
            if "tracestate" in attrs:
                carrier["tracestate"] = attrs["tracestate"]["stringValue"]

        # Continue the distributed trace
        ctx = extract(carrier)

        with tracer.start_as_current_span(
            "file_generator.process_message",
            context=ctx,
            kind=SpanKind.CONSUMER,
            attributes={
                "messaging.system": "aws_sqs",
                "messaging.message_id": message_id,
                "messaging.destination": record.get("eventSourceARN", ""),
            }
        ) as span:
            try:
                body = json.loads(record["body"])
                detail = body.get("detail", body)

                placement_id = detail["placement_id"]
                span.set_attribute("placement.id", placement_id)

                # Process with child spans
                with tracer.start_as_current_span("file_generator.generate"):
                    generate_placement_file(placement_id)

                with tracer.start_as_current_span("file_generator.upload_s3"):
                    upload_to_s3(placement_id)

                span.set_status(trace.StatusCode.OK)

            except Exception as e:
                span.set_status(trace.StatusCode.ERROR, str(e))
                span.record_exception(e)
                batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
```

### Publishing Events with Trace Context

```python
# src/infrastructure/events.py
import json
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer(__name__)


async def publish_event(event_type: str, detail: dict) -> None:
    """Publish event to EventBridge with trace context."""

    with tracer.start_as_current_span(
        f"eventbridge.publish.{event_type}",
        kind=SpanKind.PRODUCER,
        attributes={
            "messaging.system": "aws_eventbridge",
            "messaging.destination": "nedlia-events",
            "messaging.operation": "publish",
        }
    ) as span:
        # Inject trace context into event detail
        carrier = {}
        inject(carrier)

        event_detail = {
            **detail,
            "_trace": carrier,  # Propagate trace context
        }

        await eventbridge.put_events(
            Entries=[{
                "Source": "nedlia.api",
                "DetailType": event_type,
                "Detail": json.dumps(event_detail),
                "EventBusName": "nedlia-events",
            }]
        )

        span.set_attribute("event.id", detail.get("id", ""))
```

---

## SQS Message Trace Propagation

### Sending Messages with Trace Context

```python
# src/infrastructure/sqs.py
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind

tracer = trace.get_tracer(__name__)


async def send_message(queue_url: str, body: dict) -> None:
    """Send SQS message with trace context."""

    with tracer.start_as_current_span(
        "sqs.send_message",
        kind=SpanKind.PRODUCER,
        attributes={
            "messaging.system": "aws_sqs",
            "messaging.destination": queue_url,
        }
    ):
        # Inject trace context into message attributes
        carrier = {}
        inject(carrier)

        message_attributes = {
            "traceparent": {
                "DataType": "String",
                "StringValue": carrier.get("traceparent", ""),
            },
        }
        if "tracestate" in carrier:
            message_attributes["tracestate"] = {
                "DataType": "String",
                "StringValue": carrier["tracestate"],
            }

        await sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(body),
            MessageAttributes=message_attributes,
        )
```

---

## Trace Visualization

### What You'll See in Your Tracing Backend

```
Trace: 4bf92f3577b34da6a3ce929d0e0e4736
Duration: 1.2s

├─ POST /v1/placements (245ms) [nedlia-api]
│  ├─ placement.create (240ms)
│  │  ├─ placement.validate_video (15ms)
│  │  │  └─ SELECT nedlia.videos (12ms) [postgresql]
│  │  │     db.statement: SELECT * FROM videos WHERE id = $1
│  │  │
│  │  ├─ placement.check_overlaps (8ms)
│  │  │  └─ SELECT nedlia.placements (6ms) [postgresql]
│  │  │     db.statement: SELECT * FROM placements WHERE video_id = $1 AND ...
│  │  │
│  │  └─ INSERT nedlia.placements (45ms) [postgresql]
│  │     db.statement: INSERT INTO placements (...) VALUES (...)
│  │
│  └─ eventbridge.publish.placement.created (12ms)
│
├─ [async] file_generator.process_message (850ms) [nedlia-file-generator]
│  ├─ file_generator.generate (600ms)
│  │  ├─ SELECT nedlia.placements (5ms) [postgresql]
│  │  ├─ SELECT nedlia.products (3ms) [postgresql]
│  │  └─ render_template (580ms)
│  │
│  └─ file_generator.upload_s3 (200ms)
│     └─ S3.PutObject (195ms) [aws.s3]
│
└─ [async] notifier.send_notification (150ms) [nedlia-notifier]
   └─ HTTP POST external-service.com/webhook (145ms)
```

---

## Sampling Strategies

### Production Sampling

```python
# src/infrastructure/telemetry.py
from opentelemetry.sdk.trace.sampling import (
    ParentBasedTraceIdRatio,
    TraceIdRatioBased,
    ALWAYS_ON,
    ALWAYS_OFF,
)


def get_sampler(environment: str, sample_rate: float = 0.1):
    """Get appropriate sampler for environment."""

    if environment == "development":
        return ALWAYS_ON  # Trace everything in dev

    if environment == "production":
        # Sample 10% of traces, but always sample if parent is sampled
        return ParentBasedTraceIdRatio(sample_rate)

    return TraceIdRatioBased(sample_rate)
```

### Custom Sampling Rules

```python
from opentelemetry.sdk.trace.sampling import Sampler, SamplingResult, Decision

class CustomSampler(Sampler):
    """Custom sampler with business logic."""

    def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
        # Always sample errors
        if attributes and attributes.get("error"):
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Always sample slow requests (if we know ahead of time)
        if attributes and attributes.get("expected_slow"):
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        # Sample 10% of normal requests
        if trace_id % 10 == 0:
            return SamplingResult(Decision.RECORD_AND_SAMPLE)

        return SamplingResult(Decision.DROP)

    def get_description(self):
        return "CustomSampler"
```

---

## Exporting to Backends

### AWS X-Ray

```python
from opentelemetry.exporter.aws.xray import AwsXRaySpanExporter

provider.add_span_processor(
    BatchSpanProcessor(AwsXRaySpanExporter())
)
```

### Jaeger

```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

provider.add_span_processor(
    BatchSpanProcessor(JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831,
    ))
)
```

### OTLP (Grafana Tempo, etc.)

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(
        endpoint="http://otel-collector:4317",
    ))
)
```

### Multiple Exporters

```python
# Export to both X-Ray and Jaeger
provider.add_span_processor(BatchSpanProcessor(AwsXRaySpanExporter()))
provider.add_span_processor(BatchSpanProcessor(JaegerExporter()))
```

---

## Debugging Slow Queries

### Finding N+1 Queries

In your trace, look for patterns like:

```
├─ GET /v1/videos (500ms)
│  ├─ SELECT videos (10ms)
│  ├─ SELECT placements WHERE video_id = 1 (5ms)  ← N+1!
│  ├─ SELECT placements WHERE video_id = 2 (5ms)  ← N+1!
│  ├─ SELECT placements WHERE video_id = 3 (5ms)  ← N+1!
│  └─ ... (100 more queries)
```

**Fix**: Use eager loading or batch queries.

### Identifying Slow Queries

```python
# Add slow query detection
@event.listens_for(Engine, "after_cursor_execute")
def log_slow_queries(conn, cursor, statement, parameters, context, executemany):
    duration = time.perf_counter() - conn.info["query_start_time"].pop()

    if duration > 0.1:  # 100ms
        span = trace.get_current_span()
        span.add_event("slow_query_detected", {
            "duration_ms": duration * 1000,
            "statement": statement[:1000],
            "suggestion": "Consider adding an index or optimizing the query",
        })
```

### Query Analysis Dashboard

Create alerts for:

- Queries > 100ms
- More than 10 queries per request
- Missing index warnings

---

## Best Practices

### Span Naming

```python
# ✅ Good - Descriptive, hierarchical
tracer.start_as_current_span("placement.create")
tracer.start_as_current_span("placement.validate_video")
tracer.start_as_current_span("s3.upload_file")

# ❌ Bad - Too generic
tracer.start_as_current_span("process")
tracer.start_as_current_span("do_thing")
```

### Attributes

```python
# ✅ Good - Useful for filtering and debugging
span.set_attribute("placement.id", str(placement_id))
span.set_attribute("placement.video_id", str(video_id))
span.set_attribute("user.id", str(user_id))

# ❌ Bad - Sensitive data
span.set_attribute("user.email", user.email)
span.set_attribute("api.key", api_key)
```

### Error Recording

```python
try:
    result = await process()
except Exception as e:
    span.set_status(trace.StatusCode.ERROR, str(e))
    span.record_exception(e)  # Captures stack trace
    raise
```

---

## Terraform Configuration

### OpenTelemetry Collector on ECS

```hcl
# nedlia-IaC/modules/observability/otel-collector.tf
resource "aws_ecs_task_definition" "otel_collector" {
  family                   = "otel-collector"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512

  container_definitions = jsonencode([{
    name  = "otel-collector"
    image = "otel/opentelemetry-collector-contrib:latest"

    portMappings = [
      { containerPort = 4317, protocol = "tcp" },  # OTLP gRPC
      { containerPort = 4318, protocol = "tcp" },  # OTLP HTTP
    ]

    environment = [
      { name = "AWS_REGION", value = var.aws_region }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/otel-collector"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "otel"
      }
    }
  }])
}
```

---

## Related Documentation

- [Observability](observability.md) – Logging, metrics, alerting
- [Error Handling](error-handling.md) – Exception tracing
- [Resilience Patterns](resilience-patterns.md) – Retry and circuit breaker tracing
- [API Standards](api-standards.md) – Request correlation

## References

- [OpenTelemetry](https://opentelemetry.io/) – Official documentation
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) – Standard specification
- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/) – Python SDK
- [OpenTelemetry Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/) – Attribute naming
- [SQLCommenter](https://google.github.io/sqlcommenter/) – SQL trace context
