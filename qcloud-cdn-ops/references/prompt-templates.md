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

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **dynamic** (per-operation risk-based strategy from SKILL.md §Quality Gate).

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CDN — 5 rules). Do not duplicate gate text here.

| Role | Action |
|---|---|
| Generator | Load rubric §4; map op → rule 1–5; run gates; append to trace `preflight` |
| Critic | Score rubric §3 + mark §4 rules VIOLATED / SATISFIED / NOT-APPLICABLE |
| Orchestrator | Safety=0 on §4 violation (destructive) → ABORT; advisory/read-only: rubric §2 |

API flows: [SKILL.md](../SKILL.md) (Pre-flight → Execute → Verify → Recover).

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
