# CDN Well-Architected Assessment

## Reliability

| Check | Assessment | Pass Criteria |
|-------|-----------|---------------|
| Multi-origin configured | Origin has backup/weight config | ≥ 2 origins or backup origin set |
| Origin health monitoring | Origin health check configured | Health check enabled with alerts |
| Cache invalidation safety | Purge operations have safeguards | No blind wildcard purges |
| HTTPS automation | Certificate renewal automated | Cert auto-renew before expiry |

## Security

| Check | Assessment | Pass Criteria |
|-------|-----------|---------------|
| Anti-hotlinking enabled | Referer or URL signing configured | At least one protection method active |
| IP access control | Blacklist/whitelist configured | Known malicious IPs blocked |
| Origin IP protected | Origin not directly accessible | Origin IP not exposed publicly |
| HTTPS enforced | ForceRedirect to HTTPS | HTTP→HTTPS redirect enabled |
| HSTS header | Strict-Transport-Security set | HSTS max-age ≥ 31536000 |

## Cost

| Check | Assessment | Pass Criteria |
|-------|-----------|---------------|
| Cache hit ratio | Monitor hit ratio trend | > 85% for static content |
| Bandwidth optimization | Compression enabled | Gzip/Brotli enabled |
| Traffic pattern analysis | Monthly traffic review | Identify optimization opportunities |
| Tier pricing alignment | Match bandwidth to tier | Not over-provisioned |

## Efficiency

| Check | Assessment | Pass Criteria |
|-------|-----------|---------------|
| Cache rules optimized | Cache TTL configured per path | Static assets cached ≥ 1 day |
| Pre-warm strategy | PushUrlsCache for critical assets | Pre-warm before launches |
| API integration | CDN operations automated | CI/CD triggers purge on deploy |
| Logging enabled | CDN log collection active | Logs available for analysis |

## Scoring

| Score | Criteria |
|-------|----------|
| 90-100 | Multi-origin, HTTPS enforced, anti-hotlink, > 90% cache hit |
| 70-89 | Single origin, HTTPS enabled, basic access control, > 80% cache hit |
| 50-69 | No backup origin, HTTP allowed, minimal access control |
| < 50 | Origin exposed, no HTTPS, no access control, poor cache hit |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-cdn-ops` |
| `product` | `cdn` |
| Finding `id` pattern | `cdn-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Origin / availability sections |
| `security` | HTTPS / access control sections |
| `cost` | Traffic / bandwidth sections |
| `efficiency` | Cache / purge automation sections |

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
  "skill_id": "qcloud-cdn-ops",
  "product": "cdn",
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
          "id": "cdn-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "HTTPS not enforced",
          "evidence": "Domain without ForceRedirect HTTPS",
          "recommendation": "Enable HTTPS and HTTP→HTTPS redirect",
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
      "action": "Enable HTTPS and HTTP→HTTPS redirect",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli cdn DescribeDomainsConfig (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
