# Well-Architected Assessment Checklist

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Operational Excellence

- [ ] Sandbox tools defined as code (Terraform/Pulumi) or via repeatable scripts
- [ ] Image prewarming configured for production tools (WarmCount >= 3)
- [ ] CLS logging enabled on all production tools
- [ ] Audit logs reviewed weekly via CloudAudit console
- [ ] Runbooks documented for: tool deletion, key rotation, quota exhaustion

## Security

- [ ] API keys scoped via CAM policies (least privilege)
- [ ] Keys rotated quarterly via CreateAPIKey + DeleteAPIKey workflow
- [ ] SecretId/SecretKey stored in secrets manager (not in code)
- [ ] E2B_API_KEY masked in all logs (first 4 + last 4)
- [ ] Sandbox tools use isolated VPC if accessing internal services
- [ ] No long-lived keys in client-side code (use STS tokens where possible)

## Reliability

- [ ] Multi-region failover plan documented
- [ ] Exponential backoff on RequestLimitExceeded
- [ ] Instance health checked via DescribeSandboxInstanceList before use
- [ ] Quota monitoring at 80% threshold
- [ ] Graceful degradation if sandbox unavailable (fallback to local exec)

## Performance Efficiency

- [ ] Tool specs right-sized via CloudMonitor MemoryUtilization/CpuUtilization
- [ ] Image prewarming reduces cold-start to under 200ms P95
- [ ] Connection pooling for client SDK (reuse Sandbox objects within session)
- [ ] Batch instance creation where possible

## Cost Optimization

- [ ] Idle instances terminated within 5 minutes (not waiting for 24h auto-cleanup)
- [ ] Tool specs (CPU/Memory) reduced if utilization < 30% sustained
- [ ] Sandbox-hours tracked monthly per team/project tag
- [ ] CreatePreCacheImageTask WarmCount tuned to actual demand (not over-provisioned)
- [ ] Dev/test environments use smaller specs than prod

## Scoring

For each pillar, score 0-3 (0=missing, 1=partial, 2=mostly, 3=fully). Total / 75 = maturity %.

| Pillar | Score |
|---|---|
| Operational Excellence | __/15 |
| Security | __/18 |
| Reliability | __/15 |
| Performance | __/12 |
| Cost | __/15 |
| **Total** | **__/75** |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-agsx-ops` |
| `product` | `agsx` |
| Finding `id` pattern | `agsx-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability section |
| `security` | Security section |
| `cost` | Cost Optimization section |
| `efficiency` | Performance Efficiency section |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local “Score Calculation” sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-agsx-ops",
  "product": "agsx",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "agsx-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Idle sandbox pool",
          "evidence": "Running sandboxes with zero recent sessions",
          "recommendation": "Terminate idle instances; set auto-shutdown policy",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 88,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Terminate idle instances; set auto-shutdown policy",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tencentcloud-sdk-python ags DescribeSandboxToolList (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
