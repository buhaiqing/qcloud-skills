# Inspection Output Schema (Product Skill → Proactive Inspection Orchestrator)

> **Single source of truth** for `{{output.inspection_findings}}` returned by product
> skills when `qcloud-proactive-inspection` delegates Discovery/Collection.
> Distinct from Well-Architected `{{output.product_assessment}}`.

---

## 1. Top-level: `{{output.inspection_findings}}`

```json
{
  "skill_id": "qcloud-cvm-ops",
  "product": "cvm",
  "region": "ap-guangzhou",
  "inspection_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "resource_count": 12,
  "findings": [
    {
      "id": "cvm-001",
      "severity": "Warning",
      "rule_id": "cvm-cpu-high",
      "resource_id": "ins-xxxxxxxx",
      "title": "Sustained high CPU",
      "evidence": "CPU avg 92% over 1h (GetMonitorData)",
      "recommendation": "Review workload; consider scale-out or right-sizing",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": ["tccli cvm DescribeInstances ... (SecretKey=<masked>)"],
    "request_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
  },
  "errors": []
}
```

### 1.1 Required fields

| Field | Type | Rules |
|-------|------|-------|
| `skill_id` | string | Worker skill name |
| `product` | string | Product code matching registry |
| `region` | string | `{{env.TENCENTCLOUD_REGION}}` |
| `inspection_date` | string | ISO 8601 with timezone |
| `status` | enum | `OK` \| `PARTIAL` \| `ERROR` |
| `resource_count` | int | Resources discovered |
| `findings` | array | Threshold/rule violations; see §2 |
| `trace` | object | Masked commands + request_ids |
| `errors` | array | API failures; same shape as worker schema §3 |

---

## 2. Finding object

| Field | Type | Allowed values |
|-------|------|----------------|
| `id` | string | `{product}-NNN` or rule ID from product `proactive-inspection.md` |
| `severity` | string | `Critical` \| `Warning` \| `Info` |
| `rule_id` | string | Detection rule reference |
| `resource_id` | string | Cloud resource identifier |
| `title` | string | Short label |
| `evidence` | string | Metric/config fact |
| `recommendation` | string | Remediation hint (orchestrator may delegate mutation to product skill) |
| `effort` | string | `quick` \| `medium` \| `major` |

---

## 3. Orchestrator aggregation

1. Merge `findings[]` from all delegated product skills
2. Deduplicate by `resource_id` + `rule_id`
3. Sort by severity: Critical → Warning → Info
4. Feed Step 4 Diagnosis in `qcloud-proactive-inspection/SKILL.md`

**Boundary:** Inspection findings are **not** pillar scores. For four-pillar assessment → `qcloud-well-architected-review`.

---

## 4. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-06-09 | Initial inspection handoff schema (P3) |
