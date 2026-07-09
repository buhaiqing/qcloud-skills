# VPN SecOps Security Operations

> VPN security operations checklist.

## Security Checklist

- [ ] Enable strong encryption (AES-256 or AES-128)
- [ ] Use IKEv2 instead of IKEv1 for better security
- [ ] Regular pre-shared key rotation (every 90 days)
- [ ] Access control via CAM (restrict VPN gateway operations)
- [ ] Audit log monitoring via CloudAudit/CLS
- [ ] Verify peer gateway IP is legitimate
- [ ] Enable perfect forward secrecy (PFS)

## IKE Policy Recommendations

| Parameter | Recommended Value |
|-----------|-------------------|
| Encryption | AES-256 |
| Authentication | SHA-256 |
| DH Group | Group 14 (2048-bit) |
| IKE Version | IKEv2 |

## See also
- [Core Concepts](core-concepts.md)
- [Troubleshooting](troubleshooting.md)
