# CBS Well-Architected Assessment

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

Four-pillar read-only assessment for **Block storage — snapshots, unattached disks, encryption, auto-snapshot policies.**

---

## 1. Framework Overview

| Pillar | Scope |
|--------|-------|
| Reliability | HA, backup, recovery signals |
| Security | Access, encryption, network |
| Cost | Right-sizing, waste, billing mode |
| Efficiency | Automation, batch, integration |


> **Boundary vs CVM worker:** `qcloud-cvm-ops` assesses disks **attached to instances** in CVM context.
> This worker focuses **standalone CBS**: unattached disks, snapshot policies, encryption-at-rest, cross-AZ disk placement.

## 2. Reliability Pillar [assessment-readonly]

| Check | API | Pass |
|-------|-----|------|
| Auto-snapshot | `DescribeAutoSnapshotPolicies` | Production disks bound to policy |
| Snapshot age | `DescribeSnapshots` | Latest snapshot within RPO |
| Disk state | `DescribeDisks` | No critical data on unprotected volumes |

## 3. Security Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Encryption | Disks encrypted at rest |
| Snapshot access | CAM restricts snapshot sharing |

## 4. Cost Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Unattached disks | UNATTACHED > 30d flagged |
| Disk type | SSD tier justified vs IOPS need |
| Snapshot sprawl | Old snapshots beyond retention |

## 5. Efficiency Pillar [assessment-readonly]

| Check | Pass |
|-------|------|
| Batch describe | Pagination for account-wide inventory |
| Policy automation | Auto-snapshot on new disks |


---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cbs-ops` |
| `product` | `cbs` |
| Finding `id` pattern | `cbs-{rel|sec|cost|eff}-NNN` |

### Pillar → checklist map

| `pillars` key | Checklist source |
|---------------|------------------|
| `reliability` | §2 Reliability — snapshots, auto-snapshot policy |
| `security` | §3 Security — encryption, snapshot ACL |
| `cost` | §4 Cost — disk type, orphan/unattached waste |
| `efficiency` | §5 Efficiency — batch ops, lifecycle automation |

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
  "skill_id": "qcloud-cbs-ops",
  "product": "cbs",
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
          "id": "cbs-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Unattached disk with no snapshot policy",
          "evidence": "UNATTACHED disk > 30d without auto-snapshot",
          "recommendation": "Attach or snapshot; delete if orphan per finops review",
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
      "action": "Attach or snapshot; delete if orphan per finops review",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": ["tccli cbs DescribeDisks --Region ap-guangzhou (SecretKey=<masked>)"],
    "request_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
  },
  "errors": []
}
```


## References

- Product SKILL.md Well-Architected integration table
- [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)
