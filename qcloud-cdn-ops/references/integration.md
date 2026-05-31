# CDN Integration

## Python SDK Setup

```bash
pip install tencentcloud-sdk-python-cdn
```

```python
from tencentcloud.common import credential
from tencentcloud.cdn.v20180606 import cdn_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = cdn_client.CdnClient(cred, "ap-guangzhou")
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TENCENTCLOUD_SECRET_ID` | Tencent Cloud Secret ID | Yes |
| `TENCENTCLOUD_SECRET_KEY` | Tencent Cloud Secret Key | Yes |
| `TENCENTCLOUD_REGION` | Region code | Yes |

## Cross-Skill Delegation

| CDN Scenario | Delegates To | Reason |
|-------------|-------------|--------|
| Origin is COS bucket | qcloud-cos-ops | COS bucket configuration, ACL, lifecycle |
| Origin is CVM | qcloud-cvm-ops | CVM health, security groups, performance |
| Origin is CLB | qcloud-clb-ops | CLB health checks, backend servers |
| HTTPS certificate | qcloud-cam-ops | Certificate upload to CAM, CertId management |
| Traffic anomalies | qcloud-aiops-diagnosis | Intelligent traffic pattern analysis |
| Architecture review | qcloud-well-architected-review | Multi-CDN, cache safety, HTTPS automation |
