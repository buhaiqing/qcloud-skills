# Monitor Well-Architected Assessment

## Overview

This document maps Monitor (云监控) operations to Tencent Cloud's Well-Architected Framework.

---

## Pillar 1: Reliability (可靠性)

### 1.1 Alarm Policy Redundancy

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Policy backup | ✓ | Export policy config via DescribeAlarmPolicy |
| Policy restore | ✓ | Recreate from exported config |
| Default policy | ✓ | SetDefaultAlarmPolicy for fallback |

### 1.2 Backup & Recovery

| Operation | Coverage | Method |
|-----------|----------|--------|
| Export alarm policies | ✓ | DescribeAlarmPolicies → JSON |
| Restore policies | ✓ | CreateAlarmPolicy from JSON |
| Notification templates | ✓ | DescribeAlarmNotices → JSON |

**Backup Flow:**

```bash
# Export all policies
tccli monitor DescribeAlarmPolicies --Module monitor > policies-backup.json

# Export notification templates
tccli monitor DescribeAlarmNotices --Module monitor > notices-backup.json

# Restore: CreateAlarmPolicy/CreateAlarmNotice from backup
```

### 1.3 Failure-Oriented Design

| Scenario | Runbook | Recovery |
|----------|---------|----------|
| Policy deleted accidentally | Recreate from backup | < 5min |
| Notification channel failure | Multi-channel fallback | Immediate |
| Metric collection gap | Agent restart, check interval | < 10min |

### 1.4 Safety Gates

**Delete Alarm Policy:**

1. ✓ Confirm: "Delete policy-xxx? All bindings will be removed."
2. ✓ Check bindings: Warn if policy has bound objects
3. ✓ Verify deletion: Check policy absent in DescribeAlarmPolicies

---

## Pillar 2: Security (安全性)

### 2.1 CAM Permissions

**Minimum CAM Policy for Monitor Operations:**

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "monitor:DescribeAlarmPolicies",
        "monitor:CreateAlarmPolicy",
        "monitor:ModifyAlarmPolicyInfo",
        "monitor:ModifyAlarmPolicyStatus",
        "monitor:DeleteAlarmPolicy"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "monitor:GetMonitorData",
        "monitor:DescribeAlarmHistories",
        "monitor:DescribeAllNamespaces"
      ],
      "effect": "allow",
      "resource": "*"
    },
    {
      "action": [
        "monitor:DescribeAlarmNotices",
        "monitor:CreateAlarmNotice",
        "monitor:ModifyAlarmNotice",
        "monitor:DeleteAlarmNotices"
      ],
      "effect": "allow",
      "resource": "*"
    }
  ]
}
```

### 2.2 Notification Security

| Requirement | Status | Guidance |
|-------------|--------|----------|
| Webhook authentication | ✓ | Use signed webhooks |
| SMS quota protection | ✓ | Monitor SMS usage |
| Email SPF/DKIM | ✓ | Tencent Cloud handles |
| Access control | ✓ | CAM policy for alarm viewing |

### 2.3 Sensitive Metric Masking

| Metric Type | Handling | Example |
|-------------|----------|---------|
| Business metrics | May need masking | Revenue, user count |
| Infrastructure metrics | No masking needed | CPU, memory |
| Security metrics | Restricted access | Auth failures |

---

## Pillar 3: Cost (成本)

### 3.1 Notification Cost Model

| Channel | Unit Cost | Monthly Estimate |
|---------|-----------|------------------|
| SMS | ¥0.05/msg | 100 alerts = ¥5 |
| Email | Free (within quota) | 0 |
| WeChat Work | Free | 0 |
| Voice call | ¥0.15/call | 10 calls = ¥1.5 |
| Webhook | Free | 0 |

### 3.2 Cost Optimization

| Optimization | Savings | Method |
|--------------|---------|--------|
| Suppress duplicates | Reduce SMS usage | Alarm storm handling |
| Batch notifications | Fewer messages | Aggregate alerts |
| Right channels | Free vs paid | Email/Webhook over SMS |
| Threshold tuning | Fewer false alerts | Reduce unnecessary alerts |

### 3.3 Budget Alert Rules

```yaml
notification_budget:
  sms_monthly_limit: 100
  sms_overage_warning: "SMS notifications exceed 100/month"
  
  cost_by_channel:
    critical: SMS + Voice + Email  # Always notify
    warning: Email + WeChat         # Free channels
    info: Email only                # Lowest cost
```

---

## Pillar 4: Efficiency (效率)

### 4.1 Batch Operations

| Operation | Batch Support | Implementation |
|-----------|---------------|----------------|
| DeleteAlarmNotices | ✓ | Batch delete by IDs |
| DescribeAlarmPolicies | ✓ | Filter + pagination |
| BindingPolicyObject | ✓ | Batch bind objects |
| UnBindingAllPolicyObject | ✓ | Remove all bindings |

### 4.2 Automation Integration

| Integration | Support | Usage |
|-------------|---------|-------|
| CI/CD alerting | ✓ | Pipeline failure alerts |
| Terraform | ✓ | Policy as code |
| Scheduled ops | ✓ | Maintenance window alerts |

### 4.3 API Optimization

| Optimization | Method | Benefit |
|--------------|--------|---------|
| Pagination | Use Limit/Offset | Reduce payload |
| Filtering | Namespace filter | Targeted queries |
| Caching | Cache namespace list | Reduce API calls |

---

## Assessment Checklist

| Pillar | Requirement | Status |
|--------|-------------|--------|
| Reliability | Policy backup | ✓ Config export |
| Reliability | Policy restore | ✓ Create from backup |
| Reliability | Safety gates | ✓ Delete confirmation |
| Security | CAM permissions | ✓ Policy provided |
| Security | Notification security | ✓ Webhook guidance |
| Security | Access control | ✓ CAM enforcement |
| Cost | Channel costs | ✓ Pricing table |
| Cost | Optimization | ✓ Suppress/batch |
| Cost | Budget alerts | ✓ Monthly limits |
| Efficiency | Batch operations | ✓ Multi-object APIs |
| Efficiency | Automation | ✓ CI/CD/Terraform |
| Efficiency | API optimization | ✓ Pagination/filtering |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-monitor-ops` |
| `product` | `monitor` |
| Finding `id` pattern | `monitor-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Alarm coverage / SLO sections |
| `security` | N/A (typically skipped) |
| `cost` | Idle metric / utilization sections |
| `efficiency` | Dashboard / automation sections |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local “Score Calculation” sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-monitor-ops",
  "product": "monitor",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "monitor-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "No alarm on critical metric",
          "evidence": "Production CVM without CPU alarm policy",
          "recommendation": "Create alarm policy; bind to resource group",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 88,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Create alarm policy; bind to resource group",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli monitor GetMonitorData --Namespace QCE/CVM (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
