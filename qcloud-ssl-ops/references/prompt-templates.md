# SSL GCL Prompt Templates

> **TE-6:** G/C/O → [`gcl-prompt-backbone.md`](../../qcloud-skill-generator/references/gcl-prompt-backbone.md); §4 gates → [`rubric.md`](rubric.md) §4; this file: **§5 product anti-patterns** only.

---

## 1. Generator prompt template

> **TE-6 backbone:** [Generator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#1-generator-prompt-template).
> Pre-flight gates: [`references/rubric.md`](rubric.md) §4 (canonical).

| Override | Value |
|---|---|
| skill | `qcloud-ssl-ops` |
| CLI | `tccli ssl help` |
| max_iterations | 3 |


Load rubric §4 before Execute; append gate results to trace `preflight`.

---

## 2. Critic prompt template

> **TE-6 backbone:** [Critic skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#2-critic-prompt-template) — no `{{user.request}}`.
> Score [`references/rubric.md`](rubric.md) §3 + §4 (SSL).

---

## 3. Orchestrator prompt template

> **TE-6 backbone:** [Orchestrator skeleton](../../qcloud-skill-generator/references/gcl-prompt-backbone.md#3-orchestrator-prompt-template).
> `max_iterations`: **3**.

---

## 4. Per-operation variants

> **TE-6:** Pre-flight / Critic rule checks are **canonical** in [`references/rubric.md`](rubric.md) §4 (SSL — 5 rules). Do not duplicate gate text here.

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


- ❌ **Logging PEM bytes / private key** — extending the AGENTS.md list with the
  SSL-specific ban on letting `{{user.public_key}}` / `{{user.private_key}}` /
  `{{user.certificate_chain}}` / `{{user.pkcs12_password}}` /
  `TENCENTCLOUD_SECRET_KEY` appear unmasked anywhere in command, response, or
  trace. The Critic prompt above explicitly audits this and the Orchestrator
  ABORTs on any leak.

SSL-specific anti-patterns (extending the AGENTS.md §9 list):

- ❌ **`DeleteCertificate` / `DeleteCertificates` without binding list** — the
  most common SSL incident is "deleted the old cert but CLB was still using it
  for SNI — HTTPS handshake failed for a week". `DescribeHostsBindList` (or
  `DescribeCertificateDeploy`) MUST be pre-fetched and the deploy list surfaced
  to the user; the literal "CONFIRM DELETE CERT `<alias>`" MUST be captured in
  trace. Safety=0 if either is missing.
- ❌ **`BindCertificate` / `DeployCertificateInstance` without SAN match check** —
  binding a cert whose SAN list does not cover the resource's DNS name silently
  creates a hostname-mismatch condition that surfaces only at the first TLS
  handshake. The Generator MUST read the resource's listener / domain config
  and compare against the new cert's SAN list BEFORE commit.
- ❌ **`UnbindCertificate` without listing affected domains** — an unbind may
  remove HTTPS from one or more domains. If the resource serves multiple
  domains, the user may have intended only one of them. The Generator MUST
  pre-fetch `DescribeHostsBindList`, surface every domain, and require
  explicit confirmation with at least one affected domain.
- ❌ **PEM private key not masked** — even when masked, the user must confirm
  the file landed at a path with restrictive permissions (e.g. `chmod 600`).
  Critic checks the trace for `<PEM bytes redacted, N bytes>` markers AND
  the absence of any base64 / PEM delimiter substring.
- ❌ **`ReplaceCertificate` with hostname mismatch** — the replacement is
  immediate; clients with stale trust-store caches will see the new cert
  instantly. If the new cert's SAN does not cover the resource's DNS name,
  TLS clients see "hostname mismatch" errors. Generator MUST surface the SAN
  list and the resource's DNS name; mismatch ⇒ require explicit acknowledgement.
- ❌ **`ModifyCertificateProject` without RBAC-scope warning** — moving a cert
  between projects silently shifts which user / role can read or delete it.
  The Generator MUST surface the source and target `ProjectId` and warn about
  the RBAC-scope transition; both `ProjectId` values must be echoed in trace.
- ❌ **Treating `DeleteObject`-style no-op as a hard delete** — the AGENTS.md
  anti-pattern for COS extends to SSL: `DeleteCertificate` on an
  already-deleted cert is a no-op (`ResourceNotFound.NoSuchCertificate`),
  not a "real failure" to be retried. Similarly `UploadCertificate` for an
  already-uploaded cert returns `InvalidParameter.DuplicateCertificate` —
  a no-op signal, not a retry trigger.
- ❌ **Batch operations without per-resource deploy check** — extending
  the COS anti-pattern: `len(InstanceIdList) > 1` in
  `DeployCertificateInstance` (or batch `DeleteCertificates`) must enumerate
  every cert / resource in the batch, not just the first. The literal CONFIRM
  must cover every cert in the batch.
- ❌ **Following `CertificateDownloadUrl` in the Generator session** — the
  URL is time-limited and should be returned to the user, not auto-followed.
  Auto-following burns the URL clock, may leak the cert to a shared proxy
  log, and turns the Generator into a private-key exfiltration vector.

---

## 6. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 SSL rollout: Generator + Critic + Orchestrator templates (5 rules, cert-deletion deploy check, wrong-resource deploy guard, cert-apply DNS readiness, upload chain validation, replace-certificate hostname-mismatch guard) |
| 1.1.0 | 2026-06-19 | Tier A flesh-out (Phase 5 batch 2): full 7-section structure with extended Generator pre-flight (free-cert quota math, status code semantics, PKCS12 password handling, `DescribeCertificateDeploy` + `DescribeHostsBindList` for destructive ops, SAN-vs-DNS check for bind, hostname-mismatch guard for replace, RBAC-scope warning for project move, PEM-bytes masking throughout); extended Critic (5-dimension scoring, 5 §4 rule checks, 3 §3.2 SSL-specific extensions for `UnbindCertificate` / `ModifyCertificateProject` / `DownloadCertificate`); extended Orchestrator (max_iter=3 per AGENTS.md §8, ABORT triggers for PEM leaks, missing deploy list, missing SAN check, missing RBAC warning); 14 per-operation variant rows including `UnbindCertificate` / `ModifyCertificateProject` / `DownloadCertificate` / `CompleteCertificate` / `SubmitCertificateInformation` / `ModifyCertificateAlias` / `ModifyCertificateTags` / batch variants; 9 SSL-specific anti-patterns; Well-Architected-Assessment read-only variant. Aligned with the canonical structure of [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) |
| 1.3.0 | 2026-06-19 | TE-6 §4: defer per-op gates to rubric §4 only |
| 1.2.0 | 2026-06-19 | TE-6: G/C/O → gcl-prompt-backbone |

---

## 7. See also

- [AGENTS.md §7](../../AGENTS.md#7-prompt-templates-mandatory-per-skill) — generic template spec
- [AGENTS.md §9 Anti-Patterns](../../AGENTS.md#9-anti-patterns-banned) — base banned-pattern list
- [AGENTS.md §14 Reflexion Integration](../../AGENTS.md#14-reflexion-integration-lightweight-reflexion) — failure pattern memory
- [rubric.md](rubric.md) — the rubric instance these templates score against (5 dimensions, 5 SSL-specific safety rules, 3 §3.2 extensions)
- [SKILL.md](../SKILL.md) — the build-time safety gates, Execution Flows, and `## Quality Gate (GCL)` chapter
- [SKILL.md §Safety Gates](../SKILL.md#safety-gates-destructive-operations) — build-time sibling (DeleteCertificate / DeployCertificateInstance / ReplaceCertificate / ApplyCertificate / UploadCertificate)
- [SKILL.md §Quality Gate (GCL)](../SKILL.md#quality-gate-gcl) — per-skill GCL header table
- [`qcloud-cos-ops/references/prompt-templates.md`](../cos-ops/references/prompt-templates.md) — sibling templates (object storage)
- [`qcloud-cvm-ops/references/prompt-templates.md`](../cvm-ops/references/prompt-templates.md) — sibling templates (compute)
- [`qcloud-cdb-ops/references/prompt-templates.md`](../cdb-ops/references/prompt-templates.md) — sibling templates (SQL database)
- [`qcloud-clb-ops/references/prompt-templates.md`](../clb-ops/references/prompt-templates.md) — sibling templates (load balancer; related for `BindCertificate` resource side)
- [`qcloud-cdn-ops`](../cdn-ops/references/prompt-templates.md), [`qcloud-monitor-ops`](../monitor-ops/references/prompt-templates.md) — for cross-skill delegation on CDN deploy and expiry alarms
