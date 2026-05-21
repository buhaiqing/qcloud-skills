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
