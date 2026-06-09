---
name: qcloud-cdn-ops
description: >-
  Use when the user needs to manage Tencent Cloud CDN (Content Delivery Network) —
  domain add/remove/configure, cache purge/pre-warm, HTTPS certificate setup,
  origin server management, bandwidth/traffic monitoring, URL access control
  (referer, IP blacklist, URL signing), CDN log analysis, or cache hit ratio
  optimization. User mentions CDN, 内容分发, 加速域名, cache purge, origin,
  CDN log, or describes content delivery scenarios even without naming the
  product directly. Not for CLB/VPC resource operations, application-level
  caching logic, or billing management.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`), Python 3.8+ runtime for SDK fallback
  with tencentcloud-sdk-python-cdn, valid API credentials, network access to
  Tencent Cloud CDN endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/228"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cdn help` - CLI exposes AddCdnDomain, DeleteCdnDomain,
    UpdateDomainConfig, DescribeDomainsConfig, StartCdnDomain, StopCdnDomain,
    PurgeUrlsCache, PurgePathCache, PushUrlsCache, DescribeCdnData,
    ListTopData, DescribeCdnDomainLogs, and 30+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud CDN Operations Skill

## Overview

CDN (Content Delivery Network) is Tencent Cloud's content delivery service providing fast, reliable content distribution via edge nodes. This skill is an **operational runbook** for agents managing CDN domains, cache rules, HTTPS certificates, origin servers, and traffic monitoring. It uses **dual-path execution** — official `tccli` CLI as primary, Python SDK fallback for complex configurations.

### Core Operations

| Operation Category | Primary APIs |
|---|---|
| Domain management | AddCdnDomain, DeleteCdnDomain, UpdateDomainConfig, StartCdnDomain, StopCdnDomain |
| Cache management | PurgeUrlsCache, PurgePathCache, PushUrlsCache |
| Origin management | Origin configuration, weight/backup, origin pull rules |
| HTTPS/SSL | HTTPS certificate setup, ForceRedirect, HSTS |
| Traffic/monitoring | DescribeCdnData, ListTopData, DescribeCdnDomainDetailData |
| Access control | Referer config, IP blacklist, URL signing, anti-leech |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- Domain management: "添加CDN加速域名", "删除CDN域名", "配置CDN"
- Cache operations: "刷新缓存", "预热URL", "清除缓存"
- HTTPS setup: "配置HTTPS证书", "强制HTTPS"
- Origin config: "配置源站", "修改源站权重"
- Traffic monitoring: "查看CDN流量", "查看带宽使用"
- Access control: "配置防盗链", "设置IP黑白名单", "URL鉴权"
- Log analysis: "分析CDN日志", "下载CDN日志"

### SHOULD NOT Use This Skill When
- Application-level caching (Redis/Memcached) → delegate to qcloud-redis-ops
- Load balancer config → delegate to qcloud-clb-ops
- SSL certificate management (general, not CDN-specific) → use cert management skill
- Billing management → use dedicated billing tools
- Task is **full architecture review** (four pillars / multi-product) → delegate to: `qcloud-well-architected-review`
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **CDN** (HTTPS, cache, origin, traffic); return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | security / cost / efficiency (or `all`) |
| `{{user.scope}}` | `account-wide` |

**Allowed:** `Describe*`, `ListTopData`, `DescribeCdnData` — **no** Purge/Push/Add/Delete domain mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cdn`).

## Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{user.domain}}` | User | CDN domain name | `cdn.example.com` |
| `{{user.urls}}` | User | URLs to purge/pre-warm | JSON array |
| `{{user.origin_type}}` | User | Origin type (COS, CVM, CLB) | `cos` |

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | CDN-only scope; delegates resource ops to product skills |
| 2 | **Structured I/O** | Domain/URL/origin I/O with JSON paths from API responses |
| 3 | **Explicit Actionable Steps** | Each operation: Pre-flight → Execute → Validate → Recover |
| 4 | **Complete Failure Strategies** | Domain validation failures, cache purge limits, origin errors |
| 5 | **Absolute Single Responsibility** | One product (CDN), primary resource = Domain |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial release — CDN domain management, cache purge, config update |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CDN-specific safety rules incl. domain-deletion CNAME break, wildcard `/*` purge mass flush, origin config change, preload origin cost), `references/prompt-templates.md`. `max_iter=3` per AGENTS.md §8 |

## Safety Gates

**DESTRUCTIVE CONFIRMATION REQUIRED before:**
- `DeleteCdnDomain` — Confirm domain name, verify no active traffic
- `PurgeUrlsCache` with `/*` pattern — Confirm wildcard purge scope (can clear ALL cached content)
- `PurgePathCache` — Confirm path scope, estimate cache impact

**Cache operation distinctions:**
- `PurgeUrlsCache` = Delete specific cached URLs (immediate effect)
- `PurgePathCache` = Directory-level purge (broad impact)
- `PushUrlsCache` = Pre-warm cache (proactive, no risk)

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override (AGENTS.md §8 default for `qcloud-cdn-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CDN-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### CDN-specific safety rules (rubric §4)

1. `DeleteCdnDomain` — domain + CNAME echo; warn CDN stop; list origin config; literal confirm
2. `PurgeUrlsCache` with `/*` — warn ALL content cleared; surface cache hit ratio; recurse-confirm
3. `PurgePathCache` — path echo; warn broad impact; root path → recurse-confirm
4. `UpdateDomainConfig` — BEFORE/AFTER diff; warn origin/SSL mismatch; confirm per field
5. `PushUrlsCache` (preload) — URL list + size echo; warn large preload origin cost; confirm

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

---

## Execution Flows

### Add CDN Domain

**Pre-flight:**
1. Verify domain ownership (DNS record or file upload)
2. Verify origin server is accessible and healthy
3. Check if domain already configured: `tccli cdn DescribeDomainsConfig --Domain {{user.domain}}`

**Execute (tccli):**
```bash
tccli cdn AddCdnDomain \
  --Domain {{user.domain}} \
  --ServiceType web \
  --OriginType cos \
  --Origin '["your-bucket.cos.ap-guangzhou.myqcloud.com"]'
```

**Validate:**
1. Verify domain added: `tccli cdn DescribeDomainsConfig --Domain {{user.domain}}`
2. Configure CNAME in DNS provider
3. Verify CNAME propagation: `dig {{user.domain}} CNAME`

### Purge URLs from Cache

**Pre-flight:**
1. Verify CDN domain is active
2. If wildcard pattern (`/*` or `/path/*`), get explicit confirmation from user with scope estimate

**Execute (tccli):**
```bash
tccli cdn PurgeUrlsCache \
  --Urls '["https://cdn.example.com/index.html", "https://cdn.example.com/css/style.css"]'
```

**Validate:**
1. Verify purge task submitted: check FlushId from response
2. Monitor cache hit ratio recovery (temporary drop expected)

### Configure HTTPS

**Pre-flight:**
1. Verify SSL certificate is uploaded to CAM or available
2. Verify domain is in active state

**Execute (tccli):**
```bash
tccli cdn UpdateDomainConfig \
  --Domain {{user.domain}} \
  --Https '{
    "Switch": "on",
    "Http2": "on",
    "CertInfo": {
      "CertId": "{{user.cert_id}}"
    }
  }'
```

**Validate:**
1. Verify HTTPS enabled: `tccli cdn DescribeDomainsConfig --Domain {{user.domain}}`
2. Test HTTPS access: `curl -I https://{{user.domain}}`

## Troubleshooting

| Error Code | Meaning | Recovery |
|---|---|---|
| `ResourceNotFound.CdnDomain` | Domain not found | Verify domain name, check if added |
| `InvalidParameter.DomainExists` | Domain already configured | Use UpdateDomainConfig instead |
| `OperationDenied.DomainStatus` | Domain not in correct status | Check domain status, start if stopped |
| `LimitExceeded.PurgeUrlsRateLimit` | Purge rate limit exceeded | Wait and retry (default: 100 URLs/minute) |
| `FailedOperation.OriginConnectFailed` | Origin connection failed | Verify origin server is reachable and healthy |
| `AuthFailure.Unauthorized` | Caller lacks CDN permissions | Verify QcloudCDNFullAccess policy attached |
| `LimitExceeded.CdnDomainQuota` | Max domains reached | Request quota increase |
| `InvalidParameter.UrlFormat` | Invalid URL format in request | Verify URL scheme (https://) and encoding |
| `FailedOperation.CertVerifyFailed` | Certificate verification failed | Check cert domain matches CDN domain |
| `OperationDenied.DomainInDeploy` | Domain being deployed | Wait for deployment to complete, retry |

---

For detailed content, see:
- [Core Concepts](references/core-concepts.md) — CDN architecture, cache hierarchy
- [API & SDK Usage](references/api-sdk-usage.md) — Operation mapping, SDK examples
- [CLI Usage](references/cli-usage.md) — tccli cdn command reference
- [Troubleshooting](references/troubleshooting.md) — Error code diagnostics
- [Monitoring](references/monitoring.md) — CDN metrics, dashboards, alerts
- [Well-Architected Assessment](references/well-architected-assessment.md) — Multi-CDN, cache safety, HTTPS automation
- [FinOps Cost Optimization](references/finops-cost-optimization.md) — Traffic analysis, cache hit optimization
- [SecOps Security Operations](references/secops-security-operations.md) — Anti-hotlinking, URL signing
