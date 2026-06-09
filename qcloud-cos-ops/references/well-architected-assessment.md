# COS Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Four Pillars

### Reliability (可靠性)

| Requirement | Implementation |
|-------------|---------------|
| Cross-region replication | Configure replication rules |
| Versioning | Enable versioning for backup |
| Lifecycle backup | Archive objects automatically |

### Security (安全性)

| Requirement | Implementation |
|-------------|---------------|
| ACL policies | Configure bucket/object ACL |
| Encryption | Enable server-side encryption |
| Access logging | Enable COS logging |

### Cost (成本)

| Requirement | Implementation |
|-------------|---------------|
| Storage tier optimization | Lifecycle rules to ARCHIVE |
| Idle bucket detection | Monitor bucket access |
| Cost comparison | STANDARD vs ARCHIVE costs |

### Efficiency (效率)

| Requirement | Implementation |
|-------------|---------------|
| Multipart upload | Use coscmd for large files |
| Batch operations | SDK batch delete |
| CDN integration | Static website + CDN |

## Cost Comparison

| Storage Class | 30 Days | 90 Days | 365 Days |
|---------------|---------|---------|----------|
| STANDARD | ¥0.118/GB | ¥3.54/GB | ¥14.36/GB |
| STANDARD_IA | ¥0.08/GB | ¥2.4/GB | ¥9.72/GB |
| ARCHIVE | ¥0.033/GB | ¥0.99/GB | ¥4.03/GB |

## CAM Policy

```json
{
  "version": "2.0",
  "statement": [
    {
      "action": [
        "cos:GetObject",
        "cos:PutObject",
        "cos:DeleteObject"
      ],
      "effect": "allow",
      "resource": "qcs::cos:*:*:bucket-xxx/*"
    }
  ]
}
```

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cos-ops` |
| `product` | `cos` |
| Finding `id` pattern | `cos-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability / versioning sections |
| `security` | Security / CAM sections |
| `cost` | Cost / lifecycle sections |
| `efficiency` | Efficiency sections |

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
  "skill_id": "qcloud-cos-ops",
  "product": "cos",
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
          "id": "cos-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Versioning disabled on critical bucket",
          "evidence": "Production bucket without versioning",
          "recommendation": "Enable versioning and lifecycle rules",
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
      "action": "Enable versioning and lifecycle rules",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli cos ListBuckets (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```

## References

- [COS Well-Architected](https://cloud.tencent.com/document/product/436)