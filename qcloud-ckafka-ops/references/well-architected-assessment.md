# CKafka Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

Four-pillar read-only assessment for **Managed Kafka — replication, ACL, consumer lag, storage.**

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
| Replication factor | `DescribeInstances` / topic detail | Production topics RF ≥ 2 |
| ISR health | Topic metadata | No under-replicated partitions |
| Backup / DR | Cross-region mirror or export documented | Strategy exists or finding |

## 3. Security Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| ACL enabled | SASL/ACL configured for production |
| VPC isolation | Instance in private subnet |
| Public access | No open public endpoint without justification |

## 4. Cost Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Right-sizing | Instance spec matches throughput |
| Retention | Log retention not excessive vs RPO |
| Idle instance | Zero throughput instances flagged |

## 5. Efficiency Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Partition balance | Partitions sized for consumer parallelism |
| Compression | Enabled where appropriate |


---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-ckafka-ops` |
| `product` | `ckafka` |
| Finding `id` pattern | `ckafka-{rel|sec|cost|eff}-NNN` |

### Pillar → checklist map

| `pillars` key | Checklist source |
|---------------|------------------|
| `reliability` | §2 Reliability — replication, ISR, multi-AZ/broker |
| `security` | §3 Security — ACL, SASL, VPC, encryption |
| `cost` | §4 Cost — instance tier, retention, storage |
| `efficiency` | §5 Efficiency — partition count, compression, batch consume |

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
  "skill_id": "qcloud-ckafka-ops",
  "product": "ckafka",
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
          "id": "ckafka-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Consumer lag sustained high",
          "evidence": "Consumer group lag > threshold for 24h on production topic",
          "recommendation": "Scale partitions or consumers; review retention and ISR",
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
      "action": "Scale partitions or consumers; review retention and ISR",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": ["tccli ckafka DescribeInstances --Region ap-guangzhou (SecretKey=<masked>)"],
    "request_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
  },
  "errors": []
}
```


## References

- Product SKILL.md Well-Architected integration table
- [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)
