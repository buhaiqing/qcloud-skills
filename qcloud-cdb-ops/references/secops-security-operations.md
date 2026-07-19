# CDB SecOps Security Operations Module

Security operations patterns for Tencent Cloud CDB (MySQL/PostgreSQL).

---

## 1. Security Audit Logs

### CAM Audit Log Query

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_cdb_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)

    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100

    response = client.LookUpEvents(request)

    cdb_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'cdb' in e.Resources[0].ResourceName.lower()
    ]

    return cdb_events
```

### High-Risk CDB Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| DeleteDatabase | Critical | Alert before deletion |
| DeleteAccount | High | Alert before deletion |
| ModifyDBInstanceSpec (scale down) | High | Alert on spec reduction |
| ResetPassword | High | Alert on credential change |
| ModifyVPCVSecurityGroups | High | Alert on SG change |
| SetAutoRenew | Medium | Track billing changes |

---

## 2. Credential Rotation Strategy

### Rotation Schedule

| Credential | Rotation Frequency | Reminder | Method |
|------------|-------------------|----------|--------|
| CDB Root Password | 90 days | 80 days | ModifyDBInstancePassword via SDK |
| Database Accounts | 90 days | 80 days | ModifyAccountPrivileges via SDK |

### Rotation Process

```yaml
credential_rotation:
  process:
    step_1: "Generate new password (complex, ≥16 chars)"
    step_2: "Update application connection strings"
    step_3: "Test database connectivity"
    step_4: "Verify no replication lag"
    step_5: "Disable old account or rotate password"
    step_6: "Document rotation in audit log"

  safety:
    - Never delete accounts before verifying new credentials work
    - Keep old password for rollback window (24 hours)
    - Use CAM least-privilege for application accounts
```

---

## 3. Network Security

### Security Group Checklist

| Check | Rule | Status |
|-------|------|--------|
| CDB not public | Port 3306/5432 not exposed to 0.0.0.0/0 | Review |
| VPC isolation | CDB in private subnet | Review |
| SSL enforced | Require SSL for remote connections | Review |
| No 0.0.0.0/0 inbound | Except via CLB/NAT | Review |

### Security Group Audit

```python
from tencentcloud.cdb.v20170320 import cdb_client, models

def audit_cdb_security_groups(cdb_instance_id: str) -> list:
    # Check if CDB is in VPC and not publicly accessible
    # Use DescribeDBInstances to check:
    # - VpcId (should be set, not empty)
    # - WanStatus (should be "Off" for no public endpoint)
    pass
```

---

## 4. High-Risk Operations

### DeleteDatabase — Safety Gate

1. **MUST** confirm: database name shown to user
2. **MUST** warn: all data permanently lost
3. **MUST** check: no active connections (DescribeDBCfg)
4. **MUST** verify: recent backup exists
5. Require user input: `CONFIRM DELETE {{database_name}}`

### DeleteAccount — Safety Gate

1. **MUST** list all databases the account can access
2. **MUST** warn: privileges and data access will be revoked
3. **MUST** check: no active application connections
4. Require user input: `CONFIRM DELETE {{account_name}}`

### ModifyDBInstanceSpec (Scale Down) — Safety Gate

1. **MUST** warn: performance may degrade
2. **MUST** verify: current CPU < 50% and connections < 50% of target
3. **MUST** recommend: scale up during maintenance window

### ResetPassword — Safety Gate

1. **MUST** warn: existing connections will be terminated
2. **MUST** verify: new password meets complexity requirements (≥16 chars, mixed case, digits, symbols)
3. **MUST** recommend: rotate credentials in applications immediately after

---

## 5. Compliance Checklist

### CDB Security Compliance

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | VPC isolation enabled | ✓/✗ | CDB in private subnet |
| 2 | No public endpoint (WanStatus=Off) | ✓/✗ | |
| 3 | SSL connections required | ✓/✗ | |
| 4 | CAM least privilege for accounts | ✓/✗ | |
| 5 | Passwords rotated < 90 days | ✓/✗ | |
| 6 | CloudAudit enabled for CDB | ✓/✗ | |
| 7 | Security Group restricts access | ✓/✗ | |
| 8 | Backup enabled and tested | ✓/✗ | |

---

## 6. Emergency Contacts

- On-call DBA: [Contact info]
- Security team: [Contact info]
- Cloud Support: [ Tencent Cloud support ticket ]

---

## References

- [CDB API Documentation](https://cloud.tencent.com/document/api/236)
- [CloudAudit API](https://cloud.tencent.com/document/product/1026)
- [CAM Policy Guide](https://cloud.tencent.com/document/product/598)
