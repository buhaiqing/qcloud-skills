# COS Integration Guide

## SDK Setup

```bash
pip install tencentcloud-sdk-python-cos
pip install coscmd
```

## Environment

```bash
export TENCENTCLOUD_SECRET_ID="AKID..."
export TENCENTCLOUD_SECRET_KEY="..."
export TENCENTCLOUD_REGION="ap-guangzhou"
```

## SDK Usage

```python
from qcloud_cos import CosConfig, CosS3Client

config = CosConfig(
    Region="ap-guangzhou",
    SecretId=secret_id,
    SecretKey=secret_key,
)
client = CosS3Client(config)
resp = client.create_bucket(Bucket="my-bucket")
```

## Cross-Skill Delegation

| From COS | To Skill | Context |
|----------|----------|---------|
| Static website | qcloud-cdn-ops | CDN acceleration |
| Backup storage | qcloud-cdb-ops | Database backup |

## References

- [COS SDK](https://cloud.tencent.com/document/sdk/Python)