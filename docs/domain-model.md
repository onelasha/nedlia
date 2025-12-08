# Domain Model

This document defines the domain-driven design (DDD) structure for Nedlia.

## Bounded Contexts

Nedlia is divided into distinct bounded contexts, each with its own ubiquitous language and domain model.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Nedlia Platform                                 │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│   Placement     │    Campaign     │   Validation    │      Integration       │
│    Context      │    Context      │    Context      │       Context          │
├─────────────────┼─────────────────┼─────────────────┼─────────────────────────┤
│ • Placement     │ • Campaign      │ • Validation    │ • Plugin               │
│ • Video         │ • Advertiser    │ • ValidationRun │ • Sync                 │
│ • Product       │ • Budget        │ • Issue         │ • Webhook              │
│ • TimeRange     │ • Contract      │ • Report        │ • ExternalPlayer       │
└─────────────────┴─────────────────┴─────────────────┴─────────────────────────┘
```

---

## Context Map

```
┌─────────────────┐         ┌─────────────────┐
│   Placement     │◀───────▶│    Campaign     │
│    Context      │  shared │    Context      │
│                 │  kernel │                 │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │ events                    │ events
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│   Validation    │         │   Integration   │
│    Context      │         │    Context      │
│                 │         │                 │
└─────────────────┘         └─────────────────┘
```

### Context Relationships

| Upstream  | Downstream  | Relationship                                          |
| --------- | ----------- | ----------------------------------------------------- |
| Placement | Validation  | Conformist (Validation conforms to Placement's model) |
| Placement | Integration | Published Language (Events)                           |
| Campaign  | Placement   | Shared Kernel (Product, Advertiser)                   |
| Campaign  | Integration | Published Language (Events)                           |

---

## Placement Context

The core context for managing product placements in videos.

### Aggregates

#### Placement (Aggregate Root)

```python
class Placement:
    id: PlacementId
    video_id: VideoId
    product_id: ProductId
    time_range: TimeRange
    description: str
    position: PlacementPosition  # screen coordinates, optional
    status: PlacementStatus  # draft, active, archived
    created_at: datetime
    updated_at: datetime
    created_by: UserId

    # Invariants:
    # - time_range must be within video duration
    # - product must belong to an active campaign
    # - no overlapping placements for same product in same video
```

#### Video (Aggregate Root)

```python
class Video:
    id: VideoId
    title: str
    duration: Duration
    source_url: str
    status: VideoStatus  # processing, ready, archived
    metadata: VideoMetadata
    created_at: datetime

    # Invariants:
    # - duration must be positive
    # - source_url must be valid
```

### Value Objects

```python
class TimeRange:
    start_time: float  # seconds
    end_time: float    # seconds

    # Invariants:
    # - start_time >= 0
    # - end_time > start_time

class PlacementPosition:
    x: float  # 0.0 - 1.0 (percentage)
    y: float  # 0.0 - 1.0 (percentage)
    width: float
    height: float

class Duration:
    seconds: float

    # Invariants:
    # - seconds > 0
```

### Domain Events

| Event              | Trigger             | Data                                           |
| ------------------ | ------------------- | ---------------------------------------------- |
| `PlacementCreated` | New placement added | placement_id, video_id, product_id, time_range |
| `PlacementUpdated` | Placement modified  | placement_id, changes                          |
| `PlacementDeleted` | Placement removed   | placement_id, video_id                         |
| `VideoRegistered`  | New video added     | video_id, duration, source_url                 |
| `VideoArchived`    | Video archived      | video_id                                       |

---

## Campaign Context

Manages advertisers, campaigns, and budgets.

### Aggregates

#### Campaign (Aggregate Root)

```python
class Campaign:
    id: CampaignId
    advertiser_id: AdvertiserId
    name: str
    budget: Money
    spent: Money
    date_range: DateRange
    status: CampaignStatus  # draft, active, paused, completed
    products: List[ProductId]

    # Invariants:
    # - spent <= budget
    # - date_range.end > date_range.start
    # - at least one product required for active campaign
```

#### Advertiser (Aggregate Root)

```python
class Advertiser:
    id: AdvertiserId
    name: str
    contact_email: Email
    billing_info: BillingInfo
    status: AdvertiserStatus  # active, suspended

    # Invariants:
    # - contact_email must be valid
```

#### Product (Aggregate Root)

```python
class Product:
    id: ProductId
    advertiser_id: AdvertiserId
    name: str
    description: str
    category: ProductCategory
    assets: List[ProductAsset]  # images, logos

    # Invariants:
    # - must belong to an advertiser
```

### Value Objects

```python
class Money:
    amount: Decimal
    currency: Currency  # USD, EUR, etc.

class DateRange:
    start_date: date
    end_date: date

class BillingInfo:
    company_name: str
    address: Address
    tax_id: str
```

### Domain Events

| Event                     | Trigger                   | Data                               |
| ------------------------- | ------------------------- | ---------------------------------- |
| `CampaignCreated`         | New campaign              | campaign_id, advertiser_id, budget |
| `CampaignActivated`       | Campaign goes live        | campaign_id                        |
| `CampaignPaused`          | Campaign paused           | campaign_id, reason                |
| `CampaignBudgetExhausted` | Budget spent              | campaign_id                        |
| `ProductAdded`            | Product added to campaign | product_id, campaign_id            |

---

## Validation Context

Handles async validation of placements during video playback.

### Aggregates

#### ValidationRun (Aggregate Root)

```python
class ValidationRun:
    id: ValidationRunId
    video_id: VideoId
    status: ValidationStatus  # pending, running, completed, failed
    started_at: datetime
    completed_at: Optional[datetime]
    issues: List[ValidationIssue]
    summary: ValidationSummary

    # Invariants:
    # - completed_at only set when status is completed/failed
```

### Value Objects

```python
class ValidationIssue:
    placement_id: PlacementId
    issue_type: IssueType  # timing_conflict, missing_product, expired_campaign
    severity: Severity  # error, warning, info
    message: str
    time_range: TimeRange

class ValidationSummary:
    total_placements: int
    valid_placements: int
    issues_count: int
    is_valid: bool
```

### Domain Events

| Event                 | Trigger                  | Data                       |
| --------------------- | ------------------------ | -------------------------- |
| `ValidationRequested` | User requests validation | video_id, requested_by     |
| `ValidationStarted`   | Worker picks up job      | validation_run_id          |
| `ValidationCompleted` | Validation finished      | validation_run_id, summary |
| `ValidationFailed`    | Validation error         | validation_run_id, error   |

---

## Integration Context

Manages external integrations (plugins, SDKs, webhooks).

### Aggregates

#### PluginSession (Aggregate Root)

```python
class PluginSession:
    id: SessionId
    plugin_type: PluginType  # finalcut, davinci, lumafusion
    user_id: UserId
    video_id: Optional[VideoId]
    status: SessionStatus  # active, syncing, disconnected
    last_sync_at: datetime

    # Invariants:
    # - user must be authenticated
```

#### Webhook (Aggregate Root)

```python
class Webhook:
    id: WebhookId
    advertiser_id: AdvertiserId
    url: Url
    events: List[EventType]
    secret: WebhookSecret
    status: WebhookStatus  # active, disabled
    failure_count: int

    # Invariants:
    # - url must be HTTPS
    # - secret must be cryptographically random
```

### Domain Events

| Event                 | Trigger                    | Data                          |
| --------------------- | -------------------------- | ----------------------------- |
| `PluginConnected`     | Plugin establishes session | session_id, plugin_type       |
| `PluginSyncRequested` | Plugin requests sync       | session_id, video_id          |
| `PluginSyncCompleted` | Sync finished              | session_id, placements_synced |
| `WebhookDelivered`    | Webhook sent successfully  | webhook_id, event_type        |
| `WebhookFailed`       | Webhook delivery failed    | webhook_id, error, attempt    |

---

## Shared Kernel

Shared concepts across contexts.

```python
# Identity types
class UserId(UUID): pass
class PlacementId(UUID): pass
class VideoId(UUID): pass
class ProductId(UUID): pass
class CampaignId(UUID): pass
class AdvertiserId(UUID): pass

# Common value objects
class Email:
    value: str
    # Invariant: must match email regex

class Url:
    value: str
    # Invariant: must be valid URL

class Timestamp:
    value: datetime
    # Always UTC
```

---

## Anti-Corruption Layers

### Plugin → Placement Context

Plugins use their own terminology (markers, clips, timecodes). The Integration Context translates:

```python
# Plugin speaks "markers"
class PluginMarker:
    timecode_in: str   # "00:01:30:15" (HH:MM:SS:FF)
    timecode_out: str
    label: str

# Translated to domain
class PlacementFromPlugin:
    def translate(marker: PluginMarker, fps: float) -> Placement:
        return Placement(
            time_range=TimeRange(
                start_time=timecode_to_seconds(marker.timecode_in, fps),
                end_time=timecode_to_seconds(marker.timecode_out, fps),
            ),
            description=marker.label,
        )
```

### SDK → Validation Context

SDKs use simplified validation results:

```python
# SDK receives simplified response
class SDKValidationResult:
    is_valid: bool
    placements: List[SDKPlacement]
    errors: List[str]

# Translated from domain
def to_sdk_result(run: ValidationRun) -> SDKValidationResult:
    return SDKValidationResult(
        is_valid=run.summary.is_valid,
        placements=[...],
        errors=[issue.message for issue in run.issues if issue.severity == Severity.ERROR],
    )
```

---

## Domain Services

Services that don't belong to a single aggregate.

### PlacementOverlapChecker

```python
class PlacementOverlapChecker:
    """Checks for overlapping placements of the same product."""

    def check(self, video_id: VideoId, new_placement: Placement) -> List[Conflict]:
        existing = self.placement_repo.find_by_video(video_id)
        conflicts = []
        for p in existing:
            if p.product_id == new_placement.product_id:
                if p.time_range.overlaps(new_placement.time_range):
                    conflicts.append(Conflict(p, new_placement))
        return conflicts
```

### CampaignBudgetEnforcer

```python
class CampaignBudgetEnforcer:
    """Ensures placements don't exceed campaign budget."""

    def can_add_placement(self, campaign: Campaign, placement: Placement) -> bool:
        estimated_cost = self.pricing.calculate(placement)
        return campaign.spent + estimated_cost <= campaign.budget
```

---

## Invariant Enforcement

### Aggregate-Level

Invariants are enforced within aggregates:

```python
class Placement:
    def update_time_range(self, new_range: TimeRange):
        if new_range.start_time < 0:
            raise InvalidTimeRange("Start time cannot be negative")
        if new_range.end_time <= new_range.start_time:
            raise InvalidTimeRange("End time must be after start time")
        self.time_range = new_range
        self._record_event(PlacementUpdated(self.id, {"time_range": new_range}))
```

### Cross-Aggregate

Cross-aggregate invariants are eventually consistent:

```python
# When campaign budget is exhausted, placements are paused
# This happens via events, not synchronous checks

@event_handler(CampaignBudgetExhausted)
def pause_campaign_placements(event: CampaignBudgetExhausted):
    placements = placement_repo.find_by_campaign(event.campaign_id)
    for p in placements:
        p.pause(reason="Campaign budget exhausted")
        placement_repo.save(p)
```

---

## Related Documentation

- [Architecture](../ARCHITECTURE.md) – Clean architecture layers
- [ADR-003: Event-Driven](adr/003-event-driven.md) – Event patterns
- [API Standards](api-standards.md) – API design for domain operations
