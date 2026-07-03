---
name: qcloud-cam-ops
description: >-
  Use when the user needs to manage Tencent Cloud CAM (Cloud Access Management) —
  policy CRUD, user/group/role management, permission audit, API key rotation,
  SAML/OIDC configuration, access review, or least-privilege enforcement. User
  mentions CAM, 访问管理, 权限策略, IAM, policy, role, SSO, or describes access
  control scenarios even without naming the product directly. Not for billing,
  VPC/CLB/CVM resource operations, or application-level authentication that has
  its own ops skill.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`), Python 3.8+ runtime for SDK fallback
  with tencentcloud-sdk-python-cam, valid API credentials, network access to
  Tencent Cloud CAM endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/598"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli cam help` - CLI exposes CreatePolicy, GetPolicy,
    ListPolicies, UpdatePolicy, DeletePolicy, AddUser, DeleteUser, GetUser,
    ListUsers, CreateGroup, DeleteGroup, ListGroup, AddUserToGroup,
    CreateRole, DeleteRole, GetRole, ListRole, CreateApiKey, DeleteApiKey,
    ListApiKey, CreateSAMLProvider, CreateOIDCProvider, and 40+ more operations.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

# Tencent Cloud CAM Operations Skill

## Overview

CAM (Cloud Access Management) is Tencent Cloud's identity and access management service. This skill is an **operational runbook** for agents managing policies, users, groups, roles, API keys, and SSO configurations. It uses **dual-path execution** — official `tccli` CLI as primary, Python SDK fallback for complex operations.

### Core Operations

| Operation Category | Primary APIs |
|---|---|
| Policy management | CreatePolicy, GetPolicy, ListPolicies, UpdatePolicy, DeletePolicy, CreatePolicyVersion |
| User management | AddUser, DeleteUser, GetUser, ListUsers |
| Group management | CreateGroup, DeleteGroup, GetGroup, ListGroup, AddUserToGroup, DetachUserFromGroup |
| Role management | CreateRole, DeleteRole, GetRole, ListRole, AttachRolePolicy, AssumeRole |
| API key management | CreateApiKey, DeleteApiKey, ListApiKey |
| SAML/OIDC | CreateSAMLProvider, GetSAMLProvider, CreateOIDCProvider, GetOIDCProvider |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When
- Policy CRUD: "创建策略", "修改权限", "删除policy"
- User/group/role management: "添加用户", "创建角色", "分配权限"
- Permission audit: "检查权限配置", "audit permissions"
- API key rotation: "轮换API密钥"
- SSO setup: "配置SAML", "设置OIDC"
- Least-privilege review: "最小权限检查"

### SHOULD NOT Use This Skill When
- Resource CRUD (CVM, Redis, etc.) → delegate to product-specific ops skill
- Billing/account management → use dedicated billing tools
- Application-level auth (JWT, OAuth in apps) → use app-specific debugging
- Task is **full architecture review** (four pillars / multi-product) → delegate to: `qcloud-well-architected-review`
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected security audit (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Account-wide **CAM/IAM security** pillar assessment; return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | typically `security` |
| `{{user.scope}}` | `account-wide` |

**Allowed:** List/Get/Describe CAM APIs only — **no** Create/Delete/Update policy, user, role, or API key mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: cam`).

## Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | `***` (masked) |
| `{{user.policy_name}}` | User | `QcloudCVMReadOnlyAccess` |
| `{{user.user_name}}` | User | `dev-user` |
| `{{user.role_name}}` | User | `TkeAdminRole` |
| `{{user.policy_document}}` | User | JSON string |

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | CAM-only scope; delegates resource ops to product skills |
| 2 | **Structured I/O** | Policy/user/role I/O with JSON paths from API responses |
| 3 | **Explicit Actionable Steps** | Each operation: Pre-flight → Execute → Validate → Recover |
| 4 | **Complete Failure Strategies** | AuthFailure handling, rate limits, policy version conflicts |
| 5 | **Absolute Single Responsibility** | One product (CAM), primary resource = Policy/User/Role |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-21 | Initial release — policy/user/group/role/API key/SSO operations |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 CAM-specific safety rules incl. user-delete key audit, policy-delete principal check, trust policy amplification, over-permissive policy guard), `references/prompt-templates.md`. `max_iter=2` per AGENTS.md §8 |

## Safety Gates

**DESTRUCTIVE CONFIRMATION REQUIRED before:**
- `DeletePolicy` — Confirm policy name, list attached users first
- `DeleteUser` — Confirm user name, check active API keys, list group memberships
- `DeleteRole` — Confirm role name, list attached policies, check trust relationships
- `DeleteGroup` — Confirm group name, list members first
- `DeleteApiKey` — Confirm key ID, verify no active usage

**Policy version safety:**
- Always use CreatePolicyVersion → SetDefaultPolicyVersion (not direct UpdatePolicy)
- Document rollback: revert to previous version via SetDefaultPolicyVersion

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each CAM execution against an explicit
rubric, in addition to the build-time **Safety Gates** above and the build-time
**2-round self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

> **CAM security posture is the most sensitive in the catalog.** Every destructive CAM op
> (policy / user / group / role / API key / trust policy) is **immediately effective** and
> has **no soft-delete / recycle-bin / rollback window** — Tencent Cloud CAM has no
> AWS-style "default deny" grace period. For this reason, the **Correctness threshold is
> elevated to 1.0 for ALL destructive CAM ops**, not just the handful of high-blast-radius
> ones other skills target. See [`references/rubric.md`](references/rubric.md) §2 for the
> per-dimension threshold table.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override (matches AGENTS.md §8 default for `qcloud-cam-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CAM-specific safety rules, Correctness=1.0 for destructive ops |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteUser`, `DeletePolicy`, `DeleteGroup`, `DeleteRole`, `DeleteApiKey`, `DetachUserPolicy` / `DetachRolePolicy` / `DetachGroupPolicy` (when narrowing permission for active principal) | **yes** | Irreversible; permission-breaking; needs scoring |
| Trust-policy amplifying: `UpdateAssumeRolePolicy`, `CreateRole` with `Principal=*` or cross-account `Principal` | **yes** | Trust widening is the #1 CAM security risk; needs scoring |
| Sensitive mutating: `CreatePolicy` / `AttachUserPolicy` / `AttachRolePolicy` / `AttachGroupPolicy` granting `QcloudCamFullAccess` / `AdministratorAccess` / `Action=*`+`Resource=*` / `cam:*` | **yes** | Privilege escalation surface; needs scoring |
| Mutating: `AddUser`, `CreateGroup`, `CreateRole`, `CreatePolicyVersion`, `SetDefaultPolicyVersion`, `AttachUserPolicy` / `AttachRolePolicy` / `AttachGroupPolicy` (least-privilege grants) | **yes** | State-change risk; needs scoring |
| SSO mutating: `CreateSAMLProvider`, `CreateOIDCProvider`, `DeleteSAMLProvider`, `DeleteOIDCProvider` | **yes** | Federation mutation breaks IdP trust |
| Read-only: `GetPolicy`, `ListPolicies`, `GetUser`, `ListUsers`, `GetRole`, `ListRole`, `GetGroup`, `ListGroup`, `ListAttachedUserPolicies`, `ListEntitiesForPolicy`, `ListApiKey` | optional (max_iter=1, no hard abort) | Polling tails are part of the parent op's trace |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result). Secret-key leak in trace (other than the one-time `CreateApiKey` surface with `ONE_TIME_DISPLAY_ONLY` marker) is also an unconditional ABORT.
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** (Correctness ≥ 1.0 for destructive CAM ops, Safety = 1, Idempotency ≥ 0.5, Traceability ≥ 0.5, Spec Compliance ≥ 0.5) ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### CAM-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteUser` (any with attached policies) | User name + UIN echo; enumerate attached policies via `ListAttachedUserPolicies` and group member... |
| 2 | `DeletePolicy` (referenced by any principal) | Policy name + ID + `Scope` (User/Role/Group) echoed; list all attached principals via `ListEntiti... |
| 3 | `DeleteApiKey` (any, especially in-use) | Key ID + associated user echo; check if the key has been used in the last 30 days (via `GetApiKey... |
| 4 | `UpdateAssumeRolePolicy` / `ModifyRolePolicy` (trust policy modification, especially `Principal=*`) | Show BEFORE/AFTER trust policy diff; warn if the new trust policy contains `Principal=*` or `Prin... |
| 5 | `AttachUserPolicy` / `AttachRolePolicy` / `CreatePolicy` (granting over-permissive policies like `QcloudCamFullAccess`) | Surface the policy document (for CreatePolicy) or policy name (for Attach); warn if the policy gr... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteUser` with orphan access keys

A user requests "remove the legacy `ci-cd-runner` CAM user". The agent runs `DeleteUser --Name ci-cd-runner` without first enumerating the user's API keys. The user had 2 active keys — one last used 12 hours before the delete (Jenkins), the other last used 90 days ago (nightly data-sync). After the delete, **both keys are orphaned**: there is no way to revoke them through the API because the user object is gone; they will only become invalid when their 5-year CAM hard limit hits. Jenkins and the nightly data-sync silently start failing with `AuthFailure.SecretIdNotFound`.

| Dimension | Score |
|---|---|
| Correctness | 1 (user is gone — `GetUser` confirms `ResourceNotFound.UserNotExist`) |
| **Safety** | **0** (rule 1 violated — `ListApiKey` was not run before the delete; no warning was issued) |
| Idempotency | 1 |
| Traceability | 1 (ironically, full trace makes the post-mortem clean, which is what made the SAFETY_FAIL detectable) |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion emitted: rotate the orphaned keys at the account level via `cam:RotateApiKey` against `SecretId` directly (not `UserName`, since the user object is gone); create a new CI/CD user and re-issue keys into Vault; add a "ListApiKey + last-used check" pre-flight to the skill before any future `DeleteUser`. Note: this is **immediately effective** — there is no recycle-bin window to undo the `DeleteUser`; the user is gone and only the API key rotation can limit the blast radius.

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `AddUser` least-privilege starting point and RETRY on `RotateAccessKey` pivot around the 2-key limit).

---

## Execution Flows

### Create Policy

**Pre-flight:**
1. Check if policy name already exists: `tccli cam GetPolicy --PolicyName {{user.policy_name}}`
2. Validate policy document JSON syntax

**Execute (tccli):**
```bash
tccli cam CreatePolicy \
  --PolicyName {{user.policy_name}} \
  --PolicyDocument '{{user.policy_document}}' \
  --Description "Created via CAM ops"
```

**Validate:**
1. Verify policy created: `tccli cam GetPolicy --PolicyName {{user.policy_name}}`
2. Verify policy version = 1

**Recover:**
- If `PolicyNameAlreadyExists`: Use CreatePolicyVersion instead
- If `InvalidParameter.PolicyDocument`: Validate JSON, fix syntax

### Attach Policy to User

**Pre-flight:**
1. Verify user exists: `tccli cam GetUser --Name {{user.user_name}}`
2. Verify policy exists: `tccli cam GetPolicy --PolicyName {{user.policy_name}}`

**Execute (tccli):**
```bash
tccli cam AttachUserPolicy \
  --AttachUserName {{user.user_name}} \
  --DetachPolicyName {{user.policy_name}}
```

**Validate:**
1. List attached policies: `tccli cam ListAttachedUserPolicies --TargetUin {{user.user_uin}}`

### Create Role with Assume Role

**Pre-flight:**
1. Check if role exists: `tccli cam GetRole --RoleName {{user.role_name}}`

**Execute (tccli):**
```bash
tccli cam CreateRole \
  --RoleName {{user.role_name}} \
  --PrincipalService "tke.tencentcloudapi.com" \
  --Description "Role for TKE admin access"
```

**Execute (attach policy):**
```bash
tccli cam AttachRolePolicy \
  --RoleName {{user.role_name}} \
  --PolicyName QcloudTKEFullAccess
```

**Validate:**
1. Verify role created: `tccli cam GetRole --RoleName {{user.role_name}}`
2. Verify policy attached: `tccli cam ListAttachedRolePolicies --RoleName {{user.role_name}}`

## Troubleshooting

| Error Code | Meaning | Recovery |
|---|---|---|
| `AuthFailure.Unauthorized` | Caller lacks CAM permissions | Verify caller has QcloudCamFullAccess |
| `FailedOperation.PolicyNameAlreadyExists` | Policy name taken | Use CreatePolicyVersion instead |
| `InvalidParameter.PolicyDocument` | Invalid policy JSON | Validate JSON syntax, check required fields |
| `LimitExceeded.PolicyVersionLimit` | Max policy versions reached | Delete old versions first |
| `AuthFailure.InvalidSecretId` | Invalid credentials | Verify TENCENTCLOUD_SECRET_ID |
| `ResourceNotFound.User` | User not found | Verify user name exists |
| `ResourceNotFound.Role` | Role not found | Verify role name exists |
| `FailedOperation.UserAlreadyInGroup` | User already in group | Skip or use different group |
| `AuthFailure.MFAFailure` | MFA required | User must complete MFA verification |
| `LimitExceeded.PolicyNumberExceed` | Too many policies | Delete unused policies first |

---

For detailed content, see:
- [Core Concepts](references/core-concepts.md) — CAM architecture, policy syntax
- [API & SDK Usage](references/api-sdk-usage.md) — Operation mapping, SDK examples
- [CLI Usage](references/cli-usage.md) — tccli cam command reference
- [Troubleshooting](references/troubleshooting.md) — Error code diagnostics
- [Well-Architected Assessment](references/well-architected-assessment.md) — Security best practices
