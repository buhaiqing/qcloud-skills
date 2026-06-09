# Well-Architected Review Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-well-architected-review`.
> Source-of-truth: [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill) and §8
> (`qcloud-well-architected-review` → **optional**, `max_iterations = 5`).
>
> **Advisory / read-only** — no destructive ops; Safety=0 does not hard-ABORT unless
> credential leak or mutation detected.

---

## 1. Scope and applicability

| Applies to | Does NOT apply to |
|---|---|
| Full four-pillar assessments (Discover → Evaluate → Report → Recommend) | Live resource CRUD → delegate to product ops skills |
| Single-pillar or single-product scoped reviews | Billing detail queries → delegate to `qcloud-finops-ops` |
| Cross-skill read-only data collection from Delegation Matrix skills | Skills not listed in Delegation Matrix |

---

## 2. Five rubric dimensions (mandatory)

Each dimension is scored `0`, `0.5`, or `1`. Thresholds from [AGENTS.md §3](../../AGENTS.md#3-rubric-mandatory-per-skill).

| # | Dimension | Threshold | Why for Well-Architected |
|---|---|---|---|
| 1 | **Correctness** | ≥ 0.5 | Scores must reflect evidence; false pass on skipped data misleads stakeholders |
| 2 | **Safety** | ≥ 0.5 | Read-only + credential masking; mutation or leak ⇒ 0 |
| 3 | **Idempotency** | ≥ 0.5 | Re-running same scope within 1h should warn or reuse prior snapshot |
| 4 | **Traceability** | ≥ 0.5 | Every Describe* call needs command + RequestId in trace |
| 5 | **Spec Compliance** | ≥ 0.5 | Correct read APIs, pagination, GetMonitorData for metrics, delegation matrix |

**Credential leak or mutation detected → return ERROR immediately** (see Orchestrator §3).

---

## 3. Per-dimension scoring checklist

### 3.1 Correctness

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Pillar scores backed by worker `product_assessment` evidence | ✓ | partial workers only | scores without any worker payload |
| Skipped pillars marked "NOT ASSESSED" (not N/A or pass) | ✓ | — | skipped pillar given a numeric score |
| Findings include confidence HIGH/MEDIUM/LOW | ✓ | partial | no confidence on critical findings |
| Overall score uses weighted formula from SKILL.md | ✓ | — | wrong weights or missing pillar |

### 3.2 Safety

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| All API calls are read-only (Describe* / GetMonitorData only) | ✓ | — | any Create/Modify/Delete in trace |
| Report draft contains no raw SecretKey / API keys | ✓ | partial redaction | credential in report output |
| Cross-skill calls confirmed read-only in trace | ✓ | — | alarm/SG/backup modified during review |

### 3.3 Idempotency

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Same scope re-run within 1h warns user or reuses prior results | ✓ | — | duplicate full assessment without notice |
| Pagination completes without restarting Offset from 0 mid-run | ✓ | — | duplicate resource counts in report |

### 3.4 Traceability

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Worker delegation logged (skill_id per product) | ✓ | partial | orchestrator ran inline product tccli |
| `RequestId` captured in worker traces | ✓ | partial | missing |
| Assessment timestamp and scope in report header | ✓ | — | no timestamp |

### 3.5 Spec Compliance

| Check | Score 1 | Score 0.5 | Score 0 |
|---|---|---|---|
| Orchestrator did NOT inline product Describe* (workers only) | ✓ | — | DELEGATION_VIOLATION |
| Workers return valid worker-output-schema.md | ✓ | partial schema | invalid or missing product_assessment |
| Product Worker Registry respected | ✓ | — | unlisted worker invoked |

---

## 4. Threshold summary (Orchestrator)

| Dimension | Pass threshold |
|---|---|
| correctness | ≥ 0.5 |
| safety | ≥ 0.5 |
| idempotency | ≥ 0.5 |
| traceability | ≥ 0.5 |
| spec_compliance | ≥ 0.5 |

---

## 5. Well-Architected-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | Assessment scope clarity | **Surface scope (products, pillars); skipped pillars = "NOT ASSESSED"** | User may think Security passed when CAM data was unavailable |
| 2 | Read-only cross-skill data | **Describe* / GetMonitorData only; no alarm/SG/backup changes** | Assessment must be non-invasive |
| 3 | No false certainty | **Confidence per finding; caveat on partial data** | Automated review ≠ professional audit |
| 4 | Cross-pillar consistency | **Surface conflicting recommendations; Security > Reliability > Cost > Efficiency** | Multi-AZ vs cost trade-offs need explicit priority |
| 5 | Worker registry respect | **delegate-to only Product Worker Registry skills; workers run Describe*** | Orchestrator inlining product CLI duplicates workers |

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Initial: §5 advisory rules only |
| 1.1.0 | 2026-06-09 | Added §1–§4 five dimensions |
| 1.2.0 | 2026-06-09 | Orchestrator + Worker scoring; DELEGATION_VIOLATION checks |
