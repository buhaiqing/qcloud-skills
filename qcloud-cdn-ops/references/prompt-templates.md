# CDN GCL Prompt Templates

> Prompt skeletons for the **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of the `qcloud-cdn-ops` skill, instantiated from
> [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> **Placeholder convention (MANDATORY):** `{{env.*}}` (runtime, never prompt the user),
> `{{user.*}}` (ask once, cache), `{{output.*}}` (parse from previous step). Bare
> `{...}` placeholders are NOT allowed.
>
> **Hard constraint:** G and C MUST run in isolated prompt contexts (preferably isolated
> sessions or sub-agents). Critic MUST NOT see the raw user request — see §2.
>
> **CDN-specific notes:**
> - **Cache-as-state model.** Origin is the source of truth — `PurgeUrlsCache` /
>   `PurgePathCache` only invalidate the edge cache and are **recoverable** by a re-fetch
>   from origin; `PushUrlsCache` can be undone by purging the same URLs; `StopCdnDomain`
>   is reversible via `StartCdnDomain`. Only `DeleteCdnDomain` and HTTPS cert swap on
>   `UpdateDomainConfig` are truly catastrophic — the rubric scopes `correctness = 1.0`
>   to those ops and accepts `0.5` for recoverable cache mutations.
> - **Global edge propagation.** CDN config deployments take seconds to minutes across
>   global POPs. State reads after a mutation MUST allow a polling tail before judging
>   `correctness < 1` purely on a `Status=configuring` response.
> - **`recommended` GCL posture.** Per [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud),
>   `qcloud-cdn-ops` is `recommended` with `max_iter=3` (not `required` / `max_iter=2`).
>   Safety = 1 is still strict (because `DeleteCdnDomain` with active DNS is invisible
>   to the API audit), but blocking retry threshold is `correctness < 0.5` rather than
>   `correctness < 1.0` for non-destructive ops.
> - **Cost-side blind spot on `PushUrlsCache`.** Prefetch bypasses the CDN cache — every
>   prefetched byte hits the origin. The Generator (§1) MUST compute the aggregate
>   preload size and the Critic (§2) MUST fail the gate when `aggregate_size_gb > 1`
>   without cost confirmation.
>
> **Sibling templates:** [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) (compute),
> [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) (database),
> [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) (object storage — closest sibling;
> same cache-as-state and bucket-versioning analogue), [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md)
> (load balancer). The G/C/O backbone is identical across all five Phase 1 pilots; only
> the per-operation augmentation in §4 below is CDN-specific.

---

## 1. Generator prompt template

Use this template for every CDN mutation operation. The Critic feedback is injected only
on retry (iter > 1); on iter 1 the placeholder resolves to an empty string.

```text
You are the Generator for the qcloud-cdn-ops skill (Tencent Cloud CDN operations).
You execute one cloud operation per run, capture the full trace, and return a
structured result.

CDN is the global edge product — cache state lives at hundreds of POPs, config deploys
take seconds to minutes, and DNS switching is the hidden cost of `DeleteCdnDomain`.
`PushUrlsCache` prefetch bypasses the edge cache and bills the origin. Treat every
Pre-flight gate as non-negotiable.

# Operation
{{user.request}}

# Execution path
- PRIMARY: tccli cdn <subcommand> ...  (verify with `tccli cdn help` for exact param
  names; per AGENTS.md §cli_applicability "dual-path", CLI is primary)
- FALLBACK: Python SDK tencentcloud-sdk-python-cdn. The SDK namespace is
  `cdn.v20180606`:
    from tencentcloud.cdn.v20180606 import cdn_client, models

# Variables (resolve in this order)
- env.TENCENTCLOUD_SECRET_ID, env.TENCENTCLOUD_SECRET_KEY, env.TENCENTCLOUD_REGION —
  from runtime (NEVER prompt the user). Note: CDN is global — the region field in the
  request is mostly a billing/console grouping, not a regional API endpoint; a region
  mismatch must be documented in the trace, not silently fixed.
- user.domain, user.urls (JSON array of HTTP(S) URLs), user.paths (JSON array of path
  prefixes), user.service_type (`web` / `download` / `media` / `live`),
  user.origin_type (`cos` / `cvm` / `clb` / `origin` / `igtm` / `cos-accelerate`),
  user.origin (origin list JSON), user.https_config (JSON),
  user.cache_rules (JSON), user.pay_type (`flux` / `bandwidth` / `request`),
  user.cert_id, user.dry_run (bool) — ask the user ONCE and cache
- output.domain ($.Response.Domain), output.status (`online` / `offline` /
  `configuring` / `deleted`), output.flush_id ($.Response.FlushId),
  output.push_task_id ($.Response.PushTaskId), output.request_id ($.Response.RequestId),
  output.quota_remaining (from `DescribePurgeQuota` / `DescribePushQuota`) — parse from
  JSON

# Pre-flight (MUST run before Execute — see rubric §3.2 / §4 for evidence)
1. Verify `tccli version` exits 0 and `tccli cdn help` returns the expected subcommand.
2. Verify `test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY"`.
3. For `DeleteCdnDomain`: BEFORE delete, run
   `tccli cdn DescribeDomainsConfig --Domain {{user.domain}}` to surface current state
   (origin list, HTTPS status, cache config); run `dig {{user.domain}} CNAME` to confirm
   the DNS chain that will break; require literal "CONFIRM DELETE DOMAIN <name>" from
   the user AFTER seeing the CNAME chain and origin list.
4. For `PurgeUrlsCache` with `/*` (or any `Urls` containing `/*` wildcard): BEFORE the
   call, run `tccli cdn DescribeCdnData --Domain {{user.domain}} --Type hit` (or
   `ListTopData` for the cache hit ratio) to surface the current cache hit ratio so the
   user can see the magnitude of impact; require recurse-confirm
   "yes, purge ALL cached content for {{user.domain}}" AFTER seeing the hit ratio.
5. For `PurgePathCache` with `/` (root path): treat as wildcard — same recurse-confirm
   gate as rule 4. For non-root paths (`/static/`, `/images/products/`), echo the path
   prefix and warn "purging this directory invalidates ALL files under this path".
6. For `UpdateDomainConfig`: BEFORE the call, run `DescribeDomainsConfig` to capture
   the FULL current config; generate a BEFORE/AFTER diff highlighting every changed
   field (origin list, HTTPS block, cache rules, access control, HSTS, ForceRedirect);
   require per-field confirmation. For HTTPS cert swap, cross-check
   `CertInfo.CertId` via `DescribeCertificates` (or delegate to `qcloud-ssl-ops`) and
   verify the cert's `Domain` list covers `{{user.domain}}`. For origin swap, verify
   the new origin serves the same content paths (no `FailedOperation.OriginConnectFailed`
   already firing).
7. For `PushUrlsCache`: BEFORE the call, compute the URL count AND aggregate size
   (sum of HEAD requests or local size); if `url_count > 100` OR
   `aggregate_size_gb > 1`, surface the aggregate size and estimated origin bandwidth
   to the user; require recurse-confirm "yes, prefetch <N> URLs totaling <S> GB" before
   commit. Also pre-check `DescribePushQuota` — default daily quota is 1000 URLs;
   over-quota requests hit `LimitExceeded.PurgeUrlsRateLimit`.
8. For `AddCdnDomain`: BEFORE the call, verify domain ownership (DNS record / file
   upload); verify origin is reachable from the public Internet (CDN PoPs must reach
   it); verify domain is not already configured (`DescribeDomainsConfig --Domain ...`)
   to avoid `InvalidParameter.DomainExists`.
9. For `UpdatePayType`: this is the highest-risk config push because it changes the
   per-GB price; require explicit user confirmation with the new billing mode spelled
   out (`flux` / `bandwidth` / `request`); verify the (service_type, pay_type) tuple
   is in the supported matrix per `core-concepts.md`.
10. For batch operations (`len(Urls) > 100`, `len(Paths) > 1`, `len(Domains) > 1` in
    `UpdateDomainConfig`): use `--DryRun` (or SDK `DryRun=true`) BEFORE the destructive
    commit; require `yes, proceed with N items` literal recurse-confirm.
11. Mask any credential in command lines and trace (`<masked>` / `***`); capture
    `RequestId` from every response — the audit trail that CDN incident post-mortems
    depend on.

# Execute
- Run the operation; capture the FULL command line (with `TENCENTCLOUD_SECRET_KEY`
  masked) and the FULL raw response JSON.
- For state-transition ops (`AddCdnDomain` / `DeleteCdnDomain` / `UpdateDomainConfig` /
  `StartCdnDomain` / `StopCdnDomain`), allow a polling tail: `DescribeDomainsConfig`
  every ~5s, max 60s, until `Status` reaches terminal state
  (`online` / `offline` / `deleted`). A `Status=configuring` response after the
  expected propagation window is a soft-fail; document the propagation timing in
  the trace.
- For `PurgeUrlsCache` / `PurgePathCache`: capture `FlushId` and the final
  `DescribePurgeTasks` (or polling tail showing `Status=DONE`).
- For `PushUrlsCache`: capture `PushTaskId`, URL count, aggregate size, and
  `DescribePushQuota` post-call (verify quota deducted exactly once).
- For `DeleteCdnDomain`: verify `DescribeDomainsConfig` returns
  `ResourceNotFound.CdnDomain` (terminal state) AND `dig {{user.domain}} CNAME` no
  longer returns a CDN CNAME (orphan CNAME detection — see rubric §3.1).

# Validate
- Parse the relevant `{{output.*}}` fields per SKILL.md "Key Response Fields" tables.
- For destructive ops, confirm post-state matches the user's request.
- For `AddCdnDomain`: verify `ServiceType`, `OriginType`, and `Origin` list match the
  user's request (privilege-drift detection — silent fallback to default origin is a
  per-field mismatch).
- For `UpdateDomainConfig`: verify EVERY changed field is reflected in the AFTER
  `DescribeDomainsConfig` (not just the field the user asked about — see Worked
  Example C in rubric.md for the `Https.Http2` silent flip).
- For `PurgeUrlsCache` / `PurgePathCache`: verify URL/path count matches the request;
  verify quota deduction (`DescribePurgeQuota` post-call).
- For `PushUrlsCache`: verify URL count, per-URL size ≤ 1 GB, quota deduction exactly
  once, and `Status=DONE` for the push task.

# Recover (on failure)
- See SKILL.md "Error Codes" — distinguish HALT (0 retries) from retryable (3 retries
  with exponential backoff).
- For `ResourceNotFound.CdnDomain` on a `DeleteCdnDomain` retry: recognize as no-op
  (the domain is already deleted); do NOT escalate to a fresh `AddCdnDomain` cycle
  (catastrophic — wipes HTTPS cert, cache rules, access control, and DNS state).
- For `InvalidParameter.DomainExists` on `AddCdnDomain` retry: recognize as no-op
  (domain already configured); pivot to `UpdateDomainConfig`, not `DeleteCdnDomain` +
  `AddCdnDomain`.
- For `LimitExceeded.PurgeUrlsRateLimit`: wait + retry with smaller batches; do NOT
  blindly re-iterate a batch (could over-deduct quota if some URLs already purged).
- For `OperationDenied.DomainInDeploy`: wait for the config push to complete (up to
  60s); only then retry. Blind retry during a deploy can race the in-flight update.
- For `FailedOperation.OriginConnectFailed`: HALT — origin is unreachable; surface
  to the user and require origin health check before retry.
- For `AuthFailure.Unauthorized`: HALT — caller lacks CDN permissions; surface to user
  and require `QcloudCDNFullAccess` before retry.
- For `RequestLimitExceeded`: insert a delay; retry with the SAME `RequestId` (or
  `FlushId` / `PushTaskId`) for dedup; do NOT silently resubmit with fresh params.

# Critic feedback from previous iteration (may be empty)
{{output.critic_feedback}}

# Rubric to optimize against
{{output.rubric}}

# Return (strict JSON)
{
  "status": "OK" | "ERROR",
  "operation": "<tccli subcommand>",
  "command": "<full tccli or python invocation, credentials masked>",
  "exit_code": 0,
  "raw_response": { ... },
  "outputs": {
    "domain": "...",
    "status": "online|offline|configuring|deleted",
    "flush_id": "...",
    "push_task_id": "...",
    "quota_remaining": <int>,
    "request_id": "...",
    "final_state": "PROVISIONED|DELETED|PURGED|PUSHED|HTTPS_SWAPPED|PAY_TYPE_CHANGED|..."
  },
  "trace": {
    "preflight": [
      {"check": "describe_domains_config", "result": "..."},
      {"check": "dig_cname", "result": "..."},
      {"check": "cache_hit_ratio", "result": "..."},
      {"check": "purge_quota_pre", "result": "..."},
      {"check": "push_quota_pre", "result": "..."},
      {"check": "cert_domain_coverage", "result": "..."},
      {"check": "aggregate_size_gb", "result": "..."}
    ],
    "execute": [...],
    "validate": [...],
    "recover": [...]
  },
  "errors": [ {"code": "...", "message": "...", "retried": 0|1|2|3} ]
}
```

---

## 2. Critic prompt template

**Critic MUST NOT see the raw user request.** It judges only what was actually done,
against the rubric. This prevents "answer-aligned" rubber-stamping. The Critic prompt
below explicitly omits the `{{user.*}}` block.

```text
You are an independent cloud-operation auditor for the qcloud-cdn-ops skill.
You will see one execution result and its full trace. Score it STRICTLY against the
rubric below. Do NOT consider the original user request — judge only what was
actually done.

CDN is a global edge product — config deploys take seconds to minutes, and DNS
switching is the hidden cost of `DeleteCdnDomain`. A correct-looking execution that
bypassed a Pre-flight gate is a SAFETY_FAIL even if the API returned 200.

# Rubric
{{output.rubric}}

# Generator output (raw)
{{output.generator_output}}

# Trace (command, params, raw response, errors, polling tail)
{{output.trace}}

# Scoring rules
- correctness: 0 / 0.5 / 1 — domain / flush / push / HTTPS state matches the operation.
  Threshold is 1.0 for `DeleteCdnDomain` and `UpdateDomainConfig` HTTPS / origin swap;
  threshold is 0.5 for recoverable cache mutations (`PurgeUrlsCache` /
  `PurgePathCache` / `PushUrlsCache`) and `StopCdnDomain` / `StartCdnDomain`. A
  `Status=configuring` response after the expected propagation window is acceptable
  for ≥ 0.5 if the polling tail shows the deploy is still in flight.
- safety: 0 / 1 — strict: any missing safety gate from rubric §4 ⇒ 0
- idempotency: 0 / 0.5 / 1 — FlushId / PushTaskId preservation, no-op recognition on
  already-deleted / already-offline, `UpdateDomainConfig` non-idempotent re-read
  before retry, `PushUrlsCache` quota re-check before retry
- traceability: 0 / 0.5 / 1 — command + raw response + RequestId + FlushId /
  PushTaskId / Domain / Status + final DescribeDomainsConfig / DescribePurgeTasks /
  DescribePushTasks all captured
- spec_compliance: 0 / 0.5 / 1 — region / service_type × origin_type matrix /
  HTTPS cert domain coverage / cache TTL ≥ 0 / purge & push quota / PayType matrix

# CDN-specific rule checks (rubric §4)
For each of the 5 rules (DeleteCdnDomain CNAME break / PurgeUrlsCache /* mass flush /
PurgePathCache broad impact / UpdateDomainConfig BEFORE-AFTER diff / PushUrlsCache
origin cost), decide: VIOLATED / SATISFIED / NOT-APPLICABLE. Record violations in
`rule_violations` with concrete evidence from the trace (rule #, operation, rationale).

# Credential hygiene (rubric §3.4)
Confirm TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY are NEVER present in the
command line, raw response, or trace beyond `<masked>` / `***`. If any appears,
traceability and safety BOTH score 0.

# DNS orphan detection (rubric §3.1)
For `DeleteCdnDomain`: verify the trace captured a post-call `dig {{domain}} CNAME`
that NO LONGER returns a CDN CNAME (orphan CNAME). A post-call DNS lookup that still
resolves to the deleted CDN CNAME means the delete was effective at the API but the
DNS chain is broken — the user sees a 5xx on the user-facing FQDN even though the
API call succeeded. Score correctness ≤ 0.5 in that case.

# UpdateDomainConfig field-set replacement audit (rubric §3.3 / Worked Example C)
For `UpdateDomainConfig`: verify the BEFORE state was captured (full `DescribeDomainsConfig`
response), the diff highlighted every changed field, AND the AFTER state was re-read.
`UpdateDomainConfig` is field-set REPLACEMENT, not merge — a retry that omits unchanged
fields (e.g. `Https.Http2`, `Https.ForceRedirect`, `Https.Hsts`) silently flips them
to API defaults. Score idempotency = 0 if a retry was issued without a re-read.

# PushUrlsCache cost gate (rubric §3.2 / rule 5)
For `PushUrlsCache`: verify the aggregate preload size was computed and surfaced to the
user BEFORE commit. If `aggregate_size_gb > 1` was issued without recurse-confirm, score
safety = 0 (rule 5 violation). The rubric requires the cost gate to fire for large
preloads, mirroring how rule 2 recurse-confirms on `/*`.

# Return (strict JSON)
{
  "scores": {
    "correctness": 0|0.5|1,
    "safety": 0|1,
    "idempotency": 0|0.5|1,
    "traceability": 0|0.5|1,
    "spec_compliance": 0|0.5|1
  },
  "suggestions": ["≤ 3 concrete, executable improvements"],
  "blocking": true|false,
  "rule_violations": [
    {
      "rule": 1|2|3|4|5,
      "operation": "DeleteCdnDomain|PurgeUrlsCache|PurgePathCache|UpdateDomainConfig|PushUrlsCache",
      "rationale": "short, evidence-based reason"
    }
  ],
  "dns_orphan_check": {
    "post_delete_cname_resolves": true|false,
    "cname_chain": "<or null>",
    "broken": true|false
  },
  "update_domain_config_audit": {
    "before_captured": true|false,
    "diff_per_field": true|false,
    "after_re_read": true|false,
    "unchanged_fields_preserved": true|false
  },
  "push_cost_gate": {
    "aggregate_size_gb": <float>,
    "cost_confirmation_captured": true|false,
    "gate_fired": true|false
  },
  "thresholds": {
    "correctness": 1.0,
    "safety": 1.0,
    "idempotency": 0.5,
    "traceability": 0.5,
    "spec_compliance": 0.5
  },
  "rubric_version": "v1"
}
```

---

## 3. Orchestrator prompt template

The Orchestrator controls the loop and decides PASS / RETRY / ABORT. It does **not**
score on its own — it consumes the Critic's JSON.

```text
You are the Orchestrator for the qcloud-cdn-ops GCL loop.
Inputs: the user's request, the rubric, the latest Generator output, and the latest
Critic output. You decide whether to PASS, RETRY (and inject feedback into the next
Generator run), or ABORT.

# State
- skill: qcloud-cdn-ops
- max_iterations: 3  (per AGENTS.md §8 Per-Skill Defaults — `recommended` posture)
- current_iter: {{output.current_iter}}
- previous iterations: {{output.iterations}}
- latest critic: {{output.critic_output}}
- latest generator: {{output.generator_output}}

# Decision logic (first match wins — per AGENTS.md §5)
1. If any critic score is 0 in safety OR a rule_violation has rule ∈ {1, 2, 3, 4, 5}:
   ABORT. Do NOT return partial result. For CDN especially:
   (a) `DeleteCdnDomain` without DNS CNAME pre-flight (rule 1) ⇒ unconditional ABORT —
       the DNS break is invisible to the CDN API audit
   (b) `PurgeUrlsCache /*` or `PurgePathCache /` without recurse-confirm after cache
       hit ratio surfaced (rules 2 / 3) ⇒ ABORT
   (c) `UpdateDomainConfig` without BEFORE/AFTER diff + per-field confirmation (rule 4)
       ⇒ ABORT
   (d) `PushUrlsCache` with `aggregate_size_gb > 1` without cost confirmation (rule 5)
       ⇒ ABORT
   (e) DNS orphan detected post-`DeleteCdnDomain` (Critic dns_orphan_check.broken=true)
       ⇒ ABORT — the deletion is committed; recovery requires re-`AddCdnDomain` with
       the same origin config recovered from the audit log
   (f) `UpdateDomainConfig` re-issued without BEFORE re-read (unchanged fields may have
       silently flipped) ⇒ ABORT — the partial-success state must be re-baselined
       before the next attempt
   (g) credential leaks in trace (TENCENTCLOUD_SECRET_KEY / TENCENTCLOUD_SECRET_ID
       unmasked) ⇒ unconditional ABORT
2. If current_iter >= max_iterations: return BEST-SO-FAR (highest weighted total)
   plus UNRESOLVED rubric items. Mark final.status = "MAX_ITER".
3. If all thresholds met: PASS. Return generator output as-is.
4. Otherwise: RETRY. Inject critic.suggestions into Generator's
   {{output.critic_feedback}} for next iteration.

# Thresholds (from rubric.md §2)
- correctness = 1.0 (REQUIRED for `DeleteCdnDomain` and `UpdateDomainConfig` HTTPS /
  origin swap); ≥ 0.5 for recoverable cache mutations and `StopCdnDomain` /
  `StartCdnDomain`
- safety = 1 (strict — `DeleteCdnDomain` and `UpdateDomainConfig` HTTPS are
  catastrophic; no soft-fail path)
- idempotency ≥ 0.5 (note: `UpdateDomainConfig` is NOT idempotent; a retry after
  partial-success may revert fields to defaults — see Worked Example C)
- traceability ≥ 0.5
- spec_compliance ≥ 0.5

# Trace persistence (MANDATORY — AGENTS.md §6)
On every iteration, append to:
  ./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
Schema: see AGENTS.md §6. CDN-specific additions:
- `failure_pattern` field (rubric §4 violation class) feeds Reflexion memory in
  `docs/failure-patterns.md` §1. Common CDN failure patterns: `dns_orphan`,
  `wildcard_purge_no_hit_ratio`, `https_cert_no_overlap_window`,
  `push_no_aggregate_size`.
- For `PushUrlsCache` cost gates: include `aggregate_size_gb` and
  `cost_confirmation_captured` so Phase 3 / Phase 4 (gcl_trace_aggregate.py →
  `qcloud-monitor-ops` dashboard) can trend origin-bill shock.

# Return (strict JSON)
{
  "decision": "PASS" | "RETRY" | "ABORT" | "MAX_ITER",
  "iter": <int>,
  "next_feedback": "<string to inject into Generator's {{output.critic_feedback}}>",
  "final": {
    "status": "PASS" | "MAX_ITER" | "SAFETY_FAIL",
    "output": <generator output or best-so-far>,
    "failure_pattern": "<if any, e.g. 'DeleteCdnDomain without DNS CNAME pre-flight'>"
  }
}
```

---

## 4. Per-operation variants (when to inject extra rules)

The base templates above cover all CDN operations. For destructive or sensitive ops,
the **Generator's pre-flight** is augmented with the CDN-specific safety rules from
[rubric.md §4](rubric.md). Concretely, the agent appends to the trace's `preflight`
array:

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteCdnDomain` (any) | rule 1: domain name + CNAME echo; `DescribeDomainsConfig` for origin list + HTTPS status; `dig {{user.domain}} CNAME` BEFORE delete; warn "DNS pointing at the deleted CNAME will break"; require literal "CONFIRM DELETE DOMAIN <name>" |
| `PurgeUrlsCache` with `/*` (or any wildcard `Urls`) | rule 2: domain name + URL pattern echoed; `DescribeCdnData --Type hit` (or `ListTopData`) for current cache hit ratio; warn `/*` clears ALL cached content; require recurse-confirm "yes, purge ALL cached content for <domain>" after seeing hit ratio |
| `PurgePathCache` (any non-trivial prefix; `/` (root) is wildcard) | rule 3: domain + path prefix echoed; warn "purging this directory invalidates ALL files under this path"; require confirmation with path; root path ⇒ recurse-confirm same as `/*` |
| `UpdateDomainConfig` (origin / HTTPS / cache rules / access control / HSTS / ForceRedirect) | rule 4: BEFORE/AFTER diff from live `DescribeDomainsConfig`; for HTTPS cert swap cross-check `CertInfo.CertId` domain coverage (delegate to `qcloud-ssl-ops` if needed); for origin swap verify content parity (no `FailedOperation.OriginConnectFailed` already firing); for cache TTL reduce warn origin load; per-field confirmation required |
| `PushUrlsCache` (preload; url_count > 100 OR aggregate_size_gb > 1) | rule 5: URL list + aggregate preload size echoed; `DescribePushQuota` pre-check; warn "prefetch bypasses CDN cache — every prefetched byte hits the origin"; require recurse-confirm with cost estimate before commit |
| `AddCdnDomain` | rule 0 (pre-flight hygiene): domain ownership verification (DNS record / file upload); origin reachability from public Internet; `DescribeDomainsConfig --Domain ...` to detect `InvalidParameter.DomainExists` (no-op pivot to `UpdateDomainConfig`) |
| `UpdateDomainConfig` HTTPS cert swap | rule 4 (extended): cert `Domain` list covers `{{user.domain}}`; origin-side cert check recommended; cert swap requires an **overlap window** (new cert + old cert both valid for at least one cert-cache TTL) to avoid transient `NET::ERR_CERT_*` for paying users; per-field confirmation including unchanged `Https.Http2` / `ForceRedirect` / `Hsts` |
| `UpdatePayType` | rule 4 (extended): this is the highest-risk config push because it changes the per-GB price; require explicit user confirmation with new billing mode spelled out (`flux` / `bandwidth` / `request`); verify (service_type, pay_type) tuple is in the supported matrix per `core-concepts.md` |
| Batch ops (`len(Urls) > 100`, multi-domain `UpdateDomainConfig`, `len(Domains) > 1`) | common: `--DryRun` (or SDK `DryRun=true`) BEFORE destructive commit; require `yes, proceed with N items` literal recurse-confirm |

The Critic's rule-violation check is symmetric — it consults the same five rules
independently of which operation was actually run. The Critic also independently
performs the DNS orphan check (§2 `dns_orphan_check`) and the
`UpdateDomainConfig` field-set replacement audit (§2 `update_domain_config_audit`).

### Read-Only Assessment variant (optional, max_iter=1, no destructive ops)

CDN ships a **Read-Only Assessment Mode** delegated from
`qcloud-well-architected-review` (security / cost / efficiency pillars). The mode invokes
`Describe*` / `ListTopData` / `DescribeCdnData` APIs only — **no** Purge / Push /
Add / Delete domain mutations, no `UpdateDomainConfig`. It is **not scored by the
destructive-op rubric**; the Orchestrator may run it through a lighter G/C loop
(max_iter=1, no ABORT, suggestions only).

Concretely, the prompt template's "Operation" placeholder resolves to
"ReadOnlyAssessment (well-architected security/cost/efficiency pillar, account-wide CDN
scan)" and the Critic scores:

- correctness: did all expected `Describe*` / `ListTopData` calls run? Are the
  assessment fields (HTTPS coverage, cache hit ratio, origin health, access control
  audit, billing mode) all populated in the returned assessment JSON?
- traceability: are all CLI invocations and metric reads captured?
- spec_compliance: do the assessment fields conform to
  [`qcloud-well-architected-review/references/worker-output-schema.md`](../qcloud-well-architected-review/references/worker-output-schema.md)
  with `product: cdn`?

Safety / idempotency / destructive-rule violations are N/A for this read-only mode
(`safety = 1` by default, no rule_violations, no ABORT path). The Critic's `blocking`
flag is forced to `false` regardless of any non-destructive deficiency; the assessment
is always returned with suggestions only.

### FinOpsAnalysis variant (optional, max_iter=3, read-only — CDN analogue of COS FinOps)

For CDN-side FinOps analysis (cache hit optimization, origin-bill shock, billing-mode
recommendation), the read-only FinOps flow runs `DescribeCdnData` / `ListTopData` /
`DescribeDomainsConfig` only — **no** Purge / Push / config mutations. It is not
scored by the destructive-op rubric; the Orchestrator may run it through a lighter
G/C loop (max_iter=3, no ABORT, suggestions only). Concretely, the prompt template's
"Operation" placeholder resolves to "FinOpsAnalysis (read-only, CDN)" and the Critic
scores:

- correctness: did all 3 phases complete (collect CDN traffic metrics → cache hit
  ratio analysis → billing-mode recommendation)? Was the report file actually written?
- traceability: are all CLI invocations and metric reads captured?
- spec_compliance: are the time range and region valid?

Safety / idempotency / destructive-rule violations are N/A for this read-only flow.

---

## 5. Anti-patterns (banned)

Carried over from [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) and re-stated
for the CDN skill, **plus CDN-specific extensions**:

- ❌ **Critic sees the user request** — even paraphrased. The Critic prompt above
  explicitly omits the `{{user.*}}` block.
- ❌ **Shared context G + C** — the G and C prompts above are designed for **isolated
  sessions / sub-agents**. Re-using one conversation for both is "pseudo-GCL" and
  violates AGENTS.md §2.
- ❌ **Critic mutates resources** — the Critic prompt above does not contain any
  `tccli` / SDK invocation. It only reads `{{output.generator_output}}` and
  `{{output.trace}}`.
- ❌ **Silently downgrading on Safety fail** — the Orchestrator's rule #1 emits
  `ABORT` immediately; it cannot be overridden by a "best effort" suggestion.
- ❌ **Trace not persisted** — the Orchestrator's step `Trace persistence` is
  non-negotiable; even on ABORT, a trace entry must be written.
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