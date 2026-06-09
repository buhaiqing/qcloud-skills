# Well-Architected Assessment — SSL Certificate Service

> **Mode split:** `[assessment-readonly]` — Describe* / GetMonitorData only (Well-Architected worker).
> `[remediation-only]` — Create/Modify/Delete runbooks; **MUST NOT** execute when `{{user.mode}}=well-architected-readonly`.
> Worker JSON: **Worker Output Contract** at end of this file.

## Pillar 1: Reliability (可靠性)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Certificate Expiry | Expiry dates are absolute | Set alerts at 90/30/14/7 days before expiry |
| Auto-Renewal | Free certs support auto-renewal | Enable auto-renewal for free certificates |
| Multi-Domain | SAN certificates support multiple domains | Bundle related domains into one certificate |
| Failure Mode | Expired certs cause HTTPS errors | Proactive monitoring prevents outage |
| Redundancy | Deploy same cert to multiple resources | Use single cert for all related services |
| HTTPS Verification | Post-deployment TLS handshake check | Automate via openssl s_client; see SKILL.md AIOps section |
| Certificate Chain | Intermediate CA expiry can break trust | Monitor chain health; check CA expiry dates; see SKILL.md AIOps section |
| OCSP Stapling | Improves TLS handshake performance | Verify OCSP status after deployment |

## Pillar 2: Security (安全性)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Private Key | Stored securely by Tencent Cloud | Never expose private keys in logs or outputs |
| Certificate Validation | DV/OV/EV with increasing rigor | Use OV/EV for production, DV for dev |
| Key Strength | RSA 2048+/ECDSA supported | Prefer ECDSA for better performance |
| Chain Completeness | Full chain required for trust | Always include intermediate CA chain |
| Certificate Revocation | CRL and OCSP support | Monitor revocation status |
| Access Control | CAM integration | Use least-privilege CAM policies |

### Minimum CAM Permissions

```json
{
  "Version": "2.0",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssl:DescribeCertificates",
        "ssl:DescribeCertificateDetail",
        "ssl:UploadCertificate",
        "ssl:DeleteCertificate"
      ],
      "Resource": "*"
    }
  ]
}
```

## Pillar 3: Cost (成本)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Free Certificates | 20 free DV certificates per account | Use free certs for personal/dev projects |
| Paid Certificates | OV/EV/wildcard with warranty | Use paid certs for production/customer-facing |
| Renewal Pricing | Renewal may be discounted | Renew before expiry to avoid re-issue cost |
| Volume Discounts | Multi-year purchases available | Consider 2-3 year for stable domains |
| Opportunity Cost | Missing expiry = potential outage | Monitoring costs less than downtime |
| Certificate Health Score | Compound scoring (expiry+chain+deployment+key strength) | Automate health checks weekly; see SKILL.md AIOps section |
| Expiry Batch Detection | Automated detection of certs expiring within N days | Run weekly cron job; see SKILL.md AIOps section |

## Pillar 4: Efficiency (效率)

| Aspect | Assessment | Recommendation |
|--------|-----------|----------------|
| Batch Operations | Single API per operation | Use automation scripts for bulk operations |
| Automation | Full CLI + SDK support | Automate renewal and deployment |
| Deployment | One-click deploy to cloud resources | Use DeployCertificateInstance |
| Validation | DNS auto-validation via DNSPod | Prefer DNS method with auto-validation |
| Monitoring | Cloud Monitor integration | Create expiry dashboard |
| CI/CD Integration | API-based deployment | Integrate certificate management in CI/CD |

---

## Worker Output Contract (Read-Only Assessment Mode)

> Invoked when `qcloud-well-architected-review` sets `{{user.mode}}=well-architected-readonly`.
> Return **`{{output.product_assessment}}`** — field names MUST match the canonical schema.

**Canonical schema:** [worker-output-schema.md](../../qcloud-well-architected-review/references/worker-output-schema.md)

| Constant | Value |
|----------|-------|
| `skill_id` | `qcloud-ssl-ops` |
| `product` | `ssl` |
| Finding `id` pattern | `ssl-{rel|sec|cost|eff}-NNN` (3-digit sequence per pillar) |

### Pillar → checklist map

| `pillars` key | Checklist source in this document |
|---------------|-------------------------------------|
| `reliability` | Reliability / expiry sections |
| `security` | Security / TLS sections |
| `cost` | Cost sections (if assessed) |
| `efficiency` | Automation / renewal sections |

### Populate rules

1. Include only pillar keys requested by orchestrator `{{user.pillars}}` (`all` = four keys).
2. `score = round(passed / applicable × 100)`; use `status=not_assessed` when data missing (omit score or null).
3. Each failed/warn checklist item → one `findings[]` entry with all six finding fields (§2.1 in schema).
4. `recommendations[]`: top 1–5 actions with `priority`, `pillar`, `action`, `effort` (§2.2 in schema).
5. `partial=true` when any pillar is `not_assessed`; top-level `status=PARTIAL`.
6. `trace.commands`: every read API call; mask credentials. `errors[]` on API failure (§3 in schema).
7. Local “Score Calculation” sections are for manual review only — **worker mode must emit this JSON**.

### Example `{{output.product_assessment}}`

```json
{
  "skill_id": "qcloud-ssl-ops",
  "product": "ssl",
  "region": "ap-guangzhou",
  "scope": "account-wide",
  "assessment_date": "2026-06-09T10:00:00+08:00",
  "status": "OK",
  "partial": false,
  "resource_count": 3,
  "pillars": {
    "reliability": {
      "score": 75,
      "status": "assessed",
      "findings": [
        {
          "id": "ssl-rel-001",
          "severity": "High",
          "confidence": "HIGH",
          "title": "Certificate expiring within 30 days",
          "evidence": "Cert end date < 30d from assessment",
          "recommendation": "Renew or enable auto-renewal; update CLB/CDN bindings",
          "effort": "medium"
        }
      ]
    },
    "security": {
      "score": 88,
      "status": "assessed",
      "findings": []
    },
    "cost": {
      "score": 72,
      "status": "assessed",
      "findings": []
    },
    "efficiency": {
      "score": 70,
      "status": "assessed",
      "findings": []
    }
  },
  "recommendations": [
    {
      "priority": "High",
      "pillar": "reliability",
      "action": "Renew or enable auto-renewal; update CLB/CDN bindings",
      "effort": "medium"
    }
  ],
  "trace": {
    "commands": [
      "tccli ssl DescribeCertificates (SecretKey=<masked>)"
    ],
    "request_ids": [
      "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    ]
  },
  "errors": []
}
```
