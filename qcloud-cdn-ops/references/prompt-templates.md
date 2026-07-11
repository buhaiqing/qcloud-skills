# CDN GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-cdn-ops` |
| CLI | `tccli cdn help` |
| max_iterations | dynamic (per-operation risk-based) |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CDN).

### P2: Parallel Critic specialization

P2 optimization: Two specialized Critics run in parallel for efficiency.

| Critic | Focus dimensions | CDN-specific checks |
|---|---|---|
| **Data Quality Critic** | Correctness, Spec Compliance, Idempotency | API fidelity, JSON path accuracy, state transitions |
| **Safety Rules Critic** | Safety (highest priority), Traceability | CDN safety rules 1–5, credential masking, anti-patterns |

Both Critics score independently in parallel; Orchestrator aggregates scores.

**P4 Priority Grading**: See [`rubric.md`](rubric.md) §2.3 for risk levels (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL). Operations graded by risk determine GCL strictness.

**P5 Context-Aware**: See [`rubric.md`](rubric.md) §2.4 for operation classification (first-time/repeat/failure-recovery) and context-adaptive thresholds.

#### Data Quality Critic prompt

```
You are the Data Quality Critic for qcloud-cdn-ops GCL.

Evaluate the Generator's output on these dimensions ONLY:
- Correctness: Did the API call achieve the intended state?
- Spec Compliance: Are parameters and API calls correct per tccli cdn help?
- Idempotency: Can retries safely re-run without side effects?

For CDN specifically:
- Verify FlushId/PushTaskId returned for async operations
- Verify DescribeDomainsConfig state reached terminal (online/offline/deleted)
- Check UpdateDomainConfig field-set replacement model (not merge)
- Verify PurgeUrlsCache/PushUrlsCache quota deducted once

Return JSON:
{
  "critic_type": "data_quality",
  "scores": {
    "correctness": 0|0.5|1,
    "spec_compliance": 0|0.5|1,
    "idempotency": 0|0.5|1
  },
  "suggestions": ["≤ 2 concrete improvements"],
  "blocking": true|false
}
```

#### Safety Rules Critic prompt

```
You are the Safety Rules Critic for qcloud-cdn-ops GCL.

Evaluate the Generator's output on these dimensions ONLY:
- Safety: Are all CDN safety rules (1–5) satisfied?
- Traceability: Is the trace complete with RequestId, FlushId, before/after state?

CDN Safety Rules (score 0 on ANY violation):
1. DeleteCdnDomain: Domain name + CNAME check + "CONFIRM DELETE DOMAIN <name>" required
2. PurgeUrlsCache /*: Domain + URL pattern + cache hit ratio + "yes, purge ALL" required
3. PurgePathCache: Domain + path + "yes, purge <path>" required
4. UpdateDomainConfig: BEFORE/AFTER diff + per-field confirmation required
5. PushUrlsCache: URL list + aggregate size + cost warning for > 1GB

Also check:
- TENCENTCLOUD_SECRET_KEY never in trace (only <masked>)
- No DNS orphan after DeleteCdnDomain
- No wildcard purge without hit ratio context
- No HTTPS cert swap without overlap window

Return JSON:
{
  "critic_type": "safety_rules",
  "scores": {
    "safety": 0|1,
    "traceability": 0|0.5|1
  },
  "rule_violations": [{"rule": 1-5, "operation": "...", "rationale": "..."}],
  "suggestions": ["≤ 2 concrete improvements"],
  "blocking": true|false
}
```

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **dynamic** (per-operation risk-based strategy from SKILL.md §Quality Gate).
> **Early stop**: confidence (all dims ≥ 0.9), safety (all rules satisfied), convergence (Δ < 0.1 × 2 rounds), single-op (max_iter=1 passing gates) — see SKILL.md §Early stop mechanisms.
> **P2 Parallel Critics**: Data Quality Critic + Safety Rules Critic run in parallel; aggregate scores (safety score takes precedence).

### Parallel Critic aggregation

When both Critics return scores:

1. **Safety precedence**: If either Critic reports `safety = 0` → **ABORT** immediately
2. **Score aggregation**:
   - Correctness: max(DataQuality.correctness, SafetyRules — fallback only)
   - Safety: **SafetyRules Critic is authoritative** (never fallback)
   - Idempotency: DataQuality.idempotency
   - Traceability: SafetyRules.traceability
   - Spec Compliance: DataQuality.spec_compliance
3. **Suggestions merge**: ≤ 4 total (2 from each Critic)
4. **blocking**: true if either Critic reports blocking = true

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CDN — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

### P3: Adaptive backoff strategy

P3 optimization: Dynamic retry interval adjustment based on error type.

| Error Category | Examples | Backoff Strategy |
|---|---|---|
| **Transient** | `InternalError`, `RequestLimitExceeded`, `OperationDenied.DomainInDeploy` | **Exponential backoff**: 2s → 4s → 8s → 16s (max 60s) |
| **Quota exhausted** | `LimitExceeded.PurgeUrlsRateLimit`, `LimitExceeded.CdnDomainQuota` | **Fixed interval**: Wait exact quota refill time (check via DescribePurgeQuota) |
| **Config propagation** | `UpdateDomainConfig` async deploy | **Progressive polling**: 2s → 5s → 10s → 30s until Status = online |
| **Permanent** | `InvalidParameter`, `ResourceNotFound`, `AuthFailure.*` | **No retry**: HALT and surface error immediately |

CDN-specific backoff rules:
- `PurgeUrlsCache`: Rate limit 100 URLs/min — backoff 600ms per URL over limit
- `PushUrlsCache`: Daily quota 1000 — no retry on quota exceeded, wait for reset
- `AddCdnDomain` / `UpdateDomainConfig`: Config deploy takes 30-120s — progressive polling
- `DeleteCdnDomain`: DNS TTL propagation ~300s — warn user before retry

Orchestrator retry decision:
```
IF error.category == "permanent":
    ABORT with error
ELIF error.category == "transient" AND retry_count < 3:
    sleep(exponential_backoff(retry_count))
    RETRY
ELIF error.category == "quota":
    sleep(quota_refill_time OR fixed_interval(30s))
    RETRY
ELIF error.category == "propagation":
    poll DescribeDomainsConfig until Status == target OR timeout(120s)
    RETRY
```

---

## 5. Anti-patterns (banned)


> Generic GCL anti-patterns: [../../qcloud-skill-generator/references/gcl-prompt-backbone.md](../../qcloud-skill-generator/references/gcl-prompt-backbone.md) §4.
> Below: **product-only** bans.


- ❌ **Logging secret content** — extending the AGENTS.md list with the CDN-specific
  ban on letting `TENCENTCLOUD_SECRET_KEY` appear unmasked anywhere in command,
  response, or trace.
- ❌ **`DeleteCdnDomain` without DNS CNAME check** — CDN-specific: the API will
  return success on the deletion, but if DNS still points at the deleted domain's
  CDN CNAME, all HTTP/S requests fail. This is the highest-impact CDN incident class
  and is invisible to the CDN API audit log.
- ❌ **`PurgeUrlsCache --Urls "/*"` without cache-hit-ratio context and recurse-confirm**
  — CDN-specific: a `/*` purge is the most common CDN incident. The user means
  "purge this file" but types `/*` instead of `/specific-file.js`. The result: all
  cached data is flushed, origin traffic spikes, costs increase.
- ❌ **`PurgePathCache` with `/` (root) treated as a normal path** — CDN-specific:
  root-path purge is the directory-purge analogue of `/*` URL purge; treat it as a
  wildcard with recurse-confirm.
- ❌ **`UpdateDomainConfig` HTTPS cert swap without overlap window** — CDN-specific:
  swapping the cert without an overlap window (new cert + old cert both valid for at
  least one cert-cache TTL) produces transient `NET::ERR_CERT_*` for paying users.
  The Critic must verify the BEFORE/AFTER diff includes the unchanged `Https.Http2`
  / `ForceRedirect` / `Hsts` fields — silent flip on retry is the canonical catch.
- ❌ **`UpdateDomainConfig` origin swap without content parity check** — CDN-specific:
  the new origin must serve the same paths as the old origin; otherwise 404 surge
  until the cache expires. The Generator must verify
  `FailedOperation.OriginConnectFailed` is not already firing.
- ❌ **`PushUrlsCache` large preload without cost warning** — CDN-specific: prefetch
  bypasses the CDN cache and bills the origin. A 1.6 GB preload of dynamically
  generated images is the canonical "origin-bill shock" pattern. The Generator must
  compute `aggregate_size_gb` and fire the recurse-confirm gate when `> 1`.
- ❌ **`UpdatePayType` (billing mode flip) without explicit disclosure** —
  CDN-specific: `flux` ↔ `bandwidth` ↔ `request` changes the per-GB price; a silent
  flip on retry after a `RequestLimitExceeded` can move a high-traffic domain from
  pay-by-bandwidth to pay-by-flux overnight. Require explicit user confirmation.
- ❌ **`AddCdnDomain` blind retry on `InvalidParameter.DomainExists`** — CDN-specific:
  the domain is already configured; escalate to `UpdateDomainConfig`, NOT to a
  `DeleteCdnDomain` + `AddCdnDomain` cycle (which wipes HTTPS cert, cache rules,
  access control, and DNS state — catastrophic).
- ❌ **`UpdateDomainConfig` retry without `DescribeDomainsConfig` re-read** —
  CDN-specific: `UpdateDomainConfig` is field-set REPLACEMENT, not merge. A retry
  after partial-success may revert unchanged fields (e.g. `Https.Http2`) to API
  defaults. The Generator must re-read the full current config before retry.
- ❌ **`PushUrlsCache` retry without `DescribePushQuota` re-check** — CDN-specific:
  quota deduction is NOT idempotent. A retry of the same `PushTaskId` may deduct
  quota twice. The Generator must poll `DescribePushQuota` before retry to confirm
  the previous deduction already happened.
- ❌ **Trusting a successful `Status=configuring` response as terminal state** —
  CDN-specific: CDN config deploys take seconds to minutes across global POPs. A
  `Status=configuring` response after `AddCdnDomain` / `UpdateDomainConfig` is not
  a failure, but is not terminal either; the Generator must poll until the state
  reaches `online` / `offline` / `deleted` (or document the propagation timing in
  the trace if max-iter exceeded).
- ❌ **Skipping the propagation-window validation read** — CDN-specific: the
  Generator's Validate step MUST re-read the AFTER state via `DescribeDomainsConfig`
  for any mutation that touches HTTPS / origin / cache rules / access control.
  Otherwise a config push that silently failed at a subset of POPs goes undetected.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CDN rollout: Generator + Critic + Orchestrator templates for CDN (5 rules, isolated-context enforcement, domain-delete CNAME break, wildcard purge, origin config change, preload origin cost) |
| 1.1.0 | 2026-06-19 | Tier A conformance: flesh out to 7 sections (Generator / Critic / Orchestrator / Per-operation / Anti-patterns / Changelog / See also). Generator Pre-flight now mandates `DescribeDomainsConfig` BEFORE / AFTER every mutation, `dig <domain> CNAME` BEFORE `DeleteCdnDomain`, `DescribeCdnData --Type hit` BEFORE `/*` purge, `DescribePurgeQuota` / `DescribePushQuota` BEFORE purge / push, `DescribeCertificates` cross-check for HTTPS cert swap, and `aggregate_size_gb` cost gate for `PushUrlsCache` > 1 GB. Critic §2 adds DNS orphan detection (`dns_orphan_check`), `UpdateDomainConfig` field-set replacement audit (`update_domain_config_audit`), and `PushUrlsCache` cost-gate audit (`push_cost_gate`). Orchestrator §3 elevates ABORT triggers for DNS orphan, wildcard purge without hit ratio, HTTPS cert without overlap window, and `PushUrlsCache` over-quota retry. Anti-patterns §5 adds 11 CDN-specific entries: `/*` purge without recurse-confirm, root-path purge as normal path, HTTPS cert swap without overlap window, origin swap without content parity, `PushUrlsCache` over-quota retry, `UpdatePayType` silent flip, `InvalidParameter.DomainExists` blind retry, `UpdateDomainConfig` retry without re-read, `PushUrlsCache` retry without quota re-check, trusting `Status=configuring` as terminal, skipping the propagation-window validation read. Per-operation variants §4 adds `AddCdnDomain` rule 0 (pre-flight hygiene), HTTPS cert overlap window note, `UpdatePayType` confirmation, batch `--DryRun`. Read-Only Assessment variant (§4) added for `qcloud-well-architected-review` delegation; FinOpsAnalysis variant (§4) added for CDN-side FinOps read-only flow |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |
| 1.9.0 | 2026-07-10 | P5 GCL optimization: context-aware GCL (first-time/repeat/failure-recovery); P5 reference in parallel Critics |
| 1.8.0 | 2026-07-10 | P4 GCL optimization: safety rule priority grading (CRITICAL/HIGH/MEDIUM/LOW/MINIMAL); P4 reference in parallel Critics |
| 1.7.0 | 2026-07-10 | P3 GCL optimization: adaptive backoff strategy (transient exponential, quota fixed, propagation polling); CDN-specific backoff rules |
| 1.6.0 | 2026-07-10 | P2 GCL optimization: parallel Critic specialization (Data Quality Critic + Safety Rules Critic); score aggregation with safety precedence |
| 1.5.0 | 2026-07-10 | P1 GCL optimization: early stop triggers in Orchestrator template (confidence, safety, convergence, single-op); enhanced decision flow |
| 1.4.0 | 2026-07-10 | P0 GCL optimization: dynamic `max_iterations` per operation risk in Generator/Orchestrator templates; early stop mechanisms |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) — banned anti-patterns (re-stated in §5 above)
- [AGENTS.md §14](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory for cross-session learning (CDN-specific failure patterns: `dns_orphan`, `wildcard_purge_no_hit_ratio`, `https_cert_no_overlap_window`, `push_no_aggregate_size`)
- [rubric.md](rubric.md) — the rubric instance these templates score against (8 sections, Tier A, 5 CDN-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates, Execution Flows, and `## Quality Gate (GCL)` chapter
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time destructive-op confirmation list (DeleteCdnDomain / PurgeUrlsCache `/*` / PurgePathCache)
- [SKILL.md §Execution Flows](../SKILL.md#execution-flows) — `AddCdnDomain` / `PurgeUrlsCache` / HTTPS configure tccli command reference
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (database pilot)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage pilot, FinOpsAnalysis read-only variant reference; closest analogue for CDN's cache-as-state and bucket-versioning model)
- [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) — sibling templates (load balancer pilot)
- [`qcloud-ssl-ops`](../ssl-ops/references/prompt-templates.md) — sibling templates for certificate management (CDN HTTPS cert swap cross-check delegate)
