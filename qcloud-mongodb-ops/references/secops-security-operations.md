# MongoDB SecOps Security Operations Module

Security operations patterns for Tencent Cloud MongoDB.

---

## 1. Security Audit Logs

### CAM Audit Log Query

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_mongodb_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)

    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100

    response = client.LookUpEvents(request)

    mongodb_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'mongodb' in e.Resources[0].ResourceName.lower()
        or 'cmongo' in e.Resources[0].ResourceName.lower()
    ]

    return mongodb_events
```

### High-Risk MongoDB Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| DropDatabase | Critical | Alert before deletion |
| DropCollection | Critical | Alert, data loss |
| DeleteCluster | High | Alert, service loss |
| ResetPassword | High | Alert, credential change |
| ModifyDBInstanceSpec | High | Alert on spec change |
| SetBackupStrategy | Medium | Track backup config |

---

## 2. Credential Rotation Strategy

### Rotation Schedule

| Credential | Rotation Frequency | Method |
|------------|-------------------|--------|
| MongoDB Root Password | 90 days | ResetAccountPassword via SDK |
| Database Accounts | 90 days | UpdateAccountPassword via SDK |
| TENCENTCLOUD API Key | 90 days | CAM console rotation |

### Rotation Process

```yaml
credential_rotation:
  process:
    step_1: "Generate new password (complex, ≥16 chars)"
    step_2: "Update application connection strings"
    step_3: "Test MongoDB connectivity"
    step_4: "Verify no active operations blocked"
    step_5: "Document rotation in audit log"

  safety:
    - Never delete accounts before verifying new credentials work
    - Use CAM least-privilege for application accounts
    - Keep old password for rollback (24 hours)
```

---

## 3. Network Security

### Security Group Checklist

| Check | Rule | Status |
|-------|------|--------|
| MongoDB not public | Port 27017 not exposed to 0.0.0.0/0 | Review |
| VPC isolation | MongoDB in private subnet | Review |
| SSL enforced | Require SSL for remote connections | Review |
| Whitelist configured | IP allowlist set correctly | Review |

### Security Group Audit

```bash
# Check MongoDB instance network configuration
tccli mongodb DescribeDBInstances --InstanceIds '["cmgo-xxxx"]'
# Check: VpcId (should be set), Vip (should be private)

# Verify security group
tccli mongodb DescribeSecurityGroupAssociation --InstanceId cmgo-xxxx
```

---

## 4. High-Risk Operations

### DropDatabase — Safety Gate

1. **MUST** warn: entire database and all collections will be permanently deleted
2. **MUST** list all collections in the database
3. **MUST** verify: recent backup exists
4. **MUST** confirm: user input `CONFIRM DROP {{database_name}}`

### DropCollection — Safety Gate

1. **MUST** warn: all documents in the collection will be permanently deleted
2. **MUST** verify: backup of collection exists
3. **MUST** confirm: user input `CONFIRM DROP {{collection_name}}`

### DeleteCluster — Safety Gate

1. **MUST** warn: entire cluster and all databases will be terminated
2. **MUST** list all databases and their sizes
3. **MUST** verify: all data has been backed up
4. **MUST** confirm: user input `CONFIRM DELETE {{cluster_id}}`

### ResetPassword — Safety Gate

1. **MUST** warn: existing connections will be terminated
2. **MUST** verify: new password meets complexity requirements (≥8 chars, mixed case, digits)
3. **MUST** recommend: rotate credentials in applications immediately

---

## 5. Compliance Checklist

### MongoDB Security Compliance

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | VPC isolation enabled | ✓/✗ | MongoDB in private subnet |
| 2 | No public endpoint | ✓/✗ | Vip is private |
| 3 | SSL connections required | ✓/✗ | |
| 4 | Whitelist properly configured | ✓/✗ | |
| 5 | CAM least privilege for accounts | ✓/✗ | |
| 6 | Passwords rotated < 90 days | ✓/✗ | |
| 7 | CloudAudit enabled for MongoDB | ✓/✗ | |
| 8 | TDE (Transparent Data Encryption) enabled | ✓/✗ | |
| 9 | Backup enabled and tested | ✓/✗ | |

---

## 6. Emergency Contacts

- On-call DBA: [Contact info]
- Security team: [Contact info]
- Cloud Support: [ Tencent Cloud support ticket ]

---

## References

- [MongoDB API Documentation](https://cloud.tencent.com/document/api/240)
- [CloudAudit API](https://cloud.tencent.com/document/product/1026)
- [CAM Policy Guide](https://cloud.tencent.com/document/product/598)
