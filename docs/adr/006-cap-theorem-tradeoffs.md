# ADR-006: CAP Theorem Trade-offs

## Status

Accepted

## Context

Nedlia is a distributed system with multiple components (API, Workers, Database, Queues). According to the CAP theorem, we can only guarantee two of three properties:

- **Consistency**: All nodes see the same data at the same time
- **Availability**: Every request receives a response
- **Partition Tolerance**: System continues despite network failures

Since network partitions are inevitable in distributed systems, we must choose between Consistency and Availability.

## Decision

Nedlia chooses **AP (Availability + Partition Tolerance)** for most operations, with **CP (Consistency + Partition Tolerance)** for critical financial operations.

### Trade-off Matrix

| Operation              | Choice | Rationale                                    |
| ---------------------- | ------ | -------------------------------------------- |
| Read placements        | AP     | Stale data acceptable, availability critical |
| Create placement       | AP     | Eventual consistency via events              |
| Validate video         | AP     | Async operation, eventual result             |
| Update campaign budget | CP     | Financial accuracy required                  |
| Process payment        | CP     | Cannot have inconsistent money               |
| User authentication    | CP     | Security requires consistency                |

### Implementation by Component

#### API (AP - Favor Availability)

```python
# Return cached/stale data if database is slow
@fallback(get_from_cache)
async def get_placement(id: str):
    return await database.get(id)

# Accept writes even if downstream is slow
async def create_placement(request):
    placement = await database.save(request)
    # Fire-and-forget event publishing
    asyncio.create_task(publish_event(PlacementCreated(placement)))
    return placement  # Return immediately
```

#### Workers (AP - Eventual Consistency)

```python
# Workers process events eventually
# May process same event multiple times (idempotent)
@event_handler(PlacementCreated)
async def generate_file(event):
    # Check if already processed (idempotency)
    if await already_processed(event.id):
        return

    # Process and mark as done
    await generate_placement_file(event.placement_id)
    await mark_processed(event.id)
```

#### Financial Operations (CP - Favor Consistency)

```python
# Use database transactions for budget updates
async def deduct_budget(campaign_id: str, amount: Decimal):
    async with database.transaction():
        campaign = await database.get_for_update(campaign_id)  # Lock row

        if campaign.remaining_budget < amount:
            raise InsufficientBudget()

        campaign.spent += amount
        await database.save(campaign)

        # Only publish event after commit
    await publish_event(BudgetDeducted(campaign_id, amount))
```

## Consistency Patterns

### Eventual Consistency (Default)

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  Write  │────▶│  Event  │────▶│  Read   │
│  Model  │     │  Queue  │     │  Model  │
└─────────┘     └─────────┘     └─────────┘
     │                               │
     │ Immediate                     │ Eventually
     ▼                               ▼
   User                            User
   sees                            sees
   "Accepted"                      updated data
```

**Latency**: Typically < 1 second, may be minutes under load

### Strong Consistency (When Required)

```
┌─────────┐     ┌─────────┐
│  Write  │────▶│  Read   │
│         │     │         │
└─────────┘     └─────────┘
     │               │
     │ Synchronous   │ Immediate
     ▼               ▼
   User            User
   waits           sees
   for commit      consistent data
```

**Use for**: Budget updates, payment processing, authentication

### Read-Your-Writes Consistency

For better UX, ensure users see their own writes immediately:

```python
async def create_placement(request, user):
    placement = await database.save(request)

    # Cache for immediate read-your-writes
    await cache.set(
        f"user:{user.id}:placement:{placement.id}",
        placement,
        ttl=60  # 1 minute
    )

    return placement

async def get_placement(id: str, user):
    # Check user's recent writes first
    cached = await cache.get(f"user:{user.id}:placement:{id}")
    if cached:
        return cached

    # Fall back to eventually consistent read
    return await database.get(id)
```

## ACID vs BASE

### ACID (Financial Operations)

| Property        | Implementation                 |
| --------------- | ------------------------------ |
| **Atomicity**   | Database transactions          |
| **Consistency** | Constraints, validations       |
| **Isolation**   | Row-level locking              |
| **Durability**  | Aurora's durability guarantees |

```python
async def transfer_budget(from_campaign: str, to_campaign: str, amount: Decimal):
    async with database.transaction(isolation_level="SERIALIZABLE"):
        from_c = await database.get_for_update(from_campaign)
        to_c = await database.get_for_update(to_campaign)

        if from_c.remaining < amount:
            raise InsufficientFunds()

        from_c.spent += amount
        to_c.budget += amount

        await database.save(from_c)
        await database.save(to_c)
    # Both succeed or both fail
```

### BASE (Most Operations)

| Property                  | Implementation                    |
| ------------------------- | --------------------------------- |
| **Basically Available**   | Return response even if stale     |
| **Soft state**            | State may change over time        |
| **Eventually consistent** | Will converge to consistent state |

```python
async def get_campaign_stats(campaign_id: str):
    # May return slightly stale data
    stats = await cache.get(f"stats:{campaign_id}")
    if stats:
        return stats

    # Compute from eventually consistent read replica
    stats = await read_replica.compute_stats(campaign_id)
    await cache.set(f"stats:{campaign_id}", stats, ttl=300)
    return stats
```

## Conflict Resolution

### Last-Write-Wins (LWW)

Simple but may lose data:

```python
async def update_placement(id: str, updates: dict):
    placement = await database.get(id)
    placement.update(updates)
    placement.updated_at = datetime.utcnow()  # Timestamp determines winner
    await database.save(placement)
```

### Optimistic Locking (Preferred)

Detect conflicts, let application resolve:

```python
async def update_placement(id: str, updates: dict, expected_version: int):
    result = await database.execute("""
        UPDATE placements
        SET data = :data, version = version + 1
        WHERE id = :id AND version = :expected_version
    """, {"id": id, "data": updates, "expected_version": expected_version})

    if result.rowcount == 0:
        raise ConcurrentModificationError("Placement was modified by another request")
```

### Merge (Complex Cases)

For collaborative editing:

```python
def merge_placement_changes(base: Placement, theirs: Placement, mine: Placement) -> Placement:
    merged = Placement()

    # Non-conflicting: take latest
    merged.description = mine.description if mine.updated_at > theirs.updated_at else theirs.description

    # Conflicting: merge time ranges
    if theirs.time_range != base.time_range and mine.time_range != base.time_range:
        # Both modified - need manual resolution
        raise ConflictError("Time range conflict", theirs=theirs, mine=mine)

    merged.time_range = mine.time_range if mine.time_range != base.time_range else theirs.time_range

    return merged
```

## Consequences

### Positive

- High availability for read operations
- System remains responsive during partial failures
- Better user experience (fast responses)
- Scalable (can add read replicas)

### Negative

- Users may see stale data temporarily
- More complex application logic (handle eventual consistency)
- Need idempotency everywhere
- Conflict resolution required

### Mitigations

1. **UI Design**: Show "Saving..." / "Saved" indicators
2. **Polling**: Client polls for eventual updates
3. **Webhooks**: Notify when async operations complete
4. **Idempotency Keys**: Prevent duplicate operations
5. **Versioning**: Detect and resolve conflicts

## Monitoring

Track consistency-related metrics:

```python
# Measure replication lag
replication_lag = await read_replica.get_lag()
metrics.gauge("db.replication_lag_ms", replication_lag)

# Track stale reads
if data_from_cache and cache_age > 60:
    metrics.increment("reads.stale", tags={"source": "cache"})

# Track conflicts
metrics.increment("conflicts.detected", tags={"type": "optimistic_lock"})
```

## Related Documentation

- [Architecture](../../ARCHITECTURE.md) – System design
- [Data Architecture](../data-architecture.md) – Database design
- [ADR-003: Event-Driven](003-event-driven.md) – Eventual consistency patterns
