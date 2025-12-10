# Database Migration Strategy

Database migration patterns and procedures for Nedlia using Alembic with PostgreSQL (Aurora Serverless).

## Principles

1. **Always Backward Compatible**: Old code must work with new schema during deployment
2. **Small, Incremental Changes**: One logical change per migration
3. **Reversible**: Every migration should have a working downgrade
4. **Tested**: Migrations tested in staging before production
5. **Automated**: Migrations run automatically in CI/CD pipeline

---

## Tooling

| Tool           | Purpose                    |
| -------------- | -------------------------- |
| **Alembic**    | Migration management       |
| **SQLAlchemy** | ORM and schema definitions |
| **pytest**     | Migration testing          |

---

## Project Structure

```
nedlia-back-end/api/
├── alembic/
│   ├── versions/           # Migration files
│   │   ├── 001_initial_schema.py
│   │   ├── 002_add_file_url_to_placements.py
│   │   └── ...
│   ├── env.py              # Alembic environment config
│   └── script.py.mako      # Migration template
├── alembic.ini             # Alembic configuration
└── src/
    └── infrastructure/
        └── models/         # SQLAlchemy models
```

---

## Quick Reference

```bash
# Create a new migration (auto-generate from model changes)
alembic revision --autogenerate -m "add_file_url_to_placements"

# Create empty migration (for data migrations)
alembic revision -m "backfill_placement_status"

# Run all pending migrations
alembic upgrade head

# Run migrations up to specific revision
alembic upgrade abc123

# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Show current revision
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic history --indicate-current
```

---

## Creating Migrations

### Auto-Generated (Schema Changes)

When you modify SQLAlchemy models, auto-generate the migration:

```bash
# 1. Modify the model
# src/infrastructure/models/placement.py

# 2. Generate migration
alembic revision --autogenerate -m "add_file_url_to_placements"

# 3. Review the generated migration!
# alembic/versions/xxx_add_file_url_to_placements.py

# 4. Test locally
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

### Manual (Data Migrations)

For data transformations, create an empty migration:

```bash
alembic revision -m "backfill_placement_status"
```

```python
# alembic/versions/xxx_backfill_placement_status.py
"""Backfill placement status from legacy field."""

from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = 'yyy'


def upgrade() -> None:
    # Backfill in batches to avoid locking
    op.execute("""
        UPDATE placements
        SET status = CASE
            WHEN legacy_active = true THEN 'active'
            ELSE 'draft'
        END
        WHERE status IS NULL
    """)


def downgrade() -> None:
    # Data migrations typically can't be reversed
    pass
```

---

## Migration Patterns

### Adding a Column

```python
def upgrade() -> None:
    op.add_column(
        'placements',
        sa.Column('file_url', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('placements', 'file_url')
```

### Adding a Column with Default

```python
def upgrade() -> None:
    # Add column as nullable first
    op.add_column(
        'placements',
        sa.Column('priority', sa.Integer(), nullable=True)
    )

    # Backfill existing rows
    op.execute("UPDATE placements SET priority = 0 WHERE priority IS NULL")

    # Make non-nullable
    op.alter_column('placements', 'priority', nullable=False)


def downgrade() -> None:
    op.drop_column('placements', 'priority')
```

### Renaming a Column (Expand-Contract)

**Never rename directly** – use expand-contract pattern:

```python
# Migration 1: Add new column
def upgrade() -> None:
    op.add_column('placements', sa.Column('start_time', sa.Float()))

def downgrade() -> None:
    op.drop_column('placements', 'start_time')
```

```python
# Migration 2: Copy data (run separately, can be slow)
def upgrade() -> None:
    op.execute("UPDATE placements SET start_time = time_start")

def downgrade() -> None:
    op.execute("UPDATE placements SET time_start = start_time")
```

```python
# Migration 3: Drop old column (after all code updated)
def upgrade() -> None:
    op.drop_column('placements', 'time_start')

def downgrade() -> None:
    op.add_column('placements', sa.Column('time_start', sa.Float()))
    op.execute("UPDATE placements SET time_start = start_time")
```

### Adding an Index

```python
def upgrade() -> None:
    op.create_index(
        'idx_placements_video_time',
        'placements',
        ['video_id', 'start_time', 'end_time'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('idx_placements_video_time')
```

### Adding an Index Concurrently (No Locking)

```python
def upgrade() -> None:
    # Use raw SQL for CONCURRENTLY (not supported by Alembic directly)
    op.execute("""
        CREATE INDEX CONCURRENTLY idx_placements_video_time
        ON placements (video_id, start_time, end_time)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX CONCURRENTLY idx_placements_video_time")
```

### Adding a Foreign Key

```python
def upgrade() -> None:
    op.add_column(
        'placements',
        sa.Column('campaign_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_placements_campaign',
        'placements', 'campaigns',
        ['campaign_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_placements_campaign', 'placements')
    op.drop_column('placements', 'campaign_id')
```

### Adding a Check Constraint

```python
def upgrade() -> None:
    op.create_check_constraint(
        'chk_placements_time_range',
        'placements',
        'end_time > start_time AND start_time >= 0'
    )


def downgrade() -> None:
    op.drop_constraint('chk_placements_time_range', 'placements')
```

### Creating a New Table

```python
def upgrade() -> None:
    op.create_table(
        'validation_issues',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('validation_run_id', sa.UUID(), nullable=False),
        sa.Column('placement_id', sa.UUID(), nullable=False),
        sa.Column('issue_type', sa.String(50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['validation_run_id'], ['validation_runs.id']),
        sa.ForeignKeyConstraint(['placement_id'], ['placements.id']),
    )

    op.create_index('idx_validation_issues_run', 'validation_issues', ['validation_run_id'])


def downgrade() -> None:
    op.drop_table('validation_issues')
```

---

## Deployment Strategy

### Zero-Downtime Migrations

1. **Deploy migration** (schema change)
2. **Deploy new code** (uses new schema)
3. **Cleanup** (remove old columns in next release)

```
Timeline:
─────────────────────────────────────────────────────────────────
│ Old Code Running │ Migration │ New Code Deployed │ Cleanup    │
─────────────────────────────────────────────────────────────────
Schema:  v1         v1 + v2     v1 + v2             v2
```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - name: Run migrations
        run: |
          alembic upgrade head
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}

  deploy:
    needs: migrate
    runs-on: ubuntu-latest
    steps:
      - name: Deploy application
        run: |
          # Deploy Lambda/Fargate
```

### Rollback Procedure

```bash
# 1. Identify current revision
alembic current

# 2. Rollback to previous revision
alembic downgrade -1

# 3. Or rollback to specific revision
alembic downgrade abc123

# 4. Redeploy previous code version
```

---

## Testing Migrations

### Local Testing

```bash
# Test upgrade and downgrade
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

### Automated Testing

```python
# tests/migrations/test_migrations.py
import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture
def alembic_config():
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


def test_upgrade_downgrade_cycle(alembic_config):
    """Test that all migrations can be applied and rolled back."""
    # Upgrade to head
    command.upgrade(alembic_config, "head")

    # Downgrade to base
    command.downgrade(alembic_config, "base")

    # Upgrade again
    command.upgrade(alembic_config, "head")


def test_migrations_have_downgrade(alembic_config):
    """Ensure all migrations have downgrade functions."""
    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(alembic_config)

    for revision in script.walk_revisions():
        # Check that downgrade is not empty
        assert revision.module.downgrade is not None
```

---

## Best Practices

### Do

- ✅ Test migrations in staging before production
- ✅ Keep migrations small and focused
- ✅ Use transactions (Alembic does this by default)
- ✅ Add indexes concurrently for large tables
- ✅ Backfill data in batches for large tables
- ✅ Review auto-generated migrations before committing

### Don't

- ❌ Modify existing migration files after they're deployed
- ❌ Delete migration files
- ❌ Rename columns directly (use expand-contract)
- ❌ Add NOT NULL without default on existing tables
- ❌ Run long-running migrations during peak hours

---

## Troubleshooting

### Migration Conflicts

If two developers create migrations from the same base:

```bash
# 1. Identify the conflict
alembic history

# 2. Merge migrations
alembic merge -m "merge heads" rev1 rev2

# 3. Or rebase one migration
# Edit the down_revision in the newer migration
```

### Failed Migration

```bash
# 1. Check current state
alembic current

# 2. If partially applied, fix manually or rollback
alembic downgrade -1

# 3. Fix the migration and retry
alembic upgrade head
```

### Slow Migrations

For large tables, use batched updates:

```python
def upgrade() -> None:
    connection = op.get_bind()

    # Process in batches of 10000
    batch_size = 10000
    while True:
        result = connection.execute("""
            UPDATE placements
            SET status = 'active'
            WHERE id IN (
                SELECT id FROM placements
                WHERE status IS NULL
                LIMIT %s
            )
            RETURNING id
        """, batch_size)

        if result.rowcount == 0:
            break
```

---

## Related Documentation

- [Data Architecture](data-architecture.md) – Schema design, ACID principles
- [Deployment](deployment.md) – CI/CD pipeline
- [Testing Strategy](testing-strategy.md) – Migration testing
