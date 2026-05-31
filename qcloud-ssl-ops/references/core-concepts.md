# Core Concepts — SSL Certificate Service

## Certificate Types

| Type | Description | Use Case |
|------|-------------|----------|
| DV (Domain Validation) | Validates domain ownership only | Basic HTTPS, personal sites |
| OV (Organization Validation) | Validates organization identity | Business websites |
| EV (Extended Validation) | Rigorous validation, green bar | Enterprise, e-commerce, finance |
| Wildcard | Secures domain + all subdomains | Sites with multiple subdomains |
| Multi-Domain (SAN) | Secures multiple domains in one cert | Single server serving multiple domains |
| Upload Certificate | Bring your own certificate | Migrating existing certificates |

## Certificate Status

| Status | Description |
|--------|-------------|
| 0 | Applying — certificate order created, awaiting verification |
| 1 | Issued — certificate issued and active |
| 2 | Valid — certificate is valid |
| 3 | Expired — certificate past validity period |
| 4 | Revoked — certificate revoked by CA |
| 5 | Rejected — certificate application rejected |
| 6 | Pending upload — waiting for certificate upload |

## Pricing Models

| Model | Description | Typical Cost |
|-------|-------------|--------------|
| Free DV | Basic domain validation, 1-year validity | Free (20 certs/account) |
| Paid DV | Enhanced support, multi-year options | ¥500-2000/year |
| OV SSL | Organization validation | ¥2000-5000/year |
| EV SSL | Extended validation | ¥5000-15000/year |
| Wildcard | Unlimited subdomains | ¥2000-10000/year |

## Resource Limits

| Resource | Limit |
|----------|-------|
| Free certificates per account | 20 |
| Total certificates per account | 500 |
| Domains per multi-domain cert | Up to 100 |
| Wildcard levels | 1 level (`*.example.com`) |
| Certificate file size | Max 20KB (PEM) |

## Deployment Targets

| Resource Type | Supported | Description |
|---------------|-----------|-------------|
| CDN | ✅ | Content Delivery Network |
| CLB | ✅ | Cloud Load Balancer |
| WAF | ✅ | Web Application Firewall |
| LIVE | ✅ | LVB (Live Video Broadcasting) |
| TEO | ✅ | Tencent EdgeOne |
| TKE | ✅ | Tencent Kubernetes Engine |
| API Gateway | ✅ | API Gateway |
| VOD | ✅ | Video on Demand |
| TCB | ✅ | Tencent CloudBase |

## Domain Verification Methods

| Method | Description | Steps |
|--------|-------------|-------|
| DNS | Add CNAME/TXT record to DNS | Add record → Wait propagation → Verify |
| File | Upload verification file to web server | Create file at `.well-known/pki-validation/` |
| DNS Auto | Automatic DNS record via DNSPod | Requires domain on DNSPod |

## Certificate Chain

- End-entity certificate (server cert)
- Intermediate CA certificate(s)
- Root CA certificate
- Complete chain required for browser trust
