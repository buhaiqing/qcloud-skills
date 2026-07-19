# Ckafka SecOps Security Operations Module

Security operations patterns for Tencent Cloud Ckafka.

---

## 1. Security Audit Logs

### CAM Audit Log Query

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_ckafka_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)

    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100

    response = client.LookUpEvents(request)

    ckafka_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'ckafka' in e.Resources[0].ResourceName.lower()
        or 'kafka' in e.Resources[0].ResourceName.lower()
    ]

    return ckafka_events
```

### High-Risk Ckafka Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| DeleteInstance | Critical | Alert before deletion, all topics lost |
| DeleteTopic | High | Alert, all messages lost |
| DeleteUser | High | Alert, access revoked |
| ResetPassword | High | Alert, credential change |
| ModifyTopic (reduce partitions) | High | Alert, data loss possible |
| ModifyInstanceAttributes (config) | Medium | Alert on config changes |

---

## 2. Credential Rotation Strategy

### Rotation Schedule

| Credential | Rotation Frequency | Method |
|------------|-------------------|--------|
| Ckafka SASL Users | 90 days | DeleteUser + CreateUser |
| TENCENTCLOUD API Key | 90 days | CAM console rotation |

### Rotation Process

```yaml
credential_rotation:
  process:
    step_1: "Create new SASL user with new password"
    step_2: "Update all producers/consumers with new credentials"
    step_3: "Verify message produce/consume works"
    step_4: "Delete old SASL user"
    step_5: "Document rotation in audit log"

  safety:
    - Never delete old user before verifying new credentials work
    - Keep old SASL user temporarily for rollback (24 hours)
    - Use ACLs to restrict permissions per user
```

---

## 3. ACL Security

### ACL Security Checklist

| Check | Rule | Status |
|-------|------|--------|
| No Host=* with Operation=ALL | Restrict to specific IPs | Review |
| ACL least privilege | Read/Write per topic, not full access | Review |
| SASL enabled | Plain or SCRAM authentication | Review |
| No plaintext connections | Use SSL/TLS | Review |

### ACL Audit

```bash
# List all ACLs
tccli ckafka DescribeACL --InstanceId ckafka-xxxx --TopicName topic-xxx

# Check for overly permissive ACLs
# Alert if: Host="*" AND Operation="ALL" AND Permission="ALLOW"
```

---

## 4. High-Risk Operations

### DeleteInstance — Safety Gate

1. **MUST** warn: all topics, messages, consumer groups, and ACLs will be permanently deleted
2. **MUST** list all topics, partitions, and consumer groups
3. **MUST** verify: no active producers or consumers
4. **MUST** confirm: user input `CONFIRM DELETE {{instance_id}}`

### DeleteTopic — Safety Gate

1. **MUST** warn: all messages and offsets will be permanently lost
2. **MUST** list all consumer groups and their lag
3. **MUST** verify: no active producers or consumers
4. **MUST** confirm: user input `CONFIRM DELETE {{topic_name}}`

### DeleteUser — Safety Gate

1. **MUST** list all ACLs associated with the user
2. **MUST** warn: all access for this user will be revoked
3. **MUST** verify: no active producers/consumers using this user

### ResetPassword — Safety Gate

1. **MUST** warn: all producers/consumers using this user will be disconnected
2. **MUST** recommend: update all consumers/producers immediately after

### ModifyTopic (Partition Reduction) — Safety Gate

1. **MUST** warn: messages in removed partitions will be lost
2. **MUST** verify: consumer group offsets are not affected
3. **MUST** check: no active replication

---

## 5. Compliance Checklist

### Ckafka Security Compliance

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | SASL authentication enabled | ✓/✗ | |
| 2 | SSL/TLS for connections | ✓/✗ | |
| 3 | ACLs with least privilege | ✓/✗ | |
| 4 | No Host=* with Operation=ALL | ✓/✗ | |
| 5 | CAM least privilege for API keys | ✓/✗ | |
| 6 | SASL users rotated < 90 days | ✓/✗ | |
| 7 | CloudAudit enabled for Ckafka | ✓/✗ | |
| 8 | No public internet access | ✓/✗ | VPC-only |

---

## 6. Emergency Contacts

- On-call SRE: [Contact info]
- Security team: [Contact info]
- Cloud Support: [ Tencent Cloud support ticket ]

---

## References

- [Ckafka API Documentation](https://cloud.tencent.com/document/api/597)
- [CloudAudit API](https://cloud.tencent.com/document/product/1026)
- [CAM Policy Guide](https://cloud.tencent.com/document/product/598)
