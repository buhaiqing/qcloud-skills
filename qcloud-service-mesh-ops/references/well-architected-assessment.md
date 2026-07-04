# Well-Architected Assessment — Service Mesh

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Reliability

- **Multi-cluster mesh**: Deploy mesh across multiple clusters for HA
- **Circuit breaker**: Configure outlier detection to prevent cascade failures
- **Retry policies**: Set appropriate retry counts and timeouts
- **Health checks**: Enable active health checks for upstream services

## Security

- **mTLS encryption**: Enable strict mTLS for production workloads
- **Authorization policies**: Define fine-grained access control
- **Cert rotation**: Automatic certificate rotation (default 24h)
- **Egress control**: Restrict external access via egress gateways

## Cost

- **Sidecar resource optimization**: Tune CPU/memory requests
- **Selective injection**: Only inject Sidecars where needed
- **Log sampling**: Reduce log volume with appropriate sampling
- **Prometheus retention**: Adjust metrics retention period

## Efficiency

- **Connection pooling**: Optimize connection reuse
- **Locality-based routing**: Route to nearest endpoints
- **Cache warming**: Pre-warm caches before traffic shift
- **Request hedging**: Send multiple requests, use fastest response

## Assessment Checklist

| Pillar | Check | Weight |
|--------|-------|--------|
| Reliability | Multi-cluster configuration | High |
| Reliability | Circuit breaker configured | High |
| Security | Strict mTLS enabled | Critical |
| Security | Authorization policies defined | High |
| Cost | Sidecar resources optimized | Medium |
| Cost | Selective injection used | Medium |
| Efficiency | Connection pooling enabled | Medium |
| Efficiency | Locality routing configured | Low |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-service-mesh-ops` |
| `product` | `servicemesh` |
| Finding `id` pattern | `servicemesh-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

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
  "skill_id": "qcloud-service-mesh-ops",
  "product": "servicemesh",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-07-04T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 70,
      "status": "assessed",
      "findings": [
        {
          "id": "servicemesh-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Single-cluster mesh",
          "evidence": "Service mesh deployed in single cluster only",
          "recommendation": "Deploy multi-cluster mesh for high availability",
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
      "score": 65,
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
      "action": "Deploy multi-cluster mesh for high availability",
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
- [Service Mesh Best Practices](https://cloud.tencent.com/document/product/)
