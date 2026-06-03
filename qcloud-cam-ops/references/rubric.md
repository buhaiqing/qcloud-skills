# CAM Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-cam-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. CAM-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteUser` (any with attached policies) | **User name + UIN echo; enumerate attached policies via `ListAttachedUserPolicies` and group memberships via `ListGroupsForUser`; warn that deleting the user with attached policies loses those permission bindings; require confirmation that the user's API keys (via `ListApiKey`) have been rotated/revoked first** | Deleting a CAM user with active API keys is the most common CAM incident: "I deleted the CI/CD user but forgot that Jenkins was still using its API key — all deployments failed" |
| 2 | `DeletePolicy` (referenced by any principal) | **Policy name + ID + `Scope` (User/Role/Group) echoed; list all attached principals via `ListEntitiesForPolicy`; warn that deleting a referenced policy will break permissions for all attached users/roles/groups; require explicit confirmation with policy name** | Deleting a policy that is still attached to principals is a permission-breaking event. Unlike AWS, Tencent Cloud CAM does not have a "default deny" grace period. The most common pattern: "I cleaned up unused policies but deleted the one that the dev team's role depended on" |
| 3 | `DeleteApiKey` (any, especially in-use) | **Key ID + associated user echo; check if the key has been used in the last 30 days (via `GetApiKeyLastUsed` or similar); warn that deleting an in-use key will break the application/CI/CD pipeline using it; require confirmation with key ID** | API key deletion breaks integrations silently: the next API call fails with `AuthFailure.SecretIdNotFound`. The most common incident: "I rotated the API key for security but forgot to update the CI/CD pipeline variables — the build was broken for 2 hours" |
| 4 | `UpdateAssumeRolePolicy` / `ModifyRolePolicy` (trust policy modification, especially `Principal=*`) | **Show BEFORE/AFTER trust policy diff; warn if the new trust policy contains `Principal=*` or `Principal={"Service": "cvm.qcloud.com"}` (opens trust to any CVM instance); for cross-account `Principal`: warn that any user in the specified account can assume this role; require explicit confirmation for trust policy changes that widen access** | Trust policy amplification is the #1 CAM security risk. A single `"Principal": "*"` in a role's trust policy allows ANY Tencent Cloud account's users to assume the role. The most common incident: "I set up cross-account access to allow our billing team to assume an admin role, but I used `Principal=*` instead of the specific account ID" |
| 5 | `AttachUserPolicy` / `AttachRolePolicy` / `CreatePolicy` (granting over-permissive policies like `QcloudCamFullAccess`) | **Surface the policy document (for CreatePolicy) or policy name (for Attach); warn if the policy grants `QcloudCamFullAccess`, `AdministratorAccess`, or any wildcard `"Action": "*"` + `"Resource": "*"` combination; require explicit confirmation for over-permissive grants; for policies containing `"Effect": "Allow"` + `"Action": "cam:*"`, warn that the grant itself can be used to escalate privileges** | Over-permissive policies are the root cause of privilege escalation in CAM. A user with `QcloudCamFullAccess` can create new users, attach policies, and elevate themselves. The most common pattern: "I granted AdminAccess to the new engineer 'temporarily' and forgot to scope it down" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CAM rollout: rubric (5 rules: user-delete with active keys, policy-delete with attached principals, in-use API key deletion, trust policy amplification, over-permissive policy grant) |