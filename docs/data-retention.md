# Data Retention & GDPR

Data lifecycle management, retention policies, and GDPR compliance for Nedlia.

## Principles

1. **Data Minimization**: Collect only what's necessary
2. **Purpose Limitation**: Use data only for stated purposes
3. **Storage Limitation**: Delete data when no longer needed
4. **Transparency**: Users know what data we collect and why
5. **User Rights**: Support access, correction, deletion requests

---

## Data Classification

| Classification  | Description                         | Examples                      | Retention       |
| --------------- | ----------------------------------- | ----------------------------- | --------------- |
| **PII**         | Personally Identifiable Information | Email, name, IP address       | User-controlled |
| **Sensitive**   | Requires extra protection           | Payment info, auth tokens     | Minimal         |
| **Business**    | Business-critical data              | Placements, campaigns, videos | Per policy      |
| **Operational** | System operation data               | Logs, metrics, traces         | 30-90 days      |
| **Transient**   | Temporary processing data           | Session data, cache           | Hours-days      |

---

## Retention Policies

### User Data

| Data Type             | Retention Period       | After Deletion |
| --------------------- | ---------------------- | -------------- |
| User profile          | Account lifetime + 30d | Anonymized     |
| Email address         | Account lifetime       | Deleted        |
| Authentication tokens | Session duration       | Deleted        |
| Password hashes       | Account lifetime       | Deleted        |
| Audit logs (user)     | 2 years                | Anonymized     |

### Business Data

| Data Type          | Retention Period      | After Retention        |
| ------------------ | --------------------- | ---------------------- |
| Placements         | Campaign end + 1 year | Archived to S3 Glacier |
| Campaigns          | End date + 2 years    | Archived               |
| Videos             | Last access + 1 year  | Deleted                |
| Validation results | 1 year                | Deleted                |
| Analytics          | 3 years               | Aggregated/anonymized  |

### Operational Data

| Data Type        | Retention Period | After Retention |
| ---------------- | ---------------- | --------------- |
| Application logs | 30 days          | Deleted         |
| Access logs      | 90 days          | Deleted         |
| Error logs       | 90 days          | Deleted         |
| Metrics          | 15 months        | Downsampled     |
| Traces           | 7 days           | Deleted         |

---

## GDPR Compliance

### Lawful Basis for Processing

| Data             | Lawful Basis        | Purpose                           |
| ---------------- | ------------------- | --------------------------------- |
| Account email    | Contract            | Account management, communication |
| Placement data   | Contract            | Service delivery                  |
| Usage analytics  | Legitimate interest | Service improvement               |
| Marketing emails | Consent             | Marketing communications          |
| Support tickets  | Contract            | Customer support                  |

### User Rights Implementation

#### Right to Access (Article 15)

```python
# src/users/service.py
async def export_user_data(user_id: UUID) -> UserDataExport:
    """Export all data associated with a user."""
    user = await user_repo.find_by_id(user_id)
    placements = await placement_repo.find_by_user(user_id)
    campaigns = await campaign_repo.find_by_user(user_id)
    audit_logs = await audit_repo.find_by_user(user_id)

    return UserDataExport(
        user=user,
        placements=placements,
        campaigns=campaigns,
        audit_logs=audit_logs,
        exported_at=datetime.utcnow(),
    )
```

```python
# API endpoint
@router.get("/users/me/data-export")
async def request_data_export(
    current_user: CurrentUser,
    service: UserServiceDep,
) -> DataExportResponse:
    """Request export of all user data (GDPR Article 15)."""
    export = await service.export_user_data(current_user.id)

    # Generate downloadable file
    file_url = await storage.upload_temp(
        f"exports/{current_user.id}.json",
        export.model_dump_json(),
        expires_in=timedelta(hours=24),
    )

    return DataExportResponse(download_url=file_url, expires_at=...)
```

#### Right to Rectification (Article 16)

```python
@router.patch("/users/me")
async def update_user_profile(
    data: UserUpdate,
    current_user: CurrentUser,
    service: UserServiceDep,
) -> UserResponse:
    """Update user profile data (GDPR Article 16)."""
    return await service.update(current_user.id, data)
```

#### Right to Erasure (Article 17)

```python
# src/users/service.py
async def delete_user_data(user_id: UUID) -> None:
    """Delete all user data (GDPR Article 17 - Right to be Forgotten)."""

    # 1. Delete or anonymize placements
    await placement_repo.anonymize_by_user(user_id)

    # 2. Delete campaigns
    await campaign_repo.delete_by_user(user_id)

    # 3. Anonymize audit logs (keep for compliance, remove PII)
    await audit_repo.anonymize_by_user(user_id)

    # 4. Delete user account
    await user_repo.delete(user_id)

    # 5. Revoke all tokens
    await auth_service.revoke_all_tokens(user_id)

    # 6. Log deletion for compliance
    logger.info(
        "User data deleted",
        extra={"user_id": str(user_id), "reason": "gdpr_erasure_request"},
    )
```

```python
@router.delete("/users/me")
async def delete_account(
    current_user: CurrentUser,
    service: UserServiceDep,
) -> None:
    """Delete user account and all associated data (GDPR Article 17)."""
    await service.delete_user_data(current_user.id)
    return Response(status_code=204)
```

#### Right to Data Portability (Article 20)

```python
@router.get("/users/me/data-export/portable")
async def export_portable_data(
    current_user: CurrentUser,
    service: UserServiceDep,
) -> Response:
    """Export data in machine-readable format (GDPR Article 20)."""
    export = await service.export_user_data(current_user.id)

    return Response(
        content=export.model_dump_json(indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=nedlia-data-{current_user.id}.json"
        },
    )
```

---

## Data Anonymization

### Techniques

```python
# src/core/anonymization.py
import hashlib
from typing import Any


def anonymize_email(email: str) -> str:
    """Anonymize email while preserving domain for analytics."""
    local, domain = email.split("@")
    hashed = hashlib.sha256(local.encode()).hexdigest()[:8]
    return f"anon_{hashed}@{domain}"


def anonymize_ip(ip: str) -> str:
    """Anonymize IP by zeroing last octet."""
    parts = ip.split(".")
    parts[-1] = "0"
    return ".".join(parts)


def anonymize_user_data(data: dict[str, Any]) -> dict[str, Any]:
    """Anonymize PII fields in user data."""
    anonymized = data.copy()

    if "email" in anonymized:
        anonymized["email"] = anonymize_email(anonymized["email"])

    if "name" in anonymized:
        anonymized["name"] = "Anonymous User"

    if "ip_address" in anonymized:
        anonymized["ip_address"] = anonymize_ip(anonymized["ip_address"])

    return anonymized
```

### Database Anonymization

```sql
-- Anonymize deleted users
UPDATE users
SET
    email = CONCAT('deleted_', id, '@anonymized.local'),
    name = 'Deleted User',
    phone = NULL,
    deleted_at = NOW()
WHERE id = $1;

-- Anonymize old audit logs
UPDATE audit_logs
SET
    user_email = CONCAT('anon_', LEFT(MD5(user_email), 8), '@anonymized.local'),
    ip_address = CONCAT(SPLIT_PART(ip_address, '.', 1), '.', SPLIT_PART(ip_address, '.', 2), '.0.0')
WHERE created_at < NOW() - INTERVAL '2 years';
```

---

## Automated Retention Jobs

### Scheduled Cleanup

```python
# src/jobs/data_retention.py
from datetime import datetime, timedelta

from src.core.config import settings


async def cleanup_expired_data() -> None:
    """Run data retention cleanup (scheduled daily)."""

    # Delete old sessions
    await session_repo.delete_expired()

    # Archive old placements
    cutoff = datetime.utcnow() - timedelta(days=365)
    old_placements = await placement_repo.find_older_than(cutoff)
    await archive_to_glacier(old_placements)
    await placement_repo.delete_batch([p.id for p in old_placements])

    # Delete old logs
    log_cutoff = datetime.utcnow() - timedelta(days=30)
    await log_repo.delete_older_than(log_cutoff)

    # Anonymize old audit records
    audit_cutoff = datetime.utcnow() - timedelta(days=730)  # 2 years
    await audit_repo.anonymize_older_than(audit_cutoff)

    logger.info("Data retention cleanup completed")
```

### Lambda Scheduled Job

```python
# src/handlers/retention_cleanup.py
from aws_lambda_powertools import Logger

from src.jobs.data_retention import cleanup_expired_data

logger = Logger()


@logger.inject_lambda_context
async def handler(event, context):
    """Lambda handler for scheduled data retention cleanup."""
    await cleanup_expired_data()
    return {"status": "completed"}
```

```hcl
# Terraform: Schedule daily at 3 AM UTC
resource "aws_cloudwatch_event_rule" "retention_cleanup" {
  name                = "nedlia-retention-cleanup"
  schedule_expression = "cron(0 3 * * ? *)"
}

resource "aws_cloudwatch_event_target" "retention_cleanup" {
  rule      = aws_cloudwatch_event_rule.retention_cleanup.name
  target_id = "retention-cleanup-lambda"
  arn       = aws_lambda_function.retention_cleanup.arn
}
```

---

## Consent Management

### Consent Types

```python
# src/domain/consent.py
from enum import Enum


class ConsentType(str, Enum):
    ESSENTIAL = "essential"           # Required for service
    ANALYTICS = "analytics"           # Usage analytics
    MARKETING = "marketing"           # Marketing communications
    THIRD_PARTY = "third_party"       # Third-party integrations


@dataclass
class UserConsent:
    user_id: UUID
    consent_type: ConsentType
    granted: bool
    granted_at: datetime | None
    revoked_at: datetime | None
    ip_address: str
    user_agent: str
```

### Consent API

```python
@router.get("/users/me/consents")
async def get_consents(current_user: CurrentUser) -> list[ConsentResponse]:
    """Get user's consent preferences."""
    return await consent_service.get_user_consents(current_user.id)


@router.put("/users/me/consents/{consent_type}")
async def update_consent(
    consent_type: ConsentType,
    data: ConsentUpdate,
    current_user: CurrentUser,
    request: Request,
) -> ConsentResponse:
    """Update consent preference."""
    return await consent_service.update_consent(
        user_id=current_user.id,
        consent_type=consent_type,
        granted=data.granted,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
    )
```

---

## Audit Trail

### What to Log

```python
# Log all data access and modifications
logger.info(
    "User data accessed",
    extra={
        "action": "data_export",
        "user_id": str(user_id),
        "requested_by": str(admin_id),
        "ip_address": request.client.host,
        "timestamp": datetime.utcnow().isoformat(),
    },
)

logger.info(
    "User data deleted",
    extra={
        "action": "gdpr_erasure",
        "user_id": str(user_id),
        "data_types": ["profile", "placements", "campaigns"],
        "requested_by": str(user_id),  # Self-service
        "timestamp": datetime.utcnow().isoformat(),
    },
)
```

### Audit Table

```sql
CREATE TABLE data_access_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    user_id UUID,
    performed_by UUID NOT NULL,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_user ON data_access_audit(user_id);
CREATE INDEX idx_audit_created ON data_access_audit(created_at);
```

---

## Third-Party Data Sharing

### Data Processing Agreements

Maintain DPAs with all third-party processors:

| Vendor   | Purpose        | Data Shared            | DPA Status |
| -------- | -------------- | ---------------------- | ---------- |
| AWS      | Infrastructure | All data               | ✅ Active  |
| Stripe   | Payments       | Billing info           | ✅ Active  |
| SendGrid | Email          | Email addresses        | ✅ Active  |
| Sentry   | Error tracking | Error context (no PII) | ✅ Active  |

### Data Transfer Safeguards

```python
# Ensure data sent to third parties is minimized
async def send_to_analytics(event: AnalyticsEvent) -> None:
    # Remove PII before sending
    sanitized = {
        "event_type": event.type,
        "timestamp": event.timestamp,
        "user_id_hash": hash_user_id(event.user_id),  # Pseudonymized
        "properties": remove_pii(event.properties),
    }
    await analytics_client.track(sanitized)
```

---

## Related Documentation

- [Security Architecture](security-architecture.md) – Data protection
- [Logging Standards](logging-standards.md) – PII in logs
- [Data Architecture](data-architecture.md) – Database design
