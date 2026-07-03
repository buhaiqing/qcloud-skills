# FinOps Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

> Read-only **Cost pillar** worker for `qcloud-well-architected-review`. FinOps does not
> assess CVM/CLB resource topology — it supplies **billing, TCO, budget, and optimization
> signals** from Tencent Cloud Billing/Trade/Tag APIs.

---

## 1. Framework scope (this worker)

| Pillar | FinOps role in Well-Architected | Typical `status` |
|--------|--------------------------------|------------------|
| **成本 (Cost)** | **Primary** — spend, attribution, budget, waste signals | `assessed` |
| **效率 (Efficiency)** | Tag maturity, report automation, allocation coverage | `assessed` or `skipped` |
| **安全性 (Security)** | Billing CAM least-privilege, output masking (no PII leak) | `skipped` unless requested |
| **可靠性 (Reliability)** | Budget/alarm coverage for cost governance | `skipped` or `not_assessed` |

Orchestrator usually sets `{{user.pillars}}` to `cost` or `cost,efficiency`.

---

## 2. Cost pillar checklist (模块 1–3 + 5 只读)

### 2.1 Spend visibility

| Check | Read-only API | Pass criteria |
|-------|---------------|---------------|
| Monthly total retrievable | `billing DescribeBillSummaryByMonth` | Response non-empty for target month |
| Product breakdown | `DescribeBillSummaryByProduct` | Top products identified |
| Resource-level attribution | `DescribeBillResourceSummary` / `DescribeCostDetail` | ≥80% spend attributable OR gap documented |
| MoM / YoY context | Two months `DescribeBillSummaryByMonth` | Trend computed; anomaly flagged if ii > 20% |

Use `{{user.month}}` as `YYYY-MM` — do not hardcode calendar months (TE-1).

### 2.2 Financial baseline

| Check | API | Pass criteria |
|-------|-----|---------------|
| Account balance readable | `billing DescribeAccountBalance` | Cash + credit fields parsed |
| Voucher utilization | `voucher DescribeVoucherList` | Expiring vouchers within 30d flagged |
| Resource package usage | `DescribeResourcePackageUsage` | Under-utilized packages flagged |

### 2.3 Cost allocation (Tag)

| Check | API | Pass criteria |
|-------|-----|---------------|
| Tag keys exist | `tag GetTagKeys` | ≥1 cost-allocation tag (e.g. `dept`, `project-code`) |
| Tag coverage on spend | `DescribeCostDetail` + tag dimension | Untagged spend % documented |
| Env separation | Tag values include prod/non-prod | Mixed prod/dev on one tag value → finding |

### 2.4 Budget & anomaly (模块 4 — read-only)

| Check | Source | Pass criteria |
|-------|--------|---------------|
| Budget config loaded | `{{env.TENCENTCLOUD_FINOPS_CONFIG}}` if set | Thresholds applied OR defaults documented |
| ii / iii anomaly | `finops-methodology.md` algorithm | MEDIUM/HIGH anomalies → findings with confidence |
| No auto-remediation | Worker trace | Zero product mutation APIs called |

### 2.5 Optimization signals (模块 5 — recommend only)

| Signal | Delegate read | Output |
|--------|---------------|--------|
| Idle/waste hints | Cross-ref `qcloud-monitor-ops` / product skills (orchestrator) | Findings cite **estimated** savings; mark `confidence=MEDIUM` without monitor proof |
| Billing mode mismatch | Bill pay-mode summary | On-demand stable workloads → recommendation only |

**Golden rule:** Recommendations only — execution stays with product ops skills.

### 2.6 Cost pillar scoring

| Score | Criteria |
|-------|----------|
| 90-100 | Full attribution, budget tracked, no HIGH anomalies, optimization backlog documented |
| 70-89 | Most spend attributed; minor anomalies or tag gaps |
| 50-69 | Large untagged spend or recurring MEDIUM+ anomalies |
| < 50 | No cost visibility, no tags, or billing API inaccessible |

---

## 3. Efficiency pillar checklist (optional)

| Check | Pass criteria |
|-------|---------------|
| Repeatable cost report | Documented query pattern in `cost-analysis-queries.md` reusable |
| Tag automation | Tag keys standardized (`business-line`, `env`, `cost-center`) |
| FinOps config | `TENCENTCLOUD_FINOPS_CONFIG` used for thresholds (production) |

---

## 4. Security notes (when pillar requested)

| Check | Pass criteria |
|-------|---------------|
| Billing read CAM | `QcloudBillingReadOnlyAccess` or tighter custom policy |
| Trace masking | No SecretKey, invoice contacts, or raw account IDs in `trace` / findings |
| Sub-account scope | Sub-account billing authorized if assessing sub-account |

---

## 5. Read-only API allowlist

**Allowed (worker mode):**

- `billing DescribeBill*`, `DescribeCost*`, `DescribeAccountBalance`, `DescribeResourcePackage*`
- `trade DescribePayDeals`, `DescribeOrders`
- `voucher DescribeVoucherList`
- `tag GetTagKeys`, `GetTagValues`

**Forbidden:** Any order/create/modify/terminate that changes billing state or resources.

---

## 6. Cross-skill delegation (worker)

| Need | delegate-to | Mode |
|------|-------------|------|
| CPU idle proof | `qcloud-monitor-ops` | Orchestrator coordinates; finops cites monitor worker output |
| Resource metadata | Product `qcloud-*-ops` | Read-only Describe* only |
| Alert channel setup | `qcloud-monitor-ops` | Not during assessment |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-finops-ops` |
| `product` | `finops` |
| Finding `id` pattern | `finops-{rel\|sec\|cost\|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | §1 (typically `skipped` — budget alarm coverage optional) |
| `security` | §4 Security notes |
| `cost` | §2 Cost pillar checklist |
| `efficiency` | §3 Efficiency pillar checklist |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`cost` most common).
2. `score = round(passed / applicable × 100)`; billing API denied → `cost.status=not_assessed`.
3. Each failed/warn checklist item → one `findings[]` entry (all six finding fields per schema §2.1).
4. `recommendations[]`: top 1–5 savings actions; **never** imply auto-execution (schema §2.2).
5. `partial=true` if any requested pillar is `not_assessed`; `status=PARTIAL` at top level.
6. `trace.commands`: masked tccli/SDK billing calls; `errors[]` on `AuthFailure` / limit (schema §3).
7. Amount reconciliation tolerance < ¥0.01 when aggregating subtotals (FinOps quality gate #2).

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-finops-ops",
  "product": "finops",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 0,
  "pillars": {
    "cost": {
      "score": 68,
      "status": "assessed",
      "findings": [
        {
          "id": "finops-cost-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Untagged spend exceeds threshold",
          "evidence": "32% of last month spend has no cost-allocation tag",
          "recommendation": "Enforce dept/project-code tags; re-run DescribeCostDetail after tag rollout",
          "effort": "medium"
        },
        {
          "id": "finops-cost-002",
          "severity": "Medium",
          "confidence": "MEDIUM",
          "title": "MoM spend anomaly",
          "evidence": "ii_ratio=0.24 vs 3-month average (module 4 algorithm)",
          "recommendation": "Review Top 5 products; delegate monitor + product workers for root cause",
          "effort": "quick"
        }
      ]
    },
    "efficiency": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "finops-eff-001",
          "severity": "Low",
          "confidence": "HIGH",
          "title": "FinOps config not loaded",
          "evidence": "TENCENTCLOUD_FINOPS_CONFIG unset; using default thresholds",
          "recommendation": "Point env to assets/example-config.yaml for budget/tag mappings",
          "effort": "quick"
        }
      ]
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "cost",
      "action": "Reduce untagged spend via mandatory cost-allocation tags",
      "effort": "medium"
    },
    {
      "priority": "Medium",
      "pillar": "cost",
      "action": "Investigate MoM anomaly on top 5 billing products",
      "effort": "quick"
    }
  ],
  "trace": {
    "commands": [
      "tccli billing DescribeBillSummaryByMonth --Month {{user.month}} (SecretKey=<masked>)",
      "tccli billing DescribeCostDetail --Month {{user.month}} (SecretKey=<masked>)",
      "tccli tag GetTagKeys (SecretKey=<masked>)"
    ],
    "request_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
  },
  "errors": []
}
```

> `resource_count` for finops = count of **billing line items / attributed resources** in scope, or `0` when only account-level summary is assessed — document choice in `evidence`.

---

## 7. Cross-account cost visibility (module 9)

| 评估项 | 理想状态 | 检查方法 | 评分标准 |
|--------|----------|----------|----------|
| 多账号统一账单 | 组织内所有账号账单可统一查看 | `tccli organization DescribeOrganization` | 有=5, 部分=3, 无=0 |
| 成本分摊标签 | 所有资源强制打标签 | `tccli tag GetTagValues` | 强制=5, 推荐=3, 无=0 |
| 预算告警覆盖 | 每个账号/项目有预算 | `tccli monitor DescribeAlarmPolicies` | 全覆盖=5, 部分=3, 无=0 |

### 7.1 Cross-account checklist

| Check | Read-only API | Pass criteria |
|-------|---------------|---------------|
| Organization membership | `organization DescribeOrganization` | Non-empty member list |
| Cross-account billing aggregation | Module 9 script via CAM role | All member account summaries accessible |
| Per-account budget coverage | `monitor DescribeAlarmPolicies` per account | Each account has ≥1 budget alarm |

### 7.2 Scoring

| Score | Criteria |
|-------|----------|
| 90-100 | Full multi-account billing visibility, all accounts budget-covered, tags enforced |
| 70-89 | Most accounts aggregated, minor tag gaps |
| 50-69 | Partial coverage, some accounts inaccessible |
| < 50 | No cross-account aggregation |

---

## References

- [billing-api-mapping.md](billing-api-mapping.md)
- [cost-analysis-queries.md](cost-analysis-queries.md)
- [finops-methodology.md](finops-methodology.md)
- [setup-and-permissions.md](setup-and-permissions.md)
