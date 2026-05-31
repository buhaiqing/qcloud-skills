# Troubleshooting — SSL Certificate Service

## Error Code Reference

| Error Code | Meaning | Recovery |
|------------|---------|----------|
| InvalidParameter.InvalidCertificate | 证书内容无效 | Verify PEM format; check certificate validity |
| InvalidParameter.InvalidPrivateKey | 私钥内容无效 | Check private key is valid PEM format |
| InvalidParameter.CertificateNotMatch | 证书和私钥不匹配 | Ensure public/private key pair matches |
| LimitExceeded | 证书数量超限 | Delete unused certificates |
| AuthFailure | CAM鉴权错误 | HALT; check credentials |
| FailedOperation.CertificateNotFound | 证书不存在 | Verify certificate ID |
| InvalidParameter.DuplicateCertificate | 证书已存在 | Certificate with same content already uploaded |
| InvalidParameter.CertificateExpired | 证书已过期 | Renew or upload new certificate |
| FailedOperation.DomainVerificationFailed | 域名验证失败 | Check DNS record or verification file |
| InvalidParameter.DvAuthFail | 域名验证不通过 | Try alternative verification method |
| RequestLimitExceeded | 请求频率过高 | Retry with backoff |
| InternalError | 内部错误 | Retry; if persistent contact support |

## Diagnostic Workflows

### Certificate Upload Fails

1. Verify certificate file is valid PEM format:
   ```bash
   openssl x509 -in cert.pem -text -noout
   ```
2. Verify private key is valid:
   ```bash
   openssl rsa -in key.pem -check
   ```
3. Verify key pair matches:
   ```bash
   # Compare modulus from certificate and key
   openssl x509 -in cert.pem -noout -modulus | md5sum
   openssl rsa -in key.pem -noout -modulus | md5sum
   ```
4. Check certificate chain completeness

### Domain Verification Fails

1. **DNS method**: Verify DNS record is propagated:
   ```bash
   dig CNAME _dnsauth.{{domain}}
   dig TXT {{domain}}
   ```
2. **File method**: Verify file is accessible:
   ```bash
   curl -I http://{{domain}}/.well-known/pki-validation/{{filename}}.txt
   ```
3. Check TTL — may need to wait for propagation (up to 24h)
4. Try alternative verification method

### Certificate Deployment Fails

1. Verify certificate is issued (status=1) and not expired
2. Check target resource exists and is in active state
3. Verify target resource supports certificate type
4. For CLB: ensure listener is HTTPS type
5. For CDN: ensure domain is correctly configured

### Certificate Not Found

1. List all certificates to verify:
   ```bash
   tccli ssl DescribeCertificates --Limit 100
   ```
2. Search by domain or alias
3. Check if certificate was deleted

## Multi-round Diagnostics

```
Issue reported → "Can't deploy certificate instance-xxx"
  ├─ Certificate exists? (DescribeCertificateDetail)
  │  ├─ NO → HALT; verify certificate ID
  │  └─ YES → Continue
  ├─ Certificate expired? (check CertEndTime)
  │  ├─ YES → Renew or upload new cert
  │  └─ NO → Continue
  ├─ Target resource exists? (check resource type)
  │  ├─ NO → HALT; ask user to create resource first
  │  └─ YES → Continue
  └─ Try deploy again → report result
```
