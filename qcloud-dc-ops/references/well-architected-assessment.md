# Well-Architected Assessment — Direct Connect

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Reliability

- **Redundant connections**: Deploy dual DC connections to different access points
- **Health checks**: Enable BFD for fast failure detection
- **Failover**: Configure VPN backup for automatic failover
- **Monitoring**: Set up alerts for DC/tunnel state changes

## Security

- **Private connectivity**: No traffic traverses public internet
- **MACsec encryption**: Enable Layer 2 encryption where available
- **Access control**: Restrict DC modification to authorized personnel
- **Audit logging**: Enable CloudAudit for compliance

## Cost

- **Bandwidth optimization**: Right-size bandwidth based on actual usage
- **Billing models**: Consider committed use discounts for stable traffic
- **Partner connections**: Use partner facilities to reduce cross-connect costs

## Efficiency

- **Route optimization**: Use BGP for dynamic route propagation
- **Traffic engineering**: Implement traffic policies for optimal paths
- **Auto-scaling**: Consider CCN for dynamic multi-region connectivity

## Assessment Checklist

| Pillar | Check | Weight |
|--------|-------|--------|
| Reliability | Dual DC connections deployed | Critical |
| Reliability | VPN backup configured | High |
| Security | MACsec enabled (if available) | Medium |
| Security | CAM policies restrict DC modification | High |
| Cost | Bandwidth right-sized | Medium |
| Cost | Committed use discounts applied | Low |
| Efficiency | BGP routing enabled | Medium |
| Efficiency | CCN used for multi-region | Low |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-dc-ops` |
| `product` | `dc` |
| Finding `id` pattern | `dc-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

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
  "skill_id": "qcloud-dc-ops",
  "product": "dc",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-04T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 2,
  "pillars": {
    "reliability": {
      "score": 60,
      "status": "assessed",
      "findings": [
        {
          "id": "dc-rel-001",
          "severity": "Critical",
          "confidence": "HIGH",
          "title": "Single DC connection",
          "evidence": "Only one Direct Connect connection deployed",
          "recommendation": "Deploy dual DC connections to different access points for redundancy",
          "effort": "major"
        }
      ]
    },
    "security": {
      "score": 85,
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
      "priority": "Critical",
      "pillar": "reliability",
      "action": "Deploy dual DC connections to different access points for redundancy",
      "effort": "major"
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
- [Direct Connect Best Practices](https://cloud.tencent.com/document/product/)
