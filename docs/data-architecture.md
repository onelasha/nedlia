# Data Architecture

This document defines data modeling, event schemas, and data management strategies for Nedlia.

## Database Design

### Database Choice: Aurora Serverless v2 (PostgreSQL)

| Requirement        | Aurora Serverless v2        |
| ------------------ | --------------------------- |
| Serverless scaling | ✅ Auto-scales 0.5-128 ACUs |
| ACID transactions  | ✅ Full PostgreSQL ACID     |
| Cost efficiency    | ✅ Pay per ACU-second       |
| High availability  | ✅ Multi-AZ by default      |
| Performance        | ✅ Sub-millisecond latency  |

### Schema Design Principles

1. **Normalize for writes, denormalize for reads** (CQRS)
2. **Use UUIDs** for primary keys (distributed-friendly)
3. **Soft deletes** with `deleted_at` timestamp
4. **Audit columns** on all tables (`created_at`, `updated_at`, `created_by`)
5. **Optimistic locking** with `version` column

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│   advertisers   │       │    campaigns    │       │    products     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │──┐    │ id (PK)         │
│ name            │  │    │ advertiser_id(FK)│◀─┘   │ advertiser_id(FK)│
│ contact_email   │  │    │ name            │       │ name            │
│ status          │  │    │ budget          │       │ category        │
│ created_at      │  │    │ spent           │       │ created_at      │
│ updated_at      │  │    │ status          │       └────────┬────────┘
└─────────────────┘  │    │ start_date      │                │
                     │    │ end_date        │                │
                     │    │ created_at      │                │
                     │    └────────┬────────┘                │
                     │             │                         │
                     └─────────────┼─────────────────────────┘
                                   │
┌─────────────────┐       ┌────────▼────────┐       ┌─────────────────┐
│     videos      │       │   placements    │       │ validation_runs │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │◀──────│ video_id (FK)   │       │ id (PK)         │
│ title           │       │ id (PK)         │       │ video_id (FK)   │
│ duration        │       │ product_id (FK) │───────│ status          │
│ source_url      │       │ start_time      │       │ started_at      │
│ status          │       │ end_time        │       │ completed_at    │
│ created_at      │       │ description     │       │ issues (JSONB)  │
└─────────────────┘       │ status          │       │ summary (JSONB) │
                          │ created_at      │       │ created_at      │
                          │ version         │       └─────────────────┘
                          └─────────────────┘
```

---

## Table Definitions

### Core Tables

```sql
-- Advertisers
CREATE TABLE advertisers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    billing_info JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_status CHECK (status IN ('active', 'suspended'))
);

CREATE INDEX idx_advertisers_status ON advertisers(status) WHERE deleted_at IS NULL;

-- Campaigns
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    name VARCHAR(255) NOT NULL,
    budget DECIMAL(12, 2) NOT NULL,
    spent DECIMAL(12, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT chk_budget CHECK (spent <= budget),
    CONSTRAINT chk_dates CHECK (end_date > start_date),
    CONSTRAINT chk_status CHECK (status IN ('draft', 'active', 'paused', 'completed'))
);

CREATE INDEX idx_campaigns_advertiser ON campaigns(advertiser_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_status ON campaigns(status) WHERE deleted_at IS NULL;

-- Products
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    advertiser_id UUID NOT NULL REFERENCES advertisers(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    assets JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_products_advertiser ON products(advertiser_id) WHERE deleted_at IS NULL;

-- Videos
CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    duration DECIMAL(10, 3) NOT NULL,
    source_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'processing',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_duration CHECK (duration > 0),
    CONSTRAINT chk_status CHECK (status IN ('processing', 'ready', 'archived'))
);

CREATE INDEX idx_videos_status ON videos(status) WHERE deleted_at IS NULL;

-- Placements
CREATE TABLE placements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id),
    product_id UUID NOT NULL REFERENCES products(id),
    start_time DECIMAL(10, 3) NOT NULL,
    end_time DECIMAL(10, 3) NOT NULL,
    description TEXT,
    position JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    file_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT chk_time_range CHECK (end_time > start_time AND start_time >= 0),
    CONSTRAINT chk_status CHECK (status IN ('draft', 'active', 'archived'))
);

CREATE INDEX idx_placements_video ON placements(video_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_placements_product ON placements(product_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_placements_time ON placements(video_id, start_time, end_time) WHERE deleted_at IS NULL;

-- Validation Runs
CREATE TABLE validation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID NOT NULL REFERENCES videos(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    issues JSONB DEFAULT '[]',
    summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    requested_by UUID,

    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE INDEX idx_validation_runs_video ON validation_runs(video_id);
CREATE INDEX idx_validation_runs_status ON validation_runs(status);
```

### Audit Tables

```sql
-- Event log for audit trail
CREATE TABLE event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID
);

CREATE INDEX idx_event_log_aggregate ON event_log(aggregate_type, aggregate_id);
CREATE INDEX idx_event_log_type ON event_log(event_type);
CREATE INDEX idx_event_log_created ON event_log(created_at);

-- Partition by month for performance
CREATE TABLE event_log_2024_01 PARTITION OF event_log
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## Event Schema Registry

### Event Format (CloudEvents)

All events follow the [CloudEvents](https://cloudevents.io/) specification:

```json
{
  "specversion": "1.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "source": "/placements",
  "type": "com.nedlia.placement.created",
  "datacontenttype": "application/json",
  "time": "2024-01-15T10:30:00Z",
  "data": {
    "placement_id": "abc123",
    "video_id": "xyz789",
    "product_id": "def456"
  },
  "nedlia": {
    "version": "1.0",
    "environment": "production",
    "trace_id": "1-5f8d3b2a-abc123def456"
  }
}
```

### Event Catalog

#### Placement Events

```yaml
# placement.created.v1
type: com.nedlia.placement.created
version: 1
description: Emitted when a new placement is created
data:
  placement_id:
    type: string
    format: uuid
    required: true
  video_id:
    type: string
    format: uuid
    required: true
  product_id:
    type: string
    format: uuid
    required: true
  time_range:
    type: object
    properties:
      start_time:
        type: number
      end_time:
        type: number
  created_by:
    type: string
    format: uuid
consumers:
  - file-generator
  - notifier
```

```yaml
# placement.updated.v1
type: com.nedlia.placement.updated
version: 1
description: Emitted when a placement is modified
data:
  placement_id:
    type: string
    format: uuid
    required: true
  changes:
    type: object
    description: Fields that changed
  previous_version:
    type: integer
  new_version:
    type: integer
consumers:
  - file-generator
  - notifier
```

#### Video Events

```yaml
# video.validation_requested.v1
type: com.nedlia.video.validation_requested
version: 1
description: Emitted when validation is requested for a video
data:
  video_id:
    type: string
    format: uuid
    required: true
  validation_run_id:
    type: string
    format: uuid
    required: true
  requested_by:
    type: string
    format: uuid
consumers:
  - validator
```

```yaml
# video.validation_completed.v1
type: com.nedlia.video.validation_completed
version: 1
description: Emitted when validation completes
data:
  video_id:
    type: string
    format: uuid
    required: true
  validation_run_id:
    type: string
    format: uuid
    required: true
  is_valid:
    type: boolean
  issues_count:
    type: integer
consumers:
  - notifier
  - api (cache invalidation)
```

### Schema Evolution

#### Backward Compatible Changes (Safe)

- Adding optional fields
- Adding new event types
- Relaxing validation

#### Breaking Changes (Require New Version)

- Removing fields
- Changing field types
- Renaming fields

#### Versioning Strategy

```
com.nedlia.placement.created.v1  # Original
com.nedlia.placement.created.v2  # Breaking change
```

Consumers must handle both versions during migration period.

---

## Data Migration Strategy

### Migration Tool: Alembic

```bash
# Create migration
alembic revision --autogenerate -m "add_file_url_to_placements"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Migration Best Practices

1. **Always backward compatible** - Old code must work with new schema
2. **Expand-Contract pattern** for breaking changes:

   - Expand: Add new column
   - Migrate: Copy data
   - Contract: Remove old column (next release)

3. **Test migrations** in staging before production
4. **Small, incremental changes** - One change per migration

### Example: Rename Column

```python
# Migration 1: Add new column
def upgrade():
    op.add_column('placements', sa.Column('time_start', sa.Float()))

def downgrade():
    op.drop_column('placements', 'time_start')

# Migration 2: Copy data (run in background)
def upgrade():
    op.execute("UPDATE placements SET time_start = start_time")

# Migration 3: Remove old column (after all code updated)
def upgrade():
    op.drop_column('placements', 'start_time')
```

---

## CQRS Implementation

### Write Model (Commands)

Normalized tables for consistency:

```python
# Write to normalized tables
class CreatePlacementCommand:
    def execute(self, request):
        placement = Placement.create(request)
        self.repository.save(placement)
        self.event_publisher.publish(PlacementCreated(placement))
```

### Read Model (Queries)

Denormalized views for performance:

```sql
-- Materialized view for fast reads
CREATE MATERIALIZED VIEW placement_details AS
SELECT
    p.id,
    p.video_id,
    v.title AS video_title,
    p.product_id,
    pr.name AS product_name,
    pr.category AS product_category,
    a.name AS advertiser_name,
    p.start_time,
    p.end_time,
    p.description,
    p.status,
    p.file_url,
    p.created_at
FROM placements p
JOIN videos v ON p.video_id = v.id
JOIN products pr ON p.product_id = pr.id
JOIN advertisers a ON pr.advertiser_id = a.id
WHERE p.deleted_at IS NULL;

CREATE UNIQUE INDEX idx_placement_details_id ON placement_details(id);

-- Refresh on event
REFRESH MATERIALIZED VIEW CONCURRENTLY placement_details;
```

### Event-Driven View Updates

```python
@event_handler(PlacementCreated)
@event_handler(PlacementUpdated)
@event_handler(PlacementDeleted)
def refresh_placement_view(event):
    db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY placement_details")
```

---

## Data Retention

### Retention Policies

| Data Type          | Retention  | Archive    |
| ------------------ | ---------- | ---------- |
| Active placements  | Indefinite | -          |
| Deleted placements | 90 days    | S3 Glacier |
| Validation runs    | 1 year     | S3 Glacier |
| Event log          | 2 years    | S3 Glacier |
| API logs           | 30 days    | -          |

### Archival Process

```python
# Archive old data to S3
def archive_old_validations():
    cutoff = datetime.now() - timedelta(days=365)

    # Export to S3
    old_runs = db.query(ValidationRun).filter(
        ValidationRun.created_at < cutoff
    ).all()

    s3.put_object(
        Bucket='nedlia-archive',
        Key=f'validations/{cutoff.year}/data.json',
        Body=json.dumps([r.to_dict() for r in old_runs])
    )

    # Delete from database
    db.query(ValidationRun).filter(
        ValidationRun.created_at < cutoff
    ).delete()
```

---

## Backup Strategy

### Aurora Automated Backups

- **Continuous backup** to S3
- **Point-in-time recovery** up to 35 days
- **Automated snapshots** daily

### Cross-Region Replication

```hcl
# nedlia-IaC/modules/aurora/main.tf
resource "aws_rds_cluster" "main" {
  # ... other config

  backup_retention_period = 35
  preferred_backup_window = "03:00-04:00"

  # Cross-region read replica for DR
  replication_source_identifier = var.enable_dr ? aws_rds_cluster.primary.arn : null
}
```

---

## Related Documentation

- [Architecture](../ARCHITECTURE.md) – System overview
- [Domain Model](domain-model.md) – Entity definitions
- [ADR-003: Event-Driven](adr/003-event-driven.md) – Event patterns
