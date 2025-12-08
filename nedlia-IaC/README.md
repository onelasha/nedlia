# Nedlia Infrastructure as Code

Terraform + Terragrunt configuration for Nedlia AWS infrastructure.

## Structure

```text
nedlia-IaC/
  terragrunt.hcl              # Root config (backend, provider)
  environments/
    dev/                      # Development environment
    testing/                  # Testing/CI environment
    staging/                  # Pre-production
    production/               # Production
  modules/
    vpc/                      # VPC, subnets, security groups
    aurora/                   # Aurora Serverless v2 (PostgreSQL)
    lambda/                   # Lambda functions
    api-gateway/              # API Gateway
    eventbridge/              # EventBridge event bus
    sqs/                      # SQS queues with DLQ
    cognito/                  # Cognito user pools
    s3/                       # S3 buckets
```

## Prerequisites

- Terraform >= 1.5.0
- Terragrunt >= 0.50.0
- AWS CLI configured with appropriate credentials

## Usage

### Initialize

```bash
cd environments/dev
terragrunt init
```

### Plan

```bash
terragrunt plan
```

### Apply

```bash
terragrunt apply
```

### Apply all modules in an environment

```bash
cd environments/dev
terragrunt run-all apply
```

## Environment Configuration

Each environment has:

- `env.hcl` – Environment-specific variables (capacity, memory, timeouts)
- `terragrunt.hcl` – Inherits root config and passes env vars

## Remote State

State is stored in S3 with DynamoDB locking:

- Bucket: `nedlia-terraform-state`
- Lock table: `nedlia-terraform-locks`

Create these manually before first run, or use a bootstrap script.

## Modules

| Module        | Description                             |
| ------------- | --------------------------------------- |
| `vpc`         | VPC with public/private subnets         |
| `aurora`      | Aurora Serverless v2 PostgreSQL cluster |
| `lambda`      | Lambda function with IAM role and X-Ray |
| `api-gateway` | REST API Gateway with stages            |
| `eventbridge` | Event bus with schema discovery         |
| `sqs`         | SQS queue with dead-letter queue        |
| `cognito`     | User pool and app client                |
| `s3`          | Encrypted, versioned S3 bucket          |
