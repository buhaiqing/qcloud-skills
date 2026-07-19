# PostgreSQL SecOps Security Operations Module

Security operations patterns for Tencent Cloud PostgreSQL.

---

## 1. Security Audit Logs

### CAM Audit Log Query

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_postgres_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)

    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100

    response = client.LookUpEvents(request)

    postgres_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'postgres' in e.Resources[0].ResourceName.lower()
        or 'postgresql' in e.Resources[0].ResourceName.lower()
    ]

    return postgres_events
```

### High-Risk PostgreSQL Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| DeleteDatabase | Critical | Alert before deletion |
| DeleteAccount | High | Alert before deletion |
| ModifyDBInstanceSpec (scale down) | High | Alert on spec reduction |
| ResetPassword | High | Alert, credential change |
| ModifySecurityGroup | High | Alert on SG change |
| RestartDatabase | High | Alert, service disruption |

---

## 2. Credential Rotation Strategy

### Rotation Schedule

| Credential | Rotation Frequency | Method |
|------------|-------------------|--------|
| PostgreSQL Password | 90 days | ResetAccountPassword via SDK |
| Database Accounts | 90 days | ModifyAccountAttributes via SDK |
| TENCENTCLOUD API Key | 90 days | CAM console rotation |

### Rotation Process

```yaml
credential_rotation:
  process:
    step_1: "Generate new password (complex, ≥16 chars, mixed case, digits, symbols)"
    step_2: "Update application connection strings"
    step_3: "Test PostgreSQL connectivity"
    step_4: "Verify no replication lag"
    step_5: "Document rotation in audit log"

  safety:
    - Never delete accounts before verifying new credentials work
    - Use pg_hba.conf for host-based access control
    - Keep old password for rollback (24 hours)
```

---

## 3. Network Security

### Security Group Checklist

| Check | Rule | Status |
|-------|------|--------|
| PostgreSQL not public | Port 5432 not exposed to 0.0.0.0/0 | Review |
| VPC isolation | PostgreSQL in private subnet | Review |
| SSL enforced | Require SSL for remote connections | Review |
| No wildcard Host accounts | Host='*' only for specific use cases | Review |

### Security Group Audit

```bash
# Check PostgreSQL instance network configuration
tccli postgres DescribeDBInstances --DBInstanceId postgres-xxxx
# Check:VpcId (should be set), DBInstanceNetInfo for private IP

# Verify security group
tccli postgres DescribeSecurityGroup --DBInstanceId postgres-xxxx
```

---

## 4. High-Risk Operations

### DeleteDatabase — Safety Gate

1. **MUST** warn: all data in the database will be permanently lost
2. **MUST** list all tables and schemas
3. **MUST** verify: recent backup exists
4. **MUST** confirm: user input `CONFIRM DELETE {{database_name}}`

### DeleteAccount — Safety Gate

1. **MUST** list all databases the account can access
2. **MUST** warn: privileges and data access will be revoked
3. **MUST** check: no active application connections
4. **MUST** confirm: user input `CONFIRM DELETE {{account_name}}`

### ModifyDBInstanceSpec (Scale Down) — Safety Gate

1. **MUST** warn: performance may degrade
2. **MUST** verify: current CPU < 50% and connections < 50% of target
3. **MUST** recommend: scale during maintenance window

### ResetPassword — Safety Gate

1. **MUST** warn: existing connections will be terminated
2. **MUST** verify: new password meets complexity requirements (≥8 chars, mixed case, digits, symbols)
3. **MUST** recommend: rotate credentials in applications immediately
4. **MUST NOT** set Host='*' with simple passwords

### RestartDatabase — Safety Gate

1. **MUST** warn: database will be unavailable during restart
2. **MUST** verify: no long-running transactions
3. **MUST** check: maintenance window or schedule during low-traffic period

---

## 5. Compliance Checklist

### PostgreSQL Security Compliance

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | VPC isolation enabled | ✓/✗ | PostgreSQL in private subnet |
| 2 | No public endpoint | ✓/✗ | Private IP only |
| 3 | SSL connections required | ✓/✗ | |
| 4 | No wildcard Host='*' accounts | ✓/✗ | |
| 5 | Security Group restricts access | ✓/✗ | |
| 6 | CAM least privilege for accounts | ✓/✗ | |
| 7 | Passwords rotated < 90 days | ✓/✗ | |
| 8 | CloudAudit enabled for PostgreSQL | ✓/✗ | |
| 9 | Backup enabled and tested | ✓/✗ | |

---

## 6. Emergency Contacts

- On-call DBA: [Contact info]
- Security team: [Contact info]
- Cloud Support: [ Tencent Cloud support ticket ]

---

## References

- [PostgreSQL API Documentation](https://cloud.tencent.com/document/api/238)
- [CloudAudit API](https://cloud.tencent.com/document/product/1026)
- [CAM Policy Guide](https://cloud.tencent.com/document/product/598)
