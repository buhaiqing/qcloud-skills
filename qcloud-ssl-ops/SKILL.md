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

## Five Core Standards

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#five-core-standards).

> Well-Architected pillars (Reliability, Security, Cost, Efficiency): see `references/well-architected-assessment.md`.

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

| Operation | Key Field | Description |
|-----------|-----------|-------------|
| Upload | `$.Response.CertificateId` | New certificate ID |
| Describe/List | `$.Response.Certificates[].CertificateId` | Certificate list |
| Delete/Deploy | `$.Response.RequestId` | Tracking ID |

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

| Operation | Risk Level | Notes |
|-----------|------------|-------|
| Upload Certificate | Medium | Upload existing PEM cert |
| Apply Certificate | Low | DV/OV/EV via CA |
| Describe/List Certificate | None | Read-only |
| Delete Certificate | **High** | Irreversible |
| Deploy Certificate | Medium | To CDN/CLB/WAF/etc |
| Download Certificate | **High** | Exposes private key |
| Complete Domain Verify | Low | DNS or HTTP |
| Modify Certificate | Low | Name/project only |
| Check Certificate Expiry | None | Monitoring |
| Certificate Renewal | Medium | Before expiry |

## Execution Flows

Every operation: **Pre-flight → Execute (CLI primary, SDK fallback) → Validate → Recover**. Do not skip phases.

> **SDK Templates:** Init/poll/error boilerplate → [references/sdk-templates.md](references/sdk-templates.md); Code examples → [references/sdk-code-examples.md](references/sdk-code-examples.md)

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

> See `references/troubleshooting.md` for full list. Key codes:

| Code | Recovery |
|------|----------|
| `CertificateNotFound` | Verify certificate ID |
| `CertificateNotMatch` | Ensure public/private key pair matches |
| `DomainVerificationFailed` | Check DNS record or verification file |
| `RequestLimitExceeded` | Retry with backoff |
| `CertificateExpired` | Renew or upload new certificate |

## Quality Gate (GCL)

> Boilerplate: see [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#quality-gate-gcl).

### When the SSL loop runs

| Op class | Loop? | Why |
|---|---|---|
| Destructive: `DeleteCertificate` (deployed cert) | **yes** | Immediate TLS handshake failure on bound resources |
| Sensitive mutating: `DeployCertificateInstance`, `ReplaceCertificate`, `UploadCertificate` | **yes** | Live traffic impact; chain completeness |
| Mutating: `ApplyCertificate`, `DownloadCertificate`, `ModifyCertificateAlias` | **yes** | Validation timing / DNS access risk |
| Read-only: `DescribeCertificates`, `DescribeCertificateDetail`, `DescribeDeployCertificateDetail` | optional (max_iter=1) | Pre-flight for deploy/delete |

### SSL-specific safety rules

> Full rules: [`references/rubric.md`](references/rubric.md) §4.

| # | Ops | Gate (summary) |
|---:|---|---|
| 1 | `DeleteCertificate` (especially if deployed) | Certificate ID + name + domain + deploy status echo; check deployed resources via `DescribeDeployCertificateDetail` |
| 2 | `DeployCertificateInstance` | Show cert domain + resource type + ID + region; warn deploying replaces existing cert |
| 3 | `ReplaceCertificate` / `CertificateRollback` | Show old → new cert domain + expiration; warn replacement is immediate |
| 4 | `ApplyCertificate` | Show domain(s) + validation method (DNS/HTTP) + cert type (DV/OV/EV); warn DNS propagation time |
| 5 | `UploadCertificate` | Show subject + issuer + validity + SAN count; warn if chain incomplete |

Missing any ⇒ **Safety = 0** ⇒ **ABORT**.

### Worked example — DeleteCertificate still deployed on CLB

Safety=0 (rule 1 violated — no deployed resource list). `decision: ABORT`.
Recovery: Re-upload cert or deploy replacement via `DeployCertificateInstance` before users see TLS errors.

See [`references/rubric.md`](references/rubric.md) §6 for full examples (PASS on `DescribeCertificates` + RETRY on `ReplaceCertificate` domain mismatch).

> Decision flow: see [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#decision-flow-first-match-wins).

## Output Schema

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#output-schema-api-response).

## Changelog

> See `metadata.version` and `metadata.last_updated` in the frontmatter YAML.

## Reference Directory

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#reference-directory).

Core: `references/core-concepts.md`, `references/api-sdk-usage.md`, `references/cli-usage.md`, `references/sdk-templates.md`, `references/troubleshooting.md`, `references/well-architected-assessment.md`, `references/rubric.md`, `references/prompt-templates.md`.
Optional: `references/monitoring.md`, `references/aiops-self-healing.md`, `references/finops-cost-optimization.md`.

## Operational Best Practices

> See [shared-boilerplate.md](../qcloud-skill-generator/references/shared-skills-boilerplate.md#operational-best-practices).

SSL-specific: **Expiry monitoring** (alert at 90/30/14/7 days), **auto-renewal** for free certs, **HTTPS test** after deployment, **private key** never shared.

## AIOps Integration (智能运维)

> **AIOps Principle:** Predict expiry before it happens. Verify deployment automatically.

→ Health scoring, deployment verification, chain monitoring, batch expiry detection: see `references/aiops-self-healing.md`.

## FinOps Optimization (财务优化)

> **FinOps Principle:** Every certificate has a cost — direct (paid certs) or indirect (expiry-driven outages).

→ Unused cert detection, free quota monitoring, wildcard vs SAN cost analysis: see `references/finops-cost-optimization.md`.
