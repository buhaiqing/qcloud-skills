# Well-Architected Assessment — Migration

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Reliability

- **Migration validation**: Data consistency checks post-migration
- **Rollback plan**: Documented rollback procedures for each phase
- **Downtime minimization**: Use incremental sync for critical workloads
- **Testing**: Full test migration before production cutover

## Security

- **Encryption in transit**: TLS for all data transfers
- **Credential management**: Use temporary/limited credentials
- **Network isolation**: Use VPC peering or VPN for private connectivity
- **Audit logging**: Log all migration activities

## Cost

- **Right-sizing**: Match target resources to actual needs
- **Bandwidth planning**: Estimate transfer costs upfront
- **Storage optimization**: Compress data before transfer
- **Reserved instances**: Use RIs for predictable post-migration workloads

## Efficiency

- **Parallel migration**: Migrate independent workloads concurrently
- **Incremental sync**: Minimize cutover time
- **Automation**: Script repeatable migration steps
- **Monitoring**: Track migration progress and resource utilization

## Assessment Checklist

| Pillar | Check | Weight |
|--------|-------|--------|
| Reliability | Rollback plan documented | Critical |
| Reliability | Data consistency validated | Critical |
| Security | Encryption enabled | Critical |
| Security | Temporary credentials used | High |
| Cost | Target right-sized | Medium |
| Cost | Transfer costs estimated | Medium |
| Efficiency | Parallel migration where possible | Medium |
| Efficiency | Incremental sync for large datasets | High |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-migration-ops` |
| `product` | `migration` |
| Finding `id` pattern | `migration-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability section |
| `security` | Security section |
| `cost` | Cost section |
| `efficiency` | Efficiency section |

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
  "skill_id": "qcloud-migration-ops",
  "product": "migration",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-04T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 1,
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "migration-rel-001",
          "severity": "High",
          "confidence": "MEDIUM",
          "title": "Incomplete rollback documentation",
          "evidence": "Migration plan lacks detailed rollback procedures",
          "recommendation": "Document step-by-step rollback procedures for each migration phase",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 80,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 70,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 75,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Document step-by-step rollback procedures for each migration phase",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [],
    "request_ids": []
  },
  "errors": []
}
```

## References

- [Tencent Cloud Well-Architected Framework](https://cloud.tencent.com/document/product/xxx)
- [Migration Best Practices](https://cloud.tencent.com/document/product/)
