# SCF Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

Four-pillar read-only assessment for **Serverless functions — triggers, concurrency, DLQ, VPC.**

---

## 1. Framework Overview

| Pillar | Scope |
|--------|-------|
| Reliability | HA, backup, recovery signals |
| Security | Access, encryption, network |
| Cost | Right-sizing, waste, billing mode |
| Efficiency | Automation, batch, integration |


## 2. Reliability Pillar [assessment-readonly]

| Check | API | Pass |
|-------|-----|------|
| DLQ / retry | `GetFunction` / async config | Async has DLQ or retry policy |
| Timeout adequacy | Function config | Timeout matches workload |
| Multi-AZ | Namespace / region | Documented HA expectation |

## 3. Security Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Least-privilege role | Execution role scoped |
| VPC functions | Subnet/SG restricted |
| Secrets | No plaintext secrets in env (mask in output) |

## 4. Cost Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Memory tuning | Memory not over-provisioned vs metrics |
| Provisioned concurrency | Justified for latency-sensitive only |
| Idle functions | Zero-invocation functions reviewed |

## 5. Efficiency Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Trigger design | Event-driven vs polling appropriate |
| Layers | Shared layers for common deps |
| Version/alias | Production uses alias routing |


---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-scf-ops` |
| `product` | `scf` |
| Finding `id` pattern | `scf-{rel|sec|cost|eff}-NNN` |

### Pillar → checklist map

| `pillars` key | Checklist source |
|---------------|------------------|
| `reliability` | §2 Reliability — DLQ, retry, provisioned concurrency |
| `security` | §3 Security — CAM, VPC, env encryption |
| `cost` | §4 Cost — memory/duration tuning, provisioned vs on-demand |
| `efficiency` | §5 Efficiency — triggers, CI/CD, layer reuse |

### Populate rules

1. Include only pillar keys in orchestrator `{{user.pillars}}`.
2. `score = round(passed / applicable × 100)`; missing data → `not_assessed`.
3. Each checklist failure → one finding (six fields per schema §2.1).
4. `recommendations[]`: top 1–5 with `priority`, `pillar`, `action`, `effort`.
5. `partial=true` if any pillar `not_assessed`.
6. Mask credentials in `trace.commands`; populate `errors[]` on failure.
7. Do not run `[remediation-only]` commands in worker mode.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-scf-ops",
  "product": "scf",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 5,
  "pillars": {
    "reliability": {
      "score": 78,
      "status": "assessed",
      "findings": [
        {
          "id": "scf-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Function without dead-letter queue",
          "evidence": "Async functions with no DLQ configured",
          "recommendation": "Configure DLQ (CMQ/Ckafka) for failed async invocations",
          "effort": "medium"
        }
      ]
    },
    "security": { "score": 85, "status": "assessed", "findings": [] },
    "cost": { "score": 70, "status": "assessed", "findings": [] },
    "efficiency": { "score": 72, "status": "assessed", "findings": [] }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Configure DLQ (CMQ/Ckafka) for failed async invocations",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": ["tccli scf ListFunctions --Region ap-guangzhou (SecretKey=<masked>)"],
    "request_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
  },
  "errors": []
}
```


## References

- Product SKILL.md Well-Architected integration table
- [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)
