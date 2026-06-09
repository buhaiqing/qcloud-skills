# Worker Output Schema (Product Skill → Orchestrator)

> **Single source of truth** for `{{output.product_assessment}}`. Product
> `references/well-architected-assessment.md` files MUST implement this contract
> in their **Worker Output Contract** section — no alternate field names.

---

## 1. Top-level: `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-cvm-ops",
  "product": "cvm",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 12,
  "pillars": {
    "reliability": { "score": 85, "status": "assessed", "findings": [] },
    "security": { "score": 78, "status": "assessed", "findings": [] },
    "cost": { "score": 70, "status": "assessed", "findings": [] },
    "efficiency": { "score": 80, "status": "assessed", "findings": [] }
  },
  "recommendations": [],
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
| `skill_id` | string | Worker skill name, e.g. `qcloud-cvm-ops` |
| `product` | string | Registry code: `cvm`, `clb`, `es`, `mongodb`, … |
| `region` | string | `{{env.TENCENTCLOUD_REGION}}` |
| `scope` | string | Echo `{{user.scope}}` |
| `assessment_date` | string | ISO 8601 with timezone |
| `status` | enum | `OK` \| `PARTIAL` \| `ERROR` |
| `partial` | bool | `true` if any pillar `status=not_assessed` |
| `resource_count` | int | ≥ 0; primary resources discovered |
| `pillars` | object | Only keys requested in `{{user.pillars}}` (or all four if `all`) |
| `recommendations` | array | ≥ 0; see §2 |
| `trace` | object | `commands[]` + `request_ids[]`; credentials masked |
| `errors` | array | ≥ 0; see §3 |

### 1.2 `status` (top-level)

| Value | When |
|-------|------|
| `OK` | All requested pillars `assessed` or `skipped` |
| `PARTIAL` | ≥1 pillar `not_assessed` but others succeeded |
| `ERROR` | Discovery failed; no reliable pillar scores |

---

## 2. Pillar object

```json
{
  "score": 85,
  "status": "assessed",
  "findings": []
}
```

| `pillars.*.status` | Meaning |
|--------------------|---------|
| `assessed` | Scored from checklist evidence |
| `not_assessed` | Missing data/API failure — orchestrator must not impute pass |
| `skipped` | Not in `{{user.pillars}}` |

**Scoring:** `score = round(passed_checklist_items / total_applicable_items × 100)`. If `not_assessed`, omit `score` or set `null`.

### 2.1 Finding object (all fields required when present)

| Field | Type | Allowed values |
|-------|------|----------------|
| `id` | string | `{product}-{rel\|sec\|cost\|eff}-NNN` (3-digit seq per pillar) |
| `severity` | string | `Critical` \| `High` \| `Medium` \| `Low` |
| `confidence` | string | `HIGH` \| `MEDIUM` \| `LOW` |
| `title` | string | Short issue label |
| `evidence` | string | Observable fact from Describe* / metrics |
| `recommendation` | string | Actionable fix |
| `effort` | string | `quick` \| `medium` \| `major` |

**ID examples:** `cvm-rel-001`, `es-sec-002`, `mongodb-cost-003`

### 2.2 Recommendation object

| Field | Type | Allowed values |
|-------|------|----------------|
| `priority` | string | `Critical` \| `High` \| `Medium` \| `Low` |
| `pillar` | string | `reliability` \| `security` \| `cost` \| `efficiency` |
| `action` | string | Imperative remediation step |
| `effort` | string | `quick` \| `medium` \| `major` |

Include top 1–5 items sorted by priority. May mirror high-severity findings.

---

## 3. Error object (`errors[]`)

| Field | Type | Required |
|-------|------|----------|
| `code` | string | yes — API or worker code |
| `message` | string | yes — sanitized (no credentials) |
| `action` | string | yes — `HALT` \| `RETRY` \| `SKIP` |
| `request_id` | string | no |

---

## 4. Trace object

| Field | Rules |
|-------|-------|
| `commands[]` | Every Describe* / GetMonitorData / SDK read call; `SecretKey=<masked>` |
| `request_ids[]` | From `Response.RequestId` per call |

---

## 5. Orchestrator aggregation

1. Merge `pillars.*.findings` across workers per pillar key
2. Pillar score = equal-weight mean of worker pillar scores (exclude `not_assessed`)
3. [cross-product-analysis.md](cross-product-analysis.md)
4. [report-template.md](../assets/report-template.md)

---

## 6. Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-06-09 | Initial worker contract |
| 1.1.0 | 2026-06-09 | Recommendation + error objects; finding ID convention; pillar scoring rules |
