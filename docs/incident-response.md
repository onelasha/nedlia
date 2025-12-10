# Incident Response Runbook

Procedures for handling production incidents at Nedlia.

## Severity Levels

| Level | Name     | Description                                   | Response Time | Examples                            |
| ----- | -------- | --------------------------------------------- | ------------- | ----------------------------------- |
| SEV1  | Critical | Complete service outage, data loss risk       | 15 min        | API down, database corruption       |
| SEV2  | Major    | Significant degradation, major feature broken | 30 min        | Validation failing, high error rate |
| SEV3  | Minor    | Limited impact, workaround available          | 4 hours       | Slow responses, minor feature bug   |
| SEV4  | Low      | Minimal impact, cosmetic issues               | 24 hours      | UI glitch, typo in error message    |

---

## On-Call Rotation

### Schedule

- **Primary**: First responder, handles initial triage
- **Secondary**: Backup if primary unavailable
- **Escalation**: Engineering lead for SEV1/SEV2

### Responsibilities

1. Acknowledge alerts within response time
2. Triage and assess severity
3. Communicate status to stakeholders
4. Coordinate resolution
5. Document incident

---

## Incident Response Process

### 1. Detection & Alert

```
Alert Triggered
     │
     ▼
┌─────────────┐
│ On-Call     │◄── PagerDuty/Slack notification
│ Acknowledges│
└─────────────┘
     │
     ▼
┌─────────────┐
│ Initial     │
│ Assessment  │
└─────────────┘
```

### 2. Triage Checklist

- [ ] What is the impact? (users affected, revenue impact)
- [ ] When did it start?
- [ ] What changed recently? (deployments, config changes)
- [ ] Is it getting worse?
- [ ] Assign severity level

### 3. Communication

**SEV1/SEV2**: Create incident channel immediately

```
Slack: #incident-YYYY-MM-DD-brief-description
```

**Status Update Template**:

```
🔴 INCIDENT: [Brief description]
Severity: SEV[1-4]
Status: Investigating | Identified | Monitoring | Resolved
Impact: [Who/what is affected]
Started: [Time UTC]
Next update: [Time UTC]
```

### 4. Investigation

#### Quick Checks

```bash
# Check service health
curl https://api.nedlia.com/health

# Check recent deployments
aws lambda list-functions --query 'Functions[*].[FunctionName,LastModified]'

# Check error rates (CloudWatch)
aws cloudwatch get-metric-statistics \
  --namespace Nedlia/API \
  --metric-name ErrorCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

#### CloudWatch Insights Queries

```sql
-- Recent errors
fields @timestamp, @message, error_code, correlation_id
| filter level = "ERROR"
| sort @timestamp desc
| limit 100

-- Error rate by endpoint
fields @timestamp, path, status_code
| filter status_code >= 500
| stats count() by bin(5m), path

-- Slow requests
fields @timestamp, path, duration_ms
| filter duration_ms > 5000
| sort duration_ms desc
| limit 50
```

### 5. Mitigation

#### Rollback Deployment

```bash
# Lambda rollback
aws lambda update-function-code \
  --function-name nedlia-api \
  --s3-bucket nedlia-deployments \
  --s3-key previous-version.zip

# Or use alias
aws lambda update-alias \
  --function-name nedlia-api \
  --name prod \
  --function-version 42  # Previous version
```

#### Feature Flag Kill Switch

```bash
# Disable problematic feature
aws ssm put-parameter \
  --name /nedlia/prod/feature-flags/validation-v2 \
  --value "false" \
  --overwrite
```

#### Scale Up

```bash
# Increase Lambda concurrency
aws lambda put-function-concurrency \
  --function-name nedlia-api \
  --reserved-concurrent-executions 500

# Scale Fargate service
aws ecs update-service \
  --cluster nedlia-prod \
  --service api \
  --desired-count 10
```

### 6. Resolution

- [ ] Root cause identified
- [ ] Fix deployed or workaround in place
- [ ] Monitoring confirms resolution
- [ ] Affected users notified
- [ ] Incident channel updated with resolution

---

## Common Incidents

### Database Connection Issues

**Symptoms**: 500 errors, "connection refused" in logs

**Investigation**:

```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;
```

**Mitigation**:

1. Kill long-running queries: `SELECT pg_terminate_backend(pid);`
2. Increase connection pool size
3. Check for connection leaks in code

### High Error Rate

**Symptoms**: Spike in 5xx errors

**Investigation**:

```sql
-- CloudWatch Insights
fields @timestamp, @message, error_code, path
| filter level = "ERROR"
| stats count() by error_code, path
| sort count desc
```

**Mitigation**:

1. Check recent deployments
2. Rollback if deployment-related
3. Check downstream services

### Memory/CPU Exhaustion

**Symptoms**: Slow responses, OOM errors

**Investigation**:

```bash
# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=nedlia-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 60 \
  --statistics Maximum
```

**Mitigation**:

1. Increase Lambda memory
2. Identify memory leaks
3. Add request timeouts

### Third-Party Service Outage

**Symptoms**: Errors related to external service

**Investigation**:

1. Check service status page
2. Check our circuit breaker state
3. Review timeout/retry logs

**Mitigation**:

1. Enable fallback/cached responses
2. Communicate to users
3. Wait for service recovery

---

## Escalation Path

```
On-Call Primary
     │
     │ (15 min no response or SEV1)
     ▼
On-Call Secondary
     │
     │ (SEV1 or major customer impact)
     ▼
Engineering Lead
     │
     │ (Data breach, legal implications)
     ▼
CTO / Executive Team
```

---

## Post-Incident

### Postmortem Template

```markdown
# Incident Postmortem: [Title]

**Date**: YYYY-MM-DD
**Duration**: X hours Y minutes
**Severity**: SEV[1-4]
**Author**: [Name]

## Summary

[2-3 sentence summary of what happened]

## Impact

- Users affected: [number/percentage]
- Revenue impact: [if applicable]
- Data impact: [if applicable]

## Timeline (UTC)

| Time  | Event                               |
| ----- | ----------------------------------- |
| 14:00 | Alert triggered for high error rate |
| 14:05 | On-call acknowledged                |
| 14:15 | Root cause identified               |
| 14:30 | Fix deployed                        |
| 14:45 | Monitoring confirmed resolution     |

## Root Cause

[Detailed explanation of what caused the incident]

## Resolution

[What was done to fix it]

## Lessons Learned

### What went well

- [Item 1]
- [Item 2]

### What could be improved

- [Item 1]
- [Item 2]

## Action Items

| Action                          | Owner  | Due Date   |
| ------------------------------- | ------ | ---------- |
| Add monitoring for X            | @alice | 2024-01-20 |
| Implement circuit breaker for Y | @bob   | 2024-01-25 |
```

### Postmortem Meeting

- Schedule within 48 hours of SEV1/SEV2
- Blameless culture: focus on systems, not individuals
- Document action items with owners and due dates

---

## Tools & Access

| Tool        | Purpose                    | Access                     |
| ----------- | -------------------------- | -------------------------- |
| PagerDuty   | Alerting, on-call schedule | All engineers              |
| Slack       | Communication              | #incidents, #oncall        |
| AWS Console | Infrastructure             | IAM roles                  |
| CloudWatch  | Logs, metrics              | AWS Console                |
| Grafana     | Dashboards                 | https://grafana.nedlia.com |
| StatusPage  | External status            | https://status.nedlia.com  |

---

## Related Documentation

- [Observability](observability.md) – Monitoring and alerting
- [Resilience Patterns](resilience-patterns.md) – Circuit breakers, fallbacks
- [Deployment](deployment.md) – Rollback procedures
- [Security Architecture](security-architecture.md) – Security incidents
