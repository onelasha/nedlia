# ADR-007: Fargate for Domain Microservices

## Status

Accepted

## Context

Nedlia's backend needs to support different workload patterns:

1. **API Gateway requests**: Short-lived, stateless HTTP requests
2. **Event-driven workers**: Triggered by SQS/EventBridge events
3. **Domain microservices**: Long-running, stateful, complex domain logic

Initially, we planned to use Lambda for everything. However, some workloads don't fit Lambda's constraints:

- **Cold starts**: Unacceptable for latency-sensitive operations
- **Execution limits**: 15-minute max, 10GB memory
- **Connection pooling**: Difficult with Lambda's ephemeral nature
- **WebSocket/gRPC**: Not natively supported

## Decision

We adopt a **hybrid compute strategy**:

| Workload             | Compute | Rationale                        |
| -------------------- | ------- | -------------------------------- |
| API Gateway          | Lambda  | Low traffic, pay-per-request     |
| Event workers        | Lambda  | Event-driven, sporadic           |
| Domain microservices | Fargate | Long-running, connection pooling |

### Fargate Configuration

```hcl
# ECS Service definition
resource "aws_ecs_service" "placement_service" {
  name            = "placement-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.placement.arn
  desired_count   = 2

  capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight            = 80
  }
  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 20  # Base capacity for reliability
  }

  deployment_configuration {
    minimum_healthy_percent = 50
    maximum_percent         = 200
  }
}
```

### Task Definition

```hcl
resource "aws_ecs_task_definition" "placement" {
  family                   = "placement-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512   # 0.5 vCPU
  memory                   = 1024  # 1 GB

  container_definitions = jsonencode([
    {
      name  = "placement-service"
      image = "${aws_ecr_repository.placement.repository_url}:latest"
      portMappings = [{
        containerPort = 8000
        protocol      = "tcp"
      }]
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health/live || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/placement-service"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}
```

### Auto-Scaling

```hcl
resource "aws_appautoscaling_target" "placement" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.placement.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "placement_cpu" {
  name               = "placement-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.placement.resource_id
  scalable_dimension = aws_appautoscaling_target.placement.scalable_dimension
  service_namespace  = aws_appautoscaling_target.placement.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

## Decision Criteria

### Use Lambda When

- ✅ Execution time < 15 minutes
- ✅ Sporadic or unpredictable traffic
- ✅ Stateless operations
- ✅ Event-driven (SQS, EventBridge, S3)
- ✅ Cost optimization for low traffic
- ✅ Simple HTTP request/response

### Use Fargate When

- ✅ Long-running processes
- ✅ Steady, predictable traffic
- ✅ Connection pooling required (database, Redis)
- ✅ WebSocket or gRPC connections
- ✅ Complex domain logic with high memory
- ✅ Cold start latency unacceptable
- ✅ Need more than 10GB memory or 6 vCPU

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Cloud                                       │
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────┐│
│  │   Route 53  │────▶│ CloudFront  │────▶│         API Gateway             ││
│  └─────────────┘     └─────────────┘     │  (REST API - Lambda Proxy)      ││
│                                          └──────────────┬──────────────────┘│
│                                                         │                   │
│                                                         ▼                   │
│  ┌──────────────────────────────────────────────────────────────────────────┤
│  │                        VPC                                               │
│  │  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  │                    Private Subnets                                   ││
│  │  │                                                                      ││
│  │  │  ┌─────────────┐     ┌─────────────────────────────────────────────┐││
│  │  │  │   Lambda    │     │              ECS Cluster (Fargate)          │││
│  │  │  │   (API)     │     │  ┌───────────┐ ┌───────────┐ ┌───────────┐  │││
│  │  │  └──────┬──────┘     │  │ Placement │ │Validation │ │  Notif.   │  │││
│  │  │         │            │  │  Service  │ │  Service  │ │  Service  │  │││
│  │  │         │            │  │  (2-10)   │ │  (1-5)    │ │  (1-3)    │  │││
│  │  │         │            │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘  │││
│  │  │         │            └────────┼─────────────┼─────────────┼────────┘││
│  │  │         │                     │             │             │         ││
│  │  │         ▼                     ▼             ▼             ▼         ││
│  │  │  ┌─────────────────────────────────────────────────────────────────┐││
│  │  │  │                    Internal ALB                                 │││
│  │  │  └─────────────────────────────────────────────────────────────────┘││
│  │  │                                                                      ││
│  │  └──────────────────────────────────────────────────────────────────────┘│
│  │  ┌──────────────────────────────────────────────────────────────────────┐│
│  │  │                    Database Subnets                                  ││
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐            ││
│  │  │  │    Aurora     │  │  ElastiCache  │  │      S3       │            ││
│  │  │  │  (PostgreSQL) │  │    (Redis)    │  │   (Storage)   │            ││
│  │  │  └───────────────┘  └───────────────┘  └───────────────┘            ││
│  │  └──────────────────────────────────────────────────────────────────────┘│
│  └──────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│  │ EventBridge │────▶│     SQS     │────▶│   Lambda    │                   │
│  │   (Events)  │     │  (Queues)   │     │  (Workers)  │                   │
│  └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Service Communication

### Synchronous (Service-to-Service)

```python
# Via internal ALB
async def call_validation_service(video_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://internal-alb.nedlia.local/validation/validate",
            json={"video_id": video_id},
            timeout=30.0,
        )
        return response.json()
```

### Asynchronous (Event-Driven)

```python
# Via EventBridge
async def publish_placement_created(placement: Placement):
    await eventbridge.put_events(
        Entries=[{
            "Source": "nedlia.placement-service",
            "DetailType": "placement.created",
            "Detail": json.dumps(placement.to_event()),
            "EventBusName": "nedlia-events",
        }]
    )
```

## Consequences

### Positive

- **No cold starts**: Services always warm
- **Connection pooling**: Efficient database/Redis usage
- **Predictable latency**: Consistent response times
- **Flexible scaling**: Scale based on CPU/memory/custom metrics
- **Full container control**: Any runtime, any dependencies

### Negative

- **Higher base cost**: Pay even when idle (mitigated by Fargate Spot)
- **More infrastructure**: ECS cluster, ALB, service discovery
- **Deployment complexity**: Docker builds, ECR, rolling updates
- **Operational overhead**: Container monitoring, log aggregation

### Mitigations

1. **Cost**: Use Fargate Spot (up to 70% savings) with on-demand base
2. **Complexity**: Terraform modules for consistent deployments
3. **Monitoring**: Container Insights + X-Ray sidecar
4. **Deployments**: Blue/green via CodeDeploy

## Related Documentation

- [Architecture](../../ARCHITECTURE.md) – System overview
- [ADR-002: AWS Serverless](002-aws-serverless.md) – Lambda decisions
- [Resilience Patterns](../resilience-patterns.md) – Service resilience
