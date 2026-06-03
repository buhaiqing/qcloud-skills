# CAM GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-cam-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the full backbone.

---

## 1. Generator — CAM delta

```text
You are the Generator for the qcloud-cam-ops skill (Tencent Cloud CAM — access management).
- PRIMARY: tccli cam <subcommand> ...  (verify with `tccli cam help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-cam; namespace:
  from tencentcloud.cam.v20190116 import cam_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteUser` | rule 1: User name + UIN echo; list attached policies + groups + API keys; warn keys need rotation first; confirm |
| `DeletePolicy` | rule 2: Policy name + ID echo; list attached principals; warn permission-breaking; confirm |
| `DeleteApiKey` | rule 3: Key ID + associated user echo; check last-used status; warn pipeline breakage; confirm |
| `UpdateAssumeRolePolicy` / trust policy | rule 4: BEFORE/AFTER diff; warn `Principal=*` amplification; confirm for widening changes |
| `AttachUserPolicy` / `AttachRolePolicy` / `CreatePolicy` (permissive) | rule 5: Surface policy name/document; warn `Action=*` + `Resource=*` (AdminAccess); warn cam:* privilege escalation; confirm |

---

## 5. CAM-specific anti-patterns

- ❌ **DeleteUser without API key audit** — active keys break pipelines
- ❌ **DeletePolicy without attached-principals check** — permission-breaking
- ❌ **UpdateAssumeRolePolicy with `Principal=*`** — trust amplification
- ❌ **AttachUserPolicy with AdminAccess or `Action=*`** — privilege escalation root cause
- ❌ **CreatePolicy without syntax validation** — JSON syntax errors waste API calls

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 CAM rollout: templates (5 rules, user-delete key audit, policy-delete principal check, trust policy amplification guard, over-permissive policy guard) |