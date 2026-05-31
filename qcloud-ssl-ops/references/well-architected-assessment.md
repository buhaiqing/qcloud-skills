# Well-Architected Assessment — SSL Certificate Service

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
