# Deployment Orchestration

Multi-team deployment strategy for Nedlia's monorepo architecture.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Nedlia Monorepo                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Team API   │  │Team Workers │  │Team Portal  │  │ Team Infra  │        │
│  │             │  │             │  │             │  │             │        │
│  │ api/        │  │ workers/    │  │ portal/     │  │ IaC/        │        │
│  │ services/   │  │             │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │               │
│         ▼                ▼                ▼                ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CI/CD Pipeline (GitHub Actions)                   │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │   │
│  │  │ Detect  │─▶│  Build  │─▶│  Test   │─▶│ Deploy  │─▶│ Verify  │   │   │
│  │  │ Changes │  │         │  │         │  │         │  │         │   │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Principles

1. **Independent Deployability**: Each service can be deployed without affecting others
2. **Affected-Only Builds**: Only build/deploy what changed
3. **Environment Promotion**: Dev → Staging → Production
4. **Rollback Capability**: Quick rollback on failure
5. **Feature Flags**: Decouple deployment from release

---

## Team Ownership

### CODEOWNERS

```
# .github/CODEOWNERS

# Infrastructure - Platform Team
/nedlia-IaC/                    @nedlia/platform-team
/.github/workflows/             @nedlia/platform-team

# Backend API - API Team
/nedlia-back-end/api/           @nedlia/api-team
/nedlia-back-end/shared/        @nedlia/api-team @nedlia/workers-team

# Workers - Workers Team
/nedlia-back-end/workers/       @nedlia/workers-team

# Microservices - Service Teams
/nedlia-back-end/services/placement-service/    @nedlia/placement-team
/nedlia-back-end/services/validation-service/   @nedlia/validation-team
/nedlia-back-end/services/notification-service/ @nedlia/notification-team

# Frontend - Portal Team
/nedlia-front-end/portal/       @nedlia/portal-team

# SDKs - SDK Team
/nedlia-sdk/                    @nedlia/sdk-team

# Plugins - Plugin Team
/nedlia-plugin/                 @nedlia/plugin-team

# Shared Documentation
/docs/                          @nedlia/platform-team
/ARCHITECTURE.md                @nedlia/platform-team @nedlia/tech-leads
```

### Team Responsibilities

| Team             | Components               | Deploy Frequency |
| ---------------- | ------------------------ | ---------------- |
| **Platform**     | IaC, CI/CD, shared infra | Weekly           |
| **API**          | API Gateway, Lambda API  | Daily            |
| **Workers**      | Event workers, queues    | Daily            |
| **Placement**    | Placement service        | Daily            |
| **Validation**   | Validation service       | Daily            |
| **Notification** | Notification service     | Weekly           |
| **Portal**       | Web portal               | Daily            |
| **SDK**          | JS, Python, Swift SDKs   | Bi-weekly        |
| **Plugin**       | Video editor plugins     | Monthly          |

---

## Change Detection

### Path-Based Triggers

```yaml
# .github/workflows/ci.yml
on:
  push:
    branches: [main]
    paths:
      - 'nedlia-back-end/api/**'
      - 'nedlia-back-end/shared/**' # Shared affects API
  pull_request:
    paths:
      - 'nedlia-back-end/api/**'
      - 'nedlia-back-end/shared/**'
```

### Affected Services Detection

```yaml
# .github/workflows/detect-changes.yml
name: Detect Changes

on:
  push:
    branches: [main]
  pull_request:

jobs:
  detect:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.changes.outputs.api }}
      workers: ${{ steps.changes.outputs.workers }}
      placement-service: ${{ steps.changes.outputs.placement-service }}
      validation-service: ${{ steps.changes.outputs.validation-service }}
      notification-service: ${{ steps.changes.outputs.notification-service }}
      portal: ${{ steps.changes.outputs.portal }}
      infrastructure: ${{ steps.changes.outputs.infrastructure }}
      shared: ${{ steps.changes.outputs.shared }}

    steps:
      - uses: actions/checkout@v4

      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            api:
              - 'nedlia-back-end/api/**'
              - 'nedlia-back-end/shared/**'
            workers:
              - 'nedlia-back-end/workers/**'
              - 'nedlia-back-end/shared/**'
            placement-service:
              - 'nedlia-back-end/services/placement-service/**'
              - 'nedlia-back-end/shared/**'
            validation-service:
              - 'nedlia-back-end/services/validation-service/**'
              - 'nedlia-back-end/shared/**'
            notification-service:
              - 'nedlia-back-end/services/notification-service/**'
              - 'nedlia-back-end/shared/**'
            portal:
              - 'nedlia-front-end/portal/**'
            infrastructure:
              - 'nedlia-IaC/**'
            shared:
              - 'nedlia-back-end/shared/**'
```

---

## Deployment Pipeline

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Deployment Pipeline                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PR Merged to Main                                                          │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                           │
│  │   Detect    │                                                           │
│  │   Changes   │                                                           │
│  └──────┬──────┘                                                           │
│         │                                                                   │
│         ├──────────────┬──────────────┬──────────────┬──────────────┐      │
│         ▼              ▼              ▼              ▼              ▼      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐│
│  │    API    │  │  Workers  │  │ Placement │  │  Portal   │  │    IaC    ││
│  │  Changed? │  │  Changed? │  │  Changed? │  │  Changed? │  │  Changed? ││
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘│
│        │              │              │              │              │       │
│        ▼              ▼              ▼              ▼              ▼       │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                         Build & Test (Parallel)                        ││
│  └───────────────────────────────────────────────────────────────────────┘│
│        │              │              │              │              │       │
│        ▼              ▼              ▼              ▼              ▼       │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                      Deploy to Staging (Parallel)                      ││
│  └───────────────────────────────────────────────────────────────────────┘│
│        │              │              │              │              │       │
│        ▼              ▼              ▼              ▼              ▼       │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                    Integration Tests (Sequential)                      ││
│  └───────────────────────────────────────────────────────────────────────┘│
│        │                                                                   │
│        ▼                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                     Manual Approval (Production)                       ││
│  └───────────────────────────────────────────────────────────────────────┘│
│        │                                                                   │
│        ▼                                                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐│
│  │                    Deploy to Production (Canary)                       ││
│  └───────────────────────────────────────────────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Main Deployment Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production
      services:
        description: 'Services to deploy (comma-separated, or "all")'
        required: false
        default: 'all'

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false

jobs:
  # =========================================================================
  # Detect Changes
  # =========================================================================
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      api: ${{ steps.changes.outputs.api }}
      workers: ${{ steps.changes.outputs.workers }}
      placement-service: ${{ steps.changes.outputs.placement-service }}
      validation-service: ${{ steps.changes.outputs.validation-service }}
      notification-service: ${{ steps.changes.outputs.notification-service }}
      portal: ${{ steps.changes.outputs.portal }}
      infrastructure: ${{ steps.changes.outputs.infrastructure }}
      matrix: ${{ steps.matrix.outputs.matrix }}

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2

      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            api:
              - 'nedlia-back-end/api/**'
              - 'nedlia-back-end/shared/**'
            workers:
              - 'nedlia-back-end/workers/**'
              - 'nedlia-back-end/shared/**'
            placement-service:
              - 'nedlia-back-end/services/placement-service/**'
              - 'nedlia-back-end/shared/**'
            validation-service:
              - 'nedlia-back-end/services/validation-service/**'
              - 'nedlia-back-end/shared/**'
            notification-service:
              - 'nedlia-back-end/services/notification-service/**'
              - 'nedlia-back-end/shared/**'
            portal:
              - 'nedlia-front-end/portal/**'
            infrastructure:
              - 'nedlia-IaC/**'

      - name: Build deployment matrix
        id: matrix
        run: |
          SERVICES=()
          if [[ "${{ steps.changes.outputs.api }}" == "true" ]]; then
            SERVICES+=('{"name":"api","path":"nedlia-back-end/api","type":"lambda"}')
          fi
          if [[ "${{ steps.changes.outputs.workers }}" == "true" ]]; then
            SERVICES+=('{"name":"workers","path":"nedlia-back-end/workers","type":"lambda"}')
          fi
          if [[ "${{ steps.changes.outputs.placement-service }}" == "true" ]]; then
            SERVICES+=('{"name":"placement-service","path":"nedlia-back-end/services/placement-service","type":"fargate"}')
          fi
          if [[ "${{ steps.changes.outputs.validation-service }}" == "true" ]]; then
            SERVICES+=('{"name":"validation-service","path":"nedlia-back-end/services/validation-service","type":"fargate"}')
          fi
          if [[ "${{ steps.changes.outputs.notification-service }}" == "true" ]]; then
            SERVICES+=('{"name":"notification-service","path":"nedlia-back-end/services/notification-service","type":"fargate"}')
          fi
          if [[ "${{ steps.changes.outputs.portal }}" == "true" ]]; then
            SERVICES+=('{"name":"portal","path":"nedlia-front-end/portal","type":"cloudfront"}')
          fi

          if [[ ${#SERVICES[@]} -eq 0 ]]; then
            echo "matrix={\"include\":[]}" >> $GITHUB_OUTPUT
          else
            MATRIX=$(printf '%s,' "${SERVICES[@]}" | sed 's/,$//')
            echo "matrix={\"include\":[$MATRIX]}" >> $GITHUB_OUTPUT
          fi

  # =========================================================================
  # Build Services
  # =========================================================================
  build:
    needs: detect-changes
    if: needs.detect-changes.outputs.matrix != '{"include":[]}'
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
      fail-fast: false

    steps:
      - uses: actions/checkout@v4

      - name: Build Lambda
        if: matrix.type == 'lambda'
        run: |
          cd ${{ matrix.path }}
          # Build Lambda package
          pip install -t package .
          cd package && zip -r ../deployment.zip .
          cd .. && zip deployment.zip -u *.py

      - name: Build Docker (Fargate)
        if: matrix.type == 'fargate'
        run: |
          cd ${{ matrix.path }}
          docker build -t ${{ matrix.name }}:${{ github.sha }} .

      - name: Build Frontend
        if: matrix.type == 'cloudfront'
        run: |
          cd ${{ matrix.path }}
          pnpm install
          pnpm build

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.name }}-build
          path: |
            ${{ matrix.path }}/deployment.zip
            ${{ matrix.path }}/dist/
          retention-days: 1

  # =========================================================================
  # Deploy to Staging
  # =========================================================================
  deploy-staging:
    needs: [detect-changes, build]
    runs-on: ubuntu-latest
    environment: staging
    strategy:
      matrix: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
      max-parallel: 3

    steps:
      - uses: actions/checkout@v4

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: ${{ matrix.name }}-build

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy Lambda
        if: matrix.type == 'lambda'
        run: |
          aws lambda update-function-code \
            --function-name nedlia-staging-${{ matrix.name }} \
            --zip-file fileb://deployment.zip

      - name: Deploy Fargate
        if: matrix.type == 'fargate'
        run: |
          # Push to ECR
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_REPO
          docker tag ${{ matrix.name }}:${{ github.sha }} $ECR_REPO/${{ matrix.name }}:${{ github.sha }}
          docker push $ECR_REPO/${{ matrix.name }}:${{ github.sha }}

          # Update ECS service
          aws ecs update-service \
            --cluster nedlia-staging \
            --service ${{ matrix.name }} \
            --force-new-deployment

      - name: Deploy CloudFront
        if: matrix.type == 'cloudfront'
        run: |
          aws s3 sync dist/ s3://nedlia-staging-portal --delete
          aws cloudfront create-invalidation \
            --distribution-id ${{ secrets.STAGING_CF_DISTRIBUTION }} \
            --paths "/*"

  # =========================================================================
  # Integration Tests
  # =========================================================================
  integration-tests:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run integration tests
        run: |
          cd tests/integration
          npm install
          npm test
        env:
          BASE_URL: https://api.staging.nedlia.com

      - name: Run smoke tests
        run: |
          curl -f https://api.staging.nedlia.com/health || exit 1

  # =========================================================================
  # Deploy to Production (Manual Approval)
  # =========================================================================
  deploy-production:
    needs: [detect-changes, integration-tests]
    runs-on: ubuntu-latest
    environment: production # Requires manual approval
    strategy:
      matrix: ${{ fromJson(needs.detect-changes.outputs.matrix) }}
      max-parallel: 1 # Deploy one at a time for safety

    steps:
      - uses: actions/checkout@v4

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: ${{ matrix.name }}-build

      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID_PROD }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY_PROD }}
          aws-region: us-east-1

      - name: Deploy with Canary
        run: |
          # Canary deployment logic
          echo "Deploying ${{ matrix.name }} to production with canary..."
          # Implementation depends on service type

      - name: Verify deployment
        run: |
          # Health check
          curl -f https://api.nedlia.com/health || exit 1

      - name: Notify Slack
        if: always()
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Deployment ${{ job.status }}: ${{ matrix.name }} to production",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*${{ matrix.name }}* deployed to production\nStatus: ${{ job.status }}\nCommit: ${{ github.sha }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Infrastructure Deployment

### Terragrunt Orchestration

```hcl
# nedlia-IaC/terragrunt.hcl (root)
locals {
  environment = get_env("ENVIRONMENT", "dev")
  region      = get_env("AWS_REGION", "us-east-1")
}

remote_state {
  backend = "s3"
  config = {
    bucket         = "nedlia-terraform-state-${local.environment}"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    region         = local.region
    encrypt        = true
    dynamodb_table = "nedlia-terraform-locks"
  }
}
```

```hcl
# nedlia-IaC/environments/staging/terragrunt.hcl
include "root" {
  path = find_in_parent_folders()
}

inputs = {
  environment = "staging"

  # Service versions (updated by CI/CD)
  api_version                  = "latest"
  workers_version              = "latest"
  placement_service_version    = "latest"
  validation_service_version   = "latest"
  notification_service_version = "latest"
}
```

### Infrastructure CI/CD

```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'nedlia-IaC/**'
  pull_request:
    paths:
      - 'nedlia-IaC/**'

jobs:
  plan:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [staging, production]

    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Setup Terragrunt
        run: |
          wget https://github.com/gruntwork-io/terragrunt/releases/download/v0.54.0/terragrunt_linux_amd64
          chmod +x terragrunt_linux_amd64
          sudo mv terragrunt_linux_amd64 /usr/local/bin/terragrunt

      - name: Terragrunt Plan
        run: |
          cd nedlia-IaC/environments/${{ matrix.environment }}
          terragrunt run-all plan --terragrunt-non-interactive
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  apply:
    needs: plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: ${{ matrix.environment }}
    strategy:
      matrix:
        environment: [staging] # Production requires manual trigger
      max-parallel: 1

    steps:
      - uses: actions/checkout@v4

      - name: Setup Terragrunt
        run: |
          wget https://github.com/gruntwork-io/terragrunt/releases/download/v0.54.0/terragrunt_linux_amd64
          chmod +x terragrunt_linux_amd64
          sudo mv terragrunt_linux_amd64 /usr/local/bin/terragrunt

      - name: Terragrunt Apply
        run: |
          cd nedlia-IaC/environments/${{ matrix.environment }}
          terragrunt run-all apply --terragrunt-non-interactive
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

## Deployment Strategies

### Canary Deployment (Fargate)

```yaml
# For ECS services
deployment_configuration:
  deployment_circuit_breaker:
    enable: true
    rollback: true
  maximum_percent: 200
  minimum_healthy_percent: 100

# CodeDeploy for canary
deployment_config:
  type: CodeDeployDefault.ECSCanary10Percent5Minutes
```

### Blue/Green (Lambda)

```yaml
# Lambda alias with traffic shifting
- name: Deploy Lambda with alias
  run: |
    # Update function
    aws lambda update-function-code --function-name $FUNCTION --zip-file fileb://deployment.zip

    # Publish version
    VERSION=$(aws lambda publish-version --function-name $FUNCTION --query 'Version' --output text)

    # Shift traffic gradually
    aws lambda update-alias \
      --function-name $FUNCTION \
      --name live \
      --routing-config "AdditionalVersionWeights={$VERSION=0.1}"

    # Monitor for 5 minutes
    sleep 300

    # If healthy, shift all traffic
    aws lambda update-alias \
      --function-name $FUNCTION \
      --name live \
      --function-version $VERSION \
      --routing-config "AdditionalVersionWeights={}"
```

### Feature Flags (LaunchDarkly)

```python
# Decouple deployment from release
from launchdarkly import LDClient

ld_client = LDClient(os.getenv("LAUNCHDARKLY_SDK_KEY"))

def process_placement(placement):
    user = {"key": placement.user_id}

    # New feature behind flag
    if ld_client.variation("new-validation-engine", user, False):
        return new_validation_engine(placement)
    else:
        return legacy_validation(placement)
```

---

## Rollback Procedures

### Automatic Rollback

```yaml
# ECS automatic rollback on failure
- name: Deploy with rollback
  run: |
    aws ecs update-service \
      --cluster nedlia-${{ env.ENVIRONMENT }} \
      --service ${{ matrix.name }} \
      --deployment-configuration "deploymentCircuitBreaker={enable=true,rollback=true}"
```

### Manual Rollback

```bash
# Lambda: Revert to previous version
aws lambda update-alias \
  --function-name nedlia-api \
  --name live \
  --function-version $PREVIOUS_VERSION

# ECS: Revert to previous task definition
aws ecs update-service \
  --cluster nedlia-production \
  --service placement-service \
  --task-definition placement-service:$PREVIOUS_REVISION

# Frontend: Revert S3 + invalidate
aws s3 sync s3://nedlia-portal-backup/ s3://nedlia-portal/ --delete
aws cloudfront create-invalidation --distribution-id $CF_ID --paths "/*"
```

### Rollback Runbook

````markdown
## Rollback Procedure

### 1. Identify the issue

- Check CloudWatch alarms
- Check error rates in X-Ray
- Identify affected service

### 2. Decide rollback scope

- [ ] Single service rollback
- [ ] Multi-service rollback
- [ ] Full environment rollback

### 3. Execute rollback

```bash
# Use deployment workflow with previous version
gh workflow run deploy.yml \
  -f environment=production \
  -f version=v1.2.3  # Previous known-good version
```
````

### 4. Verify rollback

- [ ] Health checks passing
- [ ] Error rates normalized
- [ ] User-facing functionality restored

### 5. Post-mortem

- [ ] Create incident ticket
- [ ] Schedule post-mortem meeting
- [ ] Document root cause

````

---

## Environment Management

### Environment Matrix

| Environment | Purpose | Deploy Trigger | Approval |
|-------------|---------|----------------|----------|
| **dev** | Development testing | PR merge to dev branch | None |
| **staging** | Integration testing | PR merge to main | None |
| **production** | Live users | Manual or scheduled | Required |

### Environment Promotion

```yaml
# Promote staging to production
name: Promote to Production

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to promote (e.g., v1.2.3)'
        required: true

jobs:
  promote:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Verify staging deployment
        run: |
          # Ensure version is deployed to staging
          STAGING_VERSION=$(curl -s https://api.staging.nedlia.com/version | jq -r '.version')
          if [[ "$STAGING_VERSION" != "${{ inputs.version }}" ]]; then
            echo "Version ${{ inputs.version }} not found in staging"
            exit 1
          fi

      - name: Promote to production
        run: |
          # Tag ECR images for production
          # Update production task definitions
          # Deploy to production
````

---

## Monitoring Deployments

### Deployment Dashboard

```yaml
# CloudWatch Dashboard for deployments
Resources:
  DeploymentDashboard:
    Type: AWS::CloudWatch::Dashboard
    Properties:
      DashboardName: nedlia-deployments
      DashboardBody: |
        {
          "widgets": [
            {
              "type": "metric",
              "properties": {
                "title": "Deployment Success Rate",
                "metrics": [
                  ["Nedlia", "DeploymentSuccess", "Environment", "production"],
                  ["Nedlia", "DeploymentFailure", "Environment", "production"]
                ]
              }
            },
            {
              "type": "metric",
              "properties": {
                "title": "Error Rate Post-Deploy",
                "metrics": [
                  ["AWS/Lambda", "Errors", "FunctionName", "nedlia-api"]
                ]
              }
            }
          ]
        }
```

### Deployment Notifications

```yaml
# Slack notifications
- name: Notify deployment start
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "🚀 Deployment started",
        "attachments": [{
          "color": "#36a64f",
          "fields": [
            {"title": "Service", "value": "${{ matrix.name }}", "short": true},
            {"title": "Environment", "value": "${{ env.ENVIRONMENT }}", "short": true},
            {"title": "Version", "value": "${{ github.sha }}", "short": true},
            {"title": "Triggered by", "value": "${{ github.actor }}", "short": true}
          ]
        }]
      }
```

---

## Service Dependencies

### Dependency Graph

```
┌─────────────────────────────────────────────────────────────────┐
│                    Service Dependencies                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐                                                   │
│  │ Portal  │──────────────────────┐                            │
│  └────┬────┘                      │                            │
│       │                           │                            │
│       ▼                           ▼                            │
│  ┌─────────┐              ┌─────────────────┐                  │
│  │   API   │─────────────▶│    Placement    │                  │
│  │ Gateway │              │    Service      │                  │
│  └────┬────┘              └────────┬────────┘                  │
│       │                            │                            │
│       │                            ▼                            │
│       │                   ┌─────────────────┐                  │
│       │                   │   Validation    │                  │
│       │                   │    Service      │                  │
│       │                   └────────┬────────┘                  │
│       │                            │                            │
│       ▼                            ▼                            │
│  ┌─────────┐              ┌─────────────────┐                  │
│  │ Workers │◀─────────────│  Notification   │                  │
│  │         │              │    Service      │                  │
│  └─────────┘              └─────────────────┘                  │
│                                                                 │
│  Deploy Order: Infrastructure → Shared → Services → API → Portal│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Deployment Order

When deploying breaking changes:

1. **Infrastructure** (if needed)
2. **Shared libraries** (nedlia-back-end/shared)
3. **Downstream services** (notification, validation)
4. **Core services** (placement)
5. **API Gateway**
6. **Frontend** (portal)

---

## Related Documentation

- [Architecture](../ARCHITECTURE.md) – System design
- [ADR-005: Trunk-Based Development](adr/005-trunk-based-development.md) – Branching strategy
- [ADR-007: Fargate Microservices](adr/007-fargate-microservices.md) – Service deployment
- [Branching Strategy](branching-strategy.md) – Git workflow
