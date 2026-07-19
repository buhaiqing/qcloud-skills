# Redis SecOps Security Operations Module

Security operations patterns for Tencent Cloud Redis.

---

## 1. Security Audit Logs

### CAM Audit Log Query

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_redis_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)

    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100

    response = client.LookUpEvents(request)

    redis_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'redis' in e.Resources[0].ResourceName.lower()
    ]

    return redis_events
```

### High-Risk Redis Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| DeleteInstance | Critical | Alert before deletion, data loss |
| FlushInstance | Critical | Alert, full data loss |
| ModifyInstanceAccount | High | Alert, access change |
| ResetPassword | High | Alert, credential change |
| ModifyVPCVSecurityGroups | High | Alert on SG change |
| IsolateInstance | High | Alert, service disruption |

### Data-Plane Audit Note

> ⚠️ FLUSHALL/FLUSHDB are **data-plane operations** — they do NOT appear in CAM audit logs. Always monitor via SlowLog and command stats.

---

## 2. Credential Rotation Strategy

### Rotation Schedule

| Credential | Rotation Frequency | Method |
|------------|-------------------|--------|
| Redis Password | 90 days | ModifyInstanceAccount via SDK |
| TENCENTCLOUD API Key | 90 days | CAM console rotation |

### Rotation Process

```yaml
credential_rotation:
  process:
    step_1: "Generate new password (complex, ≥16 chars)"
    step_2: "Update application connection strings"
    step_3: "Test Redis connectivity"
    step_4: "Verify no replication lag"
    step_5: "Document rotation in audit log"

  safety:
    - Never flush before verifying new credentials work
    - Use ACL rules for least-privilege access
    - Keep old password temporarily for rollback (24 hours)
```

---

## 3. Network Security

### Security Group Checklist

| Check | Rule | Status |
|-------|------|--------|
| Redis not public | Port 6379 not exposed to 0.0.0.0/0 | Review |
| VPC isolation | Redis in private subnet | Review |
| No-password-free access | RequireAuth=yes | Review |
| SSL enforced | Encrypt=true in connection | Review |

### Security Group Audit

```bash
# Check Redis security group configuration
tccli redis DescribeSecurityGroupList --InstanceId crs-xxxx

# Verify no public access
tccli redis DescribeInstances --InstanceIds '["crs-xxxx"]'
# Check: WanStatus (should be 0 for no public)
```

---

## 4. High-Risk Operations

### DeleteInstance — Safety Gate

1. **MUST** warn: all data permanently lost
2. **MUST** verify: latest backup exists
3. **MUST** check: no active connections
4. **MUST** confirm: user input `CONFIRM DELETE {{instance_id}}`

### FlushInstance — Safety Gate

1. **MUST** warn: ALL data will be permanently erased
2. **MUST** verify: backup exists or is in progress
3. **MUST** confirm: user input `CONFIRM FLUSH {{instance_id}}`
4. **MUST NOT** proceed without explicit user assent

### ModifyInstanceAccount — Safety Gate

1. **MUST** warn: existing accounts may be affected
2. **MUST** list all accounts and their privileges
3. **MUST** verify: no application disruption

### ResetPassword — Safety Gate

1. **MUST** warn: existing connections will be terminated
2. **MUST** verify: new password meets complexity requirements (≥8 chars, mixed case, digits)
3. **MUST** recommend: rotate credentials in applications immediately

### IsolateInstance — Safety Gate

1. **MUST** warn: instance will be isolated, data may be lost after retention period
2. **MUST** check: data has been backed up or exported

---

## 5. Compliance Checklist

### Redis Security Compliance

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | VPC isolation enabled | ✓/✗ | Redis in private subnet |
| 2 | No public endpoint | ✓/✗ | WanStatus=0 |
| 3 | Password authentication required | ✓/✗ | RequireAuth enabled |
| 4 | SSL connections enforced | ✓/✗ | Encrypt=true |
| 5 | Security Group restricts access | ✓/✗ | |
| 6 | CAM least privilege for accounts | ✓/✗ | |
| 7 | Passwords rotated < 90 days | ✓/✗ | |
| 8 | CloudAudit enabled for Redis | ✓/✗ | |
| 9 | Backup enabled | ✓/✗ | |

---

## 6. Emergency Contacts

- On-call SRE: [Contact info]
- Security team: [Contact info]
- Cloud Support: [ Tencent Cloud support ticket ]

---

## References

- [Redis API Documentation](https://cloud.tencent.com/document/api/239)
- [CloudAudit API](https://cloud.tencent.com/document/product/1026)
- [CAM Policy Guide](https://cloud.tencent.com/document/product/598)
