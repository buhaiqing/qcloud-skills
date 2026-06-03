# SSL GCL Prompt Templates

> Prompt skeletons for G/C/O of `qcloud-ssl-ops`.
> See [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) for the backbone.

---

## 1. Generator — SSL delta

```text
You are the Generator for the qcloud-ssl-ops skill (Tencent Cloud SSL cert management).
- PRIMARY: tccli ssl <subcommand> ...  (verify with `tccli ssl help`)
- FALLBACK: Python SDK tencentcloud-sdk-python-ssl; namespace:
  from tencentcloud.ssl.v20191205 import ssl_client, models
```

---

## 4. Per-operation variants

| Operation | Pre-flight augmentation |
|---|---|
| `DeleteCertificate` | rule 1: Cert ID + domain + deploy status echo; list deployed resources; literal confirm |
| `DeployCertificateInstance` | rule 2: Show cert domain + target resource; warn replace; surface current cert on resource; confirm |
| `ReplaceCertificate` | rule 3: BEFORE/AFTER diff; warn immediate effect; check domain match with resource DNS; confirm |
| `ApplyCertificate` | rule 4: Show domain + validation method; warn DV/OV/EV timing; check DNS write access; confirm |
| `UploadCertificate` | rule 5: Show cert subject, issuer, validity, SAN count; warn incomplete chain; reject < 2048-bit key; confirm |

---

## 5. SSL-specific anti-patterns

- ❌ **DeleteCertificate without deploy check** — HTTPS breakage on all resources
- ❌ **DeployCertificateInstance to wrong resource** — silent cert replacement
- ❌ **ReplaceCertificate with domain mismatch** — hostname errors
- ❌ **ApplyCertificate without DNS write access** — pending validation forever
- ❌ **UploadCertificate incomplete chain** — CLB/CDN rejection

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 SSL rollout: templates (5 rules, cert-deletion deploy check, wrong-resource deploy guard, cert-apply DNS readiness, upload chain validation) |