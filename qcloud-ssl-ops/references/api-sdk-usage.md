# API & SDK Usage — SSL Certificate Service

## API Version

- **API version:** `2019-12-05`
- **API spec:** https://cloud.tencent.com/document/api/400
- **SDK package:** `tencentcloud-sdk-python` (general)

## Operation Map

| Category | API Action | CLI Command | Description |
|----------|-----------|-------------|-------------|
| Certificate | UploadCertificate | ssl UploadCertificate | Upload external certificate |
| Certificate | DescribeCertificates | ssl DescribeCertificates | List certificates |
| Certificate | DescribeCertificateDetail | ssl DescribeCertificateDetail | Get certificate details |
| Certificate | DeleteCertificate | ssl DeleteCertificate | Delete certificate |
| Certificate | ModifyCertificateAlias | ssl ModifyCertificateAlias | Rename certificate |
| Certificate | SubmitCertificateInfo | ssl SubmitCertificateInfo | Submit info for paid cert |
| Deploy | DeployCertificateInstance | ssl DeployCertificateInstance | Deploy to cloud resource |
| Apply | ApplyCertificate | ssl ApplyCertificate | Apply for new certificate |
| Verify | CompleteCertificate | ssl CompleteCertificate | Complete domain verification |
| Download | DescribeCertificateDetail | ssl DescribeCertificateDetail | Get cert details + download URL |
| Monitor | DescribeCertificates | ssl DescribeCertificates | List with expiry filters |

## Python SDK Examples

### Setup

```python
import os
from tencentcloud.common import credential
from tencentcloud.ssl.v20191205 import ssl_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
# SSL service is global — region can be empty
client = ssl_client.SslClient(cred, "")
```

### List Certificates

```python
def list_certificates(search_key=None):
    req = models.DescribeCertificatesRequest()
    req.Limit = 20
    if search_key:
        req.SearchKey = search_key
    resp = client.DescribeCertificates(req)
    return resp.to_json_string()
```

### Upload Certificate

```python
def upload_certificate(pub_key_path, priv_key_path, alias):
    with open(pub_key_path, 'r') as f:
        pub_key = f.read()
    with open(priv_key_path, 'r') as f:
        priv_key = f.read()

    req = models.UploadCertificateRequest()
    req.CertificatePublicKey = pub_key
    req.CertificatePrivateKey = priv_key
    req.Alias = alias
    req.CertificateType = "CA"
    resp = client.UploadCertificate(req)
    return resp.to_json_string()
```

### Error Handling

```python
try:
    req = models.DescribeCertificatesRequest()
    resp = client.DescribeCertificates(req)
    print(resp.to_json_string())
except TencentCloudSDKException as err:
    print(f"[ERROR] Code={err.get_code()}, Message={err.get_message()}")
```

## Pagination

Use `Limit` and `Offset` for pagination:

```bash
tccli ssl DescribeCertificates --Limit 20 --Offset 0
tccli ssl DescribeCertificates --Limit 20 --Offset 20
```

Max `Limit` value: 100 per request.
