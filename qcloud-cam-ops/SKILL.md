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

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Tencent Cloud Secret ID | `AKID...` |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Tencent Cloud Secret Key | `***` (masked) |
| `{{user.policy_name}}` | User | Policy name | `QcloudCVMReadOnlyAccess` |
| `{{user.user_name}}` | User | CAM user name | `dev-user` |
| `{{user.role_name}}` | User | Role name | `TkeAdminRole` |
| `{{user.policy_document}}` | User | Policy document (JSON) | JSON string |

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

This skill participates in the **Generator-Critic-Loop (GCL)** pilot.

| Property | Value | Source |
|---|---|---|
| GCL applicability | **required** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **2** | per-skill override |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 CAM-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### CAM-specific safety rules (rubric §4)

1. `DeleteUser` — list attached policies + groups + API keys; warn active key breakage; confirm
2. `DeletePolicy` — list attached principals; warn permission-breaking; confirm
3. `DeleteApiKey` — check last-used status; warn pipeline breakage; confirm
4. `UpdateAssumeRolePolicy` — BEFORE/AFTER diff; warn `Principal=*` amplification; confirm
5. `AttachUserPolicy` / `AttachRolePolicy` / `CreatePolicy` — warn `Action=*`+`Resource=*` AdminAccess; warn `cam:*` privilege escalation; confirm

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

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
