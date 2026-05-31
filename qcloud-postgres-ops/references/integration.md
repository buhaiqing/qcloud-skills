# Integration — TencentDB for PostgreSQL

## SDK Setup

### Install Python SDK

```bash
pip install tencentcloud-sdk-python
```

### Verify SDK Installation

```python
from tencentcloud.postgres.v20170312 import postgres_client
import importlib
importlib.metadata.version("tencentcloud-sdk-python")
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TENCENTCLOUD_SECRET_ID` | Yes | API Secret ID (AKID...) |
| `TENCENTCLOUD_SECRET_KEY` | Yes | API Secret Key |
| `TENCENTCLOUD_REGION` | Yes | Region (e.g. ap-guangzhou) |

> **NEVER** collect `{{env.*}}` values from the user. Fail with clear error if unset.

## Dependency Configuration

### Python Dependencies

```txt
# requirements.txt
tencentcloud-sdk-python>=3.0.0
jq>=1.0.0
```

### CLI Dependencies

```bash
# Install tccli
pip install tccli

# Verify
tccli --version
```

## Cross-Skill Delegation Matrix

| Scenario | Delegate To | Reason |
|----------|-------------|--------|
| VPC/subnet creation | `qcloud-vpc-ops` | PostgreSQL requires VPC |
| CAM policy configuration | `qcloud-cam-ops` | Access control |
| Monitoring alarms | `qcloud-monitor-ops` | Alarm policy management |
| SSL certificate management | `qcloud-ssl-ops` | Certificate lifecycle |
| Backup storage (COS) | `qcloud-cos-ops` | Cross-region backup storage |
| Security group modification | `qcloud-vpc-ops` | Network security |

## Testing Connectivity

### From CLI

```bash
tccli postgres DescribeDBInstances --Limit 5
```

### From Python

```python
import os
from tencentcloud.common import credential
from tencentcloud.postgres.v20170312 import postgres_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = postgres_client.PostgresClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DescribeDBInstancesRequest()
req.Limit = 5
resp = client.DescribeDBInstances(req)
print("[OK] Connected. Found {} instances.".format(len(resp.DBInstanceSet or [])))
```

## Credential Security

- **NEVER** log `TENCENTCLOUD_SECRET_KEY` or any credential value
- Check existence only: `test -n "$TENCENTCLOUD_SECRET_KEY"`
- Use minimal CAM policies for automated operations
- Rotate keys regularly via CAM console
