# Nedlia Microservices

Containerized domain-driven microservices deployed on AWS Fargate ECS.

## Services

| Service                 | Domain              | Purpose                             |
| ----------------------- | ------------------- | ----------------------------------- |
| `placement-service/`    | Placement Context   | Placement CRUD, file generation     |
| `validation-service/`   | Validation Context  | Video validation, compliance checks |
| `notification-service/` | Integration Context | Email, webhooks, push notifications |

## When to Use Fargate vs Lambda

| Criteria             | Lambda              | Fargate                      |
| -------------------- | ------------------- | ---------------------------- |
| Execution time       | < 15 minutes        | Long-running                 |
| Traffic pattern      | Sporadic, bursty    | Steady, predictable          |
| Connections          | Stateless HTTP      | WebSockets, gRPC, persistent |
| Cold start tolerance | Acceptable          | Not acceptable               |
| Memory/CPU           | Up to 10GB / 6 vCPU | Up to 120GB / 16 vCPU        |
| Cost model           | Per invocation      | Per hour (always-on)         |

## Architecture

```
                                    ┌─────────────────────────────────────┐
                                    │           ECS Cluster               │
┌─────────────┐     ┌─────────────┐ │  ┌─────────────────────────────────┐│
│   API GW    │────▶│     ALB     │─┼─▶│  Placement Service (Fargate)   ││
│  (Lambda)   │     │             │ │  │  - 2-10 tasks (auto-scaling)   ││
└─────────────┘     └─────────────┘ │  └─────────────────────────────────┘│
                          │         │  ┌─────────────────────────────────┐│
                          ├─────────┼─▶│  Validation Service (Fargate)  ││
                          │         │  │  - 1-5 tasks                    ││
                          │         │  └─────────────────────────────────┘│
                          │         │  ┌─────────────────────────────────┐│
                          └─────────┼─▶│  Notification Service (Fargate)││
                                    │  │  - 1-3 tasks                    ││
                                    │  └─────────────────────────────────┘│
                                    └─────────────────────────────────────┘
```

## Service Communication

### Synchronous (HTTP/gRPC)

```
API Gateway → ALB → Service
```

### Asynchronous (Events)

```
Service → EventBridge → SQS → Service/Worker
```

## Local Development

```bash
# Run all services
docker-compose up

# Run specific service
docker-compose up placement-service

# Build and run
docker-compose up --build
```

## Deployment

Services are deployed via Terraform + GitHub Actions:

```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
docker build -t $ECR_REPO/placement-service:$VERSION .
docker push $ECR_REPO/placement-service:$VERSION

# Deploy via Terraform
cd nedlia-IaC/environments/production
terragrunt apply -target=module.ecs
```

## Health Checks

All services expose:

- `GET /health/live` – Liveness (is process running?)
- `GET /health/ready` – Readiness (can handle requests?)

## Observability

- **Logs**: CloudWatch Logs via awslogs driver
- **Metrics**: CloudWatch Container Insights
- **Traces**: X-Ray daemon sidecar
