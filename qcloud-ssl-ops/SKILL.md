---
name: qcloud-ssl-ops
description: >-
  Use when the user needs to apply, deploy, manage, or troubleshoot Tencent
  Cloud SSL Certificate Service (SSL 证书服务) — certificate lifecycle,
  domain verification, certificate deployment, monitoring, and renewal. User
  mentions SSL, TLS, certificate, 证书, HTTPS, domain verification, or
  describes certificate expiry, deployment failures, certificate order,
  or upload scenarios even without naming the product directly. Not for billing,
  CAM, or related products that have their own ops skills.
license: MIT
compatibility: >-
  Official Tencent Cloud CLI (`tccli`, Python tool, pip installable),
  Python 3.8+ runtime (for SDK fallback with tencentcloud-sdk-python),
  valid API credentials, network access to Tencent Cloud endpoints.
metadata:
  author: qcloud
  version: "1.1.0"
  last_updated: "2026-06-04"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  python_version_minimum: "3.8"
  api_profile: "https://cloud.tencent.com/document/api/400 — 2019-12-05"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    Verified via `tccli ssl help` — actions covering certificate upload,
    describe, delete, deploy, and download operations. Python SDK fallback
    for edge cases.
  environment:
    - TENCENTCLOUD_SECRET_ID
    - TENCENTCLOUD_SECRET_KEY
    - TENCENTCLOUD_REGION
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Tencent Cloud SSL Certificate Service Operations Skill

## Overview

SSL Certificate Service (SSL 证书服务) on Tencent Cloud provides certificate lifecycle management including application, upload, deployment, monitoring, and renewal. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **`tccli` CLI** primary, **Python SDK** fallback), response validation, and failure recovery.

> **UX Compliance:** This skill follows the User Experience Specification. All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI Applicability

- **`cli_applicability: dual-path`:** Official `tccli` supports SSL Certificate Service. CLI is the **primary** execution path. Python SDK is the **fallback** for edge cases.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (SSL Certificate), one primary resource (Certificate); cross-product delegation to other skills |

### Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **可靠性 (Reliability)** | Certificate expiry monitoring, auto-renewal, multi-domain certificate management | `references/well-architected-assessment.md` |
| **安全性 (Security)** | Private key protection, certificate chain validation, domain verification, CRL/OCSP | `references/well-architected-assessment.md` |
| **成本 (Cost)** | Free vs paid certificate comparison, wildcard vs single domain, multi-year pricing | `references/well-architected-assessment.md` |
| **效率 (Efficiency)** | Batch certificate deployment, automated domain validation, renewal automation | `references/well-architected-assessment.md` |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "SSL certificate", "TLS certificate", "HTTPS", "证书", "ssl证书"
- Task involves CRUD or lifecycle operations on **Certificate** (apply, upload, describe, deploy, delete, download)
- Task keywords: ssl, tls, certificate, cert, 证书, https, 域名验证, 部署, 续期
- User asks to apply for, upload, deploy, or manage certificates **via API, SDK, CLI, or automation**
- Certificate expiry monitoring or renewal reminders

### SHOULD NOT Use This Skill When

- Task is purely billing / account management → delegate to: billing skills
- Task is CAM / permission model only → delegate to: `qcloud-cam-ops`
- Task is about SSL/TLS protocol configuration within application code → state limitation
- User asks for generic HTTPS setup (nginx, apache, IIS) without referencing SSL Certificate Service → state limitation
- Task is about VPC / security group design → delegate to: `qcloud-vpc-ops`
- Task is **architecture design review** / four-pillar Well-Architected assessment → delegate to: `qcloud-well-architected-review`

### Delegation Rules

- If deploying certificate to CDN, delegate CDN certificate binding to `qcloud-cdn-ops`
- If deploying certificate to CLB, delegate CLB certificate configuration to `qcloud-clb-ops`
- If configuring CAM policies for certificate management, delegate to `qcloud-cam-ops`
- If setting up certificate expiry monitoring alarms, delegate to `qcloud-monitor-ops`
- Proactive inspection (read-only) → invoked by `qcloud-proactive-inspection`; see `references/proactive-inspection.md`
- Well-Architected assessment (read-only) → invoked by `qcloud-well-architected-review`; see **Read-Only Assessment Mode** below

## Read-Only Assessment Mode (delegate-from: qcloud-well-architected-review)

> **delegate-to marker:** Read-only Well-Architected assessment for **SSL certificates** (expiry, renewal, deployment coverage); return `{{output.product_assessment}}`.

| Input from orchestrator | Value |
|---|---|
| `{{user.mode}}` | `well-architected-readonly` |
| `{{user.pillars}}` | typically `security`, `reliability`; may include `efficiency` |
| `{{user.scope}}` | `account-wide` |

**Allowed:** `Describe*`, `List*` certificate APIs only — **no** DeleteCertificates/Upload/Modify mutations.

**Execute:** [well-architected-assessment.md](references/well-architected-assessment.md) § **Worker Output Contract** → [worker-output-schema.md](../qcloud-well-architected-review/references/worker-output-schema.md) (`product: ssl`).

## Variable Convention

| Placeholder | Source | Meaning | Agent Action |
|-------------|--------|---------|--------------|
| `{{env.TENCENTCLOUD_SECRET_ID}}` | Environment | Secret ID | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_SECRET_KEY}}` | Environment | Secret Key | NEVER ask user; fail if unset |
| `{{env.TENCENTCLOUD_REGION}}` | Environment | Region | Use from env (SSL service is global) |
| `{{user.certificate_id}}` | User | Certificate ID (xxxxxx) | Ask once; reuse |
| `{{user.domain}}` | User | Domain name for certificate | Ask once |
| `{{user.certificate_name}}` | User | Certificate display name | Ask once |
| `{{user.certificate_type}}` | User | Certificate type (CA/Upload/Download) | Ask once |
| `{{user.public_key}}` | User | Certificate public key content | Provide as file path or text |
| `{{user.certificate_chain}}` | User | Certificate chain (optional) | Provide as file path or text |
| `{{user.private_key}}` | User | Private key content | **MASK in logs** |
| `{{output.certificate_id}}` | API Response | New certificate ID | Parse from UploadCertificate response |
| `{{output.deploy_id}}` | API Response | Deployment task ID | Parse from deploy response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose `TENCENTCLOUD_SECRET_KEY`, `SecretKey`, `PrivateKey`, or any credential field value in console output, debug messages, error messages, or logs. Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"` ✅.

## API and Response Conventions

- **API version:** `2019-12-05` (canonical for all operations)
- **API spec:** https://cloud.tencent.com/document/api/400
- **Errors:** SSL uses `Response.Error` pattern with business error codes
- **Region:** SSL Certificate Service is a global service — region parameter may be optional

### Response Fields

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Upload | `$.Response.CertificateId` | string | New certificate ID |
| Describe | `$.Response.Certificates[0].CertificateId` | string | Certificate ID |
| List | `$.Response.Certificates[].CertificateId` | array | Certificate IDs |
| Delete | `$.Response.RequestId` | string | Request tracking ID |
| Deploy | `$.Response.RequestId` | string | Request tracking ID |

### Certificate Status

| Status | Description |
|--------|-------------|
| 0 | Applying for certificate |
| 1 | Issued successfully |
| 2 | Certificate is valid |
| 3 | Certificate expired |
| 4 | Certificate revoked |
| 5 | Certificate application rejected |
| 6 | Certificate upload pending |

## Quick Start

### Prerequisites
- [ ] `tccli` CLI installed (or Python 3.8+ runtime for SDK fallback)
- [ ] Tencent Cloud credentials configured: `TENCENTCLOUD_SECRET_ID`, `TENCENTCLOUD_SECRET_KEY`

### Verify Setup
```bash
tccli ssl DescribeCertificates --Limit 5
```

### Your First Command
```bash
# List all certificates
tccli ssl DescribeCertificates --Limit 20
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Certificate types, statuses
- [Common Operations](#execution-flows) — Upload, deploy, monitor
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Upload Certificate | Upload existing certificate | Low | Medium |
| Apply Certificate | Apply for free/paid certificate | High | Low |
| Describe Certificate | View certificate details | Low | None |
| List Certificates | List all certificates | Low | None |
| Delete Certificate | Delete a certificate | Low | **High** — irreversible |
| Deploy Certificate | Deploy to cloud resources | Medium | Medium |
| Download Certificate | Download certificate files | Low | **High** — exposes private key |
| Complete Domain Verify | Complete domain verification | Medium | Low |
| Modify Certificate | Update certificate name/project | Low | Low |
| Check Certificate Expiry | Monitor expiration dates | Low | None |
| Submit Certificate Info | Submit info for paid cert | Medium | Low |
| Certificate Renewal | Renew expiring certificates | Medium | Medium |

## Execution Flows

Every operation: **Pre-flight → Execute (CLI primary, SDK fallback) → Validate → Recover**. Do not skip phases.

### Operation: Upload Certificate

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI | `tccli version` | Exit code 0 | Install CLI |
| Credentials | Check env vars | Non-empty | HALT; configure env |
| Certificate file | Check file exists | Readable file | Ask user for file path |
| Private key | Check private key provided | Non-empty key | HALT; private key required |

#### Execution — CLI (Primary Path)

```bash
tccli ssl UploadCertificate \
  --CertificatePublicKey "{{user.public_key}}" \
  --CertificatePrivateKey "{{user.private_key}}" \
  --Alias "{{user.certificate_name}}" \
  --CertificateType "CA"
```

Parameters:
- `CertificatePublicKey`: PEM-encoded public certificate content
- `CertificatePrivateKey`: PEM-encoded private key content (**handle securely**)
- `Alias`: Display name for the certificate
- `CertificateType`: `CA` (external upload) or `SVR` (server certificate)
- `CertificateUse`: `SSL` (default)
- `CertificateChain`: Optional intermediate CA chain (PEM)

#### Execution — Python SDK (Fallback)

```python
#!/usr/bin/env python3
import os, json
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ssl.v20191205 import ssl_client, models

def main():
    try:
        cred = credential.Credential(
            os.environ.get("TENCENTCLOUD_SECRET_ID"),
            os.environ.get("TENCENTCLOUD_SECRET_KEY")
        )
        client = ssl_client.SslClient(cred, "")

        req = models.UploadCertificateRequest()
        req.CertificatePublicKey = "-----BEGIN CERTIFICATE-----\n..."
        req.CertificatePrivateKey = "-----BEGIN PRIVATE KEY-----\n..."
        req.Alias = "my-certificate"
        req.CertificateType = "CA"

        resp = client.UploadCertificate(req)
        print(json.dumps(resp.to_json_string(), indent=2))
    except TencentCloudSDKException as err:
        print(f"[ERROR] {err}")

if __name__ == "__main__":
    main()
```

#### Post-execution Validation

1. Parse `{{output.certificate_id}}` from response (`$.Response.CertificateId`)
2. Verify certificate exists:
```bash
tccli ssl DescribeCertificateDetail --CertificateId "{{output.certificate_id}}"
```
3. Report certificate ID, alias, and validity period to user

#### Failure Recovery

| Error Code | Description | Recovery |
|------------|-------------|----------|
| InvalidParameter.CertificateNotMatch | 证书和私钥不匹配 | Verify public/private key pair |
| InvalidParameter.InvalidCertificate | 证书内容无效 | Check PEM format and certificate validity |
| InvalidParameter.InvalidPrivateKey | 私钥内容无效 | Verify private key is valid PEM |
| LimitExceeded | 证书数量超限 | Delete unused certificates first |
| AuthFailure | CAM鉴权错误 | HALT; check credentials |

### Operation: List Certificates

#### Execution

```bash
# List all certificates with search
tccli ssl DescribeCertificates --Limit 20

# Search by domain
tccli ssl DescribeCertificates \
  --SearchKey "example.com" \
  --Limit 20
```

SDK fallback:
```python
req = models.DescribeCertificatesRequest()
req.Limit = 20
resp = client.DescribeCertificates(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

#### Present to User

| Field | JSON Path | Description |
|-------|-----------|-------------|
| CertificateId | `$.Response.Certificates[0].CertificateId` | Certificate ID |
| Alias | `$.Response.Certificates[0].Alias` | Display name |
| Domain | `$.Response.Certificates[0].Domain` | Primary domain |
| Status | `$.Response.Certificates[0].Status` | 1=issued, 2=valid, 3=expired |
| CertBeginTime | `$.Response.Certificates[0].CertBeginTime` | Valid from |
| CertEndTime | `$.Response.Certificates[0].CertEndTime` | Valid until |
| ProductType | `$.Response.Certificates[0].ProductType` | Certificate type |
| Organization | `$.Response.Certificates[0].Organization` | Organization name |

### Operation: Describe Certificate Detail

```bash
tccli ssl DescribeCertificateDetail \
  --CertificateId "{{user.certificate_id}}"
```

SDK fallback:
```python
req = models.DescribeCertificateDetailRequest()
req.CertificateId = "{{user.certificate_id}}"
resp = client.DescribeCertificateDetail(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

### Operation: Delete Certificate (Safety Gate — High Risk)

> **Destructive operation — irreversible.**

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: "Are you sure you want to delete certificate `{{user.certificate_name}}` (`{{user.certificate_id}}`)? This is irreversible."
- **MUST** check if certificate is deployed to any resources first
- **MUST** warn user if certificate is currently in use by CDN/CLB/etc.

#### Execution

```bash
tccli ssl DeleteCertificate \
  --CertificateId "{{user.certificate_id}}"
```

#### Post-execution Validation

1. Verify certificate no longer listed:
```bash
tccli ssl DescribeCertificates --SearchKey "{{user.certificate_name}}"
```
2. Confirm to user: "Certificate `{{user.certificate_name}}` has been deleted."

### Operation: Deploy Certificate

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Certificate exists | DescribeCertificateDetail | Valid certificate | HALT |
| Certificate not expired | Check CertEndTime | Not expired | Suggest renewal first |
| Target resource | Ask user | Resource type + ID | Cannot deploy |

#### Execution

Deploy to CDN:
```bash
tccli ssl DeployCertificateInstance \
  --CertificateId "{{user.certificate_id}}" \
  --InstanceIdList '["cdn-xxxxx"]' \
  --ResourceType "cdn"
```

Resource types: `cdn`, `clb`, `waf`, `live`, `teo`, `tke`, `apigateway`, `vod`, `tcb`.

Deploy to CLB:
```bash
tccli ssl DeployCertificateInstance \
  --CertificateId "{{user.certificate_id}}" \
  --InstanceIdList '["lb-xxxxx"]' \
  --ResourceType "clb"
```

#### Post-execution Validation

1. Check deploy status:
   ```bash
   tccli ssl DescribeCertificateDetail --CertificateId "{{user.certificate_id}}" | jq '.Response.DeployedResources'
   ```
2. Confirm deployment to user
3. Suggest testing HTTPS access to the resource

### Operation: Apply for Free Certificate

#### Pre-flight Checks

- User must have domain ownership verified
- Domain should not already have an active free certificate (limit: 20 free certs/account)

#### Execution

```bash
tccli ssl ApplyCertificate \
  --DvAuthMethod "DNS" \
  --Domain "{{user.domain}}" \
  --ValidityPeriod 12
```

Parameters:
- `DvAuthMethod`: `DNS` (DNS record verification) or `FILE` (HTTP file verification)
- `Domain`: Domain name to secure
- `ValidityPeriod`: 12 months (free certs)
- `PackageType`: Choose free certificate type
- `ContactEmail`: Contact email for verification notifications

#### Post-execution Validation

1. Get certificate status:
   ```bash
   tccli ssl DescribeCertificateDetail --CertificateId "{{output.certificate_id}}"
   ```
2. If DV auth method is DNS, provide DNS record info to user
3. Guide user to complete domain verification

### Operation: Complete Domain Verification

```bash
# Submit DNS verification (after DNS record is added)
tccli ssl CompleteCertificate \
  --CertificateId "{{user.certificate_id}}"
```

Verification methods:
- **DNS**: Add CNAME/TXT record to domain DNS
- **File**: Place verification file on `http://{{domain}}/.well-known/pki-validation/`

### Operation: Download Certificate

> **Security Gate:** Certificate download exposes private key. Warn user.

```bash
# Get download URL
tccli ssl DescribeCertificateDetail \
  --CertificateId "{{user.certificate_id}}" | jq '.Response.CertificateDownloadUrl'

# Download certificate package
tccli ssl DescribeCertificateDetail --CertificateId "{{user.certificate_id}}"
```

Different certificate packages include:
- Nginx: `fullchain.crt` + `private.key`
- Apache: `server.crt` + `server.key` + `chain.crt`
- IIS: `cert.pfx`
- Tomcat: `cert.jks`

### Operation: Check Certificate Expiry

```bash
# List certificates expiring within 30 days
tccli ssl DescribeCertificates --Limit 100 | \
  jq '.Response.Certificates[] | select(.Status == 1) | select(.CertEndTime < now + 2592000) | {CertificateId, Alias, Domain, CertEndTime}'
```

## Error Code Reference

| Code | Meaning | Recovery |
|------|---------|----------|
| InvalidParameter.InvalidCertificate | 证书内容无效 | Verify PEM format; check certificate validity period |
| InvalidParameter.InvalidPrivateKey | 私钥内容无效 | Check private key is valid PEM format |
| InvalidParameter.CertificateNotMatch | 证书和私钥不匹配 | Ensure public/private key pair matches |
| LimitExceeded | 证书数量超限 | Delete unused certificates |
| AuthFailure | CAM鉴权错误 | HALT; check credentials |
| InvalidParameterValue | 参数值错误 | Check parameter values per API spec |
| FailedOperation | 操作失败 | Retry; if persistent contact support |
| FailedOperation.CertificateNotFound | 证书不存在 | Verify certificate ID |
| InvalidParameter.DuplicateCertificate | 证书已存在 | Certificate with same content already uploaded |
| RequestLimitExceeded | 请求频率过高 | Retry with backoff |
| InvalidParameter.CertificateExpired | 证书已过期 | Renew or upload new certificate |
| FailedOperation.DomainVerificationFailed | 域名验证失败 | Check DNS record or verification file |
| InvalidParameter.DvAuthFail | 域名验证不通过 | Try alternative verification method |

## Safety Gates (Destructive Operations)

Every **Delete** or **irreversible** operation MUST have:

1. **Explicit user confirmation** with resource identifier (`{{user.certificate_name}}` / `{{user.certificate_id}}`)
2. **Deployment check** — verify if certificate is in use by other resources
3. **Post-delete verification** — confirm certificate no longer listed

---

## Quality Gate (GCL)

This skill participates in the **Generator-Critic-Loop (GCL)** pilot. The Quality Gate
is a **runtime** scoring layer that audits each SSL execution against an explicit rubric,
in addition to the build-time **Safety Gates** above and the build-time **2-round
self-review** in [AGENTS.md](../../AGENTS.md#mandatory-rule-2-round-self-review-after-every-skill-update).

| Property | Value | Source |
|---|---|---|
| GCL applicability | **recommended** | [AGENTS.md §8](../../AGENTS.md#8-per-skill-defaults-qcloud) |
| `max_iterations` | **3** | per-skill override (AGENTS.md §8 default for `qcloud-ssl-ops`) |
| Rubric instance | [`references/rubric.md`](references/rubric.md) | 5 dimensions, 5 SSL-specific safety rules |
| Prompt templates | [`references/prompt-templates.md`](references/prompt-templates.md) | Generator + Critic + Orchestrator, isolated-context |
| Trace path | `./audit-results/gcl-trace-YYYYMMDD-HHMMSS.json` | [AGENTS.md §6](../../AGENTS.md#6-trace--audit-mandatory) |

### When the loop runs

| Op class | Loop runs? | Why |
|---|---|---|
| Destructive: `DeleteCertificate` (deployed cert) | **yes** | Immediate TLS handshake failure on bound resources |
| Sensitive mutating: `DeployCertificateInstance`, `ReplaceCertificate`, `UploadCertificate` | **yes** | Live traffic impact; chain completeness |
| Mutating: `ApplyCertificate`, `DownloadCertificate`, `ModifyCertificateAlias` | **yes** | Validation timing / DNS access risk |
| Read-only: `DescribeCertificates`, `DescribeCertificateDetail`, `DescribeDeployCertificateDetail` | optional (max_iter=1, no hard abort) | Pre-flight for deploy/delete |

### Decision flow (first match wins)

1. **Safety = 0** OR rule violation in `{1, 2, 3, 4, 5}` ⇒ **ABORT** (no partial result)
2. **`current_iter >= max_iterations`** ⇒ return best-so-far + unresolved rubric items
3. **All thresholds met** ⇒ **PASS**
4. **Otherwise** ⇒ **RETRY** with Critic's suggestions injected into next Generator run

### SSL-specific safety rules (rubric §4)

Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Operation(s) | Gate (summary) |
|---:|---|---|
| 1 | `DeleteCertificate` (any; especially if deployed) | Certificate ID + name + domain + issuer + deploy status echo; check if cert is deployed to any re... |
| 2 | `DeployCertificateInstance` (deploy to specific resource type: CLB, CDN, API GW, TKE, WAF, Live, TEO, VOD, TCB) | Show certificate domain + resource type + resource ID + resource region; warn that deploying repl... |
| 3 | `ReplaceCertificate` / `CertificateRollback` (replace in-place on a resource) | Show old cert domain + expiration → new cert domain + expiration; warn that the replacement is im... |
| 4 | `ApplyCertificate` (apply for a new DV/OV/EV cert; includes `ApplyCertificatePackage`) | Show domain name(s), validation method (DNS / HTTP), and certificate type (DV/OV/EV); warn that D... |
| 5 | `UploadCertificate` (upload PEM / PKCS12 / SSL certificate with private key) | Show certificate subject, issuer, valid-from, valid-to, SAN count; warn if the certificate chain ... |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — `DeleteCertificate` still deployed on CLB

| Dimension | Score |
|---|---|
| Correctness | 0.5 (cert deleted, but deploy status not checked) |
| **Safety** | **0** (rule 1 violated — no deployed resource list) |
| Idempotency | 1 |
| Traceability | 0.5 |
| Spec Compliance | 1 |

`decision: ABORT`. Recovery suggestion: "Re-upload cert or deploy replacement via `DeployCertificateInstance` before users see TLS errors."

See [`references/rubric.md`](references/rubric.md) §6 for two more examples (PASS on `DescribeCertificates` and RETRY on `ReplaceCertificate` domain mismatch).

---

## Output Schema

All responses follow Tencent Cloud API structure:

```json
{
  "Response": {
    "RequestId": "abc123",
    "CertificateId": "xxxxx",
    "Certificates": [
      {
        "CertificateId": "xxxxx",
        "Alias": "my-cert",
        "Domain": "example.com",
        "Status": 1,
        "CertBeginTime": "2026-05-31 00:00:00",
        "CertEndTime": "2027-05-31 23:59:59",
        "ProductType": "Free",
        "Organization": "My Company"
      }
    ]
  }
}
```

Error responses:
```json
{
  "Response": {
    "RequestId": "abc123",
    "Error": {
      "Code": "InvalidParameter.InvalidCertificate",
      "Message": "证书内容无效"
    }
  }
}
```

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-31 | Initial release — SSL certificate upload, describe, delete, deploy, download, apply, domain verification |
| 1.1.0 | 2026-06-04 | Phase 1 GCL rollout: added `## Quality Gate (GCL)` chapter, `references/rubric.md` (5 dimensions + 5 SSL-specific safety rules incl. cert-deletion with deployed resources, wrong-resource deploy, cert-apply DNS readiness, upload chain validation), `references/prompt-templates.md`. `max_iter=3` per AGENTS.md §8 |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Certificate types, statuses, pricing
- [API & SDK Usage](references/api-sdk-usage.md) — Operation map, Python SDK examples
- [CLI Usage](references/cli-usage.md) — tccli ssl command reference
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes + diagnostic workflows
- [Monitoring & Alerts](references/monitoring.md) — Certificate expiry monitoring, alerts
- [Integration](references/integration.md) — SDK setup, env vars, cross-skill delegation
- [Well-Architected Assessment](references/well-architected-assessment.md) — 4-pillar assessment

## Operational Best Practices

- **Expiry monitoring:** Set alerts at 90, 30, 14, and 7 days before expiry
- **Auto-renewal:** Enable auto-renewal for free certificates
- **Private key security:** Never share private keys; restrict download access
- **Certificate deployment:** Use DeployCertificateInstance for consistent deployment
- **Validation:** Always test HTTPS after deployment
- **Record keeping:** Maintain certificate inventory with domains, CAs, and expiry dates

## AIOps Integration (智能运维)

> **AIOps Principle:** Predict expiry before it happens. Verify deployment automatically. Correlate certificate health across all resources.

### Certificate Health Score (证书健康评分)

Evaluate certificate health with a compound score:

| Check | Weight | Criteria | Score |
|-------|--------|----------|-------|
| Days to expiry | 40% | >90 days=10, 30-90=7, 14-30=4, 7-14=2, <7=0 | /40 |
| Chain completeness | 25% | Full chain verified=10, missing intermediate=3, broken=0 | /25 |
| Deployed status | 20% | Fully deployed=10, partial=5, not deployed=0 | /20 |
| Key strength | 15% | ECDSA 256+=10, RSA 4096+=8, RSA 2048=6, <2048=0 | /15 |

```bash
#!/bin/bash
# certificate-health-check.sh — Score each certificate
echo "=== Certificate Health Score Report ==="
tccli ssl DescribeCertificates --Limit 100 \
  | jq -r '.Response.Certificates[] | "\(.CertificateId)|\(.Alias)|\(.Domain)|\(.CertEndTime)|\(.Status)"' \
  | while IFS='|' read -r ID ALIAS DOMAIN ENDTIME STATUS; do
    if [ "$ENDTIME" != "null" ]; then
      DAYS_LEFT=$(( ($(date -d "$ENDTIME" +%s) - $(date +%s)) / 86400 ))
      EXPIRY_SCORE=$(echo "if($DAYS_LEFT > 90) 40 else if($DAYS_LEFT > 30) 28 else if($DAYS_LEFT > 14) 16 else if($DAYS_LEFT > 7) 8 else 0" | bc)
      TOTAL=$EXPIRY_SCORE
      echo "| $ALIAS ($DOMAIN) | expires in ${DAYS_LEFT}d | Score: ${TOTAL}/100 | $(if [ $TOTAL -lt 40 ]; then echo 'CRITICAL'; elif [ $TOTAL -lt 70 ]; then echo 'WARN'; else echo 'OK'; fi) |"
    fi
  done
```

### Automated Deployment Verification (部署自动验证)

After deploying a certificate, **automatically verify** HTTPS works:

```bash
#!/bin/bash
# Verify HTTPS after certificate deployment
DOMAIN="{{user.domain}}"
CERT_ID="{{user.certificate_id}}"

echo "=== HTTPS Deployment Verification ==="

# Step 1: Wait for propagation (DNS + CDN/CLB cache)
echo "[VERIFY] Waiting 30s for propagation..."
sleep 30

# Step 2: TLS handshake check (with timeout guard)
echo "[VERIFY] Checking TLS handshake..."
TLS_RESULT=$(timeout 15 openssl s_client -connect "${DOMAIN}:443" -servername "$DOMAIN" </dev/null 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "[FAIL] TLS handshake timed out or failed after 15s — check network and DNS"
  exit 1
fi
echo "$TLS_RESULT" | openssl x509 -noout -dates -subject -issuer \
  | while read LINE; do echo "[TLS] $LINE"; done

# Step 3: Check certificate serial matches deployed
DEPLOYED_SERIAL=$(echo "$TLS_RESULT" | openssl x509 -noout -serial)
echo "[VERIFY] Deployed certificate serial: $DEPLOYED_SERIAL"

# Step 4: HTTP status check (with timeout)
HTTP_CODE=$(timeout 10 curl -o /dev/null -s -w "%{http_code}" "https://${DOMAIN}/")
echo "[HTTP] HTTPS status code: $HTTP_CODE"
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 301 ] || [ "$HTTP_CODE" -eq 302 ]; then
  echo "[PASS] HTTPS is serving correctly"
else
  echo "[FAIL] HTTPS returned code $HTTP_CODE — investigate deployment"
fi

# Step 5: Check OCSP stapling
OCSP=$(echo "$TLS_RESULT" | grep "OCSP response" | head -1)
echo "[OCSP] $OCSP"

# Safety: clear TLS result from memory
unset TLS_RESULT
```

### Certificate Chain Health Monitoring (证书链健康监控)

```bash
#!/bin/bash
# Check full certificate chain health
DOMAIN="{{user.domain}}"

echo "=== Certificate Chain Analysis ==="
openssl s_client -connect "${DOMAIN}:443" -servername "$DOMAIN" -showcerts </dev/null 2>/dev/null \
  | openssl crl2pkcs7 -nocrl -certfile /dev/stdin 2>/dev/null \
  | openssl pkcs7 -print_certs -text -noout 2>/dev/null \
  | grep -E "(Subject:|Issuer:|Not Before:|Not After )" | head -20

echo ""
echo "[CHAIN] Check intermediate CA expiry:"
echo "| Cert Level | Expires | Status |"
echo "|------------|---------|--------|"
openssl s_client -connect "${DOMAIN}:443" -servername "$DOMAIN" -showcerts </dev/null 2>/dev/null \
  | openssl crl2pkcs7 -nocrl -certfile /dev/stdin 2>/dev/null \
  | openssl pkcs7 -print_certs -text -noout 2>/dev/null \
  | awk '/subject=/,/notAfter=/' | grep -E "(subject=|notAfter=)" \
  | while read LINE; do
    if echo "$LINE" | grep -q "notAfter"; then
      EXPIRY=$(echo "$LINE" | sed 's/.*notAfter=//')
      DAYS_LEFT=$(( ($(date -d "$EXPIRY" +%s) - $(date +%s)) / 86400 ))
      STATUS=$(if [ $DAYS_LEFT -gt 90 ]; then echo "OK"; elif [ $DAYS_LEFT -gt 30 ]; then echo "WARN"; else echo "EXPIRING"; fi)
      echo "| Level-? | $EXPIRY ($DAYS_LEFT days) | $STATUS |"
    fi
  done
```

### Certificate Revocation Monitoring (证书吊销监控)

Detect certificates revoked by the CA — these will cause browser trust errors:

```bash
#!/bin/bash
# Check for revoked certificates
echo "=== Certificate Revocation Check ==="
REVOKED=$(tccli ssl DescribeCertificates --Limit 100 \
  | jq '[.Response.Certificates[] | select(.Status == 4)]')
REVOKED_COUNT=$(echo "$REVOKED" | jq 'length')
if [ "$REVOKED_COUNT" -gt 0 ]; then
  echo "[ALERT] $REVOKED_COUNT certificate(s) revoked!"
  echo "$REVOKED" | jq -r '.[] | "\(.CertificateId) | \(.Alias) | \(.Domain) | Action: Replace immediately"'
  for ID in $(echo "$REVOKED" | jq -r '.[].CertificateId'); do
    echo "  Replace: tccli ssl ApplyCertificate --Domain \"$(tccli ssl DescribeCertificateDetail --CertificateId "$ID" | jq -r '.Domain')\" --DvAuthMethod DNS"
  done
else
  echo "[OK] No revoked certificates found"
fi
```

### Batch Expiry Detection & Renewal Workflow (批量到期检测与续期)

```bash
#!/bin/bash
# Batch detect and notify about expiring certificates
THRESHOLD_DAYS=30

echo "=== Certificates Expiring within ${THRESHOLD_DAYS} days ==="
tccli ssl DescribeCertificates --Limit 100 \
  | jq -r '.Response.Certificates[] | select(.Status == 1) | "\(.CertificateId)|\(.Alias)|\(.Domain)|\(.CertEndTime)"' \
  | while IFS='|' read -r ID ALIAS DOMAIN ENDTIME; do
    if [ "$ENDTIME" != "null" ]; then
      DAYS_LEFT=$(( ($(date -d "$ENDTIME" +%s) - $(date +%s)) / 86400 ))
      if [ $DAYS_LEFT -le $THRESHOLD_DAYS ]; then
        echo "[EXPIRING] $ALIAS ($DOMAIN) — expires in ${DAYS_LEFT} days"
        echo "  Action: tccli ssl ApplyCertificate --Domain \"$DOMAIN\" --DvAuthMethod \"DNS\" --ValidityPeriod 12"
      fi
    fi
  done
```

## FinOps Optimization (财务优化)

> **FinOps Principle:** Every certificate has a cost — whether direct (paid certs) or indirect (expiry-driven outages). Track and optimize.

### Unused Certificate Detection (未使用证书检测)

```bash
#!/bin/bash
# Find certificates that are uploaded but never deployed
echo "=== Unused Certificate Detection ==="
tccli ssl DescribeCertificates --Limit 100 \
  | jq -r '.Response.Certificates[] | select(.Status == 1) | "\(.CertificateId)|\(.Alias)|\(.Domain)|\(.CertEndTime)"' \
  | while IFS='|' read -r ID ALIAS DOMAIN ENDTIME; do
    DEPLOY_COUNT=$(tccli ssl DescribeCertificateDetail --CertificateId "$ID" \
      | jq '.Response.DeployedResources | length')
    if [ "$DEPLOY_COUNT" -eq 0 ]; then
      DAYS_LEFT=$(( ($(date -d "$ENDTIME" +%s) - $(date +%s)) / 86400 ))
      echo "[UNUSED] $ALIAS ($DOMAIN) — expires in ${DAYS_LEFT}d, not deployed anywhere"
      echo "  Action: Delete if no deployment planned: tccli ssl DeleteCertificate --CertificateId \"$ID\""
    fi
  done
```

### Multi-Domain vs Wildcard Cost Analysis (多域名 vs 泛域名成本对比)

When user needs to secure multiple subdomains:

| Scenario | Option A: Multiple single-domain | Option B: Wildcard (*.domain) | Option C: Multi-domain (SAN) |
|----------|--------------------------------|------------------------------|------------------------------|
| example.com + api.example.com + admin.example.com | 3 × free DV = ¥0 | 1 × wildcard = ¥2000-5000/yr | 1 × SAN certificate = ¥1500-3000/yr |
| 10 subdomains | 10 × free DV = ¥0 (limited) | 1 × wildcard = ¥2000-5000/yr | 1 × SAN (10 domains) = ¥3000-6000/yr |
| 100 subdomains | Not feasible | 1 × wildcard = ¥2000-5000/yr | 1 × SAN (100 domains) = ¥8000-15000/yr |

**Recommendation:**
- ≤ 3 subdomains + free DV available → Use multiple free DV certs (¥0)
- 4-20 subdomains + exists in one account → Wildcard (most cost-effective at scale)
- Mixed domains (example.com + otherdomain.com) → Multi-domain SAN
- Production/customer-facing → Use paid cert with warranty regardless of count

### Free Certificate Quota Monitoring (免费证书额度监控)

```bash
#!/bin/bash
# Monitor free certificate quota
echo "=== Free Certificate Quota ==="

# Count free certificates used this year
FREE_COUNT=$(tccli ssl DescribeCertificates --Limit 100 \
  | jq '[.Response.Certificates[] | select(.ProductType == "Free" or .ProductType == "DV")] | length')

echo "| Resource | Used | Limit | Remaining |"
echo "|----------|------|-------|-----------|"
echo "| Free certificates | $FREE_COUNT | 20 | $((20 - FREE_COUNT)) |"

if [ "$((20 - FREE_COUNT))" -le 3 ]; then
  echo "[ALERT] Free certificate quota nearly exhausted ($((20 - FREE_COUNT)) remaining). Plan to purchase paid certificates."
fi
```

### Cost Optimization Decision Tree

```
Need to secure a domain?
├─ 1-3 domains + dev/test → Free DV certs (¥0)
├─ Production domain → Paid OV/EV (¥2000-15000/yr, includes warranty)
├─ Need to cover subdomains?
│  ├─ 4-20 subdomains → Wildcard (best price-per-domain)
│  ├─ 20-100 subdomains → Wildcard OR SAN (compare pricing)
│  └─ Mixed top-level domains → Multi-domain SAN cert
└─ Existing certs expiring → Renew before expiry (cheaper than re-issue)
```

### Budget Alert Integration (预算告警集成)

Link certificate expiry to billing budget planning:

```bash
#!/bin/bash
# Calculate future certificate costs for budget planning
echo "=== Certificate Budget Forecast ==="

FREE_EXPIRING=$(tccli ssl DescribeCertificates --Limit 100 \
  | jq '[.Response.Certificates[] | select(.Status == 1) | select(.CertEndTime | strptime("%Y-%m-%d %H:%M:%S") | mktime < now + 7776000)] | length')
FREE_LEFT=$((20 - $(tccli ssl DescribeCertificates --Limit 100 \
  | jq '[.Response.Certificates[] | select(.ProductType == "Free")] | length')))

echo "| Metric | Value | Budget Impact |"
echo "|--------|-------|---------------|"
echo "| Free certs expiring in 90d | $FREE_EXPIRING | May need replacement certs |"
echo "| Free quota remaining | $FREE_LEFT of 20 | $(( FREE_EXPIRING > FREE_LEFT ? (FREE_EXPIRING - FREE_LEFT) : 0 )) certs may need paid purchase (~¥$(( (FREE_EXPIRING > FREE_LEFT ? FREE_EXPIRING - FREE_LEFT : 0) * 2000 )) ) |"

if [ "$FREE_EXPIRING" -gt "$FREE_LEFT" ]; then
  NEED_PAID=$((FREE_EXPIRING - FREE_LEFT))
  echo "[BUDGET-ALERT] ~¥$((NEED_PAID * 2000)) needed for $NEED_PAID paid certificate(s) — factor into next quarter budget"
fi
```
