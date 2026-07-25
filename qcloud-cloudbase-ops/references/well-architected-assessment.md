# CloudBase Well-Architected Assessment

## Overview

This document provides a four-pillar assessment framework for CloudBase (云开发) based on Tencent Cloud's Well-Architected Framework.

## Reliability (可靠性)

### Strengths

| Practice | Description |
|----------|-------------|
| Environment isolation | Each environment is fully isolated with independent database, storage, and functions |
| Automatic backups | Database collections are backed up automatically |
| CDN-backed static hosting | Static assets served via CDN with global edge nodes |
| Async operations | Long-running operations (env creation) can be polled and monitored |

### Concerns

| Risk | Mitigation |
|------|-----------|
| No multi-environment HA | Use multiple envs in different regions; no built-in failover |
| No point-in-time DB restore | Export data before destructive operations |
| No read replicas (basic tier) | Upgrade to higher-tier packages for production |

### Assessment Questions

- [ ] Are multiple environments used (dev/staging/prod isolation)?
- [ ] Is database data exported before DeleteEnv?
- [ ] Are static assets backed up separately?
- [ ] Is there a disaster recovery plan?

## Security (安全性)

### Strengths

| Practice | Description |
|----------|-------------|
| Auth domains (安全域名) | Browser access restricted to whitelisted domains |
| Database ACL | Per-collection permission control |
| CAM integration | Uses Tencent Cloud CAM for API access control |
| API key rotation | Keys can be revoked and recreated |

### Concerns

| Risk | Mitigation |
|------|-----------|
| API key SecretKey shown once only | Save immediately at creation; use env vars |
| Database ACL defaults to admin | Set least-privilege ACL per collection |
| No IP whitelist | Use auth domains for browser access control |

### Assessment Questions

- [ ] Are auth domains configured to restrict browser access?
- [ ] Is database ACL set per collection (not default admin)?
- [ ] Are API keys stored securely (env vars, not hardcoded)?
- [ ] Is the principle of least privilege applied?

## Cost (成本)

### Strengths

| Practice | Description |
|----------|-------------|
| Resource point billing | Single unit for all consumption types |
| Pay-as-you-go | No upfront commitment; scale to zero |
| Included quotas | Basic tier includes DB reads/writes, storage, CDN |

### Concerns

| Risk | Mitigation |
|------|-----------|
| Unused environments | Delete dev/test envs when not needed |
| Over-provisioning | Start with basic tier; upgrade only when needed |
| CDN traffic spikes | Set budget alerts; use resource packages |

### Assessment Questions

- [ ] Is the billing model (resource points vs traditional) appropriate for the workload?
- [ ] Are unused environments deleted promptly?
- [ ] Are usage metrics monitored via DescribeCurveData?
- [ ] Are budget alerts configured?

### Cost Optimization Actions

| Action | Benefit | Priority |
|--------|---------|----------|
| Switch to resource point billing | Unified, often cheaper for mixed workloads | High if usage is unbalanced |
| Delete unused environments | Immediate savings | High |
| Use resource packages | Discount for predictable usage | Medium |
| Right-size by monitoring | Avoid over-provisioning | Medium |

## Efficiency (效率)

### Strengths

| Practice | Description |
|----------|-------------|
| One-click deployment | Deploy static sites and functions without server management |
| CloudBase Build Service | CI/CD integration for frontend builds |
| Integrated storage | No separate COS configuration needed |
| Mini-program support | Native integration with WeChat ecosystem |

### Concerns

| Risk | Mitigation |
|------|-----------|
| Vendor lock-in | CloudBase-specific APIs differ from standard S3/MongoDB |
| Limited customization | Some advanced COS/SCF features not available |

### Assessment Questions

- [ ] Is the Build Service used for automated deployments?
- [ ] Are functions designed to minimize cold start latency?
- [ ] Is static content using CDN caching effectively?

## Assessment Output Schema

```json
{
  "skill_id": "qcloud-cloudbase-ops",
  "product": "cloudbase",
  "assessment_date": "YYYY-MM-DD",
  "scope": "env-xxxxxxxx",
  "region": "ap-guangzhou",
  "status": "OK",
  "partial": false,
  "errors": [],
  "resource_count": {"env": 1, "function": 2, "storage": 1, "database": 1},
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "cloudbase-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-AZ concentration",
          "evidence": "All CloudBase functions in same region",
          "recommendation": "Enable multi-region deployment for critical functions",
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
      "score": 70,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 80,
      "status": "assessed",
      "findings": []
    }
  },
  "overall_score": 78,
  "recommendations": [],
  "trace": {
    "commands": ["tccli tcb DescribeEnvInfo --EnvId xxx"],
    "duration_ms": 1234
  }
}
```

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cloudbase-ops` |
| `product` | `cloudbase` |
| Finding `id` pattern | `cloudbase-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | §2 Reliability Pillar |
| `security` | §3 Security Pillar |
| `cost` | §4 Cost Pillar |
| `efficiency` | §5 Efficiency Pillar |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local "Score Calculation" sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-cloudbase-ops",
  "product": "cloudbase",
  "assessment_date": "2026-07-25",
  "scope": "env-xxxxxxxx",
  "region": "ap-guangzhou",
  "status": "OK",
  "partial": false,
  "errors": [],
  "resource_count": {"env": 1, "function": 2, "storage": 1, "database": 1},
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "cloudbase-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-AZ concentration",
          "evidence": "All CloudBase functions in same region",
          "recommendation": "Enable multi-region deployment for critical functions",
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
      "score": 70,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 80,
      "status": "assessed",
      "findings": []
    }
  },
  "overall_score": 78,
  "recommendations": [],
  "trace": {
    "commands": ["tccli tcb DescribeEnvInfo --EnvId xxx"],
    "duration_ms": 1234
  }
}
```


## References

- [Tencent Cloud Well-Architected Framework](https://cloud.tencent.com/document/product/1388)
- [CloudBase Documentation](https://cloud.tencent.com/document/product/876)
- [CloudBase Billing](https://cloud.tencent.com/document/product/876/56375)
