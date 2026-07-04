# SSL Certificate Service — Python SDK Code Examples

This file contains all Python SDK code examples extracted from the main `SKILL.md` for reference.

## Upload Certificate

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

## List Certificates

```python
req = models.DescribeCertificatesRequest()
req.Limit = 20
resp = client.DescribeCertificates(req)
print(json.dumps(resp.to_json_string(), indent=2))
```

## Describe Certificate Detail

```python
req = models.DescribeCertificateDetailRequest()
req.CertificateId = "{{user.certificate_id}}"
resp = client.DescribeCertificateDetail(req)
print(json.dumps(resp.to_json_string(), indent=2))
```
