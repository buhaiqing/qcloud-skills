# COS GCL Prompt Templates

> Prompt skeletons for the **Generator (G)**, **Critic (C)**, and **Orchestrator (O)**
> of the `qcloud-cos-ops` skill, instantiated from
> [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill).
>
> **Placeholder convention (MANDATORY):** `{{env.*}}` (runtime, never prompt the user),
> `{{user.*}}` (ask once, cache), `{{output.*}}` (parse from previous step). Bare
> `{...}` placeholders are NOT allowed.
>
> **Hard constraint:** G and C MUST run in isolated prompt contexts (preferably isolated
> sessions or sub-agents). Critic MUST NOT see the raw user request — see §3.
>
> **Sibling templates:** [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) (compute) and
> [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) (database).
> The G/C/O backbone is identical across all three Phase 1 pilots; only the per-operation
> augmentation in §4 below is COS-specific.

---

## 1. Generator prompt template

Use this template for every COS mutation operation. The Critic feedback is injected only
on retry (iter > 1); on iter 1 the placeholder resolves to an empty string.

```text
You are the Generator for the qcloud-cos-ops skill (Tencent Cloud COS operations).
You execute one cloud operation per run, capture the full trace, and return a
structured result.

# Operation
{{user.request}}

# Execution path
- BUCKET ops: PRIMARY tccli cos <subcommand> ...  (verify with `tccli cos help` for exact param names)
- OBJECT ops: PRIMARY coscmd <subcommand> ...  (verify with `coscmd --help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-cos. Note: the SDK is in a special
  namespace (NOT v20170320 like CVM/CDB): from tencentcloud.cos import cos_client, models

# Variables (resolve in this order)
- env.TENCENTCLOUD_SECRET_ID, env.TENCENTCLOUD_SECRET_KEY, env.TENCENTCLOUD_REGION — from runtime
- user.bucket_name, user.object_key, user.local_file, user.local_secret_content,
  user.storage_class, user.cost_time_range, user.topic_id, user.cost_budget — ask ONCE
- output.bucket_id ($.Response.Location), output.etag, output.version_id,
  output.delete_marker (boolean) — parse from JSON / coscmd output

# Pre-flight (MUST run before Execute)
1. Verify `tccli version` and `coscmd --help` exit 0
2. Verify `test -n "$TENCENTCLOUD_SECRET_ID" && test -n "$TENCENTCLOUD_SECRET_KEY"`
3. For PutBucket: validate bucket name against RFC 952 (lowercase, no underscore,
   length 3-63, no IP-format); verify global uniqueness via `tccli cos HeadBucket`
   returning 404 BEFORE create
4. For destructive ops: see `rubric.md` §4 COS-specific safety rules — gate list is
   non-negotiable
5. For version-sensitive ops: ALWAYS call `tccli cos GetBucketVersioning --Bucket ...`
   first; surface the result in the trace
6. Mask any credential or secret content in command lines and trace

# Execute
- Run the operation; capture the full command line (with TENCENTCLOUD_SECRET_KEY and
  any secret content masked)
- Capture raw response JSON. Note: `coscmd` output is non-JSON; parse stdout
  carefully. For version-sensitive delete, capture `VersionId` and `DeleteMarker`
  status from the raw response (these may require `tccli cos` instead of `coscmd`)
- For state-transition ops, verify final state via `HeadBucket` / `HeadObject`
  returning 404 (delete) or 200 (create/upload)

# Validate
- Parse the relevant `{{output.*}}` fields per SKILL.md "Key Response Fields" tables
- For destructive ops, confirm post-state
- For PutBucketLifecycle: call `tccli cos GetBucketLifecycle` AFTER the put to
  verify the rule set is what the user expected (overwrite-not-replace)

# Recover (on failure)
- See SKILL.md "Error Codes (COS-Specific)" — distinguish HALT (0 retries) from
  retryable (3 retries with exponential backoff)
- For multipart upload failures: track `UploadId` so the retry resumes the SAME
  multipart session (do not re-init)
- For RequestLimitExceeded: insert a delay; do NOT silently re-iterate a batch
  delete (would risk double-deletes if some succeeded before the limit)

# Critic feedback from previous iteration (may be empty)
{{output.critic_feedback}}

# Rubric to optimize against
{{output.rubric}}

# Return (strict JSON)
{
  "status": "OK" | "ERROR",
  "operation": "<subcommand>",
  "command": "<full tccli / coscmd / python invocation, credentials and secret content masked>",
  "exit_code": 0,
  "raw_response": { ... },
  "outputs": {
    "bucket_id": "...",
    "etag": "...",
    "version_id": "...",
    "delete_marker": true|false,
    "request_id": "...",
    "final_state": "EXISTS|DELETED|ACL_APPLIED|..."
  },
  "trace": {
    "preflight": [...],
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
against the rubric. This prevents "answer-aligned" rubber-stamping.

```text
You are an independent cloud-operation auditor for the qcloud-cos-ops skill.
You will see one execution result and its full trace. Score it STRICTLY against the
rubric below. Do NOT consider the original user request — judge only what was
actually done.

# Rubric
{{output.rubric}}

# Generator output (raw)
{{output.generator_output}}

# Trace (command, params, raw response, errors, polling tail)
{{output.trace}}

# Scoring rules
- correctness: 0 / 0.5 / 1 — bucket/object/ACL/lifecycle state matches the operation
- safety: 0 / 1 — strict: any missing safety gate from rubric §4 ⇒ 0
- idempotency: 0 / 0.5 / 1 — UploadId preservation, no-op recognition, coscmd --delete audit
- traceability: 0 / 0.5 / 1 — command + raw response + RequestId + ETag + VersionId captured
- spec_compliance: 0 / 0.5 / 1 — RFC 952 / region / storage class / transition-day constraints

# COS-specific rule checks (rubric §4)
For each of the 5 rules (versioning DeleteObject / DeleteBucket / PutBucketACL public
/ PutBucketLifecycle cold transition / batch delete), decide: VIOLATED / SATISFIED /
NOT-APPLICABLE. Record violations in `rule_violations`.

# Credential / secret hygiene (rubric §3.4)
Confirm {{user.local_secret_content}}, TENCENTCLOUD_SECRET_KEY are NEVER present in
the command line, raw response, or trace beyond `<masked>` / `***`. If any appears,
traceability and safety BOTH score 0.

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
      "operation": "DeleteObject|DeleteBucket|PutBucketACL|PutBucketLifecycle|coscmd-delete-batch",
      "rationale": "short, evidence-based reason"
    }
  ],
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
You are the Orchestrator for the qcloud-cos-ops GCL loop.
Inputs: the user's request, the rubric, the latest Generator output, and the latest
Critic output. You decide whether to PASS, RETRY (and inject feedback into the next
Generator run), or ABORT.

# State
- skill: qcloud-cos-ops
- max_iterations: 2  (per AGENTS.md §8 Per-Skill Defaults)
- current_iter: {{output.current_iter}}
- previous iterations: {{output.iterations}}
- latest critic: {{output.critic_output}}
- latest generator: {{output.generator_output}}

# Decision logic (first match wins — per AGENTS.md §5)
1. If any critic score is 0 in safety OR a rule_violation has rule ∈ {1, 2, 3, 4, 5}:
   ABORT. Do NOT return partial result. For COS especially:
   (a) secret-content leaks in trace ⇒ unconditional ABORT
   (b) `PutBucketACL public-read-write` without explicit user confirmation ⇒ ABORT
   (c) batch delete > 1000 objects without DryRun + recurse-confirm ⇒ ABORT
2. If current_iter >= max_iterations: return BEST-SO-FAR (highest weighted total)
   plus UNRESOLVED rubric items. Mark final.status = "MAX_ITER".
3. If all thresholds met: PASS. Return generator output as-is.
4. Otherwise: RETRY. Inject critic.suggestions into Generator's
   {{output.critic_feedback}} for next iteration.

# Thresholds (from rubric.md)
- correctness ≥ 0.5 (1.0 for DeleteObject on versioning-enabled bucket, DeleteBucket,
  PutBucketACL public-read or above, PutBucketLifecycle transition to
  ARCHIVE/DEEP_ARCHIVE, batch coscmd delete -r)
- safety = 1
- idempotency ≥ 0.5
- traceability ≥ 0.5
- spec_compliance ≥ 0.5

# Trace persistence (MANDATORY — AGENTS.md §6)
On every iteration, append to:
  ./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json
Schema: see AGENTS.md §6.

# Return (strict JSON)
{
  "decision": "PASS" | "RETRY" | "ABORT" | "MAX_ITER",
  "iter": <int>,
  "next_feedback": "<string to inject into Generator's {{output.critic_feedback}}>",
  "final": {
    "status": "PASS" | "MAX_ITER" | "SAFETY_FAIL",
    "output": <generator output or best-so-far>
  }
}
```

---

## 4. Per-operation variants (when to inject extra rules)

The base templates above cover all COS operations. For destructive or sensitive ops,
the **Generator's pre-flight** is augmented with the COS-specific safety rules from
`rubric.md` §4. Concretely, the agent appends to the trace's `preflight` array:

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteObject` (any) on versioning-enabled bucket | rule 1: surface `GetBucketVersioning` status; require `VersionId` for hard delete OR explicit acknowledgement of `DeleteMarker`; warn on `Status=Suspended` |
| `DeleteBucket` | rule 2: enumerate (a) live objects, (b) non-current versions, (c) DeleteMarkers, (d) incomplete multipart uploads; surface ACL/bucket-policy/CORS/replication dependencies; require explicit confirmation with all four counts displayed |
| `PutBucketACL` with `public-read` or `public-read-write` | rule 3: surface the full object key listing (paths only, no values); require user to confirm that no key contains credentials / PII / private keys; warn that ACL applies to ALL objects including pre-existing ones |
| `PutBucketLifecycle` with `Transition → ARCHIVE` / `DEEP_ARCHIVE` (or `Expiration`) | rule 4: show BEFORE/AFTER rule diff (compare `GetBucketLifecycle` pre-call to response post-call); require re-confirmation when prefix is broad AND target is `ARCHIVE` / `DEEP_ARCHIVE`; for `Expiration`, require non-zero `Days` |
| `coscmd delete -r` / `coscmd delete -f prefix/` / multi-object API with count > 1000 | rule 5: `coscmd delete --dry-run` first; surface count + sample keys; require literal "yes, delete <count> objects" recurse-confirm; block if count > 10000 unless explicit `--force-bulk` rationale in trace |

The Critic's rule-violation check is symmetric — it consults the same five rules
independently of which operation was actually run.

### FinOpsAnalysis variant (optional, max_iter=5, read-only)

The `FinOpsAnalysis` operation is read-only (5 phases: collect COS metadata → verify
CLS → execute CLS cost queries → idle detection → generate report). It is **not
scored by the hard rubric**; the Orchestrator may run it through a lighter G/C loop
(max_iter=5, no ABORT, suggestions only). Concretely, the prompt template's
"Operation" placeholder resolves to "FinOpsAnalysis (read-only)" and the Critic
scores:

- correctness: did all 5 phases complete? Was the report file actually written?
- traceability: are all CLI invocations and CLS queries captured?
- spec_compliance: are the CLS topic ID and region valid?

Safety / idempotency / destructive-rule violations are N/A for this read-only
operation.

---

## 5. Anti-patterns (banned)

Carried over from [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) and re-stated
for the COS skill:

- ❌ **Critic sees the user request** — even paraphrased. The Critic prompt above
  explicitly omits the `{{user.*}}` block.
- ❌ **Shared context G + C** — the G and C prompts above are designed for **isolated
  sessions / sub-agents**. Re-using one conversation for both is "pseudo-GCL" and
  violates AGENTS.md §2.
- ❌ **Critic mutates resources** — the Critic prompt above does not contain any
  `tccli` / `coscmd` / SDK invocation. It only reads `{{output.generator_output}}` and
  `{{output.trace}}`.
- ❌ **Silently downgrading on Safety fail** — the Orchestrator's rule #1 emits
  `ABORT` immediately; it cannot be overridden by a "best effort" suggestion.
- ❌ **Trace not persisted** — the Orchestrator's step `Trace persistence` is
  non-negotiable; even on ABORT, a trace entry must be written.
- ❌ **Logging secret content** — extending the AGENTS.md list with the COS-specific
  ban on letting `{{user.local_secret_content}}` / `TENCENTCLOUD_SECRET_KEY` appear
  unmasked anywhere in command, response, or trace.
- ❌ **Silent `public-read` / `public-read-write` ACL** — COS-specific: applying
  `public-read` or `public-read-write` without object enumeration is the same family
  of bug as a credential leak; the Generator must surface the default and the Critic
  must catch it.
- ❌ **Treating `DeleteObject` on a versioning-enabled bucket as a hard delete** —
  COS-specific: the most common misunderstanding. `DeleteObject` without `VersionId`
  on a versioning-enabled bucket creates a `DeleteMarker`, not a hard delete.
- ❌ **`coscmd delete -r` without `--dry-run` first** — COS-specific: a single typo on
  a prefix can wipe a million objects. The 30-second `--dry-run` is non-negotiable.
- ❌ **`PutBucketLifecycle` with broad prefix and cold transition in one shot** —
  COS-specific: cold storage transitions are nearly free to apply, costly to recover.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 COS rollout: Generator + Critic + Orchestrator templates for COS (5 rules, isolated-context enforcement, versioning + public-ACL + batch-delete hygiene, FinOpsAnalysis read-only variant) |

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [rubric.md](rubric.md) — the rubric instance these templates score against
- [SKILL.md](../SKILL.md) — the build-time safety gates and pre-flight tables
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (CVM pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (CDB pilot)
