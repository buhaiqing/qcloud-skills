# CLI Usage — tccli ssl

## Setup

```bash
# Verify CLI support
tccli ssl help

# List all actions
tccli ssl help | grep -E "^\s+[A-Z]"
```

## Command Map

| Operation | CLI Command | Description |
|-----------|-------------|-------------|
| List | `tccli ssl DescribeCertificates` | List all certificates |
| Detail | `tccli ssl DescribeCertificateDetail` | Get certificate details |
| Upload | `tccli ssl UploadCertificate` | Upload a certificate |
| Delete | `tccli ssl DeleteCertificate` | Delete a certificate |
| Deploy | `tccli ssl DeployCertificateInstance` | Deploy to cloud resource |
| Apply | `tccli ssl ApplyCertificate` | Apply for new certificate |
| Complete | `tccli ssl CompleteCertificate` | Complete domain verification |
| Rename | `tccli ssl ModifyCertificateAlias` | Modify certificate alias |
| Submit Info | `tccli ssl SubmitCertificateInfo` | Submit certificate info |

## Common Invocation Patterns

### List with search
```bash
tccli ssl DescribeCertificates --SearchKey "example.com" --Limit 20
```

### Get certificate details
```bash
tccli ssl DescribeCertificateDetail --CertificateId "xxxxx" | jq '.Response'
```

### Upload certificate from files (using shell)
```bash
tccli ssl UploadCertificate \
  --CertificatePublicKey "$(cat cert.pem)" \
  --CertificatePrivateKey "$(cat key.pem)" \
  --Alias "my-cert"
```

## Coverage Gaps

| Operation | CLI | SDK | Notes |
|-----------|-----|-----|-------|
| List certificates | ✅ | ✅ | Both paths work |
| Certificate details | ✅ | ✅ | Both paths work |
| Upload certificate | ✅ | ✅ | Both paths work |
| Delete certificate | ✅ | ✅ | Both paths work |
| Deploy certificate | ✅ | ✅ | Both paths work |
| Apply certificate | ✅ | ✅ | Both paths work |
| Complete verification | ✅ | ✅ | Both paths work |
| Modify alias | ✅ | ✅ | Both paths work |

CLI applicability: `dual-path` — CLI covers all major operations. SDK is fallback.
