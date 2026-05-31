# Integration — SSL Certificate Service

## SDK Setup

### Install Python SDK

```bash
pip install tencentcloud-sdk-python
```

### Verify SDK Installation

```python
from tencentcloud.ssl.v20191205 import ssl_client
import importlib
importlib.metadata.version("tencentcloud-sdk-python")
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API Secret ID (AKID...) |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API Secret Key |

> SSL Certificate Service is a global service — `TENCENTCLOUD_REGION` is not required.
> **NEVER** collect `{{env.*}}` values from the user. Fail with clear error if unset.

## Dependency Configuration

```txt
# requirements.txt
tencentcloud-sdk-python>=3.0.0
jq>=1.0.0
openssl  # for certificate validation
```

## Cross-Skill Delegation Matrix

| Scenario | Delegate To | Reason |
|----------|-------------|--------|
| Deploy to CDN | `qcloud-cdn-ops` | CDN certificate binding |
| Deploy to CLB | `qcloud-clb-ops` | CLB HTTPS listener config |
| CAM policy configuration | `qcloud-cam-ops` | Access control |
| Monitoring alarms | `qcloud-monitor-ops` | Alarm policy management |
| DNS record management | `qcloud-vpc-ops` or external DNS | Domain verification |

## Testing Connectivity

### From CLI

```bash
tccli ssl DescribeCertificates --Limit 5
```

### From Python

```python
import os
from tencentcloud.common import credential
from tencentcloud.ssl.v20191205 import ssl_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = ssl_client.SslClient(cred, "")

req = models.DescribeCertificatesRequest()
req.Limit = 5
resp = client.DescribeCertificates(req)
print("[OK] Connected. Found {} certificates.".format(len(resp.Certificates or [])))
```

## Credential Security

- **NEVER** log `TENCENTCLOUD_SECRET_KEY`, `PrivateKey`, or any credential value
- Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"`
- Use minimal CAM policies for automated operations
- Rotate keys regularly via CAM console
- Certificate private keys should be handled as sensitive data (mask in logs, never echo)
