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
  version: "1.7.0"
  last_updated: "2026-07-10"
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
related_skills:
  - qcloud-redis-ops
  - qcloud-clb-ops
  - qcloud-aiops-diagnosis
  - qcloud-monitor-ops
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
- Task is **origin 5xx RCA, cache hit drop, edge latency correlation, or cross-layer origin diagnosis** (CDN + COS/CVM/CLB) → delegate to: `qcloud-aiops-diagnosis` (read-only); execute fixes via this skill per bundle recommendations — see [`references/aiops-diagnosis.md`](references/aiops-diagnosis.md)
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

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | `***` (masked) |
| `{{user.domain}}` | User | `cdn.example.com` |
| `{{user.urls}}` | User | JSON array |
| `{{user.origin_type}}` | User | `cos` |

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
| 1.7.0 | 2026-07-10 | P4 GCL optimization: safety rule priority grading (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL); strictness adapts to operation risk level |
| 1.6.0 | 2026-07-10 | P3 GCL optimization: adaptive backoff strategy (transient exponential, quota fixed, propagation polling); CDN-specific backoff rules for purge/push/config deploy |
| 1.5.0 | 2026-07-10 | P2 GCL optimization: parallel Critic specialization (Data Quality Critic + Safety Rules Critic); score aggregation with safety precedence; enhanced Quality Gate table |
| 1.4.0 | 2026-07-10 | P1 GCL optimization: early stop mechanisms (confidence early stop Δ ≥ 0.9, single-op early stop for max_iter=1 ops, irreversible abort for DeleteCdnDomain with score < 1.0); enhanced decision flow with 8 rules |
| 1.3.0 | 2026-07-10 | P0 GCL optimization: dynamic `max_iterations` per operation risk (2 for destructive, 1 for cache mutations, 3 for sensitive config changes); early stop mechanisms (safety rule satisfaction, score convergence) |
| 1.2.0 | 2026-06-13 | Rule P reverse delegation: `references/aiops-diagnosis.md`; Trigger & Scope aiops delegate for origin 5xx/cache/latency RCA |

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

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each CDN execution against an explicit rubric,
in addition to the build-time **Safety Gates** above and the build-time **2-round
self-review** in [AGENTS.md](../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **dynamic** | per-operation risk-based strategy (see below) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CDN-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + **2 parallel Critics** + Orchestrator, isolated-context |
| **Parallel Critics** | **Data Quality Critic** + **Safety Rules Critic** | See [`prompt-templates.md`](references/prompt-templates.md) §2 P2 |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../AGENTS.md#6-trace--audit-mandatory) |

### Dynamic max_iterations strategy

| Operation class | `max_iterations` | Rationale |
|---|---|---|
| Destructive: `DeleteCdnDomain` | **2** | Irreversible; stricter iteration with early abort on safety violations |
| Cache mutation: `PurgeUrlsCache` / `PurgePathCache` with `/*` or `/` | **1** | Recoverable from origin; single iteration sufficient for safety gates |
| Sensitive mutating: `UpdateDomainConfig` (origin / HTTPS cert swap), `StopCdnDomain` | **3** | Complex config propagation; needs iterative verification |
| Mutating: `AddCdnDomain`, `PushUrlsCache`, `UpdatePayType`, `EnableCdnDomain` | **2** | Cost/config risk; moderate iteration |
| Read-only: `DescribeDomainsConfig`, `DescribeCdnData`, `DescribePurgeQuota` | **1** | Pre-flight only; no hard abort |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteCdnDomain` | **yes** | Irreversible; DNS still pointing to CNAME breaks all traffic |
| Cache mutation: `PurgeUrlsCache` / `PurgePathCache` with `/*` or `/` | **yes** | Origin traffic spike; cost impact; needs scoring |
| Sensitive mutating: `UpdateDomainConfig` (origin / HTTPS cert swap), `StopCdnDomain` | **yes** | Silent user-impact surface; TLS handshake failures |
| Mutating: `AddCdnDomain`, `PushUrlsCache`, `UpdatePayType`, `EnableCdnDomain` | **yes** | Cost / config risk; needs scoring |
| Read-only: `DescribeDomainsConfig`, `DescribeCdnData`, `DescribePurgeQuota` | optional (max_iter=1, no hard abort) | Pre-flight for parent mutations |

### Early stop mechanisms

P1 optimization: 提前终止不必要的迭代。

| Trigger | Condition | Action | Rationale |
|---|---|---|---|
| **Safety early stop** | All CDN safety rules (rules 1–5) satisfied + other dimensions ≥ threshold | **PASS** | Safety is the primary concern; if all safety gates passed, no need to continue |
| **Confidence early stop** | All dimensions ≥ 0.9 AND no rule violations | **PASS** | High confidence result; marginal improvements unlikely |
| **Convergence early stop** | Δ < 0.1 for 2 consecutive rounds | **PASS** | Critic scores stabilized; further iteration yields diminishing returns |
| **Single-op early stop** | `max_iter=1` ops (cache mutations, read-only) that pass safety gates | **PASS** after iter 1 | No benefit from iteration; safety gates sufficient |
| **Irreversible abort** | `DeleteCdnDomain` with any safety concern (score < 1.0) | **ABORT** | Cannot undo; strictest iteration control |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (immediate stop, no partial result)
2. **Confidence early stop**: All dimensions ≥ 0.9 AND no rule violations ⇒ **PASS** (high confidence)
3. **Safety early stop**: All CDN safety rules satisfied + other dimensions meet thresholds ⇒ **PASS**
4. **Single-op early stop**: `max_iter=1` ops (cache mutations, read-only) that pass safety gates ⇒ **PASS** after iter 1
5. **Convergence early stop**: Δ < 0.1 for 2 consecutive rounds ⇒ **PASS** (convergence)
6. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
7. **All dimension thresholds met** ⇒ **PASS**
8. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### P3: Adaptive backoff on retry

P3 optimization: Retry intervals adapt to error type (see [`prompt-templates.md`](references/prompt-templates.md) §4).

| Error class | Strategy | CDN examples |
|---|---|---|
| Transient (`InternalError`, `RequestLimitExceeded`) | Exponential backoff: 2s → 4s → 8s → 16s (max 60s) | API overload, rate limiting |
| Quota exhausted (`LimitExceeded.*`) | Fixed interval: check quota refill time via DescribePurgeQuota | Purge/push rate limits |
| Config propagation (`UpdateDomainConfig`) | Progressive polling: 2s → 5s → 10s → 30s until Status = target | Async deploy |
| Permanent (`InvalidParameter`, `ResourceNotFound`) | No retry — HALT immediately | User error, missing resource |

### CDN-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteCdnDomain` (any) | Domain name + CNAME + traffic/bandwidth estimate echo; warn that deletion deactivates the domain'... |
| 2 | `PurgeUrlsCache` with `/*` wildcard (purge all) | Domain name + URL pattern echoed; warn that `/*` clears ALL cached content for the domain — every... |
| 3 | `PurgePathCache` (directory-level) | Domain name + path prefix echoed; warn that purging a directory invalidates ALL files under that ... |
| 4 | `UpdateDomainConfig` (any configuration change: origin, SSL cert, cache rules, access control) | Show BEFORE/AFTER config diff; for origin change: warn that new origin must serve the same conten... |
| 5 | `PushUrlsCache` (prefetch / URL preload) | URL list + estimated preload size echoed; warn that prefetching large files (>1GB total) may incu... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteCdnDomain` with active DNS

| Dimension | Score |
|---|---|
| Correctness | 0.5 (domain deleted, but gate should have caught DNS) |
| **Safety** | **0** (rule 1 violated — no `dig` CNAME check, no literal confirm) |
| Idempotency | 1 |
| Traceability | 1 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion: "Re-add domain via `AddCdnDomain`; update DNS to point away from CDN CNAME before retry."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `PurgeUrlsCache` and RETRY on `UpdateDomainConfig` HTTPS cert swap).

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
