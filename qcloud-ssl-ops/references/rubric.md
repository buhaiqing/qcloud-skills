# SSL Quality-Gate Rubric (GCL)

> Runtime rubric for **Generator-Critic-Loop (GCL)** of `qcloud-ssl-ops`.
> See [`qcloud-clb-ops/references/rubric.md`](../clb-ops/references/rubric.md) for the backbone.

---

## 4. SSL-specific safety rules

| # | Operation | Rule | Rationale |
|---|---|---|---|
| 1 | `DeleteCertificate` (any; especially if deployed) | **Certificate ID + name + domain + issuer + deploy status echo; check if cert is deployed to any resource (CLB, CDN, API GW, etc.) via `DescribeCertificateDeploy`; warn that deletion will cause HTTPS errors on ALL deployed resources; require literal "CONFIRM DELETE CERT <cert_name>"** | Deleting a certificate that is actively deployed breaks HTTPS on all resources using it. The most common SSL incident: "I deleted the old expired cert but the CLB was still using it for SNI — the HTTPS handshake failed for a week" |
| 2 | `DeployCertificateInstance` (deploy to specific resource type: CLB, CDN, API GW, TKE) | **Show certificate domain + resource type + resource ID + resource region; warn that deploying replaces the existing certificate on the target resource; surface the current certificate's name and expiration on the resource; require explicit confirmation with resource ID** | Deploying a cert to the wrong resource silently replaces the existing cert. The most common incident: "I deployed the staging cert to the production CLB because they had similar names — HTTPS users saw the wrong certificate for 2 hours" |
| 3 | `ReplaceCertificate` / `CertificateRollback` (replace in-place on a resource) | **Show old cert domain + expiration → new cert domain + expiration; warn that the replacement is immediate — there is no grace period for DNS propagation; if the new cert's domain does not match the resource's DNS name: warn that HTTPS clients will see hostname mismatch errors; require confirmation** | Certificate replacement is instant but DNS/TLS client caching may cause issues. The most common incident: "I tried to replace the cert before the old one expired but the new cert had a different SAN — all Android clients got SSL errors" |
| 4 | `ApplyCertificate` (apply for a new DV/OV/EV cert; includes `ApplyCertificatePackage`) | **Show domain name(s), validation method (DNS / HTTP), and certificate type (DV/OV/EV); warn that DV certificates take 5-30 minutes and OV/EV take 1-3 business days; for DNS validation: warn that the user must add a CNAME to their DNS provider; require confirmation that the user has DNS write access** | Applying for a cert without DNS write access causes the validation to fail silently. The most common pattern: "I applied for a DV cert for `*.example.com` but forgot that the DNS zone was managed by another team — the cert was stuck in 'pending' for 3 days" |
| 5 | `UploadCertificate` (upload PEM / PKCS12 / SSL certificate with private key) | **Show certificate subject, issuer, valid-from, valid-to, SAN count; warn if the certificate chain is incomplete (missing intermediate CA); warn if the private key password (for PKCS12) is not provided; warn if the cert's private key size < 2048 bits (insecure); require confirmation** | Uploading a cert with an incomplete chain causes "incomplete chain" errors on all resources using it. The most common incident: "I uploaded the LE-issued cert without the intermediate CA and the CLB rejected it because it could not build the trust path" |

---

## 7. Changelog

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-06-04 | Phase 1 SSL rollout: rubric (5 rules: cert-deletion with deployed resources, wrong-resource deploy, certificate replacement hostname mismatch, cert-apply DNS validation readiness, upload incomplete chain) |