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
from tencentcloud.cos import cos_client, models

client = cos_client.CosClient(cred, "ap-guangzhou")
req = models.PutBucketRequest()
req.Bucket = "my-bucket"
resp = client.PutBucket(req)
```

## Cross-Skill Delegation

| From COS | To Skill | Context |
|----------|----------|---------|
| Static website | qcloud-cdn-ops | CDN acceleration |
| Backup storage | qcloud-mysql-ops | Database backup |

## References

- [COS SDK](https://cloud.tencent.com/document/sdk/Python)