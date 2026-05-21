# VPC SecOps Security Operations Module

## 1. Security Audit Logs

### CloudAudit Integration

```python
from tencentcloud.cloudaudit import cloudaudit_client, models

def query_vpc_audit_logs(start_time: str, end_time: str) -> list:
    client = cloudaudit_client.CloudauditClient(cred, region)
    
    request = models.LookUpEventsRequest()
    request.StartTime = start_time
    request.EndTime = end_time
    request.MaxResults = 100
    
    response = client.LookUpEvents(request)
    
    vpc_events = [
        {
            'event_id': e.EventId,
            'action': e.EventName,
            'resource': e.Resources[0].ResourceName,
            'user': e.Username,
            'time': e.EventTime,
            'result': e.ErrorCode
        }
        for e in response.Events
        if 'vpc' in e.Resources[0].ResourceName.lower()
    ]
    
    return vpc_events
```

### Security-Relevant VPC Actions

| Action | Risk Level | Monitor |
|--------|------------|---------|
| CreateVpc | Medium | Track new VPCs |
| DeleteVpc | High | Alert before deletion |
| CreateSubnet | Low | Track subnet creation |
| DeleteSubnet | High | Alert before deletion |
| CreateNetworkAcl | Medium | Review ACL rules |
| ModifyNetworkAcl | High | Alert on rule changes |
| CreateFlowLog | Low | Verify logging enabled |

### Audit Log Analysis

```python
def analyze_vpc_audit_logs(events: list) -> dict:
    report = {'warnings': [], 'action_counts': {}}
    
    high_risk_actions = ['DeleteVpc', 'DeleteSubnet', 'ModifyNetworkAcl']
    high_risk_events = [e for e in events if e['action'] in high_risk_actions]
    
    if len(high_risk_events) > 0:
        report['warnings'].append(
            f"⚠️ {len(high_risk_events)} high-risk VPC actions detected"
        )
    
    failed_events = [e for e in events if e['result'] != '0']
    if len(failed_events) > 0:
        report['warnings'].append(
            f"⚠️ {len(failed_events)} failed VPC operations - possible permission issues"
        )
    
    return report
```

## 2. Credential Rotation Strategy

### Rotation Schedule for VPC

| Credential | Rotation Frequency | Reminder | Method |
|------------|-------------------|----------|--------|
| API SecretKey | 90 days | 80 days | Generate new, test, disable old |
| SSH Key (for VPN) | 180 days | 170 days | Generate new, remove old |

### Rotation Process

```yaml
credential_rotation:
  process:
    step_1: "Generate new SecretKey in CAM console"
    step_2: "Update environment variables: TENCENTCLOUD_SECRET_KEY"
    step_3: "Test VPC API access: tccli vpc DescribeVpcs"
    step_4: "Disable old SecretKey"
    step_5: "Document rotation in audit log"
  
  safety:
    - Never delete old key before verifying new key
    - Keep old key for rollback (24 hours)
```

## 3. Security Group Best Practices

### VPC Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| No 0.0.0.0/0 inbound (except HTTP/HTTPS) | ✓/✗ | |
| SSH (22) restricted to office IPs | ✓/✗ | |
| Database ports (3306, 5432) not public | ✓/✗ | |
| VPC Flow Logs enabled | ✓/✗ | |
| Network ACL configured per tier | ✓/✗ | |

### Security Group Audit

```bash
# Audit security groups in VPC
tccli vpc DescribeSecurityGroups --Filters "[{\"Name\":\"vpc-id\",\"Values\":[\"vpc-xxx\"]}]"

# Check for public exposure
tccli vpc DescribeSecurityGroups | jq '.Response.SecurityGroupSet[].InboundSet[] | select(.CidrBlock == "0.0.0.0/0")'
```

## 4. Network Isolation Patterns

### Recommended VPC Architecture

```
Internet → CLB (public subnet)
              ↓
         App Servers (private subnet) → NAT Gateway → Internet (outbound)
              ↓
         Database (private subnet, no outbound)
```

### Network ACL Rules per Tier

| Tier | Inbound | Outbound |
|------|---------|----------|
| Public | HTTP/HTTPS from 0.0.0.0/0 | To private subnet |
| App | From public subnet | To DB subnet + NAT |
| DB | From app subnet only | None |

## 5. Compliance Checklist

### VPC Security Compliance

| # | Check | Status |
|---|-------|--------|
| 1 | VPC Flow Logs enabled | ✓/✗ |
| 2 | Security Groups reviewed | ✓/✗ |
| 3 | Network ACLs per tier | ✓/✗ |
| 4 | No public database exposure | ✓/✗ |
| 5 | SSH restricted to VPN/IPs | ✓/✗ |
| 6 | CAM least privilege for VPC | ✓/✗ |
| 7 | Credential rotation < 90 days | ✓/✗ |
| 8 | Audit logs reviewed weekly | ✓/✗ |

## References

- [SecOps Security Operations](../qcloud-skill-generator/references/secops-security-operations.md)