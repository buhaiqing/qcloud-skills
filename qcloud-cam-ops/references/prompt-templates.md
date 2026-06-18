# CAM GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-cam-ops` |
| CLI | `tccli cam help` |
| max_iterations | 2 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (CAM).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **2**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (CAM — 5 rules). Do not duplicate gate text here.

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


- ❌ **CreateApiKey without flagging `SecretKey` as one-time display** — CAM-specific:
  the surfaced `SecretKey` is the ONLY time the user will ever see this credential.
  Re-using it, echoing it in a subsequent command, or omitting the `ONE_TIME_DISPLAY_ONLY`
  marker is the same family of bug as a credential leak.
- ❌ **`DeleteUser` without `ListApiKey` pre-flight** — CAM-specific: the user object
  is the only handle through which the API keys can be revoked. Delete the user first
  and the orphaned keys can only be invalidated at the account level (CAM API has no
  `RotateApiKey` by `SecretId` for orphaned keys). This is the most common CAM
  incident pattern.
- ❌ **`RotateAccessKey` blind execution** — CAM-specific: the per-user 2-key limit
  means a blind `CreateApiKey` against a user with 2 keys will hit
  `LimitExceeded.ApiKeyCountLimit`. The Pre-flight `ListApiKey` + `DeleteApiKey` (older
  first) + `CreateApiKey` cycle is non-negotiable.
- ❌ **`DeletePolicy` without `ListEntitiesForPolicy` pre-flight** — CAM-specific: a
  policy referenced by N attached principals will silently break those principals'
  permissions. CAM has no AWS-style "default deny" grace period.
- ❌ **`UpdateAssumeRolePolicy` with `Principal=*`** — CAM-specific: trust policy
  amplification is the #1 CAM security risk. A single `Principal=*` allows ANY
  Tencent Cloud account's users to assume the role.
- ❌ **Over-permissive policy grant** (`Action=*` + `Resource=*`, `QcloudCamFullAccess`,
  `AdministratorAccess`, `cam:*` self-escalation) — CAM-specific: privilege-escalation
  root cause. A user with `QcloudCamFullAccess` can create new users, attach policies,
  and elevate themselves.
- ❌ **Policy `*:*` over-permissive (any cross-product wildcard)** — CAM-specific
  superset of the previous: a single statement with both wildcards grants effective
  admin across the account; this is the most-overlooked incident class because the
  policy NAME looks innocuous (e.g. `QcloudDevOpsAccess`).
- ❌ **Orphan access keys (keys with no user)** — CAM-specific: when a user is deleted
  with keys still active, the keys become orphans. They are NOT auto-revoked by CAM;
  they remain valid until their 5-year hard limit OR until manually invalidated at
  the account level. The Generator's Pre-flight rule 1 is the canonical prevention.
- ❌ **Trust policy and permission policy confused** — CAM-specific: when calling
  `CreateRole`, the `PolicyDocument` parameter is the **trust policy** (who can
  assume), not the permission policy (what they can do). Using permission-policy
  syntax in `CreateRole.PolicyDocument` either breaks the role entirely or grants
  the wrong identity access.
- ❌ **Policy document byte-level drift** — CAM-specific: a `CreatePolicy` /
  `CreatePolicyVersion` call whose submitted `PolicyDocument` differs from the user's
  specification (e.g. silently defaulted to a wildcard policy) is a privilege-drift
  incident. The Critic's byte-level diff is the canonical catch.
- ❌ **UserType confusion** — CAM-specific: choosing `SubUser` for what should be a
  SAML-federated user (which requires `CreateSAMLProvider` + role assumption) breaks
  the user's authentication path silently. The Critic verifies the `UserType`
  rationale is in the trace.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CAM rollout: Generator + Critic + Orchestrator templates for CAM (5 rules, isolated-context enforcement, user-delete key audit, policy-delete principal check, trust policy amplification, over-permissive policy guard) |
| 1.1.0 | 2026-06-19 | Tier A conformance: flesh out to 7 sections (Generator / Critic / Orchestrator / Per-operation / Anti-patterns / Changelog / See also). Generator Pre-flight now mandates `ListAttached*` / `ListApiKey` / `ListEntitiesForPolicy` / `ListGroupsForUser` BEFORE every destructive op with explicit warning templates. Critic §2 adds policy-document **byte-for-byte** diff audit AND `SecretKey` `ONE_TIME_DISPLAY_ONLY` marker audit (CAM-specific additions beyond the generic Tier A backbone). Orchestrator §3 elevates ABORT triggers for `SecretKey` re-use, policy drift, and rule 1 / 2 / 3 / 4 / 5 violations. Anti-patterns §5 adds 9 CAM-specific entries: `SecretKey` re-emission, `DeleteUser` without `ListApiKey`, `RotateAccessKey` blind execution, `DeletePolicy` without `ListEntitiesForPolicy`, `Principal=*` amplification, over-permissive policy grant, `*:*` wildcard, orphan access keys, trust-vs-permission policy confusion, byte-level drift, UserType confusion. Read-Only Assessment variant added to §4 (delegate from `qcloud-well-architected-review`, max_iter=1, no ABORT) |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9](../../AGENTS.md#9-anti-patterns-banned) — banned anti-patterns (re-stated in §5 above)
- [rubric.md](rubric.md) — the rubric instance these templates score against (8 sections, Tier A, 5 CAM-specific safety rules)
- [SKILL.md](../SKILL.md) — the build-time safety gates, Execution Flows, and `## Quality Gate (GCL)` chapter
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time destructive-op confirmation list
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute pilot)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (database pilot)
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage pilot, FinOpsAnalysis read-only variant reference)
- [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) — sibling templates (load balancer pilot)
