# Monitor SecOps Security Operations

## Overview

Security patterns for Monitor (云监控) operations.

---

## 1. CAM Permissions

### Minimum CAM Policy

```json
{
  "version": "2.0",
  "statement": [
    {
      "effect": "allow",
      "action": [
        "monitor:DescribeAlarmPolicies",
        "monitor:DescribeAlarmHistories",
        "monitor:GetMonitorData",
        "monitor:DescribeAllNamespaces"
      ],
      "resource": "*"
    },
    {
      "effect": "allow",
      "action": [
        "monitor:CreateAlarmPolicy",
        "monitor:ModifyAlarmPolicyInfo",
        "monitor:ModifyAlarmPolicyCondition"
      ],
      "resource": "*",
      "condition": {
        "string_equal": {
          "qcs:resource_tag": ["Environment:production"]
        }
      }
    },
    {
      "effect": "allow",
      "action": [
        "monitor:DeleteAlarmPolicy"
      ],
      "resource": "*",
      "condition": {
        "string_equal": {
          "qcs:user_name": ["approved_admin_users"]
        }
      }
    }
  ]
}
```

### Role-Based Access

| Role | Permissions | Use Case |
|------|--------------|----------|
| **Monitor-Viewer** | Describe*, GetMonitorData | Dashboard viewing |
| **Monitor-Operator** | CreatePolicy, BindPolicy | Alarm configuration |
| **Monitor-Admin** | DeletePolicy, ModifyAll | Full management |

---

## 2. Notification Security

### Webhook Security

| Requirement | Implementation |
|-------------|----------------|
| Authentication | HMAC signature or API key |
| HTTPS required | TLS 1.2+ encryption |
| IP whitelist | Restrict webhook IPs |
| Retry policy | Secure retry mechanism |

### Webhook Authentication Template

```yaml
webhook_security:
  authentication:
    type: hmac_sha256
    secret: "{{env.WEBHOOK_SECRET}}"
    header: "X-Signature"
    
  transport:
    protocol: https
    tls_version: 1.2
    
  ip_whitelist:
    enabled: true
    allowed_ips:
      - "10.0.0.0/8"  # Internal
```

---

## 3. Sensitive Metric Protection

### Metrics Classification

| Classification | Examples | Access Control |
|----------------|----------|----------------|
| **Public** | CPUUsage, MemUsage | All users |
| **Internal** | Connection count | Team members |
| **Sensitive** | Business revenue, user count | Restricted |

### Access Control Matrix

```yaml
metric_access_control:
  public_metrics:
    - CPUUsage
    - MemUsage
    - DiskUsage
    access: all
    
  internal_metrics:
    - ConnectionUsage
    - TrafficIn
    access: team_members
    
  sensitive_metrics:
    - BusinessRevenue
    - ActiveUsers
    access: administrators_only
```

---

## 4. Alarm Policy Security

### Policy Creation Checks

| Check | Requirement |
|-------|-------------|
| Naming convention | Must include Environment tag |
| Threshold validation | Within acceptable ranges |
| Notification validation | Approved channels only |

### Policy Modification Logging

```yaml
policy_modification_audit:
  events:
    - CreateAlarmPolicy
    - ModifyAlarmPolicyCondition
    - DeleteAlarmPolicy
    
  logging:
    enabled: true
    destination: CloudAudit
    
  alerts:
    - condition: "DeleteAlarmPolicy"
      notify: security_team
```

---

## 5. Credential Security

### API Key Management

| Practice | Implementation |
|----------|----------------|
| Environment variables | Use env vars, never hardcode |
| Masking | Never print SecretKey |
| Rotation | 90-day rotation cycle |
| CAM role | Prefer over static keys |

---

## 6. Compliance Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | CAM least privilege | ✓ |
| 2 | Webhook authentication | ✓ |
| 3 | HTTPS for notifications | ✓ |
| 4 | Sensitive metric restricted | ✓ |
| 5 | Policy modification logged | ✓ |
| 6 | Credentials masked | ✓ |
| 7 | Key rotation policy | ✓ |
| 8 | Audit logging enabled | ✓ |