# Integration — TencentDB for MongoDB

## Python SDK Setup

```bash
pip install tencentcloud-sdk-python-mongodb
```

Verify installation:
```bash
python3 -c "from tencentcloud.mongodb.v20190725 import mongodb_client; print('OK')"
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| TENCENTCLOUD_SECRET_ID | Yes | — | API key ID |
| TENCENTCLOUD_SECRET_KEY | Yes | — | API key secret |
| TENCENTCLOUD_REGION | Yes | — | Region (e.g. ap-guangzhou) |

## Cross-Skill Delegation Matrix

| If user asks about | Delegate to | Reason |
|-------------------|-------------|--------|
| App server connecting to MongoDB | `qcloud-cvm-ops` | CVM instance management |
| MongoDB in VPC/subnet | `qcloud-vpc-ops` | VPC/subnet/SG configuration |
| CAM permissions for MongoDB | `qcloud-cam-ops` | Policy and role management |
| MongoDB monitoring alarm | `qcloud-monitor-ops` | Alarm policy configuration |
| Store backup to COS | `qcloud-cos-ops` | Backup file download/storage |
| Ship audit logs to CLS | `qcloud-cls-ops` | Log shipping/delivery |

## CI/CD Integration Patterns

### Automated Backup Script

```python
#!/usr/bin/env python3
# Automated MongoDB backup with rotation
import os, json
from tencentcloud.common import credential
from tencentcloud.mongodb.v20190725 import mongodb_client, models

INSTANCE_ID = os.environ.get("MONGODB_INSTANCE_ID")
BACKUP_RETENTION = int(os.environ.get("BACKUP_RETENTION_DAYS", "7"))

def create_backup():
    cred = credential.Credential(
        os.environ.get("TENCENTCLOUD_SECRET_ID"),
        os.environ.get("TENCENTCLOUD_SECRET_KEY")
    )
    client = mongodb_client.MongodbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

    req = models.CreateBackupDBInstanceRequest()
    req.InstanceId = INSTANCE_ID
    resp = client.CreateBackupDBInstance(req)
    print(f"Backup created: {resp.to_json_string()}")

if __name__ == "__main__":
    create_backup()
```

### Spec Change Automation

```bash
#!/bin/bash
# Scale MongoDB instance based on monitoring alert
INSTANCE_ID="$1"
NEW_MEMORY="$2"
NEW_VOLUME="$3"

# Price check first
PRICE=$(tccli mongodb InquirePriceModifyDBInstanceSpec \
  --InstanceId "$INSTANCE_ID" \
  --Memory "$NEW_MEMORY" \
  --Volume "$NEW_VOLUME" \
  | jq -r '.Response.OriginalPrice')

echo "Price: $PRICE CNY"
read -p "Confirm? (y/n): " CONFIRM
[ "$CONFIRM" != "y" ] && exit 1

# Execute modify
tccli mongodb ModifyDBInstanceSpec \
  --InstanceId "$INSTANCE_ID" \
  --Memory "$NEW_MEMORY" \
  --Volume "$NEW_VOLUME"
```

### Multi-Instance Status Check

```python
#!/usr/bin/env python3
# Health check for all MongoDB instances
import os, json, sys
from tencentcloud.common import credential
from tencentcloud.mongodb.v20190725 import mongodb_client, models

cred = credential.Credential(
    os.environ.get("TENCENTCLOUD_SECRET_ID"),
    os.environ.get("TENCENTCLOUD_SECRET_KEY")
)
client = mongodb_client.MongodbClient(cred, os.environ.get("TENCENTCLOUD_REGION"))

req = models.DescribeDBInstancesRequest()
req.Limit = 100
resp = client.DescribeDBInstances(req)

details = json.loads(resp.to_json_string())
healthy = True
for inst in details.get("InstanceDetails", []):
    name = inst.get("InstanceName", "unknown")
    status = inst.get("Status", -1)
    if status != 2:
        print(f"⚠️  {name}: status={status} (not running)")
        healthy = False
    else:
        print(f"✅ {name}: running")

sys.exit(0 if healthy else 1)
```
