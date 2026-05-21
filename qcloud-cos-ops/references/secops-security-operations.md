# COS SecOps Security Operations Module

## 1. Security Audit Logs

### COS Access Audit

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_cos_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)
    
    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    
    response = client.LookUpEvents(request)
    
    cos_events = [
        {
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime
        }
        for e in response.Events
        if 'cos' in e.Resources[0].ResourceName.lower()
    ]
    
    return cos_events
```

### High-Risk COS Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| PutBucketACL | High | Public access alert |
| PutBucketPolicy | High | Policy change alert |
| DeleteBucket | Critical | Pre-deletion alert |
| DeleteObject | High | Track deletions |

## 2. ACL Security

### ACL Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| Bucket ACL != public-read-write | ✓/✗ | |
| Object ACL properly set | ✓/✗ | |
| Bucket Policy reviewed | ✓/✗ | |
| No unauthorized public access | ✓/✗ | |

### Public Access Audit

```bash
tccli cos GetBucketACL --Bucket bucket-name | jq '.Response.ACL'

# Alert if ACL == public-read or public-read-write
```

## 3. Bucket Policy Security

### Recommended Bucket Policy

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": ["cos:GetObject"],
      "effect": "allow",
      "principal": {"qcs": ["qcs::cam::uin/123456:root"]},
      "resource": ["qcs::cos:*:*:bucket-name/*"]
    },
    {
      "action": ["cos:PutObject"],
      "effect": "allow",
      "principal": {"qcs": ["qcs::cam::uin/123456:root"]},
      "resource": ["qcs::cos:*:*:bucket-name/*"],
      "condition": {"ip_equal": {"qcs:ip": ["10.0.0.0/8"]}}
    }
  ]
}
```

## 4. Encryption

### Server-Side Encryption

| Encryption Type | Use Case |
|-----------------|----------|
| AES-256 | Default encryption |
| KMS | Sensitive data |

### Enable Encryption

```bash
tccli cos PutBucketEncryption --Bucket bucket-name \
  --EncryptionConfiguration '{"ServerSideEncryption":{"Algorithm":"AES256"}}'
```

## 5. Compliance Checklist

### COS Security Compliance

| # | Check | Status |
|---|-------|--------|
| 1 | Bucket ACL != public | ✓/✗ |
| 2 | Bucket Policy reviewed | ✓/✗ |
| 3 | Encryption enabled | ✓/✗ |
| 4 | Versioning enabled (critical buckets) | ✓/✗ |
| 5 | Access logging enabled | ✓/✗ |
| 6 | Lifecycle rules set | ✓/✗ |
| 7 | CAM least privilege | ✓/✗ |

## References

- [SecOps Security Operations](../qcloud-skill-generator/references/secops-security-operations.md)